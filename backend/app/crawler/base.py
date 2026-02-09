# -*- coding: utf-8 -*-
"""Base crawler interface and proxy/anti-block helpers."""
from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING

from app.schemas import UnifiedPost, UnifiedComment

if TYPE_CHECKING:
    from app.proxy.proxy_ip_pool import ProxyIpPool


class BaseCrawler(ABC):
    """Abstract crawler: search and get_comments. Optional proxy pool and anti-block."""

    def __init__(self, proxy_pool: Optional["ProxyIpPool"] = None) -> None:
        self._proxy_pool = proxy_pool
        self.proxy: Optional[str] = None  # current proxy URL for requests

    async def _before_request(self) -> None:
        """Call before each outbound request: random delay and refresh proxy if enabled."""
        import asyncio
        from app.config import settings
        if self._proxy_pool:
            from app.crawler.anti_block import random_sleep
            await random_sleep()
        else:
            await asyncio.sleep(0.4)  # 无代理时短延迟，便于示例结果快速返回
        if self._proxy_pool:
            self.proxy = None
            proxy = await self._proxy_pool.get_or_refresh_proxy()
            if proxy.user and proxy.password:
                self.proxy = f"http://{proxy.user}:{proxy.password}@{proxy.ip}:{proxy.port}"
            else:
                self.proxy = f"http://{proxy.ip}:{proxy.port}"

    @abstractmethod
    async def search(
        self,
        keywords: str,
        max_count: int = 30,
        time_range: str = "all",
        content_types: Optional[List[str]] = None,
    ) -> List[UnifiedPost]:
        """Search by keyword, return list of UnifiedPost."""
        pass

    async def get_comments(
        self,
        platform: str,
        post_id: str,
        max_count: int = 20,
        enable_sub: bool = False,
    ) -> List[UnifiedComment]:
        """Get comments for a post. Default: return []."""
        return []
