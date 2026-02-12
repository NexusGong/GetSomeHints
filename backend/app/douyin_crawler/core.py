# -*- coding: utf-8 -*-
"""抖音爬虫核心：启动浏览器、搜索、评论（从 MC 抽取，不依赖 bundle）。"""
import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from playwright.async_api import BrowserContext, BrowserType, async_playwright

from app.douyin_crawler import config
from app.douyin_crawler.base_crawler import AbstractCrawler
from app.douyin_crawler.client import DouYinClient
from app.douyin_crawler.exception import DataFetchError
from app.douyin_crawler.field import PublishTimeType, SearchChannelType
from app.douyin_crawler.login import DouYinLogin
from app.douyin_crawler.store import (
    _extract_note_image_list,
    _extract_video_download_url,
    batch_update_dy_aweme_comments,
    update_douyin_aweme,
)
from app.douyin_crawler.utils import format_proxy_info, logger

# 用户可读输出：同时推送到前端实时日志 + 后台控制台
_user_log = logging.getLogger("app.douyin_crawler")
_last_was_progress = False
REPLACE_ID_SEARCH_PROGRESS = "search_progress"


def _user_msg(msg: str, level: str = "info", platform: str = "抖音") -> None:
    global _last_was_progress
    try:
        from app.services.ws_broadcast import push_log_sync
        if _last_was_progress:
            sys.stderr.write("\n")
            sys.stderr.flush()
            _last_was_progress = False
        push_log_sync(msg, level, platform)
    except Exception:
        pass
    _user_log.info("[抖音] %s", msg)


def _user_progress(msg: str, platform: str = "抖音") -> None:
    """推送“正在搜索第 N 条”，实时日志与终端均原地更新。"""
    global _last_was_progress
    try:
        from app.services.ws_broadcast import push_log_sync
        push_log_sync(msg, "info", platform, replace_id=REPLACE_ID_SEARCH_PROGRESS)
    except Exception:
        pass
    sys.stderr.write("\r[%s] %s   \r" % (platform, msg))
    sys.stderr.flush()
    _last_was_progress = True


class DouYinCrawler(AbstractCrawler):
    context_page = None
    dy_client: Optional[DouYinClient] = None
    browser_context: Optional[BrowserContext] = None
    ip_proxy_pool = None

    def __init__(self) -> None:
        self.index_url = "https://www.douyin.com"

    async def start(self) -> None:
        playwright_proxy, httpx_proxy = None, None
        if config.ENABLE_IP_PROXY:
            from app.proxy.proxy_ip_pool import create_ip_pool
            self.ip_proxy_pool = await create_ip_pool(
                ip_pool_count=config.IP_PROXY_POOL_COUNT,
                enable_validate_ip=True,
            )
            ip_info = await self.ip_proxy_pool.get_proxy()
            playwright_proxy, httpx_proxy = format_proxy_info(ip_info)

        async with async_playwright() as playwright:
            chromium = playwright.chromium
            logger.info("[DouYinCrawler] 使用标准模式启动浏览器")
            self.browser_context = await self.launch_browser(
                chromium, playwright_proxy, None, headless=config.HEADLESS
            )
            try:
                stealth_path = os.path.join(os.path.dirname(__file__), "libs", "stealth.min.js")
                if os.path.isfile(stealth_path):
                    await self.browser_context.add_init_script(path=stealth_path)
            except Exception:
                pass
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            self.dy_client = await self._create_douyin_client(httpx_proxy)
            if not await self.dy_client.pong(self.browser_context):
                login_obj = DouYinLogin(
                    login_type=config.LOGIN_TYPE,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    login_phone="",
                    cookie_str=config.COOKIES,
                )
                await login_obj.begin()
                await self.dy_client.update_cookies(self.browser_context)

            from app.douyin_crawler.var import crawler_type_var
            crawler_type_var.set(config.CRAWLER_TYPE)

            if config.CRAWLER_TYPE == "search":
                await self.search()
            elif config.CRAWLER_TYPE == "detail":
                await self.get_specified_awemes()
            elif config.CRAWLER_TYPE == "creator":
                await self.get_creators_and_videos()

            _user_msg("爬取流程结束")

    async def search(self) -> None:
        from app.douyin_crawler.var import request_keyword_var, source_keyword_var

        # 运行时从环境变量读取，确保 douyin.py 注入的关键词/时间/条数生效（config 在 import 时已固化）
        keywords_str = os.environ.get("MC_KEYWORDS", "热门").strip() or "热门"
        publish_time_type = int(os.environ.get("MC_PUBLISH_TIME_TYPE", "0"))
        max_notes = max(1, int(os.environ.get("CRAWLER_MAX_NOTES_COUNT", "15")))
        start_page = int(os.environ.get("MC_START_PAGE", "1"))

        _user_msg("开始搜索关键词: %s" % keywords_str)
        dy_limit = 10
        for keyword in [k.strip() for k in keywords_str.split(",") if k.strip()]:
            source_keyword_var.set(keyword)
            request_keyword_var.set(keyword)
            _user_msg("正在搜索: 「%s」" % keyword)
            aweme_list: List[str] = []
            page = 0
            dy_search_id = ""
            while (page - start_page + 1) * dy_limit <= max_notes:
                if page < start_page:
                    page += 1
                    continue
                try:
                    search_channel_str = os.environ.get("MC_SEARCH_CHANNEL", "aweme_general")
                    search_channel = (
                        SearchChannelType.VIDEO
                        if search_channel_str == "aweme_video_web"
                        else SearchChannelType.GENERAL
                    )
                    posts_res = await self.dy_client.search_info_by_keyword(
                        keyword=keyword,
                        offset=page * dy_limit - dy_limit,
                        search_channel=search_channel,
                        publish_time=PublishTimeType(publish_time_type),
                        search_id=dy_search_id,
                    )
                    data = posts_res.get("data")
                    if data is None or data == []:
                        # 与「获取」一致：start_page 下 page 已是 1-based 语义
                        _user_msg("第 %d 页无结果" % page)
                        break
                except DataFetchError:
                    _user_msg("搜索「%s」请求失败" % keyword, level="error")
                    break

                # start_page 跳过导致首次请求时 page 已是 1，故直接用 page 作为 1-based 页码
                current_page_one_based = page
                page += 1
                if "data" not in posts_res:
                    break
                dy_search_id = posts_res.get("extra", {}).get("logid", "")
                data_list = posts_res.get("data", [])
                remaining = max_notes - len(aweme_list)
                if remaining <= 0:
                    break
                page_aweme_list = []
                for post_item in data_list[:remaining]:
                    try:
                        aweme_info = post_item.get("aweme_info") or (post_item.get("aweme_mix_info") or {}).get("mix_items", [{}])[0]
                    except (TypeError, IndexError):
                        continue
                    aweme_id = aweme_info.get("aweme_id", "")
                    aweme_list.append(aweme_id)
                    page_aweme_list.append(aweme_id)
                    _user_progress("正在搜索第 %d 条" % len(aweme_list))
                    await update_douyin_aweme(aweme_item=aweme_info)
                    await self.get_aweme_media(aweme_item=aweme_info)
                await self.batch_get_note_comments(page_aweme_list)
                _user_msg("第 %d 页获取 %d 条" % (current_page_one_based, len(page_aweme_list)))
                if len(aweme_list) >= max_notes:
                    break
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
            _user_msg("关键词「%s」共 %d 条" % (keyword, len(aweme_list)), level="success")

    async def get_aweme_media(self, aweme_item: Dict) -> None:
        if not config.ENABLE_GET_MEIDAS:
            return
        note_urls = _extract_note_image_list(aweme_item)
        video_url = _extract_video_download_url(aweme_item)
        if note_urls:
            await self._get_aweme_images(aweme_item)
        elif video_url:
            await self._get_aweme_video(aweme_item)

    async def _get_aweme_images(self, aweme_item: Dict) -> None:
        if not config.ENABLE_GET_MEIDAS:
            return
        from app.douyin_crawler.store import update_dy_aweme_image
        aweme_id = aweme_item.get("aweme_id")
        urls = _extract_note_image_list(aweme_item)
        for i, url in enumerate(urls):
            if not url:
                continue
            content = await self.dy_client.get_aweme_media(url)
            if content:
                await update_dy_aweme_image(aweme_id, content, f"{i:>03d}.jpeg")

    async def _get_aweme_video(self, aweme_item: Dict) -> None:
        if not config.ENABLE_GET_MEIDAS:
            return
        from app.douyin_crawler.store import update_dy_aweme_video
        aweme_id = aweme_item.get("aweme_id")
        url = _extract_video_download_url(aweme_item)
        if not url:
            return
        content = await self.dy_client.get_aweme_media(url)
        if content:
            await update_dy_aweme_video(aweme_id, content, "video.mp4")

    async def batch_get_note_comments(self, aweme_list: List[str]) -> None:
        if not config.ENABLE_GET_COMMENTS:
            return
        sem = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
        tasks = [self.get_comments(aid, sem) for aid in aweme_list]
        if tasks:
            await asyncio.gather(*tasks)

    async def get_comments(self, aweme_id: str, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            try:
                await self.dy_client.get_aweme_all_comments(
                    aweme_id=aweme_id,
                    crawl_interval=config.CRAWLER_MAX_SLEEP_SEC,
                    is_fetch_sub_comments=config.ENABLE_GET_SUB_COMMENTS,
                    callback=batch_update_dy_aweme_comments,
                    max_count=config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
                )
                await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
            except DataFetchError as e:
                logger.error("[DouYinCrawler.get_comments] aweme_id %s failed: %s", aweme_id, e)

    async def get_specified_awemes(self) -> None:
        pass  # 需要 DY_SPECIFIED_ID_LIST 等，可后续扩展

    async def get_creators_and_videos(self) -> None:
        pass  # 可后续扩展

    async def _create_douyin_client(self, httpx_proxy: Optional[str]) -> DouYinClient:
        from app.douyin_crawler.utils import convert_cookies
        cookie_str, cookie_dict = convert_cookies(await self.browser_context.cookies())
        ua = await self.context_page.evaluate("() => navigator.userAgent")
        headers = {
            "User-Agent": ua,
            "Cookie": cookie_str,
            "Host": "www.douyin.com",
            "Origin": "https://www.douyin.com/",
            "Referer": "https://www.douyin.com/",
            "Content-Type": "application/json;charset=UTF-8",
        }
        return DouYinClient(
            proxy=httpx_proxy,
            headers=headers,
            playwright_page=self.context_page,
            cookie_dict=cookie_dict,
            proxy_ip_pool=self.ip_proxy_pool,
        )

    async def launch_browser(
        self,
        chromium: BrowserType,
        playwright_proxy: Optional[Dict],
        user_agent: Optional[str],
        headless: bool = True,
    ) -> BrowserContext:
        if config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(config.BROWSER_DATA_BASE, config.USER_DATA_DIR % config.PLATFORM)
            return await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent,
            )
        browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
        return await browser.new_context(viewport={"width": 1920, "height": 1080}, user_agent=user_agent)

    async def close(self) -> None:
        if self.browser_context:
            try:
                await self.browser_context.close()
            except Exception as e:
                logger.debug("[DouYinCrawler.close] close ignored: %s", e)
            self.browser_context = None
        logger.info("[DouYinCrawler.close] Browser context closed ...")
