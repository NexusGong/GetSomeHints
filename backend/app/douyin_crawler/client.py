# -*- coding: utf-8 -*-
"""抖音 Web API 客户端（从 MC 抽取，依赖 playwright 页面取 cookie/UA）。"""
import asyncio
import copy
import json
import urllib.parse
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

import httpx
from playwright.async_api import BrowserContext

from app.douyin_crawler.exception import DataFetchError
from app.douyin_crawler.field import PublishTimeType, SearchChannelType, SearchSortType
from app.douyin_crawler.help import get_a_bogus, get_web_id
from app.douyin_crawler.utils import convert_cookies, logger
from app.douyin_crawler.var import request_keyword_var
from app.proxy.proxy_mixin import ProxyRefreshMixin

if TYPE_CHECKING:
    from playwright.async_api import Page


class DouYinClient(ProxyRefreshMixin):
    def __init__(
        self,
        timeout: int = 60,
        proxy: Optional[str] = None,
        *,
        headers: Dict,
        playwright_page: Optional["Page"],
        cookie_dict: Dict,
        proxy_ip_pool=None,
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.headers = headers
        self._host = "https://www.douyin.com"
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        if hasattr(self, "init_proxy_pool"):
            self.init_proxy_pool(proxy_ip_pool)

    async def _process_req_params(
        self,
        uri: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        request_method: str = "GET",
    ) -> None:
        if not params:
            return
        headers = headers or self.headers
        local_storage: Dict = await self.playwright_page.evaluate("() => window.localStorage")  # type: ignore
        common = {
            "device_platform": "webapp",
            "aid": "6383",
            "channel": "channel_pc_web",
            "version_code": "190600",
            "version_name": "19.6.0",
            "update_version_code": "170400",
            "pc_client_type": "1",
            "cookie_enabled": "true",
            "browser_language": "zh-CN",
            "browser_platform": "MacIntel",
            "browser_name": "Chrome",
            "browser_version": "125.0.0.0",
            "browser_online": "true",
            "engine_name": "Blink",
            "os_name": "Mac OS",
            "os_version": "10.15.7",
            "cpu_core_num": "8",
            "device_memory": "8",
            "engine_version": "109.0",
            "platform": "PC",
            "screen_width": "2560",
            "screen_height": "1440",
            "effective_type": "4g",
            "round_trip_time": "50",
            "webid": get_web_id(),
            "msToken": local_storage.get("xmst"),
        }
        params.update(common)
        query_string = urllib.parse.urlencode(params)
        post_data = params if request_method == "POST" else {}
        if "/v1/web/general/search" not in uri:
            a_bogus = await get_a_bogus(uri, query_string, post_data, headers["User-Agent"], self.playwright_page)
            params["a_bogus"] = a_bogus

    async def request(self, method: str, url: str, **kwargs) -> Any:
        if hasattr(self, "_refresh_proxy_if_expired"):
            await self._refresh_proxy_if_expired()
        async with httpx.AsyncClient(proxy=self.proxy, timeout=self.timeout) as client:
            response = await client.request(method, url, **kwargs)
        if response.text in ("", "blocked"):
            raise DataFetchError(f"response: {response.text}")
        try:
            return response.json()
        except Exception as e:
            raise DataFetchError(f"{e}, {response.text}")

    async def get(self, uri: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Any:
        await self._process_req_params(uri, params, headers)
        headers = headers or self.headers
        return await self.request("GET", f"{self._host}{uri}", params=params, headers=headers)

    async def post(self, uri: str, data: dict, headers: Optional[Dict] = None) -> Any:
        await self._process_req_params(uri, data, headers, "POST")
        headers = headers or self.headers
        return await self.request("POST", f"{self._host}{uri}", data=data, headers=headers)

    async def pong(self, browser_context: BrowserContext) -> bool:
        local_storage = await self.playwright_page.evaluate("() => window.localStorage")  # type: ignore
        if local_storage.get("HasUserLogin", "") == "1":
            return True
        _, cookie_dict = convert_cookies(await browser_context.cookies())
        return cookie_dict.get("LOGIN_STATUS") == "1"

    async def update_cookies(self, browser_context: BrowserContext) -> None:
        cookie_str, cookie_dict = convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def search_info_by_keyword(
        self,
        keyword: str,
        offset: int = 0,
        search_channel: SearchChannelType = SearchChannelType.GENERAL,
        sort_type: SearchSortType = SearchSortType.GENERAL,
        publish_time: PublishTimeType = PublishTimeType.UNLIMITED,
        search_id: str = "",
    ) -> Dict:
        query_params = {
            "search_channel": search_channel.value,
            "enable_history": "1",
            "keyword": keyword,
            "search_source": "tab_search",
            "query_correct_type": "1",
            "is_filter_search": "0",
            "from_group_id": "7378810571505847586",
            "offset": offset,
            "count": "15",
            "need_filter_settings": "1",
            "list_type": "multi",
            "search_id": search_id,
        }
        if sort_type != SearchSortType.GENERAL or publish_time != PublishTimeType.UNLIMITED:
            query_params["filter_selected"] = json.dumps({"sort_type": str(sort_type.value), "publish_time": str(publish_time.value)})
            query_params["is_filter_search"] = 1
        referer_url = f"https://www.douyin.com/search/{keyword}?aid=f594bbd9-a0e2-4651-9319-ebe3cb6298c1&type=general"
        headers = copy.copy(self.headers)
        headers["Referer"] = urllib.parse.quote(referer_url, safe=":/")
        return await self.get("/aweme/v1/web/general/search/single/", query_params, headers=headers)

    async def get_video_by_id(self, aweme_id: str) -> Any:
        params = {"aweme_id": aweme_id}
        headers = copy.copy(self.headers)
        headers.pop("Origin", None)
        res = await self.get("/aweme/v1/web/aweme/detail/", params, headers=headers)
        return res.get("aweme_detail", {})

    async def get_aweme_comments(self, aweme_id: str, cursor: int = 0) -> Dict:
        uri = "/aweme/v1/web/comment/list/"
        params = {"aweme_id": aweme_id, "cursor": cursor, "count": 20, "item_type": 0}
        keywords = request_keyword_var.get()
        referer_url = "https://www.douyin.com/search/" + keywords + "?aid=3a3cec5a-9e27-4040-b6aa-ef548c2c1138&publish_time=0&sort_type=0&source=search_history&type=general"
        headers = copy.copy(self.headers)
        headers["Referer"] = urllib.parse.quote(referer_url, safe=":/")
        return await self.get(uri, params, headers=headers)

    async def get_sub_comments(self, aweme_id: str, comment_id: str, cursor: int = 0) -> Dict:
        uri = "/aweme/v1/web/comment/list/reply/"
        params = {"comment_id": comment_id, "cursor": cursor, "count": 20, "item_type": 0, "item_id": aweme_id}
        keywords = request_keyword_var.get()
        referer_url = "https://www.douyin.com/search/" + keywords + "?aid=3a3cec5a-9e27-4040-b6aa-ef548c2c1138&publish_time=0&sort_type=0&source=search_history&type=general"
        headers = copy.copy(self.headers)
        headers["Referer"] = urllib.parse.quote(referer_url, safe=":/")
        return await self.get(uri, params, headers=headers)

    async def get_aweme_all_comments(
        self,
        aweme_id: str,
        crawl_interval: float = 1.0,
        is_fetch_sub_comments: bool = False,
        callback: Optional[Callable] = None,
        max_count: int = 10,
    ) -> List:
        result = []
        comments_has_more = 1
        comments_cursor = 0
        while comments_has_more and len(result) < max_count:
            comments_res = await self.get_aweme_comments(aweme_id, comments_cursor)
            comments_has_more = comments_res.get("has_more", 0)
            comments_cursor = comments_res.get("cursor", 0)
            comments = comments_res.get("comments", [])
            if not comments:
                continue
            if len(result) + len(comments) > max_count:
                comments = comments[: max_count - len(result)]
            result.extend(comments)
            if callback:
                await callback(aweme_id, comments)
            await asyncio.sleep(crawl_interval)
            if not is_fetch_sub_comments:
                continue
            for comment in comments:
                reply_total = comment.get("reply_comment_total", 0)
                if reply_total <= 0:
                    continue
                cid = comment.get("cid")
                sub_has_more, sub_cursor = 1, 0
                while sub_has_more:
                    sub_res = await self.get_sub_comments(aweme_id, str(cid), sub_cursor)
                    sub_has_more = sub_res.get("has_more", 0)
                    sub_cursor = sub_res.get("cursor", 0)
                    sub_comments = sub_res.get("comments", [])
                    if sub_comments:
                        result.extend(sub_comments)
                        if callback:
                            await callback(aweme_id, sub_comments)
                    await asyncio.sleep(crawl_interval)
        return result

    async def get_user_info(self, sec_user_id: str) -> Dict:
        uri = "/aweme/v1/web/user/profile/other/"
        params = {"sec_user_id": sec_user_id, "publish_video_strategy_type": 2, "personal_center_strategy": 1}
        return await self.get(uri, params)

    async def get_aweme_media(self, url: str) -> Optional[bytes]:
        async with httpx.AsyncClient(proxy=self.proxy, timeout=self.timeout) as client:
            try:
                r = await client.get(url, follow_redirects=True)
                r.raise_for_status()
                return r.content if r.reason_phrase == "OK" else None
            except httpx.HTTPError as e:
                logger.error("[DouYinClient.get_aweme_media] %s - %s", type(e).__name__, e)
                return None
