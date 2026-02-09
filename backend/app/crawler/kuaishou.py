# -*- coding: utf-8 -*-
"""快手 (ks) 爬虫桩."""
from typing import List, Optional

from app.crawler.base import BaseCrawler
from app.schemas import UnifiedPost, UnifiedAuthor


class KuaishouCrawler(BaseCrawler):
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
                platform="ks",
                post_id="ks_mock_1",
                title=f"快手 - {keywords}",
                content="快手爬虫示例。",
                author=UnifiedAuthor(author_id="ks_1", author_name="示例用户", platform="ks"),
                publish_time="2025-01-01T12:00:00",
                like_count=66,
                comment_count=5,
                share_count=1,
                url="https://www.kuaishou.com/",
                image_urls=[],
                platform_data={},
            ),
        ][:max(1, min(max_count, 5))]
