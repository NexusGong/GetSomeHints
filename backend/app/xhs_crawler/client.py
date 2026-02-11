# -*- coding: utf-8 -*-
"""小红书 Web API 客户端（从 MC 抽取，依赖 playwright 签名）。"""
import asyncio
import json
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

import httpx
from playwright.async_api import BrowserContext, Page
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type

from app.xhs_crawler import config as xhs_config
from app.xhs_crawler.exception import DataFetchError, IPBlockError, NoteNotFoundError
from app.xhs_crawler.extractor import XiaoHongShuExtractor
from app.xhs_crawler.field import SearchNoteType, SearchSortType
from app.xhs_crawler.help import get_search_id
from app.xhs_crawler.playwright_sign import sign_with_playwright
from app.xhs_crawler.utils import convert_cookies, logger
from app.proxy.proxy_mixin import ProxyRefreshMixin

if TYPE_CHECKING:
    from app.proxy.proxy_ip_pool import ProxyIpPool


class XiaoHongShuClient(ProxyRefreshMixin):
    def __init__(
        self,
        timeout: int = 60,
        proxy: Optional[str] = None,
        *,
        headers: Dict[str, str],
        playwright_page: Page,
        cookie_dict: Dict[str, str],
        proxy_ip_pool: Optional["ProxyIpPool"] = None,
    ):
        self.proxy = proxy
        self.timeout = timeout
        self.headers = headers
        self._host = "https://edith.xiaohongshu.com"
        self._domain = "https://www.xiaohongshu.com"
        self.IP_ERROR_STR = "Network connection error, please check network settings or restart"
        self.IP_ERROR_CODE = 300012
        self.NOTE_NOT_FOUND_CODE = -510000
        self.NOTE_ABNORMAL_CODE = -510001
        self.playwright_page = playwright_page
        self.cookie_dict = cookie_dict
        self._extractor = XiaoHongShuExtractor()
        self.init_proxy_pool(proxy_ip_pool)

    async def _pre_headers(
        self, url: str, params: Optional[Dict] = None, payload: Optional[Dict] = None
    ) -> Dict:
        a1_value = self.cookie_dict.get("a1", "")
        if params is not None:
            data = params
            method = "GET"
        elif payload is not None:
            data = payload
            method = "POST"
        else:
            raise ValueError("params or payload is required")
        signs = await sign_with_playwright(
            page=self.playwright_page, uri=url, data=data, a1=a1_value, method=method
        )
        headers = {
            "X-S": signs["x-s"],
            "X-T": signs["x-t"],
            "x-S-Common": signs["x-s-common"],
            "X-B3-Traceid": signs["x-b3-traceid"],
        }
        self.headers.update(headers)
        return self.headers

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_not_exception_type(NoteNotFoundError),
    )
    async def request(self, method: str, url: str, **kwargs) -> Union[str, Any]:
        await self._refresh_proxy_if_expired()
        return_response = kwargs.pop("return_response", False)
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)
        if response.status_code in (471, 461):
            verify_type = response.headers.get("Verifytype", "")
            verify_uuid = response.headers.get("Verifyuuid", "")
            msg = f"CAPTCHA appeared, request failed, Verifytype: {verify_type}, Verifyuuid: {verify_uuid}"
            logger.error(msg)
            raise Exception(msg)
        if return_response:
            return response.text
        data: Dict = response.json()
        if data.get("success"):
            return data.get("data", data.get("success", {}))
        if data.get("code") == self.IP_ERROR_CODE:
            raise IPBlockError(self.IP_ERROR_STR)
        if data.get("code") in (self.NOTE_NOT_FOUND_CODE, self.NOTE_ABNORMAL_CODE):
            raise NoteNotFoundError(f"Note not found or abnormal, code: {data.get('code')}")
        err_msg = data.get("msg") or response.text
        raise DataFetchError(err_msg)

    async def get(self, uri: str, params: Optional[Dict] = None) -> Dict:
        headers = await self._pre_headers(uri, params=params)
        full_url = f"{self._host}{uri}"
        return await self.request(method="GET", url=full_url, headers=headers, params=params)

    async def post(self, uri: str, data: dict, **kwargs) -> Dict:
        headers = await self._pre_headers(uri, payload=data)
        json_str = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return await self.request(
            method="POST",
            url=f"{self._host}{uri}",
            data=json_str,
            headers=headers,
            **kwargs,
        )

    async def get_note_media(self, url: str) -> Optional[bytes]:
        await self._refresh_proxy_if_expired()
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            try:
                response = await client.request("GET", url, timeout=self.timeout)
                response.raise_for_status()
                if response.reason_phrase != "OK":
                    logger.error(f"[XiaoHongShuClient.get_note_media] request {url} err, res:{response.text}")
                    return None
                return response.content
            except httpx.HTTPError as exc:
                logger.error(f"[XiaoHongShuClient.get_note_media] {exc.__class__.__name__} - {exc}")
                return None

    async def update_cookies(self, browser_context: BrowserContext) -> None:
        cookie_str, cookie_dict = convert_cookies(await browser_context.cookies())
        self.headers["Cookie"] = cookie_str
        self.cookie_dict = cookie_dict

    async def query_self(self) -> Optional[Dict]:
        uri = "/api/sns/web/v1/user/selfinfo"
        headers = await self._pre_headers(uri, params={})
        await self._refresh_proxy_if_expired()
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.get(f"{self._host}{uri}", headers=headers, timeout=self.timeout)
        if response.status_code == 200:
            return response.json()
        return None

    async def pong(self) -> bool:
        logger.info("[XiaoHongShuClient.pong] Begin to check login state...")
        try:
            self_info = await self.query_self()
            if self_info and self_info.get("data", {}).get("result", {}).get("success"):
                logger.info("[XiaoHongShuClient.pong] Login state result: True")
                return True
        except Exception as e:
            logger.error("[XiaoHongShuClient.pong] Check login state failed: %s", e)
        logger.info("[XiaoHongShuClient.pong] Login state result: False")
        return False

    async def get_note_by_keyword(
        self,
        keyword: str,
        search_id: str = None,
        page: int = 1,
        page_size: int = 20,
        sort: SearchSortType = SearchSortType.GENERAL,
        note_type: SearchNoteType = SearchNoteType.ALL,
    ) -> Dict:
        if search_id is None:
            search_id = get_search_id()
        uri = "/api/sns/web/v1/search/notes"
        data = {
            "keyword": keyword,
            "page": page,
            "page_size": page_size,
            "search_id": search_id,
            "sort": sort.value,
            "note_type": note_type.value,
        }
        return await self.post(uri, data)

    async def get_note_by_id(
        self, note_id: str, xsec_source: str, xsec_token: str
    ) -> Dict:
        if xsec_source == "":
            xsec_source = "pc_search"
        data = {
            "source_note_id": note_id,
            "image_formats": ["jpg", "webp", "avif"],
            "extra": {"need_body_topic": 1},
            "xsec_source": xsec_source,
            "xsec_token": xsec_token,
        }
        uri = "/api/sns/web/v1/feed"
        res = await self.post(uri, data)
        if res and res.get("items"):
            return res["items"][0]["note_card"]
        logger.error(f"[XiaoHongShuClient.get_note_by_id] get note id:{note_id} empty and res:{res}")
        return {}

    async def get_note_comments(
        self, note_id: str, xsec_token: str, cursor: str = ""
    ) -> Dict:
        uri = "/api/sns/web/v2/comment/page"
        params = {
            "note_id": note_id,
            "cursor": cursor,
            "top_comment_id": "",
            "image_formats": "jpg,webp,avif",
            "xsec_token": xsec_token,
        }
        return await self.get(uri, params)

    async def get_note_sub_comments(
        self,
        note_id: str,
        root_comment_id: str,
        xsec_token: str,
        num: int = 10,
        cursor: str = "",
    ) -> Dict:
        uri = "/api/sns/web/v2/comment/sub/page"
        params = {
            "note_id": note_id,
            "root_comment_id": root_comment_id,
            "num": str(num),
            "cursor": cursor,
            "image_formats": "jpg,webp,avif",
            "top_comment_id": "",
            "xsec_token": xsec_token,
        }
        return await self.get(uri, params)

    async def get_note_all_comments(
        self,
        note_id: str,
        xsec_token: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
        max_count: int = 10,
    ) -> List[Dict]:
        result = []
        comments_has_more = True
        comments_cursor = ""
        while comments_has_more and len(result) < max_count:
            comments_res = await self.get_note_comments(
                note_id=note_id, xsec_token=xsec_token, cursor=comments_cursor
            )
            comments_has_more = comments_res.get("has_more", False)
            comments_cursor = comments_res.get("cursor", "")
            if "comments" not in comments_res:
                break
            comments = comments_res["comments"]
            if len(result) + len(comments) > max_count:
                comments = comments[: max_count - len(result)]
            if callback:
                await callback(note_id, comments)
            await asyncio.sleep(crawl_interval)
            result.extend(comments)
            sub_comments = await self.get_comments_all_sub_comments(
                comments=comments,
                xsec_token=xsec_token,
                crawl_interval=crawl_interval,
                callback=callback,
            )
            result.extend(sub_comments)
        return result

    async def get_comments_all_sub_comments(
        self,
        comments: List[Dict],
        xsec_token: str,
        crawl_interval: float = 1.0,
        callback: Optional[Callable] = None,
    ) -> List[Dict]:
        if not xhs_config.ENABLE_GET_SUB_COMMENTS:
            return []
        result = []
        for comment in comments:
            note_id = comment.get("note_id")
            sub_comments = comment.get("sub_comments")
            if sub_comments and callback:
                await callback(note_id, sub_comments)
            sub_comment_has_more = comment.get("sub_comment_has_more")
            if not sub_comment_has_more:
                continue
            root_comment_id = comment.get("id")
            sub_comment_cursor = comment.get("sub_comment_cursor")
            while sub_comment_has_more:
                comments_res = await self.get_note_sub_comments(
                    note_id=note_id,
                    root_comment_id=root_comment_id,
                    xsec_token=xsec_token,
                    num=10,
                    cursor=sub_comment_cursor,
                )
                if comments_res is None:
                    continue
                sub_comment_has_more = comments_res.get("has_more", False)
                sub_comment_cursor = comments_res.get("cursor", "")
                if "comments" not in comments_res:
                    break
                result.extend(comments_res["comments"])
                if callback:
                    await callback(note_id, comments_res["comments"])
                await asyncio.sleep(crawl_interval)
        return result

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_note_by_id_from_html(
        self,
        note_id: str,
        xsec_source: str,
        xsec_token: str,
        enable_cookie: bool = False,
    ) -> Optional[Dict]:
        url = (
            "https://www.xiaohongshu.com/explore/"
            + note_id
            + f"?xsec_token={xsec_token}&xsec_source={xsec_source}"
        )
        copy_headers = self.headers.copy()
        if not enable_cookie:
            copy_headers.pop("Cookie", None)
        html = await self.request(
            method="GET", url=url, return_response=True, headers=copy_headers
        )
        return self._extractor.extract_note_detail_from_html(note_id, html)
