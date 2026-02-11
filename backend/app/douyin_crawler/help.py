# -*- coding: utf-8 -*-
"""抖音 a_bogus 签名与 URL 解析（仅供学习研究）。"""
import os
import random
import re

from app.douyin_crawler.crawler_util import extract_url_params_to_dict
from app.douyin_crawler.model import CreatorUrlInfo, VideoUrlInfo

_js_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")
_js_path = os.path.join(_js_dir, "douyin.js")
_douyin_sign_obj = None


def _get_sign_obj():
    global _douyin_sign_obj
    if _douyin_sign_obj is None:
        import execjs
        with open(_js_path, encoding="utf-8-sig") as f:
            _douyin_sign_obj = execjs.compile(f.read())
    return _douyin_sign_obj


def get_web_id() -> str:
    def e(t):
        if t is not None:
            return str(t ^ (int(16 * random.random()) >> (t // 4)))
        return "".join([str(int(1e7)), "-", str(int(1e3)), "-", str(int(4e3)), "-", str(int(8e3)), "-", str(int(1e11))])

    web_id = "".join(e(int(x)) if x in "018" else x for x in e(None))
    return web_id.replace("-", "")[:19]


def get_a_bogus_from_js(url: str, params: str, user_agent: str) -> str:
    sign_js_name = "sign_reply" if "/reply" in url else "sign_datail"
    return _get_sign_obj().call(sign_js_name, params, user_agent)


async def get_a_bogus(url: str, params: str, post_data: dict, user_agent: str, page=None) -> str:
    return get_a_bogus_from_js(url, params, user_agent)


def parse_video_info_from_url(url: str) -> VideoUrlInfo:
    if url.isdigit():
        return VideoUrlInfo(aweme_id=url, url_type="normal")
    if "v.douyin.com" in url or (url.startswith("http") and len(url) < 50 and "video" not in url):
        return VideoUrlInfo(aweme_id="", url_type="short")
    params = extract_url_params_to_dict(url)
    modal_id = params.get("modal_id")
    if modal_id:
        return VideoUrlInfo(aweme_id=modal_id, url_type="modal")
    m = re.search(r"/video/(\d+)", url)
    if m:
        return VideoUrlInfo(aweme_id=m.group(1), url_type="normal")
    raise ValueError(f"Unable to parse video ID from URL: {url}")


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    if url.startswith("MS4wLjABAAAA") or (not url.startswith("http") and "douyin.com" not in url):
        return CreatorUrlInfo(sec_user_id=url)
    m = re.search(r"/user/([^/?]+)", url)
    if m:
        return CreatorUrlInfo(sec_user_id=m.group(1))
    raise ValueError(f"Unable to parse creator ID from URL: {url}")
