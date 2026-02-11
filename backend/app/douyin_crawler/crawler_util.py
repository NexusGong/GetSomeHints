# -*- coding: utf-8 -*-
"""URL 等工具。"""
import urllib.parse
from typing import Dict


def extract_url_params_to_dict(url: str) -> Dict[str, str]:
    if not url:
        return {}
    parsed = urllib.parse.urlparse(url)
    return dict(urllib.parse.parse_qsl(parsed.query))
