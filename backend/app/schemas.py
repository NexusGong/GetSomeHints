# -*- coding: utf-8 -*-
"""API request/response schemas (match frontend contract)."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --- Search API ---

class SearchStartRequest(BaseModel):
    """POST /api/search/start body."""
    keywords: str
    platforms: List[str]  # xhs, dy, ks, bili, wb, tieba, zhihu
    max_count: Optional[int] = 100
    enable_comments: Optional[bool] = True
    enable_sub_comments: Optional[bool] = False
    max_comments_per_note: Optional[int] = 14  # 单条内容最大评论数，默认 14
    sort_type: Optional[str] = None
    time_range: Optional[str] = "all"  # all, 1day, 1week, 1month, 3months, 6months
    content_types: Optional[List[str]] = None  # video, image_text, link


class UnifiedAuthor(BaseModel):
    author_id: str = ""
    author_name: str = ""
    author_avatar: Optional[str] = None
    platform: str = ""
    user_unique_id: Optional[str] = None
    short_user_id: Optional[str] = None
    sec_uid: Optional[str] = None
    signature: Optional[str] = None
    ip_location: Optional[str] = None


class UnifiedPost(BaseModel):
    platform: str
    post_id: str
    title: str = ""
    content: str = ""
    author: UnifiedAuthor
    publish_time: str = ""
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    collect_count: Optional[int] = None
    url: str = ""
    image_urls: List[str] = Field(default_factory=list)
    video_url: Optional[str] = None
    platform_data: Dict[str, Any] = Field(default_factory=dict)


class UnifiedComment(BaseModel):
    comment_id: str
    post_id: str
    platform: str
    content: str = ""
    author: UnifiedAuthor
    comment_time: str = ""
    like_count: int = 0
    parent_comment_id: Optional[str] = None
    sub_comment_count: int = 0


class SearchResponse(BaseModel):
    """Search status/start response."""
    task_id: str
    status: str  # pending, running, completed, failed, stopped
    total_found: int = 0
    by_platform: Dict[str, int] = Field(default_factory=dict)
    progress: Optional[int] = None
    message: str = ""
