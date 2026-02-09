# -*- coding: utf-8 -*-
"""贴吧 (tieba) 爬虫桩."""
from typing import List, Optional

from app.crawler.base import BaseCrawler
from app.schemas import UnifiedPost, UnifiedAuthor


class TiebaCrawler(BaseCrawler):
    async def search(
        self,
        keywords: str,
        max_count: int = 30,
        time_range: str = "all",
        content_types: Optional[List[str]] = None,
    ) -> List[UnifiedPost]:
        await self._before_request()
        return [
            UnifiedPost(
                platform="tieba",
                post_id="tieba_mock_1",
                title=f"贴吧 - {keywords}",
                content="百度贴吧爬虫示例。",
                author=UnifiedAuthor(author_id="tieba_1", author_name="示例用户", platform="tieba"),
                publish_time="2025-01-01T12:00:00",
                like_count=50,
                comment_count=12,
                share_count=0,
                url="https://tieba.baidu.com/",
                image_urls=[],
                platform_data={},
            ),
        ][:max(1, min(max_count, 5))]
