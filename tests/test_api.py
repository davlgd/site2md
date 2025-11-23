import pytest
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient
from site2md import create_app, Settings
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
