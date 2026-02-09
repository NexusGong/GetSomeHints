# -*- coding: utf-8 -*-
"""抖音 (dy) 爬虫。有 mediacrawler_bundle 时走 MediaCrawler 真实抓取，否则返回示例数据。"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

from app.crawler.base import BaseCrawler
from app.schemas import UnifiedPost, UnifiedAuthor, UnifiedComment

logger = logging.getLogger(__name__)


def _bundle_dir() -> Optional[Path]:
    backend = Path(__file__).resolve().parent.parent.parent
    bundle = backend / "mediacrawler_bundle"
    return bundle if bundle.is_dir() else None


def _time_range_to_publish_time_type(time_range: str) -> int:
    """前端 time_range 映射到 MC PublishTimeType：0=全部, 1=一天, 7=一周, 180=六个月。"""
    m = {"all": 0, "1day": 1, "1week": 7, "1month": 7, "3months": 7, "6months": 180}
    return m.get(time_range, 0)


def _run_douyin_sync_in_thread(
    keywords: str,
    max_count: int,
    max_comments_per_note: int,
    time_range: str = "all",
) -> tuple[List[dict], List[tuple]]:
    """在独立线程中运行 MC 抖音搜索（新建事件循环），避免阻塞主循环。"""
    thread_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(thread_loop)
    try:
        return thread_loop.run_until_complete(
            _run_mediacrawler_douyin_search(
                keywords, max_count, max_comments_per_note, time_range
            ),
        )
    finally:
        thread_loop.close()


def _aweme_to_unified_post(aweme_item: dict) -> UnifiedPost:
    """将 MC 的 aweme 字典转为 UnifiedPost。"""
    author = aweme_item.get("author") or {}
    stats = aweme_item.get("statistics") or {}
    aweme_id = aweme_item.get("aweme_id", "")
    desc = aweme_item.get("desc", "")
    avatar = (author.get("avatar_thumb") or {}).get("url_list") or []
    avatar_url = avatar[0] if avatar else None
    create_time = aweme_item.get("create_time") or 0
    if isinstance(create_time, (int, float)) and create_time > 0:
        # 抖音接口为秒；>=1e12 视为毫秒，转秒后存为 Unix 秒字符串，排序/展示一致
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


async def _run_mediacrawler_douyin_search(
    keywords: str,
    max_count: int,
    max_comments_per_note: int,
    time_range: str = "all",
) -> tuple[List[dict], List[tuple]]:
    """在 bundle 中运行 MC 抖音搜索，返回 (aweme_list, comments_list)。Playwright、登录态、代理池由 MC 配置（见 docs/playwright_login.md）。"""
    bundle = _bundle_dir()
    if not bundle:
        logger.info("[Douyin] no mediacrawler_bundle, will return mock")
        return [], []
    from app.config import settings
    from app.debug_log import debug_log
    debug_log(f"[Douyin] using bundle at {bundle}")
    logger.info("[Douyin] using bundle at %s", bundle)
    old_cwd = os.getcwd()
    old_path = list(sys.path)
    try:
        os.chdir(str(bundle))
        if str(bundle) not in sys.path:
            sys.path.insert(0, str(bundle))
        # 本次任务参数
        os.environ["MC_PLATFORM"] = "dy"
        os.environ["MC_KEYWORDS"] = keywords.strip() or "热门"
        os.environ["MC_CRAWLER_TYPE"] = "search"
        os.environ["CRAWLER_MAX_NOTES_COUNT"] = str(max(10, min(max_count, 100)))
        os.environ["CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES"] = str(max(0, min(max_comments_per_note, 50)))
        os.environ["MC_PUBLISH_TIME_TYPE"] = str(_time_range_to_publish_time_type(time_range))
        # 代理池：与 backend/.env 一致，使用 app 配置
        os.environ["ENABLE_IP_PROXY"] = "true" if settings.ENABLE_IP_PROXY else "false"
        os.environ["IP_PROXY_POOL_COUNT"] = str(settings.IP_PROXY_POOL_COUNT)
        # Playwright / 登录态：未在 .env 设置时使用默认（有头、保存登录态、标准模式）
        if "MC_LOGIN_TYPE" not in os.environ:
            os.environ["MC_LOGIN_TYPE"] = "qrcode"
        if "MC_HEADLESS" not in os.environ:
            os.environ["MC_HEADLESS"] = "false"
        if "MC_SAVE_LOGIN_STATE" not in os.environ:
            os.environ["MC_SAVE_LOGIN_STATE"] = "true"
        if "MC_ENABLE_CDP_MODE" not in os.environ:
            os.environ["MC_ENABLE_CDP_MODE"] = "false"

        # 只输出关键日志：MC 内 utils.logger 名为 MediaCrawler，设为 WARNING 后仅保留关键/错误信息
        import logging as _log
        for _name in (
            "MediaCrawler",
            "tools.utils",
            "tools",
            "media_platform",
            "media_platform.douyin",
            "store",
            "store.douyin",
            "proxy",
        ):
            _log.getLogger(_name).setLevel(_log.WARNING)

        for mod in list(sys.modules.keys()):
            if mod in ("config", "config.base_config", "var", "store", "store.douyin"):
                sys.modules.pop(mod, None)
        logger.info("[Douyin] importing store.douyin and media_platform.douyin.core ...")
        import store.douyin as douyin_store
        notes_list: List[dict] = []
        comments_list: List[tuple] = []
        douyin_store.set_collector(notes_list, comments_list)
        from media_platform.douyin.core import DouYinCrawler
        crawler = DouYinCrawler()
        logger.info("[Douyin] starting MC DouYinCrawler (browser may open, please login if needed) ...")
        await crawler.start()
        try:
            await crawler.close()
        except Exception as close_err:
            # 浏览器/context 可能已被关闭（如用户关窗口或 AUTO_CLOSE），不影响已爬取数据
            logger.warning("[Douyin] crawler.close() ignored: %s", close_err)
        logger.info("[Douyin] MC finished, notes=%d comments=%d", len(notes_list), len(comments_list))
        return notes_list, comments_list
    except Exception as e:
        logger.exception("[Douyin] MC run failed: %s", e)
        raise RuntimeError(f"抖音爬虫执行失败: {e!s}") from e
    finally:
        os.chdir(old_cwd)
        sys.path[:] = old_path


class DouYinCrawler(BaseCrawler):
    """抖音爬虫：有 bundle 时走 MediaCrawler，否则返回 mock。"""

    async def search(
        self,
        keywords: str,
        max_count: int = 30,
        time_range: str = "all",
        content_types: Optional[List[str]] = None,
    ) -> List[UnifiedPost]:
        bundle = _bundle_dir()
        if not bundle:
            from app.debug_log import debug_log
            debug_log("[Douyin] no bundle, returning mock")
            logger.info("[Douyin] no mediacrawler_bundle, returning mock")
            await self._before_request()
            return [
                UnifiedPost(
                    platform="dy",
                    post_id="dy_mock_1",
                    title=f"抖音 - {keywords}",
                    content="抖音爬虫示例。请先运行 backend/scripts/sync_mediacrawler.py 并安装 playwright。",
                    author=UnifiedAuthor(author_id="dy_author_1", author_name="示例用户", platform="dy"),
                    publish_time="2025-01-01T12:00:00",
                    like_count=88,
                    comment_count=6,
                    share_count=2,
                    url="https://www.douyin.com/",
                    image_urls=[],
                    platform_data={},
                ),
            ][:max(1, min(max_count, 5))]

        # 在单独线程中运行 MC，避免阻塞主事件循环（否则前端轮询 status 无响应）
        notes_list, comments_list = await asyncio.to_thread(
            _run_douyin_sync_in_thread,
            keywords,
            max_count,
            20,
            time_range,
        )
        posts = [_aweme_to_unified_post(n) for n in notes_list]
        comment_map: dict = {}
        for aweme_id, c in comments_list:
            aid = str(aweme_id)
            comment_map.setdefault(aid, []).append(_comment_to_unified(aid, c))
        for p in posts:
            p.platform_data["comments"] = [c.model_dump() for c in comment_map.get(p.post_id, [])]
        return posts[:max_count]
