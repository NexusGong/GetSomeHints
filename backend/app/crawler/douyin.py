# -*- coding: utf-8 -*-
"""抖音 (dy) 爬虫。使用内嵌的 douyin_crawler 逻辑，不依赖 mediacrawler_bundle。"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional

_user_log = logging.getLogger("app.douyin_crawler")

from app.crawler.base import BaseCrawler
from app.schemas import UnifiedPost, UnifiedAuthor, UnifiedComment

logger = logging.getLogger(__name__)


def _time_range_to_publish_time_type(time_range: str) -> int:
    """前端 time_range 映射到 MC PublishTimeType：0=全部, 1=一天, 7=一周, 180=六个月。"""
    m = {"all": 0, "1day": 1, "1week": 7, "1month": 7, "3months": 7, "6months": 180}
    return m.get(time_range, 0)


def _run_douyin_sync_in_thread(
    keywords: str,
    max_count: int,
    max_comments_per_note: int,
    time_range: str = "all",
    content_types: Optional[List[str]] = None,
) -> tuple[List[dict], List[tuple]]:
    """在独立线程中运行抖音搜索（新建事件循环），避免阻塞主循环。"""
    thread_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(thread_loop)
    try:
        return thread_loop.run_until_complete(
            _run_douyin_crawler_search(keywords, max_count, max_comments_per_note, time_range, content_types),
        )
    finally:
        thread_loop.close()


def _aweme_to_unified_post(aweme_item: dict) -> UnifiedPost:
    """将 aweme 字典转为 UnifiedPost。"""
    author = aweme_item.get("author") or {}
    stats = aweme_item.get("statistics") or {}
    aweme_id = aweme_item.get("aweme_id", "")
    desc = aweme_item.get("desc", "")
    avatar = (author.get("avatar_thumb") or {}).get("url_list") or []
    avatar_url = avatar[0] if avatar else None
    create_time = aweme_item.get("create_time") or 0
    if isinstance(create_time, (int, float)) and create_time > 0:
        sec = int(create_time / 1000) if create_time >= 1e12 else int(create_time)
        publish_time = str(sec)
    else:
        publish_time = str(create_time) if create_time else ""
    video_url = None
    v = aweme_item.get("video") or {}
    for key in ("play_addr_h264", "play_addr_256", "play_addr"):
        url_list = (v.get(key) or {}).get("url_list") or []
        if len(url_list) >= 2:
            video_url = url_list[-1]
            break
    image_urls = []
    for img in aweme_item.get("images") or []:
        u = (img.get("url_list") or [])[-1]
        if u:
            image_urls.append(u)
    return UnifiedPost(
        platform="dy",
        post_id=str(aweme_id),
        title=desc[:500] if desc else "",
        content=desc,
        author=UnifiedAuthor(
            author_id=str(author.get("uid", "")),
            author_name=author.get("nickname") or author.get("unique_id") or "",
            platform="dy",
            author_avatar=avatar_url,
            user_unique_id=author.get("unique_id"),
            short_user_id=author.get("short_id"),
            sec_uid=author.get("sec_uid"),
            signature=author.get("signature"),
            ip_location=aweme_item.get("ip_label"),
        ),
        publish_time=publish_time,
        like_count=int(stats.get("digg_count") or 0),
        comment_count=int(stats.get("comment_count") or 0),
        share_count=int(stats.get("share_count") or 0),
        collect_count=int(stats.get("collect_count") or 0) or None,
        url=f"https://www.douyin.com/video/{aweme_id}",
        image_urls=image_urls,
        video_url=video_url,
        platform_data={"raw_aweme": aweme_item},
    )


def _comment_to_unified(aweme_id: str, comment_item: dict) -> UnifiedComment:
    user = comment_item.get("user") or {}
    cid = comment_item.get("cid", "")
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
    avatar = (user.get("avatar_thumb") or user.get("avatar_medium") or {}).get("url_list") or []
    return UnifiedComment(
        comment_id=cid,
        post_id=str(aweme_id),
        platform="dy",
        content=comment_item.get("text", ""),
        author=UnifiedAuthor(
            author_id=str(user.get("uid", "")),
            author_name=user.get("nickname") or user.get("unique_id") or "",
            platform="dy",
            author_avatar=avatar[0] if avatar else None,
        ),
        comment_time=comment_time,
        like_count=int(comment_item.get("digg_count") or 0),
        sub_comment_count=int(comment_item.get("reply_comment_total") or 0),
    )


def _content_types_to_search_channel(content_types: Optional[List[str]]) -> str:
    """前端 content_types 映射到抖音 search_channel：仅要视频时用 aweme_video_web，否则综合。"""
    if not content_types:
        return "aweme_general"
    types = [t.lower() for t in content_types]
    if types == ["video"] or (len(types) == 1 and "video" in types):
        return "aweme_video_web"
    return "aweme_general"


async def _run_douyin_crawler_search(
    keywords: str,
    max_count: int,
    max_comments_per_note: int,
    time_range: str = "all",
    content_types: Optional[List[str]] = None,
) -> tuple[List[dict], List[tuple]]:
    """使用 app.douyin_crawler 运行抖音搜索，返回 (aweme_list, comments_list)。"""
    from app.config import settings
    from app.douyin_crawler import set_collector
    from app.douyin_crawler.core import DouYinCrawler
    from app.services.ws_broadcast import push_log_sync

    backend_dir = Path(__file__).resolve().parent.parent.parent
    old_cwd = os.getcwd()
    try:
        os.chdir(str(backend_dir))
        os.environ["MC_BROWSER_DATA_DIR"] = (
            settings.BROWSER_DATA_DIR or str(backend_dir / "browser_data")
        )
        push_log_sync("正在准备搜索…", "info", "抖音")
        _user_log.info("[抖音] 正在准备搜索…")
        os.environ["MC_PLATFORM"] = "dy"
        os.environ["MC_KEYWORDS"] = (keywords or "").strip() or "热门"
        os.environ["MC_CRAWLER_TYPE"] = "search"
        os.environ["CRAWLER_MAX_NOTES_COUNT"] = str(max(1, min(max_count, 100)))
        os.environ["CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES"] = str(max(0, min(max_comments_per_note, 50)))  # noqa: E501
        os.environ["MC_PUBLISH_TIME_TYPE"] = str(_time_range_to_publish_time_type(time_range))
        os.environ["MC_SEARCH_CHANNEL"] = _content_types_to_search_channel(content_types)
        os.environ["ENABLE_IP_PROXY"] = "true" if settings.ENABLE_IP_PROXY else "false"
        os.environ["IP_PROXY_POOL_COUNT"] = str(settings.IP_PROXY_POOL_COUNT)
        os.environ.setdefault("MC_LOGIN_TYPE", "qrcode")
        os.environ.setdefault("MC_HEADLESS", "false")
        os.environ.setdefault("MC_SAVE_LOGIN_STATE", "true")
        os.environ.setdefault("MC_ENABLE_CDP_MODE", "false")
        os.environ["CRAWLER_MAX_SLEEP_SEC"] = str(max(1, getattr(settings, "CRAWLER_MAX_SLEEP_SEC", 2)))
        os.environ["ENABLE_GET_COMMENTS"] = "true" if getattr(settings, "ENABLE_GET_COMMENTS", True) else "false"
        os.environ["ENABLE_GET_MEIDAS"] = "false"

        notes_list: List[dict] = []
        comments_list: List[tuple] = []
        set_collector(notes_list, comments_list)
        crawler = DouYinCrawler()
        push_log_sync("正在启动浏览器（如需登录请扫码）…", "info", "抖音")
        _user_log.info("[抖音] 正在启动浏览器（如需登录请扫码）…")
        await crawler.start()
        try:
            await crawler.close()
        except Exception as close_err:
            logger.warning("[Douyin] crawler.close() ignored: %s", close_err)
        push_log_sync("搜索完成，共 %d 条" % len(notes_list), "success", "抖音")
        _user_log.info("[抖音] 搜索完成，共 %d 条", len(notes_list))
        return notes_list, comments_list
    except Exception as e:
        logger.exception("[Douyin] run failed: %s", e)
        raise RuntimeError(f"抖音爬虫执行失败: {e!s}") from e
    finally:
        os.chdir(old_cwd)


def run_search_sync(
    keywords: str,
    max_count: int,
    enable_comments: bool = True,
    max_comments_per_note: int = 20,
    time_range: str = "all",
    content_types: Optional[List[str]] = None,
) -> List[UnifiedPost]:
    """
    平台适配器：在调用线程中运行抖音搜索，返回已挂好评论的 UnifiedPost 列表。
    供 crawler_runner 统一调用，不暴露内部 aweme/comment 结构。
    """
    notes_list, comments_list = _run_douyin_sync_in_thread(
        keywords,
        max_count,
        max_comments_per_note if enable_comments else 0,
        time_range,
        content_types,
    )
    posts = [_aweme_to_unified_post(n) for n in notes_list]
    comment_map: dict = {}
    for aweme_id, c in comments_list:
        aid = str(aweme_id)
        comment_map.setdefault(aid, []).append(_comment_to_unified(aid, c))
    for p in posts:
        p.platform_data.setdefault("comments", [])
        p.platform_data["comments"] = [c.model_dump() for c in comment_map.get(p.post_id, [])]
    return posts[:max_count]


class DouYinCrawler(BaseCrawler):
    """抖音爬虫：使用内嵌 douyin_crawler，不依赖 mediacrawler_bundle。"""

    run_search_sync = run_search_sync  # 平台适配器，供 crawler_runner 统一调用

    async def search(
        self,
        keywords: str,
        max_count: int = 30,
        time_range: str = "all",
        content_types: Optional[List[str]] = None,
    ) -> List[UnifiedPost]:
        await self._before_request()
        return await asyncio.to_thread(
            run_search_sync,
            keywords,
            max_count,
            True,
            20,
            time_range,
            content_types,
        )
