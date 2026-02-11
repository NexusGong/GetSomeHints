# -*- coding: utf-8 -*-
"""小红书 API 枚举。"""
from enum import Enum


class SearchSortType(Enum):
    GENERAL = "general"
    MOST_POPULAR = "popularity_descending"
    LATEST = "time_descending"


class SearchNoteType(Enum):
    ALL = 0
    VIDEO = 1
    IMAGE = 2
