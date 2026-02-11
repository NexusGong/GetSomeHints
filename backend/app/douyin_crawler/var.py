# -*- coding: utf-8 -*-
"""运行期上下文变量，无 database 依赖。"""
from contextvars import ContextVar

request_keyword_var: ContextVar[str] = ContextVar("request_keyword", default="")
crawler_type_var: ContextVar[str] = ContextVar("crawler_type", default="")
source_keyword_var: ContextVar[str] = ContextVar("source_keyword", default="")
