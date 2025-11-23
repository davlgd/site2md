import os
import json
import hashlib
import httpx
from enum import Enum

from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from site2md.config import Settings
from site2md.converter import extract_content
from site2md.logging import logger
from urllib.parse import urlparse, unquote


class OutputFormat(str, Enum):
    """Supported output formats"""
    MARKDOWN = "markdown"
    JSON = "json"


def parse_forwarded_header(header: str) -> list[dict[str, str]]:
    """Parse RFC 7239 Forwarded header into list of directive dicts

    Example: "proto=https;for=1.2.3.4:1234;by=5.6.7.8"
    Returns: [{"proto": "https", "for": "1.2.3.4", "by": "5.6.7.8"}]
    """
    entries = []
    for entry in header.split(","):
        directives = {}
        for part in entry.strip().split(";"):
            if "=" in part:
                key, value = part.split("=", 1)
                # Extract IP without port (for=1.2.3.4:1234 -> 1.2.3.4)
                if ":" in value and key.strip().lower() in ("for", "by"):
                    value = value.rsplit(":", 1)[0]
                directives[key.strip().lower()] = value.strip()
        if directives:
            entries.append(directives)
    return entries


def get_client_ip(request: Request, trusted_proxies: list[str]) -> str:
    """Extract real client IP from request, handling reverse proxies

    Uses the RFC 7239 Forwarded header for security. Only trusts the client IP
    if the 'by' directive matches a trusted proxy IP.

    Args:
        request: FastAPI request object
        trusted_proxies: List of trusted proxy IP addresses

    Returns:
        str: The real client IP address
    """
    client_ip = request.client.host if request.client else "unknown"

    # If no trusted proxies configured, return direct IP
    if not trusted_proxies:
        return client_ip

    # Parse Forwarded header (RFC 7239)
    forwarded = request.headers.get("forwarded", "")
    if forwarded:
        entries = parse_forwarded_header(forwarded)
        # Check last entry (closest proxy to our app)
        if entries:
            last_entry = entries[-1]
            proxy_ip = last_entry.get("by", "")
            if proxy_ip in trusted_proxies:
                # Trusted proxy, use the 'for' IP
                return last_entry.get("for", client_ip)

    return client_ip


def clean_url(url: str) -> str:
    """Clean and validate URL

    Args:
        url: URL to clean and validate

    Returns:
        str: Cleaned URL

    Raises:
        ValueError: If URL is invalid or not HTTP(S)
    """
    url = unquote(url)
    parsed = urlparse(url)

    if not (parsed.scheme and parsed.netloc):
        raise ValueError("Invalid URL format")
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("Only HTTP(S) URLs are supported")

    return url

def create_app(settings: Settings) -> FastAPI:
    """Create FastAPI application with settings

    Creates and configures a FastAPI application with the given settings,
    including static files, CORS, rate limiting and caching.

    Args:
        settings: Application settings

    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI()
    app.state.settings = settings

    if settings.static_dir:
        try:
            open(f"{settings.static_dir}/index.html")
            app.mount("/static", StaticFiles(directory=settings.static_dir))
        except FileNotFoundError:
            logger.warning("Static directory not found, disabling")
            settings.static_dir = None

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET"],
        allow_headers=["*"]
    )

    @app.get("/")
    async def root() -> FileResponse:
        if not settings.static_dir:
            return Response("No static directory configured", status_code=404)
        return FileResponse(f"{settings.static_dir}/index.html")

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.get("/{url:path}")
    async def convert(url: str, request: Request, format: OutputFormat = OutputFormat.MARKDOWN) -> Response:
        """Convert webpage to markdown or JSON

        Fetches a webpage and converts it to markdown or JSON format,
        with optional caching and rate limiting.

        Args:
            url: URL to convert
            request: FastAPI request object
            format: Output format (markdown or json)

        Returns:
            Response: Converted content

        Raises:
            HTTPException: On various error conditions
        """
        if url == "favicon.ico":
            if settings.static_dir:
                favicon_path = f"{settings.static_dir}/favicon.ico"
                if os.path.exists(favicon_path):
                    return FileResponse(favicon_path)
                else:
                    raise HTTPException(status_code=404, detail="Favicon not found")

        if settings.rate_limiter:
            client_ip = get_client_ip(request, settings.trusted_proxies)
            settings.rate_limiter.check_limits(client_ip)

        wants_json = format == OutputFormat.JSON
        try:
            url = clean_url(url)
            cache_key = f"{hashlib.md5(url.encode()).hexdigest()}:{format.value}"

            if settings.cache_backend and (cached := settings.cache_backend.get(cache_key)):
                return JSONResponse(json.loads(cached)) if wants_json else Response(cached, media_type="text/plain")

            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                response = await client.get(url)
                response.raise_for_status()

            if len(response.content) > settings.max_content_size:
                raise HTTPException(status_code=413, detail="Content too large")

            result = extract_content(response.text, wants_json)
            if not result:
                return JSONResponse({}) if wants_json else Response("")

            if settings.cache_backend:
                settings.cache_backend.set(cache_key, json.dumps(result) if wants_json else result)

            return JSONResponse(result) if wants_json else Response(result, media_type="text/plain")

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request timeout")
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=502, detail=f"Upstream error: {e.response.status_code}")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            logger.exception("Unexpected error during conversion")
            raise HTTPException(status_code=500, detail="Internal server error")

    return app
