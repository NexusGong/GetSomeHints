# -*- coding: utf-8 -*-
"""Runs crawlers per platform and updates task state."""
import asyncio
import logging
from typing import List

from app.config import settings
from app.services.task_manager import task_manager
from app.services.ws_broadcast import broadcast, drain_pending_logs

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
    await task_manager.set_running(task_id)
    platform_names = "、".join(PLATFORM_LABEL.get(p, p) for p in platforms)
    await broadcast("搜索开始：关键词「%s」 平台 %s" % (keywords, platform_names), "info")
    logger.info("搜索开始 task_id=%s 关键词=%s 平台=%s max_count=%d", task_id[:8], keywords, platforms, max_count)
    total = 0
    by_platform: dict = {p: 0 for p in platforms}

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
                if crawler_cls:
                    platform_label = PLATFORM_LABEL.get(platform, platform)
                    await broadcast(f"开始爬取 {platform_label}...", "info", platform=platform_label)
                    logger.info("开始爬取 %s…", platform_label)
                    posts = []
                    run_sync = getattr(crawler_cls, "run_search_sync", None)
                    if callable(run_sync):
                        # 使用平台适配器：dy/xhs 等在独立线程中运行，返回已挂评论的 UnifiedPost
                        limit = min(max_count, settings.CRAWLER_MAX_NOTES_COUNT)
                        task = asyncio.create_task(
                            asyncio.to_thread(
                                run_sync,
                                keywords,
                                limit,
                                enable_comments,
                                20 if enable_comments else 0,
                                time_range,
                                content_types or ["video", "image_text", "link"],
                            )
                        )
                        while not task.done():
                            for item in drain_pending_logs():
                                msg, level, plat = item[0], item[1], item[2]
                                rid = item[3] if len(item) > 3 else None
                                await broadcast(msg, level, plat, rid)
                            await asyncio.sleep(0.4)
                        posts = task.result()
                    else:
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
                        await broadcast(f"{platform_label} 已获取 {count} 条", "success", platform=platform_label)
                        logger.info("%s 已获取 %d 条", platform_label, count)
                    else:
                        await broadcast(f"{platform_label} 本页无新结果", "info", platform=platform_label)
                        logger.info("%s 本页无新结果", platform_label)
                    consecutive_failures = 0
                else:
                    pass
                idx = platforms.index(platform) + 1
                progress = int(100 * idx / len(platforms)) if platforms else 0
                # 使用去重后的实际条数作为 total_found，与前端「本页结果」一致
                actual_total = len(task_manager.get_results(task_id))
                await task_manager.set_progress(task_id, actual_total, by_platform, progress=progress)
            except Exception as e:
                logger.exception("[Crawler] platform %s failed: %s", platform, e)
                platform_label = PLATFORM_LABEL.get(platform, platform)
                await broadcast("%s 爬取失败: %s" % (platform_label, e), "error", platform=platform_label)
                logger.warning("%s 爬取失败: %s", platform_label, e)
                consecutive_failures += 1
                if proxy_pool:
                    proxy_pool.invalidate_current()
                by_platform[platform] = 0
                actual_total = len(task_manager.get_results(task_id))
                await task_manager.set_progress(task_id, actual_total, by_platform)
                if consecutive_failures >= max_failures_before_skip:
                    break

        actual_total = len(task_manager.get_results(task_id))
        await task_manager.set_completed(task_id, actual_total, by_platform)
        await broadcast("爬取结束，共 %d 条" % actual_total, "success")
        logger.info("爬取结束 task_id=%s 共 %d 条 %s", task_id[:8], actual_total, by_platform)
    except asyncio.CancelledError:
        await task_manager.set_stopped(task_id)
        logger.info("搜索已取消 task_id=%s", task_id[:8])
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
