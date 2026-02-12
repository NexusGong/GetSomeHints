# -*- coding: utf-8 -*-
"""小红书爬虫。使用 app.xhs_crawler（不依赖 mediacrawler_bundle）。"""
from __future__ import annotations

import asyncio
import os
from typing import List, Optional

from app.crawler.base import BaseCrawler
from app.schemas import UnifiedPost, UnifiedAuthor, UnifiedComment


def _note_to_unified_post(note_item: dict) -> UnifiedPost:
    """将 xhs_crawler 的 note 字典转为 UnifiedPost。"""
    user = note_item.get("user") or {}
    interact = note_item.get("interact_info") or {}
    note_id = note_item.get("note_id", "")
    title = (note_item.get("title") or note_item.get("desc") or "")[:500]
    desc = note_item.get("desc", "")
    image_list = note_item.get("image_list") or []
    image_urls = [
        (img.get("url_default") or img.get("url") or "").strip()
        for img in image_list
        if (img.get("url_default") or img.get("url"))
    ]
    video_url = None
    if note_item.get("type") == "video":
        v = (note_item.get("video") or {}).get("consumer") or {}
        key = v.get("origin_video_key") or v.get("originVideoKey")
        if key:
            video_url = f"http://sns-video-bd.xhscdn.com/{key}"
    time_val = note_item.get("time") or 0
    if isinstance(time_val, (int, float)) and time_val > 0:
        from datetime import datetime
        try:
            publish_time = datetime.fromtimestamp(time_val / 1000.0).isoformat() + "Z"
        except Exception:
            publish_time = str(time_val)
    else:
        publish_time = str(time_val) if time_val else ""
    note_url = f"https://www.xiaohongshu.com/explore/{note_id}"
    if note_item.get("xsec_token"):
        note_url += f"?xsec_token={note_item.get('xsec_token')}&xsec_source=pc_search"
    return UnifiedPost(
        platform="xhs",
        post_id=note_id,
        title=title,
        content=desc,
        author=UnifiedAuthor(
            author_id=str(user.get("user_id", "")),
            author_name=(user.get("nickname") or user.get("user_name") or ""),
            platform="xhs",
            author_avatar=user.get("avatar"),
            ip_location=note_item.get("ip_location"),
        ),
        publish_time=publish_time,
        like_count=int(interact.get("liked_count") or 0),
        comment_count=int(interact.get("comment_count") or 0),
        share_count=int(interact.get("share_count") or 0),
        collect_count=int(interact.get("collected_count") or 0) or None,
        url=note_url,
        image_urls=image_urls,
        video_url=video_url,
        platform_data={"raw_note": note_item},
    )


def _comment_to_unified(note_id: str, comment_item: dict) -> UnifiedComment:
    """将 (note_id, comment_item) 转为 UnifiedComment。"""
    user = comment_item.get("user_info") or {}
    cid = comment_item.get("id", "")
    if isinstance(cid, (int, float)):
        cid = str(cid)
    ct = comment_item.get("create_time") or 0
    if isinstance(ct, (int, float)) and ct > 0:
        from datetime import datetime
        try:
            comment_time = datetime.fromtimestamp(ct).isoformat() + "Z"
        except Exception:
            comment_time = str(ct)
    else:
        comment_time = str(ct) if ct else ""
    return UnifiedComment(
        comment_id=cid,
        post_id=note_id,
        platform="xhs",
        content=comment_item.get("content", ""),
        author=UnifiedAuthor(
            author_id=str(user.get("user_id", "")),
            author_name=(user.get("nickname") or user.get("user_name") or ""),
            platform="xhs",
            author_avatar=user.get("image"),
        ),
        comment_time=comment_time,
        like_count=int(comment_item.get("like_count") or 0),
        sub_comment_count=int(comment_item.get("sub_comment_count") or 0),
    )


def _content_types_to_note_type(content_types: Optional[List[str]]) -> str:
    """前端 content_types 映射到小红书 MC_NOTE_TYPE: video | image | all。"""
    if not content_types or len(content_types) == 0:
        return "all"
    types = [t.lower() for t in content_types]
    if types == ["video"]:
        return "video"
    if types == ["image_text"]:
        return "image"
    return "all"


def _run_xhs_sync_in_thread(
    keywords: str,
    max_count: int,
    enable_comments: bool,
    max_comments_per_note: int,
    content_types: Optional[List[str]] = None,
) -> tuple[list, list]:
    """在单独线程中运行小红书 MC 搜索，返回 (notes_list, comments_list)。"""
    from pathlib import Path
    notes_list: List[dict] = []
    comments_list: List[tuple] = []

    from app.config import settings
    backend_dir = Path(__file__).resolve().parent.parent.parent
    os.environ["MC_BROWSER_DATA_DIR"] = (
        settings.BROWSER_DATA_DIR or str(backend_dir / "browser_data")
    )
    os.environ["MC_PLATFORM"] = "xhs"
    os.environ["MC_KEYWORDS"] = keywords.strip() or "热门"
    os.environ["MC_CRAWLER_TYPE"] = "search"
    os.environ["MC_NOTE_TYPE"] = _content_types_to_note_type(content_types)
    os.environ["CRAWLER_MAX_NOTES_COUNT"] = str(max(1, min(max_count, 100)))
    os.environ["ENABLE_GET_COMMENTS"] = "true" if enable_comments else "false"
    os.environ["CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES"] = str(max(0, min(max_comments_per_note, 50)))
    os.environ["ENABLE_GET_SUB_COMMENTS"] = "false"
    os.environ.setdefault("MC_LOGIN_TYPE", "qrcode")
    os.environ.setdefault("MC_HEADLESS", "false")
    os.environ.setdefault("MC_SAVE_LOGIN_STATE", "true")
    os.environ.setdefault("MC_SORT_TYPE", "general")
    os.environ["ENABLE_IP_PROXY"] = "true" if settings.ENABLE_IP_PROXY else "false"
    os.environ["IP_PROXY_POOL_COUNT"] = str(settings.IP_PROXY_POOL_COUNT)

    from app.xhs_crawler import set_collector, XiaoHongShuCrawler
    set_collector(notes_list, comments_list)
    crawler = XiaoHongShuCrawler()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(crawler.start())
        loop.run_until_complete(crawler.close())
    finally:
        loop.close()
    return notes_list, comments_list


def run_search_sync(
    keywords: str,
    max_count: int,
    enable_comments: bool = True,
    max_comments_per_note: int = 20,
    time_range: str = "all",
    content_types: Optional[List[str]] = None,
) -> List[UnifiedPost]:
    """
    平台适配器：在调用线程中运行小红书搜索，返回已挂好评论的 UnifiedPost 列表。
    供 crawler_runner 统一调用，不暴露内部 note/comment 结构。
    """
    notes_list, comments_list = _run_xhs_sync_in_thread(
        keywords,
        max_count,
        enable_comments,
        max_comments_per_note if enable_comments else 0,
        content_types,
    )
    posts = [_note_to_unified_post(n) for n in notes_list]
    comment_map: dict = {}
    for nid, c in comments_list:
        comment_map.setdefault(nid, []).append(_comment_to_unified(nid, c))
    for p in posts:
        p.platform_data.setdefault("comments", [])
        p.platform_data["comments"] = [c.model_dump() for c in comment_map.get(p.post_id, [])]
    return posts[:max_count]


class XiaoHongShuCrawler(BaseCrawler):
    """小红书爬虫：使用 app.xhs_crawler 真实抓取。"""

    run_search_sync = run_search_sync  # 平台适配器，供 crawler_runner 统一调用

    async def search(
        self,
        keywords: str,
        max_count: int = 30,
        time_range: str = "all",
        content_types: Optional[List[str]] = None,
        enable_comments: bool = True,
        max_comments_per_note: int = 20,
    ) -> List[UnifiedPost]:
        """关键词搜索。内部使用 run_search_sync，供单测或直接调用。"""
        await self._before_request()
        return await asyncio.to_thread(
            run_search_sync,
            keywords.strip() or "热门",
            max(1, min(max_count, 100)),
            enable_comments,
            max_comments_per_note,
            time_range,
            content_types,
        )

    async def get_comments(
        self,
        platform: str,
        post_id: str,
        max_count: int = 20,
        enable_sub: bool = False,
    ) -> List[UnifiedComment]:
        """获取评论。当前仅支持从上次搜索结果的 platform_data 中取。"""
        await self._before_request()
        return [
            UnifiedComment(
                comment_id="c1",
                post_id=post_id,
                platform=platform or "xhs",
                content="示例评论（单独拉评论需指定帖子 URL）",
                author=UnifiedAuthor(author_id="u1", author_name="评论用户", platform=platform or "xhs"),
                comment_time="2025-01-01T12:00:00",
                like_count=0,
                sub_comment_count=0,
            ),
        ][:max_count]
