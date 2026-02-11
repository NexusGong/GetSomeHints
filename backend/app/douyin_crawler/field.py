# -*- coding: utf-8 -*-
"""抖音 API 枚举。"""
from enum import Enum


class SearchChannelType(Enum):
    GENERAL = "aweme_general"
    VIDEO = "aweme_video_web"
    USER = "aweme_user_web"
    LIVE = "aweme_live"


class SearchSortType(Enum):
    GENERAL = 0
    MOST_LIKE = 1
    LATEST = 2


class PublishTimeType(Enum):
    UNLIMITED = 0
    ONE_DAY = 1
    ONE_WEEK = 7
    SIX_MONTH = 180
