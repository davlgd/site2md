import os
import uvicorn
from site2md import create_app, Settings
from site2md.cache import KVCache
from site2md.config import kvConfig

if __name__ == "__main__":
    kv_config = kvConfig(
        host="materiakv.eu-fr-1.services.clever-cloud.com",
        port=6379,
        tls=True,
        db=0,
        password=os.getenv("KV_TOKEN"),
        ttl=3600,
        socket_timeout=1,
        socket_connect_timeout=1
    )

    cache = KVCache(config=kv_config)

    settings = Settings(
        static_dir=None,
        max_content_size=2_000_000,
        cache_backend=cache,
        rate_limiter=None
    )
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port)
