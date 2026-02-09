# -*- coding: utf-8 -*-
"""Proxy provider abstract base and in-memory IP cache."""
import json
import time
from abc import ABC, abstractmethod
from typing import List

from app.proxy.types import IpInfoModel


class IpGetError(Exception):
    """Raised when proxy IP fetch fails."""


class ProxyProvider(ABC):
    """Abstract proxy provider: get_proxy(num) -> List[IpInfoModel]."""

    @abstractmethod
    async def get_proxy(self, num: int) -> List[IpInfoModel]:
        """Fetch num proxy IPs from provider."""
        raise NotImplementedError


class IpCache:
    """In-memory IP cache (key -> value, ex). No Redis dependency."""

    def __init__(self) -> None:
        self._store: dict = {}  # key -> (value_str, expire_ts)

    def set_ip(self, ip_key: str, ip_value_info: str, ex: int) -> None:
        """Set IP with TTL ex (seconds from now)."""
        expire_ts = int(time.time()) + ex
        self._store[ip_key] = (ip_value_info, expire_ts)

    def load_all_ip(self, proxy_brand_name: str) -> List[IpInfoModel]:
        """Load all unexpired IPs for this provider from cache."""
        now = int(time.time())
        prefix = f"{proxy_brand_name}_"
        result: List[IpInfoModel] = []
        for key, (value, expire_ts) in list(self._store.items()):
            if not key.startswith(prefix) or expire_ts <= now:
                if not key.startswith(prefix):
                    continue
                del self._store[key]
                continue
            try:
                result.append(IpInfoModel(**json.loads(value)))
            except Exception:
                pass
        return result
