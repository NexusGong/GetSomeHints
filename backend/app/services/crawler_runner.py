# -*- coding: utf-8 -*-
"""Runs crawlers per platform and updates task state."""
import asyncio
import logging
from typing import List

from app.config import settings
from app.services.task_manager import task_manager
from app.services.ws_broadcast import broadcast

logger = logging.getLogger(__name__)

PLATFORM_LABEL = {"dy": "抖音", "xhs": "小红书"}


async def run_search_task(
    task_id: str,
    keywords: str,
    platforms: List[str],
    max_count: int = 100,
    enable_comments: bool = True,
    enable_sub_comments: bool = False,
    time_range: str = "all",
    content_types: List[str] | None = None,
) -> None:
    """
    Background task: run crawlers for each platform, update task_manager.
    Serial execution (MAX_CONCURRENCY_NUM=1). Current crawlers are stubs (no Playwright).
    """
    from app.debug_log import debug_log
    debug_log(f"[Crawler] run_search_task started task_id={task_id[:8]}... platforms={platforms}")
    logger.info("[Crawler] run_search_task started task_id=%s platforms=%s", task_id[:8], platforms)
    await task_manager.set_running(task_id)
    await broadcast("开始爬取", "info")
    total = 0
    by_platform: dict = {p: 0 for p in platforms}
    logger.info("[Crawler] task_id=%s keywords=%r platforms=%s", task_id[:8], keywords, platforms)

    # 单平台搜索超时（秒），避免 MC 浏览器/登录卡住导致任务一直 running
    SEARCH_TIMEOUT = 600

    proxy_pool = None
    if settings.ENABLE_IP_PROXY:
        try:
            from app.proxy.proxy_ip_pool import create_ip_pool
            proxy_pool = await asyncio.wait_for(create_ip_pool(), timeout=8.0)
            logger.info("[Crawler] proxy pool ready")
        except asyncio.TimeoutError:
            logger.warning("[Crawler] proxy pool timeout, continuing without proxy")
            proxy_pool = None
        except Exception as e:
            logger.warning("[Crawler] proxy pool failed: %s, continuing without proxy", e)
            proxy_pool = None

    consecutive_failures = 0
    max_failures_before_skip = 3

    try:
        for platform in platforms:
            if task_manager.is_stop_requested(task_id):
                await task_manager.set_stopped(task_id)
                return

            try:
                from app.crawler.registry import get_crawler
                crawler_cls = get_crawler(platform)
                logger.info("[Crawler] platform=%s crawler_cls=%s", platform, crawler_cls)
                if crawler_cls:
                    platform_label = PLATFORM_LABEL.get(platform, platform)
                    await broadcast(f"开始爬取 {platform_label}...", "info", platform=platform_label)
                    crawler = crawler_cls(proxy_pool=proxy_pool)
                    try:
                        posts = await asyncio.wait_for(
                            crawler.search(
                                keywords=keywords,
                                max_count=min(max_count, settings.CRAWLER_MAX_NOTES_COUNT),
                                time_range=time_range,
                                content_types=content_types or ["video", "image_text", "link"],
                            ),
                            timeout=SEARCH_TIMEOUT,
                        )
                    except asyncio.TimeoutError:
                        logger.warning("[Crawler] platform=%s search timeout after %ss", platform, SEARCH_TIMEOUT)
                        raise RuntimeError(f"平台 {platform} 搜索超时（{SEARCH_TIMEOUT}秒），请检查浏览器/登录是否卡住")
                    if posts:
                        await task_manager.append_results(task_id, posts)
                        count = len(posts)
                        by_platform[platform] = count
                        total += count
                        logger.info("[Crawler] %s got %d posts", platform, count)
                        await broadcast(f"{platform_label} 已获取 {count} 条", "success", platform=platform_label)
                    else:
                        await broadcast(f"{platform_label} 本页无新结果", "info", platform=platform_label)
                    consecutive_failures = 0
                else:
                    logger.info("[Crawler] no crawler for platform %s", platform)
                idx = platforms.index(platform) + 1
                progress = int(100 * idx / len(platforms)) if platforms else 0
                await task_manager.set_progress(task_id, total, by_platform, progress=progress)
            except Exception as e:
                logger.exception("[Crawler] platform %s failed: %s", platform, e)
                platform_label = PLATFORM_LABEL.get(platform, platform)
                await broadcast(f"{platform_label} 爬取失败: {e!s}", "error", platform=platform_label)
                consecutive_failures += 1
                if proxy_pool:
                    proxy_pool.invalidate_current()
                by_platform[platform] = 0
                await task_manager.set_progress(task_id, total, by_platform)
                if consecutive_failures >= max_failures_before_skip:
                    break

        await task_manager.set_completed(task_id, total, by_platform)
        logger.info("[Crawler] task_id=%s completed total=%d by_platform=%s", task_id[:8], total, by_platform)
        await broadcast(f"爬取结束，共 {total} 条", "success")
    except asyncio.CancelledError:
        logger.info("[Crawler] task_id=%s stopped", task_id[:8])
        await task_manager.set_stopped(task_id)
    except Exception as e:
        logger.exception("[Crawler] task_id=%s failed: %s", task_id[:8], e)
        await task_manager.set_failed(task_id, str(e))


def start_search_background(
    task_id: str,
    keywords: str,
    platforms: List[str],
    max_count: int = 100,
    enable_comments: bool = True,
    enable_sub_comments: bool = False,
    time_range: str = "all",
    content_types: List[str] | None = None,
) -> asyncio.Task:
    """Start run_search_task in background; return the asyncio Task."""
    return asyncio.create_task(
        run_search_task(
            task_id=task_id,
            keywords=keywords,
            platforms=platforms,
            max_count=max_count,
            enable_comments=enable_comments,
            enable_sub_comments=enable_sub_comments,
            time_range=time_range or "all",
            content_types=content_types,
        )
    )
