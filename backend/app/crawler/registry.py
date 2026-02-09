# -*- coding: utf-8 -*-
"""Crawler registry: map platform code to crawler class."""
from typing import List, Optional, Type

from app.crawler.base import BaseCrawler


def _crawlers() -> dict:
    crawlers = {}
    try:
        from app.crawler.xhs import XiaoHongShuCrawler
        crawlers["xhs"] = XiaoHongShuCrawler
    except ImportError:
        pass
    try:
        from app.crawler.douyin import DouYinCrawler
        crawlers["dy"] = DouYinCrawler
    except ImportError:
        pass
    try:
        from app.crawler.kuaishou import KuaishouCrawler
        crawlers["ks"] = KuaishouCrawler
    except ImportError:
        pass
    try:
        from app.crawler.bilibili import BilibiliCrawler
        crawlers["bili"] = BilibiliCrawler
    except ImportError:
        pass
    try:
        from app.crawler.weibo import WeiboCrawler
        crawlers["wb"] = WeiboCrawler
    except ImportError:
        pass
    try:
        from app.crawler.tieba import TiebaCrawler
        crawlers["tieba"] = TiebaCrawler
    except ImportError:
        pass
    try:
        from app.crawler.zhihu import ZhihuCrawler
        crawlers["zhihu"] = ZhihuCrawler
    except ImportError:
        pass
    return crawlers


def get_crawler(platform: str) -> Optional[Type[BaseCrawler]]:
    return _crawlers().get(platform)


def supported_platforms() -> List[str]:
    return list(_crawlers().keys())
