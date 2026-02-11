# -*- coding: utf-8 -*-
"""小红书请求异常。"""


class DataFetchError(Exception):
    """请求或解析失败"""


class IPBlockError(Exception):
    """IP 被限流"""


class NoteNotFoundError(Exception):
    """笔记不存在或异常"""
