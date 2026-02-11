# -*- coding: utf-8 -*-
"""小红书爬虫逻辑（从 MediaCrawler 抽取，不依赖 mediacrawler_bundle）。"""
from app.xhs_crawler.core import XiaoHongShuCrawler
from app.xhs_crawler.store import set_collector

__all__ = ["XiaoHongShuCrawler", "set_collector"]
