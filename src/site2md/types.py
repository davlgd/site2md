from typing import Protocol, Optional

class CacheBackend(Protocol):
    """Protocol for cache implementations"""
    def get(self, key: str) -> Optional[str]: ...
    def set(self, key: str, value: str) -> None: ...

class RateLimiter(Protocol):
    """Protocol for rate limiting implementations"""
    def check_limits(self, ip: str) -> None: ...
