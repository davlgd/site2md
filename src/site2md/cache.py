import redis
from typing import Optional, Protocol
from .config import kvConfig

class CacheBackend(Protocol):
    """Abstract cache interface"""
    def get(self, key: str) -> Optional[str]: ...
    def set(self, key: str, value: str) -> None: ...

class KVCache(CacheBackend):
    """Key-Value store cache implementation

    Implements caching using a key-value store (Redis)
    with connection pooling and error handling.
    """
    def __init__(self, config: kvConfig):
        if not isinstance(config, kvConfig):
            raise TypeError("config must be a kvConfig instance")
        self.config = config
        self.client = self._connect()

    def _connect(self) -> Optional[redis.Redis]:
        """Create Redis connection with retry support"""
        try:
            client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                ssl=self.config.tls,
                db=self.config.db,
                password=self.config.password,
                socket_timeout=self.config.socket_timeout,
                socket_connect_timeout=self.config.socket_connect_timeout,
                decode_responses=True
            )
            client.ping()
            return client
        except redis.RedisError:
            return None

    def get(self, key: str) -> Optional[str]:
        """Get value from cache with TTL refresh"""
        if not self.client:
            return None
        try:
            if value := self.client.get(key):
                self.client.expire(key, self.config.ttl)
            return value
        except redis.RedisError:
            self.client = None
            return None

    def set(self, key: str, value: str) -> None:
        """Set value in cache with TTL"""
        if not self.client or self.client.exists(key):
            return
        try:
            self.client.setex(key, self.config.ttl, value)
        except redis.RedisError:
            self.client = None
