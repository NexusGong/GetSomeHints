# -*- coding: utf-8 -*-
"""小红书爬虫核心：启动浏览器、搜索、评论（从 MC 抽取，不依赖 bundle）。"""
import asyncio
import logging
import os
import random
import sys
from typing import Dict, List, Optional

from playwright.async_api import BrowserContext, BrowserType, Page, async_playwright
from tenacity import RetryError

from app.xhs_crawler import config as xhs_config
from app.xhs_crawler.client import XiaoHongShuClient
from app.xhs_crawler.exception import DataFetchError, NoteNotFoundError
from app.xhs_crawler.field import SearchNoteType, SearchSortType
from app.xhs_crawler.help import get_search_id, parse_creator_info_from_url, parse_note_info_from_note_url
from app.xhs_crawler.login import XiaoHongShuLogin
from app.xhs_crawler.store import (
    batch_update_xhs_note_comments,
    get_video_url_arr,
    update_xhs_note,
)
from app.xhs_crawler.utils import convert_cookies, logger

# 与 douyin_crawler 一致的抽象（仅接口）
from app.douyin_crawler.base_crawler import AbstractCrawler

_user_log = logging.getLogger("app.xhs_crawler")
_last_was_progress = False
REPLACE_ID_SEARCH_PROGRESS = "search_progress"


def _user_msg(msg: str, level: str = "info", platform: str = "小红书") -> None:
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
    _user_log.info("[小红书] %s", msg)


def _user_progress(msg: str, platform: str = "小红书") -> None:
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


class XiaoHongShuCrawler(AbstractCrawler):
    context_page: Optional[Page] = None
    xhs_client: Optional[XiaoHongShuClient] = None
    browser_context: Optional[BrowserContext] = None
    ip_proxy_pool = None

    def __init__(self) -> None:
        self.index_url = "https://www.xiaohongshu.com"
        self.user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        )

    async def start(self) -> None:
        playwright_proxy_format: Optional[Dict] = None
        httpx_proxy_format: Optional[str] = None
        if xhs_config.ENABLE_IP_PROXY:
            from app.proxy.proxy_ip_pool import create_ip_pool
            from app.douyin_crawler.utils import format_proxy_info
            self.ip_proxy_pool = await create_ip_pool(
                ip_pool_count=xhs_config.IP_PROXY_POOL_COUNT,
                enable_validate_ip=True,
            )
            ip_info = await self.ip_proxy_pool.get_proxy()
            playwright_proxy_format, httpx_proxy_format = format_proxy_info(ip_info)

        async with async_playwright() as playwright:
            chromium = playwright.chromium
            _user_msg("正在启动浏览器")
            self.browser_context = await self.launch_browser(
                chromium,
                playwright_proxy_format,
                self.user_agent,
                headless=xhs_config.HEADLESS,
            )
            try:
                stealth_path = os.path.join(os.path.dirname(__file__), "libs", "stealth.min.js")
                if os.path.isfile(stealth_path):
                    await self.browser_context.add_init_script(path=stealth_path)
            except Exception:
                pass
            self.context_page = await self.browser_context.new_page()
            await self.context_page.goto(self.index_url)

            self.xhs_client = await self.create_xhs_client(httpx_proxy_format)
            if not await self.xhs_client.pong():
                login_obj = XiaoHongShuLogin(
                    login_type=xhs_config.LOGIN_TYPE,
                    browser_context=self.browser_context,
                    context_page=self.context_page,
                    login_phone="",
                    cookie_str=xhs_config.COOKIES,
                )
                await login_obj.begin()
                await self.xhs_client.update_cookies(self.browser_context)

            from app.xhs_crawler.var import crawler_type_var
            crawler_type_var.set(xhs_config.CRAWLER_TYPE)

            if xhs_config.CRAWLER_TYPE == "search":
                await self.search()
            # detail/creator 可后续按需扩展

            _user_msg("爬取流程结束")

    async def close(self) -> None:
        if self.browser_context:
            await self.browser_context.close()
            self.browser_context = None
        logger.info("[XiaoHongShuCrawler.close] Browser context closed ...")

    async def search(self) -> None:
        from app.xhs_crawler.var import source_keyword_var

        keywords_str = os.environ.get("MC_KEYWORDS", "热门").strip() or "热门"
        max_notes = max(20, int(os.environ.get("CRAWLER_MAX_NOTES_COUNT", "20")))
        start_page = int(os.environ.get("MC_START_PAGE", "1"))
        sort_type_str = os.environ.get("MC_SORT_TYPE", "general").strip() or "general"
        sort_type = SearchSortType(sort_type_str) if sort_type_str in [e.value for e in SearchSortType] else SearchSortType.GENERAL
        note_type_str = getattr(xhs_config, "NOTE_TYPE", "all").strip().lower() or "all"
        if note_type_str == "video":
            note_type = SearchNoteType.VIDEO
        elif note_type_str == "image":
            note_type = SearchNoteType.IMAGE
        else:
            note_type = SearchNoteType.ALL

        xhs_limit_count = 20
        total_count = 0
        _user_msg("开始搜索关键词: %s" % keywords_str)
        for keyword in [k.strip() for k in keywords_str.split(",") if k.strip()]:
            source_keyword_var.set(keyword)
            _user_msg("正在搜索: 「%s」" % keyword)
            page = 1
            search_id = get_search_id()
            while (page - start_page + 1) * xhs_limit_count <= max_notes:
                if page < start_page:
                    page += 1
                    continue
                try:
                    _user_msg("正在获取第 %s 页 …" % page)
                    notes_res = await self.xhs_client.get_note_by_keyword(
                        keyword=keyword,
                        search_id=search_id,
                        page=page,
                        page_size=xhs_limit_count,
                        sort=sort_type,
                        note_type=note_type,
                    )
                    if not notes_res or not notes_res.get("has_more", False):
                        _user_msg("没有更多结果")
                        break
                    items = [
                        post_item
                        for post_item in notes_res.get("items", [])
                        if post_item.get("model_type") not in ("rec_query", "hot_query")
                    ]
                    if not items:
                        page += 1
                        await asyncio.sleep(xhs_config.CRAWLER_MAX_SLEEP_SEC)
                        continue
                    semaphore = asyncio.Semaphore(xhs_config.MAX_CONCURRENCY_NUM)
                    task_list = [
                        self.get_note_detail_async_task(
                            note_id=post_item.get("id"),
                            xsec_source=post_item.get("xsec_source", ""),
                            xsec_token=post_item.get("xsec_token", ""),
                            semaphore=semaphore,
                        )
                        for post_item in items
                    ]
                    note_details = await asyncio.gather(*task_list)
                    note_ids: List[str] = []
                    xsec_tokens: List[str] = []
                    for note_detail in note_details:
                        if note_detail:
                            await update_xhs_note(note_detail)
                            await self.get_notice_media(note_detail)
                            note_ids.append(note_detail.get("note_id", ""))
                            xsec_tokens.append(note_detail.get("xsec_token", ""))
                    total_count += len(note_ids)
                    _user_progress("正在搜索第 %d 条" % total_count)
                    _user_msg("本页获取 %s 条，关键词「%s」当前共 %s 条" % (len(note_ids), keyword, total_count))
                    await self.batch_get_note_comments(note_ids, xsec_tokens)
                    page += 1
                    await asyncio.sleep(xhs_config.CRAWLER_MAX_SLEEP_SEC)
                except DataFetchError as e:
                    logger.error("[XiaoHongShuCrawler.search] Get note detail error: %s", e)
                    break
        _user_msg("搜索完成")

    async def get_note_detail_async_task(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        semaphore: asyncio.Semaphore,
    ) -> Optional[Dict]:
        note_detail = None
        async with semaphore:
            try:
                try:
                    note_detail = await self.xhs_client.get_note_by_id(note_id, xsec_source, xsec_token)
                except RetryError:
                    pass
                if not note_detail:
                    note_detail = await self.xhs_client.get_note_by_id_from_html(
                        note_id, xsec_source, xsec_token, enable_cookie=True
                    )
                    if not note_detail:
                        raise Exception("Failed to get note detail, Id: %s" % note_id)
                note_detail = dict(note_detail)
                note_detail.update({"xsec_token": xsec_token, "xsec_source": xsec_source})
                await asyncio.sleep(xhs_config.CRAWLER_MAX_SLEEP_SEC)
                return note_detail
            except NoteNotFoundError:
                logger.warning("[XiaoHongShuCrawler] Note not found: %s", note_id)
                return None
            except DataFetchError as e:
                logger.error("[XiaoHongShuCrawler] Get note detail error: %s", e)
                return None
            except KeyError as e:
                logger.error("[XiaoHongShuCrawler] note detail key error note_id:%s err:%s", note_id, e)
                return None

    async def batch_get_note_comments(self, note_list: List[str], xsec_tokens: List[str]) -> None:
        if not xhs_config.ENABLE_GET_COMMENTS:
            return
        semaphore = asyncio.Semaphore(xhs_config.MAX_CONCURRENCY_NUM)
        task_list = [
            asyncio.create_task(
                self.get_comments(note_id=note_id, xsec_token=xsec_tokens[i], semaphore=semaphore),
                name=note_id,
            )
            for i, note_id in enumerate(note_list)
        ]
        await asyncio.gather(*task_list)

    async def get_comments(self, note_id: str, xsec_token: str, semaphore: asyncio.Semaphore) -> None:
        async with semaphore:
            await self.xhs_client.get_note_all_comments(
                note_id=note_id,
                xsec_token=xsec_token,
                crawl_interval=float(xhs_config.CRAWLER_MAX_SLEEP_SEC),
                callback=batch_update_xhs_note_comments,
                max_count=xhs_config.CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES,
            )
            await asyncio.sleep(xhs_config.CRAWLER_MAX_SLEEP_SEC)

    async def create_xhs_client(self, httpx_proxy: Optional[str]) -> XiaoHongShuClient:
        cookie_str, cookie_dict = convert_cookies(await self.browser_context.cookies())
        return XiaoHongShuClient(
            proxy=httpx_proxy,
            headers={
                "accept": "application/json, text/plain, */*",
                "accept-language": "zh-CN,zh;q=0.9",
                "cache-control": "no-cache",
                "content-type": "application/json;charset=UTF-8",
                "origin": "https://www.xiaohongshu.com",
                "pragma": "no-cache",
                "priority": "u=1, i",
                "referer": "https://www.xiaohongshu.com/",
                "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-site",
                "user-agent": self.user_agent,
                "Cookie": cookie_str,
            },
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
        if xhs_config.SAVE_LOGIN_STATE:
            user_data_dir = os.path.join(
                xhs_config.BROWSER_DATA_BASE, xhs_config.USER_DATA_DIR % xhs_config.PLATFORM
            )
            return await chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                accept_downloads=True,
                headless=headless,
                proxy=playwright_proxy,
                viewport={"width": 1920, "height": 1080},
                user_agent=user_agent or self.user_agent,
            )
        browser = await chromium.launch(headless=headless, proxy=playwright_proxy)
        return await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=user_agent or self.user_agent,
        )

    async def get_notice_media(self, note_detail: Dict) -> None:
        if not xhs_config.ENABLE_GET_MEIDAS:
            return
        note_id = note_detail.get("note_id")
        image_list: List[Dict] = note_detail.get("image_list", [])
        for img in image_list:
            if img.get("url_default"):
                img["url"] = img.get("url_default")
        pic_num = 0
        for pic in image_list:
            url = pic.get("url")
            if not url:
                continue
            content = await self.xhs_client.get_note_media(url)
            await asyncio.sleep(random.random())
            if content is None:
                continue
            from app.xhs_crawler import store as xhs_store
            await xhs_store.update_xhs_note_image(note_id, content, f"{pic_num}.jpg")
            pic_num += 1
        videos = get_video_url_arr(note_detail)
        video_num = 0
        for url in videos:
            content = await self.xhs_client.get_note_media(url)
            await asyncio.sleep(random.random())
            if content is None:
                continue
            from app.xhs_crawler import store as xhs_store
            await xhs_store.update_xhs_note_video(note_id, content, f"{video_num}.mp4")
            video_num += 1
