# -*- coding: utf-8 -*-
# Generate Xiaohongshu signature by calling window.mnsv2 via Playwright

import hashlib
import json
import time
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse, quote

from playwright.async_api import Page

from app.xhs_crawler.xhs_sign import b64_encode, encode_utf8, get_trace_id, mrc


def _build_sign_string(uri: str, data: Optional[Union[Dict, str]] = None, method: str = "POST") -> str:
    if method.upper() == "POST":
        c = uri
        if data is not None:
            if isinstance(data, dict):
                c += json.dumps(data, separators=(",", ":"), ensure_ascii=False)
            elif isinstance(data, str):
                c += data
        return c
    else:
        if not data or (isinstance(data, dict) and len(data) == 0):
            return uri
        if isinstance(data, dict):
            params = []
            for key in data.keys():
                value = data[key]
                if isinstance(value, list):
                    value_str = ",".join(str(v) for v in value)
                elif value is not None:
                    value_str = str(value)
                else:
                    value_str = ""
                value_str = quote(value_str, safe="")
                params.append(f"{key}={value_str}")
            return f"{uri}?{'&'.join(params)}"
        elif isinstance(data, str):
            return f"{uri}?{data}"
        return uri


def _md5_hex(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def _build_xs_payload(x3_value: str, data_type: str = "object") -> str:
    s = {
        "x0": "4.2.1",
        "x1": "xhs-pc-web",
        "x2": "Mac OS",
        "x3": x3_value,
        "x4": data_type,
    }
    return "XYS_" + b64_encode(encode_utf8(json.dumps(s, separators=(",", ":"))))


def _build_xs_common(a1: str, b1: str, x_s: str, x_t: str) -> str:
    payload = {
        "s0": 3,
        "s1": "",
        "x0": "1",
        "x1": "4.2.2",
        "x2": "Mac OS",
        "x3": "xhs-pc-web",
        "x4": "4.74.0",
        "x5": a1,
        "x6": x_t,
        "x7": x_s,
        "x8": b1,
        "x9": mrc(x_t + x_s + b1),
        "x10": 154,
        "x11": "normal",
    }
    return b64_encode(encode_utf8(json.dumps(payload, separators=(",", ":"))))


async def get_b1_from_localstorage(page: Page) -> str:
    try:
        local_storage = await page.evaluate("() => window.localStorage")
        return local_storage.get("b1", "")
    except Exception:
        return ""


async def call_mnsv2(page: Page, sign_str: str, md5_str: str) -> str:
    sign_str_escaped = sign_str.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
    md5_str_escaped = md5_str.replace("\\", "\\\\").replace("'", "\\'")
    try:
        result = await page.evaluate(f"window.mnsv2('{sign_str_escaped}', '{md5_str_escaped}')")
        return result if result else ""
    except Exception:
        return ""


async def sign_xs_with_playwright(
    page: Page,
    uri: str,
    data: Optional[Union[Dict, str]] = None,
    method: str = "POST",
) -> str:
    sign_str = _build_sign_string(uri, data, method)
    md5_str = _md5_hex(sign_str)
    x3_value = await call_mnsv2(page, sign_str, md5_str)
    data_type = "object" if isinstance(data, (dict, list)) else "string"
    return _build_xs_payload(x3_value, data_type)


async def sign_with_playwright(
    page: Page,
    uri: str,
    data: Optional[Union[Dict, str]] = None,
    a1: str = "",
    method: str = "POST",
) -> Dict[str, Any]:
    b1 = await get_b1_from_localstorage(page)
    x_s = await sign_xs_with_playwright(page, uri, data, method)
    x_t = str(int(time.time() * 1000))
    return {
        "x-s": x_s,
        "x-t": x_t,
        "x-s-common": _build_xs_common(a1, b1, x_s, x_t),
        "x-b3-traceid": get_trace_id(),
    }


async def pre_headers_with_playwright(
    page: Page,
    url: str,
    cookie_dict: Dict[str, str],
    params: Optional[Dict] = None,
    payload: Optional[Dict] = None,
) -> Dict[str, str]:
    a1_value = cookie_dict.get("a1", "")
    uri = urlparse(url).path
    if params is not None:
        data = params
        method = "GET"
    elif payload is not None:
        data = payload
        method = "POST"
    else:
        raise ValueError("params or payload is required")
    signs = await sign_with_playwright(page, uri, data, a1_value, method)
    return {
        "X-S": signs["x-s"],
        "X-T": signs["x-t"],
        "x-S-Common": signs["x-s-common"],
        "X-B3-Traceid": signs["x-b3-traceid"],
    }
