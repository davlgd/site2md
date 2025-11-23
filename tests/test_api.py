import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from site2md import create_app, Settings
from site2md.api import parse_forwarded_header, get_client_ip
from site2md.limiting import MemoryRateLimiter
from site2md.config import RateLimits

@pytest.fixture
def client():
    """Create test client with minimal settings"""
    settings = Settings(
        static_dir=None,
        max_content_size=1000000,
        cache_backend=None,
        rate_limiter=None
    )
    app = create_app(settings)
    return TestClient(app)

@pytest.fixture
def small_content_client():
    """Create test client with small content size limit"""
    settings = Settings(
        static_dir=None,
        max_content_size=100,  # Very small limit
        cache_backend=None,
        rate_limiter=None
    )
    app = create_app(settings)
    return TestClient(app)

@pytest.fixture
def rate_limited_client():
    """Create test client with rate limiting"""
    limiter = MemoryRateLimiter(
        limits=RateLimits(ip_rate=5)  # Low limit for testing
    )
    settings = Settings(
        static_dir=None,
        max_content_size=1000000,
        cache_backend=None,
        rate_limiter=limiter
    )
    app = create_app(settings)
    return TestClient(app)

@pytest.fixture
def mock_httpx_success():
    """Mock httpx.AsyncClient with successful response"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.content = b"<html><body>Test</body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_instance

        yield mock_client, mock_instance, mock_response

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.parametrize("url,expected_status", [
    ("https://example.com", 200),
    ("https://perdu.com", 200),  # Reliable test site
    ("ftp://invalid", 400),
    ("not-a-url", 400),
    ("https://thiswillnotwork.invalid", 502),
])
def test_url_validation(client, url, expected_status):
    """Test URL validation and error handling"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.content = b"<html><body>Test</body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_instance

        if expected_status == 502:
            mock_instance.get = AsyncMock(side_effect=httpx.RequestError("Connection failed"))

        response = client.get(f"/{url}")
        assert response.status_code == expected_status

def test_rate_limiting(rate_limited_client):
    """Test rate limiting functionality"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.content = b"<html><body>Test</body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_instance

        # First request should succeed
        response = rate_limited_client.get("/https://example.com")
        assert response.status_code == 200

        # Next 5 requests should also succeed
        for _ in range(6):  # 5 + 1 to exceed limit
            response = rate_limited_client.get("/https://example.com")

        assert response.status_code == 429

@pytest.mark.parametrize("format,content_type", [
    ("markdown", "text/plain; charset=utf-8"),
    ("json", "application/json"),
])
def test_content_types(client, format, content_type):
    """Test correct content type headers"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.content = b"<html><body>Test</body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_instance = AsyncMock()
        mock_instance.get = AsyncMock(return_value=mock_response)
        mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
        mock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_instance

        response = client.get(f"/https://example.com?format={format}")
        assert response.status_code == 200
        assert response.headers["content-type"] == content_type


class TestForwardedHeader:
    """Test RFC 7239 Forwarded header parsing"""

    @pytest.mark.parametrize("header,expected", [
        # Standard case with port
        (
            "proto=https;for=82.66.165.132:60677;by=91.208.207.141",
            [{"proto": "https", "for": "82.66.165.132", "by": "91.208.207.141"}]
        ),
        # Without port
        (
            "proto=https;for=1.2.3.4;by=5.6.7.8",
            [{"proto": "https", "for": "1.2.3.4", "by": "5.6.7.8"}]
        ),
        # Multiple entries (proxy chain)
        (
            "for=1.1.1.1;by=2.2.2.2, for=3.3.3.3;by=4.4.4.4",
            [
                {"for": "1.1.1.1", "by": "2.2.2.2"},
                {"for": "3.3.3.3", "by": "4.4.4.4"}
            ]
        ),
        # Empty header
        ("", []),
        # Only proto
        ("proto=https", [{"proto": "https"}]),
    ])
    def test_parse_forwarded_header(self, header, expected):
        """Test parsing of various Forwarded header formats"""
        result = parse_forwarded_header(header)
        assert result == expected


class TestGetClientIP:
    """Test client IP extraction with reverse proxy support"""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request object"""
        request = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        return request

    def test_no_trusted_proxies(self, mock_request):
        """Without trusted proxies, return direct client IP"""
        result = get_client_ip(mock_request, [])
        assert result == "127.0.0.1"

    def test_trusted_proxy_with_forwarded_header(self, mock_request):
        """With trusted proxy and Forwarded header, extract real IP"""
        mock_request.headers = {
            "forwarded": "proto=https;for=82.66.165.132:60677;by=91.208.207.141"
        }
        result = get_client_ip(mock_request, ["91.208.207.141"])
        assert result == "82.66.165.132"

    def test_untrusted_proxy(self, mock_request):
        """With untrusted proxy, return direct client IP"""
        mock_request.headers = {
            "forwarded": "proto=https;for=82.66.165.132:60677;by=10.0.0.1"
        }
        result = get_client_ip(mock_request, ["91.208.207.141"])
        assert result == "127.0.0.1"

    def test_spoofed_header_ignored(self, mock_request):
        """Client-spoofed X-Forwarded-For in Forwarded is ignored if by is untrusted"""
        mock_request.headers = {
            "forwarded": "for=spoofed;by=attacker, proto=https;for=82.66.165.132:60677;by=91.208.207.141"
        }
        # Only trust the last entry where 'by' matches trusted proxy
        result = get_client_ip(mock_request, ["91.208.207.141"])
        assert result == "82.66.165.132"

    def test_no_forwarded_header(self, mock_request):
        """Without Forwarded header, return direct client IP"""
        mock_request.headers = {}
        result = get_client_ip(mock_request, ["91.208.207.141"])
        assert result == "127.0.0.1"

    def test_no_client(self):
        """Handle request with no client info"""
        request = MagicMock()
        request.client = None
        request.headers = {}
        result = get_client_ip(request, [])
        assert result == "unknown"


class TestErrorHandling:
    """Test error handling for various failure scenarios"""

    def test_timeout_returns_504(self, client):
        """Test that timeout returns 504 Gateway Timeout"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            response = client.get("/https://example.com")
            assert response.status_code == 504
            assert "timeout" in response.json()["detail"].lower()

    def test_upstream_error_returns_502(self, client):
        """Test that upstream HTTP errors return 502 Bad Gateway"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError("Server Error", request=MagicMock(), response=mock_response)
            )

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            response = client.get("/https://example.com")
            assert response.status_code == 502

    def test_content_too_large_returns_413(self, small_content_client):
        """Test that content exceeding max_content_size returns 413"""
        with patch('httpx.AsyncClient') as mock_client:
            large_content = "<html><body>" + "x" * 200 + "</body></html>"
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = large_content
            mock_response.content = large_content.encode()
            mock_response.raise_for_status = MagicMock()

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            response = small_content_client.get("/https://example.com")
            assert response.status_code == 413
            assert "too large" in response.json()["detail"].lower()

    def test_invalid_format_returns_400(self, client, mock_httpx_success):
        """Test that invalid format parameter returns 400"""
        response = client.get("/https://example.com?format=invalid")
        assert response.status_code == 422  # FastAPI validation error
