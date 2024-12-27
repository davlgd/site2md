import time
from .config import RateLimits
from fastapi import HTTPException
from typing import Dict, List, Optional, Set

class MemoryRateLimiter:
    """In-memory rate limiter with sliding window"""

    def __init__(self, limits: Optional[RateLimits] = None):
        self.limits = limits or RateLimits()
        self._store: Dict[str, Dict[str, List[float]]] = {
            'global': {'requests': []},
            'ip': {},
            'daily': {},
            'weekly': {},
            'monthly': {}
        }
        self._allowed_ips: Set[str] = set()
        self._last_cleanup = time.time()

    def add_allowed_ip(self, ip: str) -> None:
        """Add IP to allowlist"""
        self._allowed_ips.add(ip)

    def is_allowed(self, ip: str) -> bool:
        """Check if IP is allowed"""
        return not self._allowed_ips or ip in self._allowed_ips

    def _clean_old(self, now: float, window: float = 1.0) -> None:
        """Remove expired timestamps"""
        cutoff = now - window

        self._store['global']['requests'] = [
            t for t in self._store['global']['requests']
            if t > cutoff
        ]

        for ip in list(self._store['ip'].keys()):
            self._store['ip'][ip] = [
                t for t in self._store['ip'].get(ip, [])
                if t > cutoff
            ]
            if not self._store['ip'][ip]:
                del self._store['ip'][ip]

    def check_limits(self, ip: str) -> None:
        """Check if request is allowed under rate limits

        Args:
            ip: Client IP address
        Raises:
            HTTPException: If limits are exceeded
        """
        if not self.is_allowed(ip):
            raise HTTPException(status_code=403, detail="IP not allowed")

        now = time.time()
        if now - self._last_cleanup > 1.0:
            self._clean_old(now)
            self._last_cleanup = now

        # Vérifier les limites par IP en premier
        ip_requests = self._store['ip'].setdefault(ip, [])
        if len(ip_requests) >= self.limits.ip_rate:
            raise HTTPException(status_code=429, detail="IP rate limit exceeded")

        # Mettre à jour les compteurs
        self._store['global']['requests'].append(now)
        ip_requests.append(now)

        periods = {
            'daily': ('daily', 86400),
            'weekly': ('weekly', 604800),
            'monthly': ('monthly', 2592000)
        }

        for name, (key, seconds) in periods.items():
            period_start = int(now / seconds) * seconds
            period_requests = self._store[key].setdefault(period_start, {})
            count = period_requests.setdefault(ip, 0) + 1

            if count > getattr(self.limits, name):
                raise HTTPException(
                    status_code=429,
                    detail=f"{name.title()} rate limit exceeded"
                )

            period_requests[ip] = count
