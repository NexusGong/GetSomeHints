# -*- coding: utf-8 -*-
"""Proxy IP pool: get one proxy, refresh when expired or on failure."""
import random
from typing import List

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.config import settings
from app.proxy.base_proxy import ProxyProvider
from app.proxy.types import IpInfoModel, ProviderNameEnum

# URL used to validate proxy (echo service)
VALIDATE_URL = "https://httpbin.org/ip"


class ProxyIpPool:
    """Pool of proxy IPs; get one, refresh when expired."""

    def __init__(
        self,
        ip_pool_count: int,
        enable_validate_ip: bool,
        ip_provider: ProxyProvider,
    ) -> None:
        self.ip_pool_count = ip_pool_count
        self.enable_validate_ip = enable_validate_ip
        self.ip_provider = ip_provider
        self.proxy_list: List[IpInfoModel] = []
        self.current_proxy: IpInfoModel | None = None
        self.valid_ip_url = VALIDATE_URL

    async def load_proxies(self) -> None:
        """Load IPs from provider into pool."""
        self.proxy_list = await self.ip_provider.get_proxy(self.ip_pool_count)

    async def _is_valid_proxy(self, proxy: IpInfoModel) -> bool:
        """Check proxy with a simple GET."""
        try:
            if proxy.user and proxy.password:
                url = f"http://{proxy.user}:{proxy.password}@{proxy.ip}:{proxy.port}"
            else:
                url = f"http://{proxy.ip}:{proxy.port}"
            async with httpx.AsyncClient(proxy=url, timeout=10.0) as client:
                r = await client.get(self.valid_ip_url)
                return r.status_code == 200
        except Exception:
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_proxy(self) -> IpInfoModel:
        """Get one proxy from pool; reload if empty."""
        if not self.proxy_list:
            await self._reload_proxies()
        proxy = random.choice(self.proxy_list)
        self.proxy_list.remove(proxy)
        if self.enable_validate_ip and not await self._is_valid_proxy(proxy):
            raise Exception("Proxy validation failed")
        self.current_proxy = proxy
        return proxy

    def is_current_proxy_expired(self, buffer_seconds: int = 30) -> bool:
        """True if current proxy is expired or not set."""
        if self.current_proxy is None:
            return True
        return self.current_proxy.is_expired(buffer_seconds)

    async def get_or_refresh_proxy(self, buffer_seconds: int = 30) -> IpInfoModel:
        """Return current proxy or refresh and return new one."""
        if self.is_current_proxy_expired(buffer_seconds):
            return await self.get_proxy()
        return self.current_proxy

    def invalidate_current(self) -> None:
        """Call on 403/502/503 so next get_or_refresh_proxy fetches a new IP."""
        self.current_proxy = None

    async def _reload_proxies(self) -> None:
        """Refill pool from provider."""
        self.proxy_list = []
        await self.load_proxies()


def get_proxy_provider() -> ProxyProvider:
    """Return provider by settings.IP_PROXY_PROVIDER."""
    name = (settings.IP_PROXY_PROVIDER or "kuaidaili").lower()
    if name == "kuaidaili":
        from app.proxy.providers.kuaidaili import new_kuai_daili_proxy
        return new_kuai_daili_proxy()
    raise ValueError(f"Unknown proxy provider: {name}")


async def create_ip_pool(
    ip_pool_count: int | None = None,
    enable_validate_ip: bool = False,
) -> ProxyIpPool:
    """Create and load proxy pool."""
    count = ip_pool_count or settings.IP_PROXY_POOL_COUNT
    pool = ProxyIpPool(
        ip_pool_count=count,
        enable_validate_ip=enable_validate_ip,
        ip_provider=get_proxy_provider(),
    )
    await pool.load_proxies()
    return pool
