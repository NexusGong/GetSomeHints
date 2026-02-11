# -*- coding: utf-8 -*-
"""小红书 URL 解析与 search_id。"""
import random
import re
import time

from app.xhs_crawler.model import CreatorUrlInfo, NoteUrlInfo
from app.xhs_crawler.crawler_util import extract_url_params_to_dict


def base36encode(number: int, alphabet: str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") -> str:
    if not isinstance(number, int):
        raise TypeError("number must be an integer")
    base36 = ""
    sign = ""
    if number < 0:
        sign = "-"
        number = -number
    if 0 <= number < len(alphabet):
        return sign + alphabet[number]
    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36
    return sign + base36


def get_search_id() -> str:
    e = int(time.time() * 1000) << 64
    t = int(random.uniform(0, 2147483646))
    return base36encode(e + t)


def parse_note_info_from_note_url(url: str) -> NoteUrlInfo:
    note_id = url.split("/")[-1].split("?")[0]
    params = extract_url_params_to_dict(url)
    xsec_token = params.get("xsec_token", "")
    xsec_source = params.get("xsec_source", "")
    return NoteUrlInfo(note_id=note_id, xsec_token=xsec_token, xsec_source=xsec_source)


def parse_creator_info_from_url(url: str) -> CreatorUrlInfo:
    if len(url) == 24 and all(c in "0123456789abcdef" for c in url):
        return CreatorUrlInfo(user_id=url, xsec_token="", xsec_source="")
    user_pattern = r"/user/profile/([^/?]+)"
    match = re.search(user_pattern, url)
    if match:
        user_id = match.group(1)
        params = extract_url_params_to_dict(url)
        xsec_token = params.get("xsec_token", "")
        xsec_source = params.get("xsec_source", "")
        return CreatorUrlInfo(user_id=user_id, xsec_token=xsec_token, xsec_source=xsec_source)
    raise ValueError(f"Unable to parse creator info from URL: {url}")
