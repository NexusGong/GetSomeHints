# -*- coding: utf-8 -*-
"""微博 (wb) 爬虫桩."""
from typing import List, Optional

from app.crawler.base import BaseCrawler
from app.schemas import UnifiedPost, UnifiedAuthor


class WeiboCrawler(BaseCrawler):
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
                platform="wb",
                post_id="wb_mock_1",
                title=f"微博 - {keywords}",
                content="微博爬虫示例。",
                author=UnifiedAuthor(author_id="wb_1", author_name="示例用户", platform="wb"),
                publish_time="2025-01-01T12:00:00",
                like_count=100,
                comment_count=8,
                share_count=3,
                url="https://weibo.com/",
                image_urls=[],
                platform_data={},
            ),
        ][:max(1, min(max_count, 5))]
