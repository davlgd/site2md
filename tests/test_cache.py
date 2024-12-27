import pytest
import redis
import time

from site2md.cache import KVCache
from site2md.config import kvConfig

@pytest.fixture
def kv_config():
    """Basic KV store configuration"""
    return kvConfig(
        host="localhost",
        port=6379,
        ttl=2
    )

def is_kv_available(config: kvConfig) -> bool:
    """Check if KV store is available"""
    try:
        client = redis.Redis(
            host=config.host,
            port=config.port,
            socket_timeout=1,
            socket_connect_timeout=1
        )
        return client.ping()
    except (redis.ConnectionError, redis.TimeoutError):
        return False

@pytest.mark.skipif(
    not is_kv_available(kvConfig()),
    reason="KV store not available"
)
class TestKVCache:
    """Test KV cache functionality"""

    def test_basic_operations(self, kv_config):
        """Test basic set/get operations"""
        cache = KVCache(kv_config)
        cache.set("test1", "value1")
        assert cache.get("test1") == "value1"

    def test_ttl(self, kv_config):
        """Test TTL expiration"""
        cache = KVCache(kv_config)
        cache.set("expire", "value")
        assert cache.get("expire") == "value"
        time.sleep(3)  # Wait for TTL
        assert cache.get("expire") is None

    def test_non_existent(self, kv_config):
        """Test getting non-existent keys"""
        cache = KVCache(kv_config)
        assert cache.get("nonexistent") is None

def test_offline_behavior():
    """Test behavior when KV store is offline"""
    config = kvConfig(host="invalid-host", port=6379)
    cache = KVCache(config)

    assert cache.get("any") is None
    cache.set("any", "value")  # Should not raise
    assert cache.client is None
