import uvicorn
from site2md import create_app, Settings

if __name__ == "__main__":
    settings = Settings(
        static_dir=None,
    )

    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port)
