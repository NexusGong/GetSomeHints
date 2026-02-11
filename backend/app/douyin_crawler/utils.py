# -*- coding: utf-8 -*-
"""MC 兼容的 utils：logger、cookie、UA、二维码、代理格式等。"""
import base64
import logging
import random
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import httpx
from PIL import Image
from playwright.async_api import Cookie

from app.douyin_crawler.crawler_util import extract_url_params_to_dict
from app.douyin_crawler.time_util import get_current_timestamp

logger = logging.getLogger("MediaCrawler")


def convert_cookies(cookies: Optional[List[Cookie]]) -> Tuple[str, Dict]:
    if not cookies:
        return "", {}
    cookies_str = ";".join([f"{c.get('name')}={c.get('value')}" for c in cookies])
    cookie_dict = {c.get("name"): c.get("value") for c in cookies}
    return cookies_str, cookie_dict


def convert_str_cookie_to_dict(cookie_str: str) -> Dict[str, str]:
    out = {}
    if not cookie_str:
        return out
    for part in cookie_str.split(";"):
        part = part.strip()
        if not part:
            continue
        kv = part.split("=", 1)
        if len(kv) != 2:
            continue
        out[kv[0]] = kv[1]
    return out


def get_user_agent() -> str:
    uas = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    ]
    return random.choice(uas)


def format_proxy_info(ip_proxy_info) -> Tuple[Optional[Dict], Optional[str]]:
    """返回 (playwright_proxy_dict, httpx_proxy_url)。"""
    if ip_proxy_info is None:
        return None, None
    ip, port = getattr(ip_proxy_info, "ip", ""), getattr(ip_proxy_info, "port", 0)
    user = getattr(ip_proxy_info, "user", None) or ""
    password = getattr(ip_proxy_info, "password", None) or ""
    protocol = getattr(ip_proxy_info, "protocol", "http") or "http"
    server = f"{protocol}://{ip}:{port}"
    playwright_proxy = {"server": server, "username": user, "password": password}
    if user and password:
        httpx_proxy = f"http://{user}:{password}@{ip}:{port}"
    else:
        httpx_proxy = f"http://{ip}:{port}"
    return playwright_proxy, httpx_proxy


async def find_login_qrcode(page, selector: str) -> str:
    try:
        el = await page.wait_for_selector(selector, timeout=10000)
        src = str(await el.get_property("src"))
        if src.startswith("http"):
            async with httpx.AsyncClient(follow_redirects=True) as client:
                r = await client.get(src, headers={"User-Agent": get_user_agent()})
                if r.status_code == 200:
                    return base64.b64encode(r.content).decode("utf-8")
        return src
    except Exception:
        return ""


def show_qrcode(qr_code: str) -> None:
    if "," in qr_code:
        qr_code = qr_code.split(",", 1)[1]
    data = base64.b64decode(qr_code)
    img = Image.open(BytesIO(data))
    img.show()


# 供 login 使用
from app.douyin_crawler.slider_util import Slide, get_tracks  # noqa: E402

__all__ = [
    "logger",
    "convert_cookies",
    "convert_str_cookie_to_dict",
    "get_user_agent",
    "format_proxy_info",
    "find_login_qrcode",
    "show_qrcode",
    "get_current_timestamp",
    "extract_url_params_to_dict",
    "Slide",
    "get_tracks",
]
