# -*- coding: utf-8 -*-
"""B站 (bili) 爬虫桩."""
from typing import List, Optional

from app.crawler.base import BaseCrawler
from app.schemas import UnifiedPost, UnifiedAuthor


class BilibiliCrawler(BaseCrawler):
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
                platform="bili",
                post_id="bili_mock_1",
                title=f"B站 - {keywords}",
                content="B站爬虫示例。",
                author=UnifiedAuthor(author_id="bili_1", author_name="示例UP主", platform="bili"),
                publish_time="2025-01-01T12:00:00",
                like_count=999,
                comment_count=20,
                share_count=10,
                url="https://www.bilibili.com/",
                image_urls=[],
                platform_data={},
            ),
        ][:max(1, min(max_count, 5))]
