import os
import json
import hashlib
import requests

from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from site2md.config import Settings
from site2md.converter import extract_content
from site2md.logging import logger
from urllib.parse import urlparse, unquote

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
    async def convert(url: str, request: Request, format: str = "markdown") -> Response:
        """Convert webpage to markdown or JSON

        Fetches a webpage and converts it to markdown or JSON format,
        with optional caching and rate limiting.

        Args:
            url: URL to convert
            request: FastAPI request object
            format: Output format ("markdown" or "json")

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
            settings.rate_limiter.check_limits(request.client.host)

        wants_json = format.lower() == "json"
        try:
            url = clean_url(url)
            cache_key = f"{hashlib.md5(url.encode()).hexdigest()}:{format}"

            if settings.cache_backend and (cached := settings.cache_backend.get(cache_key)):
                return JSONResponse(json.loads(cached)) if wants_json else Response(cached, media_type="text/plain")

            response = requests.get(url, timeout=settings.request_timeout)
            response.raise_for_status()

            if len(response.content) > settings.max_content_size:
                raise HTTPException(status_code=413, detail="Content too large")

            result = extract_content(response.text, wants_json)
            if not result:
                return JSONResponse({}) if wants_json else Response("")

            if settings.cache_backend:
                settings.cache_backend.set(cache_key, json.dumps(result) if wants_json else result)

            return JSONResponse(result) if wants_json else Response(result, media_type="text/plain")

        except requests.Timeout:
            raise HTTPException(status_code=504, detail="Request timeout")
        except requests.RequestException as e:
            raise HTTPException(status_code=502, detail=str(e))
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app
