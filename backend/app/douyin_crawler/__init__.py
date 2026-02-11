# -*- coding: utf-8 -*-
"""抖音爬虫逻辑（从 MediaCrawler 抽取，不依赖 mediacrawler_bundle）。"""
from app.douyin_crawler.core import DouYinCrawler
from app.douyin_crawler.store import set_collector

__all__ = ["DouYinCrawler", "set_collector"]
