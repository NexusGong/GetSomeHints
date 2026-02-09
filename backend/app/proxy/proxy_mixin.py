# -*- coding: utf-8 -*-
"""Mixin: refresh proxy before each request (for crawler clients)."""
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.proxy.proxy_ip_pool import ProxyIpPool


class ProxyRefreshMixin:
    """Call _refresh_proxy_if_expired() before each request. Requires self._proxy_ip_pool and self.proxy (URL string)."""

    _proxy_ip_pool: Optional["ProxyIpPool"] = None

    def init_proxy_pool(self, proxy_ip_pool: Optional["ProxyIpPool"]) -> None:
        self._proxy_ip_pool = proxy_ip_pool

    async def _refresh_proxy_if_expired(self) -> None:
        if self._proxy_ip_pool is None:
            return
        if self._proxy_ip_pool.is_current_proxy_expired():
            new_proxy = await self._proxy_ip_pool.get_or_refresh_proxy()
            if new_proxy.user and new_proxy.password:
                self.proxy = f"http://{new_proxy.user}:{new_proxy.password}@{new_proxy.ip}:{new_proxy.port}"
            else:
                self.proxy = f"http://{new_proxy.ip}:{new_proxy.port}"
