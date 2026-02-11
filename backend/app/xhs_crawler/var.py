# -*- coding: utf-8 -*-
"""运行期上下文变量。"""
from contextvars import ContextVar

source_keyword_var: ContextVar[str] = ContextVar("source_keyword", default="")
crawler_type_var: ContextVar[str] = ContextVar("crawler_type", default="")
