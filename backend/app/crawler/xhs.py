# -*- coding: utf-8 -*-
"""Xiaohongshu (xhs) crawler. Uses anti-block; real data via MediaCrawler bundle (Playwright + login)."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import List, Optional

from app.crawler.base import BaseCrawler
from app.schemas import UnifiedPost, UnifiedAuthor, UnifiedComment

# 是否已尝试加载 bundle（避免重复插入 path）
_bundle_path_checked: Optional[Path] = None


def _bundle_dir() -> Optional[Path]:
    """mediacrawler_bundle 目录（backend/mediacrawler_bundle）。"""
    global _bundle_path_checked
    backend = Path(__file__).resolve().parent.parent.parent
    bundle = backend / "mediacrawler_bundle"
    if not bundle.is_dir():
        return None
    return bundle


def _note_to_unified_post(note_item: dict) -> UnifiedPost:
    """将 MediaCrawler 的 note 字典转为 UnifiedPost。"""
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
    """将 MC 的 (note_id, comment_item) 转为 UnifiedComment。"""
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


async def _run_mediacrawler_xhs_search(
    keywords: str,
    max_count: int,
    enable_comments: bool,
    max_comments_per_note: int,
) -> tuple[List[dict], List[tuple]]:
    """在 bundle 中运行 MC 小红书搜索，返回 (notes, comments_list)。Playwright、登录态、代理池见 docs/playwright_login.md。"""
    bundle = _bundle_dir()
    if not bundle:
        return [], []

    from app.config import settings
    old_cwd = os.getcwd()
    old_path = list(sys.path)
    try:
        os.chdir(str(bundle))
        if str(bundle) not in sys.path:
            sys.path.insert(0, str(bundle))

        os.environ["MC_PLATFORM"] = "xhs"
        os.environ["MC_KEYWORDS"] = keywords.strip() or "热门"
        os.environ["MC_CRAWLER_TYPE"] = "search"
        os.environ["CRAWLER_MAX_NOTES_COUNT"] = str(max(20, min(max_count, 100)))
        os.environ["CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES"] = str(max(0, min(max_comments_per_note, 50)))
        os.environ["ENABLE_IP_PROXY"] = "true" if settings.ENABLE_IP_PROXY else "false"
        os.environ["IP_PROXY_POOL_COUNT"] = str(settings.IP_PROXY_POOL_COUNT)
        if "MC_LOGIN_TYPE" not in os.environ:
            os.environ["MC_LOGIN_TYPE"] = "qrcode"
        if "MC_HEADLESS" not in os.environ:
            os.environ["MC_HEADLESS"] = "false"
        if "MC_SAVE_LOGIN_STATE" not in os.environ:
            os.environ["MC_SAVE_LOGIN_STATE"] = "true"
        if "MC_ENABLE_CDP_MODE" not in os.environ:
            os.environ["MC_ENABLE_CDP_MODE"] = "false"

        # 让 config 重新加载
        for mod in list(sys.modules.keys()):
            if mod in ("config", "config.base_config", "var", "store", "store.xhs"):
                sys.modules.pop(mod, None)

        import store.xhs as xhs_store
        notes_list: List[dict] = []
        comments_list: List[tuple] = []
        xhs_store.set_collector(notes_list, comments_list)

        from media_platform.xhs.core import XiaoHongShuCrawler
        crawler = XiaoHongShuCrawler()
        await crawler.start()
        await crawler.close()
        return notes_list, comments_list
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_path


class XiaoHongShuCrawler(BaseCrawler):
    """XHS 爬虫：有 bundle 时走 MediaCrawler 真实抓取，否则返回示例数据。"""

    async def search(
        self,
        keywords: str,
        max_count: int = 30,
        time_range: str = "all",
        content_types: Optional[List[str]] = None,
        enable_comments: bool = True,
        max_comments_per_note: int = 20,
    ) -> List[UnifiedPost]:
        """关键词搜索。有 mediacrawler_bundle 时启动浏览器并抓取，否则返回 mock。"""
        bundle = _bundle_dir()
        if not bundle:
            await self._before_request()
            return [
                UnifiedPost(
                    platform="xhs",
                    post_id="xhs_mock_1",
                    title=f"示例笔记 - {keywords}",
                    content="这是小红书爬虫的示例结果。请先运行 backend/scripts/sync_mediacrawler.py 并安装 playwright。",
                    author=UnifiedAuthor(author_id="author_1", author_name="示例用户", platform="xhs"),
                    publish_time="2025-01-01T12:00:00",
                    like_count=100,
                    comment_count=10,
                    share_count=5,
                    url="https://www.xiaohongshu.com/explore/mock",
                    image_urls=[],
                    platform_data={},
                ),
            ][:max(1, min(max_count, 5))]

        notes_list, comments_list = await _run_mediacrawler_xhs_search(
            keywords=keywords,
            max_count=max_count,
            enable_comments=enable_comments,
            max_comments_per_note=max_comments_per_note if enable_comments else 0,
        )
        posts = [_note_to_unified_post(n) for n in notes_list]
        # 按 note_id 聚合评论，写入 platform_data 便于前端展示（可选）
        comment_map: dict = {}
        for nid, c in comments_list:
            comment_map.setdefault(nid, []).append(_comment_to_unified(nid, c))
        for p in posts:
            p.platform_data["comments"] = [c.model_dump() for c in comment_map.get(p.post_id, [])]
        return posts[:max_count]

    async def get_comments(
        self,
        platform: str,
        post_id: str,
        max_count: int = 20,
        enable_sub: bool = False,
    ) -> List[UnifiedComment]:
        """获取评论。当前仅支持从上次搜索结果的 platform_data 中取；单独拉评论需 MC detail 模式。"""
        await self._before_request()
        # Stub：若后续在 search 时已把评论放进 post.platform_data["comments"]，可由上层从 results 里取
        return [
            UnifiedComment(
                comment_id="c1",
                post_id=post_id,
                platform=platform or "xhs",
                content="示例评论（单独拉评论需 MC 指定帖子 URL）",
                author=UnifiedAuthor(author_id="u1", author_name="评论用户", platform=platform or "xhs"),
                comment_time="2025-01-01T12:00:00",
                like_count=0,
                sub_comment_count=0,
            ),
        ][:max_count]
