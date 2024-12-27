from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
import os

class kvConfig(BaseModel):
    """KV connection settings"""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        frozen=True
    )
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    tls: bool = Field(default=False)
    db: int = Field(default=0)
    password: Optional[str] = Field(default=None)
    ttl: int = Field(default=60)  # Cache TTL in seconds
    socket_timeout: int = Field(default=1)
    socket_connect_timeout: int = Field(default=1)

class RateLimits(BaseModel):
    """Rate limiting configuration"""
    model_config = ConfigDict(frozen=True)
    global_rate: int = Field(default=500, description="Requests per second globally")
    ip_rate: int = Field(default=50, description="Requests per second per IP")
    daily: int = Field(default=10000, description="Daily requests per IP")
    weekly: int = Field(default=50000, description="Weekly requests per IP")
    monthly: int = Field(default=150000, description="Monthly requests per IP")

class Settings(BaseModel):
    """Main application settings"""

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        env_prefix="HTML2MD_",
        case_sensitive=False
    )

    host: str = Field(default="0.0.0.0")
    port: int = Field(default=9000)
    debug: bool = Field(default=False)


    max_content_size: int = Field(
        default=5 * 1024 * 1024,  # 5MB
        description="Maximum size of content to process"
    )
    request_timeout: int = Field(default=10)


    allowed_origins: List[str] = Field(default=["*"])
    allowed_ips: List[str] = Field(
        default_factory=lambda: os.getenv("ALLOWED_IPS", "*").split(",")
    )

    static_dir: Optional[str] = Field(
        default="static",
        description="Directory for static files, None to disable"
    )
    cache_backend: Optional[Any] = Field(default=None)
    rate_limiter: Optional[Any] = Field(default=None)
    rate_limits: Optional[RateLimits] = Field(default=None)

    log_level: str = Field(default="INFO")
    log_format: str = Field(
        default="%(asctime)s - %(levelname)s - %(message)s"
    )

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings from environment variables"""
        return cls()
