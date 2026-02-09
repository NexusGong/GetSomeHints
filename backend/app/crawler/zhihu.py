# -*- coding: utf-8 -*-
"""知乎 (zhihu) 爬虫桩."""
from typing import List, Optional

from app.crawler.base import BaseCrawler
from app.schemas import UnifiedPost, UnifiedAuthor


class ZhihuCrawler(BaseCrawler):
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
                platform="zhihu",
                post_id="zhihu_mock_1",
                title=f"知乎 - {keywords}",
                content="知乎爬虫示例。",
                author=UnifiedAuthor(author_id="zhihu_1", author_name="示例用户", platform="zhihu"),
                publish_time="2025-01-01T12:00:00",
                like_count=200,
                comment_count=15,
                share_count=5,
                url="https://www.zhihu.com/",
                image_urls=[],
                platform_data={},
            ),
        ][:max(1, min(max_count, 5))]
