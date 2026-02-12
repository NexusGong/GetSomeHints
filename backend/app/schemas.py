# -*- coding: utf-8 -*-
"""API request/response schemas (match frontend contract)."""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --- Search API ---

class SearchStartRequest(BaseModel):
    """POST /api/search/start body."""
    keywords: str
    platforms: List[str]  # xhs, dy, ks, bili, wb, tieba, zhihu
    max_count: Optional[int] = 50
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


# --- LLM Leads Analysis API ---

class ContactSummary(BaseModel):
    """单条联系方式（由 LLM 从正文/评论抽取）。"""
    author_id: str = ""
    platform: str = ""
    contact_type: str = ""  # wechat | phone | private_message | other
    value: str = ""
    source: str = ""  # post_content | comment | signature 等


class PotentialSeller(BaseModel):
    """潜在卖家条目。"""
    author_id: str = ""
    author_name: str = ""
    platform: str = ""
    reason: str = ""
    source_post_id: str = ""
    contacts: List[str] = Field(default_factory=list)


class PotentialBuyer(BaseModel):
    """潜在买家条目。intent_level: explicit_inquiry | interested | sharing_only | unknown"""
    author_id: str = ""
    author_name: str = ""
    platform: str = ""
    intent_level: str = ""
    reason: str = ""
    source_post_id: str = ""
    contacts: List[str] = Field(default_factory=list)


class LlmLeadsRequest(BaseModel):
    """POST /api/analysis/llm-leads 可选 body：帖子列表（与 task_id 二选一）、模型、场景。"""
    posts: Optional[List[UnifiedPost]] = None
    model: Optional[str] = None  # 如 deepseek-chat
    scene: Optional[str] = None  # 分析场景 id，见 GET /api/analysis/llm-scenarios


class LlmLeadsResult(BaseModel):
    """大模型潜在卖/买家分析结果。"""
    potential_sellers: List[PotentialSeller] = Field(default_factory=list)
    potential_buyers: List[PotentialBuyer] = Field(default_factory=list)
    contacts_summary: List[ContactSummary] = Field(default_factory=list)
    analysis_summary: Optional[str] = None
