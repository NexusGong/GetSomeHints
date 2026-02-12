# -*- coding: utf-8 -*-
"""Application configuration."""
import os
from typing import List


def _bool(val: str) -> bool:
    return str(val).lower() in ("1", "true", "yes")


def _int(val: str, default: int) -> int:
    try:
        return int(val) if val else default
    except ValueError:
        return default


def _float(val: str, default: float) -> float:
    try:
        return float(val) if val else default
    except ValueError:
        return default


class Settings:
    """App settings from env."""

    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = _int(os.getenv("API_PORT"), 8000)

    # Proxy
    ENABLE_IP_PROXY: bool = _bool(os.getenv("ENABLE_IP_PROXY", "false"))
    IP_PROXY_POOL_COUNT: int = _int(os.getenv("IP_PROXY_POOL_COUNT"), 2)
    IP_PROXY_PROVIDER: str = os.getenv("IP_PROXY_PROVIDER", "kuaidaili")

    # Anti-block
    CRAWLER_MIN_SLEEP_SEC: float = _float(os.getenv("CRAWLER_MIN_SLEEP_SEC"), 1.0)
    CRAWLER_MAX_SLEEP_SEC: float = _float(os.getenv("CRAWLER_MAX_SLEEP_SEC"), 3.0)
    MAX_REQUESTS_PER_IP: int = _int(os.getenv("MAX_REQUESTS_PER_IP"), 50)
    MAX_CONCURRENCY_NUM: int = _int(os.getenv("MAX_CONCURRENCY_NUM"), 1)
    PROXY_BUFFER_SECONDS: int = _int(os.getenv("PROXY_BUFFER_SECONDS"), 30)

    # Crawler limits
    CRAWLER_MAX_NOTES_COUNT: int = _int(os.getenv("CRAWLER_MAX_NOTES_COUNT"), 50)
    CRAWLER_MAX_COMMENTS_COUNT: int = _int(os.getenv("CRAWLER_MAX_COMMENTS_COUNT"), 20)
    ENABLE_GET_COMMENTS: bool = _bool(os.getenv("ENABLE_GET_COMMENTS", "true"))
    ENABLE_GET_SUB_COMMENTS: bool = _bool(os.getenv("ENABLE_GET_SUB_COMMENTS", "false"))

    # Kuaidaili (from env, never commit)
    KDL_SECRET_ID: str = os.getenv("KDL_SECRET_ID", "") or os.getenv("KDL_SECERT_ID", "")
    KDL_SIGNATURE: str = os.getenv("KDL_SIGNATURE", "") or os.getenv("kdl_signature", "")
    KDL_USER_NAME: str = os.getenv("KDL_USER_NAME", "") or os.getenv("kdl_user_name", "")
    KDL_USER_PWD: str = os.getenv("KDL_USER_PWD", "") or os.getenv("kdl_user_pwd", "")

    # Playwright 浏览器数据目录（空则用 backend/browser_data，可设为项目外路径如 ~/.getsomehints/browser_data）
    BROWSER_DATA_DIR: str = os.getenv("BROWSER_DATA_DIR", "").strip()

    # DeepSeek LLM（大模型分析潜在卖/买家，与 Nexus 配置命名一致）
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
    DEEPSEEK_API_BASE: str = (
        os.getenv("DEEPSEEK_API_BASE", "").strip()
        or os.getenv("LLM_API_BASE", "https://api.deepseek.com").strip()
        or "https://api.deepseek.com"
    )
    DEEPSEEK_ENABLE_SEARCH: bool = _bool(os.getenv("DEEPSEEK_ENABLE_SEARCH", "false"))


settings = Settings()

# Platforms supported (match frontend)
PLATFORMS: List[str] = ["xhs", "dy", "ks", "bili", "wb", "tieba", "zhihu"]
