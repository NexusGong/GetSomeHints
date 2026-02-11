# -*- coding: utf-8 -*-
"""抖音请求异常。"""
from httpx import RequestError


class DataFetchError(RequestError):
    """请求或解析失败"""


class IPBlockError(RequestError):
    """IP 被限流"""
