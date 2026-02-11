# -*- coding: utf-8 -*-
"""从 HTML 中解析笔记/用户信息。"""
import json
import re
from typing import Any, Dict, Optional


def _decamelize_key(s: str) -> str:
    s = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", s)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s).lower()


def _decamelize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {_decamelize_key(k): _decamelize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decamelize(i) for i in obj]
    return obj


class XiaoHongShuExtractor:
    def extract_note_detail_from_html(self, note_id: str, html: str) -> Optional[Dict]:
        if "noteDetailMap" not in html:
            return None
        state = re.findall(r"window.__INITIAL_STATE__=({.*})</script>", html)[0].replace("undefined", '""')
        if state != "{}":
            note_dict = _decamelize(json.loads(state))
            return note_dict["note"]["note_detail_map"][note_id]["note"]
        return None

    def extract_creator_info_from_html(self, html: str) -> Optional[Dict]:
        match = re.search(r"<script>window.__INITIAL_STATE__=(.+)<\/script>", html, re.M)
        if match is None:
            return None
        info = json.loads(match.group(1).replace(":undefined", ":null"), strict=False)
        if info is None:
            return None
        return info.get("user", {}).get("userPageData")
