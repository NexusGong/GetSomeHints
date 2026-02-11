# -*- coding: utf-8 -*-
"""抖音 MC 运行期配置，由 app/crawler/douyin 通过 os.environ 注入。"""
import os


def _bool(key: str, default: bool = False) -> bool:
    v = os.environ.get(key, "").lower()
    if not v:
        return default
    return v in ("1", "true", "yes")


def _int(key: str, default: int) -> int:
    try:
        v = os.environ.get(key, "")
        return int(v) if v else default
    except ValueError:
        return default


# 以下由 douyin.py 在调用前设置
PLATFORM = os.environ.get("MC_PLATFORM", "dy")
KEYWORDS = os.environ.get("MC_KEYWORDS", "热门")
LOGIN_TYPE = os.environ.get("MC_LOGIN_TYPE", "qrcode")
COOKIES = os.environ.get("MC_COOKIES", "")
CRAWLER_TYPE = os.environ.get("MC_CRAWLER_TYPE", "search")
ENABLE_IP_PROXY = _bool("ENABLE_IP_PROXY", False)
IP_PROXY_POOL_COUNT = _int("IP_PROXY_POOL_COUNT", 2)
HEADLESS = _bool("MC_HEADLESS", False)
SAVE_LOGIN_STATE = _bool("MC_SAVE_LOGIN_STATE", True)
ENABLE_CDP_MODE = _bool("MC_ENABLE_CDP_MODE", False)
CDP_HEADLESS = _bool("CDP_HEADLESS", False)
USER_DATA_DIR = os.environ.get("MC_USER_DATA_DIR", "%s_user_data_dir")
START_PAGE = _int("MC_START_PAGE", 1)
CRAWLER_MAX_NOTES_COUNT = _int("CRAWLER_MAX_NOTES_COUNT", 15)
MAX_CONCURRENCY_NUM = _int("MAX_CONCURRENCY_NUM", 1)
ENABLE_GET_MEIDAS = _bool("ENABLE_GET_MEIDAS", False)
ENABLE_GET_COMMENTS = _bool("ENABLE_GET_COMMENTS", True)
ENABLE_GET_SUB_COMMENTS = _bool("ENABLE_GET_SUB_COMMENTS", False)
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = _int("CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES", 10)
CRAWLER_MAX_SLEEP_SEC = _int("CRAWLER_MAX_SLEEP_SEC", 2)
PUBLISH_TIME_TYPE = _int("MC_PUBLISH_TIME_TYPE", 0)
