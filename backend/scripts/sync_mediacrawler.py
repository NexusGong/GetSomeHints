#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 MediaCrawler 拉取必要文件到 mediacrawler_bundle/，不克隆整个仓库。
方式一：git sparse-checkout（推荐，需 git）
方式二：按 URL 下载单个文件（备用）
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

# 项目 backend 目录
BACKEND_DIR = Path(__file__).resolve().parent.parent
BUNDLE_DIR = BACKEND_DIR / "mediacrawler_bundle"
MC_REPO = "https://github.com/NanmiCoder/MediaCrawler.git"
RAW_BASE = "https://raw.githubusercontent.com/NanmiCoder/MediaCrawler/main"


def run_git_sparse_clone() -> bool:
    """使用 git sparse-checkout 只拉取需要的目录。"""
    if shutil.which("git") is None:
        print("未找到 git，跳过 sparse clone")
        return False
    if BUNDLE_DIR.exists():
        print(f"已存在 {BUNDLE_DIR}，跳过 clone。删除该目录后可重新拉取。")
        return True
    # 只拉取这些目录（不含单文件 var.py，后面用 write_bundle_var 写入）
    dirs = [
        "media_platform",
        "base",
        "tools",
        "config",
        "model",
        "store",
        "constant",
        "libs",
        "proxy",
    ]
    try:
        subprocess.run(
            [
                "git", "clone", "--depth", "1",
                "--filter=blob:none", "--sparse",
                MC_REPO, str(BUNDLE_DIR),
            ],
            cwd=BACKEND_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "sparse-checkout", "set"] + dirs,
            cwd=BUNDLE_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"已拉取 MediaCrawler 到 {BUNDLE_DIR}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"git 执行失败: {e.stderr or e}")
        return False


def write_bundle_config() -> None:
    """写入适配用 config，从环境变量读取，避免依赖 MC 原 config 树。"""
    config_dir = BUNDLE_DIR / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    # 覆盖 base_config，从 env 读取
    content = '''# -*- coding: utf-8 -*-
# GetSomeHints 适配：从环境变量读取，供 mediacrawler_bundle 使用
import os

def _env_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).lower() in ("1", "true", "yes")

def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default

PLATFORM = os.getenv("MC_PLATFORM", "xhs")
KEYWORDS = os.getenv("MC_KEYWORDS", "")
LOGIN_TYPE = os.getenv("MC_LOGIN_TYPE", "qrcode")
COOKIES = os.getenv("MC_COOKIES", "")
CRAWLER_TYPE = os.getenv("MC_CRAWLER_TYPE", "search")
ENABLE_IP_PROXY = _env_bool("ENABLE_IP_PROXY", "false")
IP_PROXY_POOL_COUNT = _env_int("IP_PROXY_POOL_COUNT", 2)
IP_PROXY_PROVIDER_NAME = os.getenv("IP_PROXY_PROVIDER", "kuaidaili")
HEADLESS = _env_bool("MC_HEADLESS", "false")
SAVE_LOGIN_STATE = _env_bool("MC_SAVE_LOGIN_STATE", "true")
ENABLE_CDP_MODE = _env_bool("MC_ENABLE_CDP_MODE", "true")
CDP_DEBUG_PORT = _env_int("MC_CDP_DEBUG_PORT", 9222)
CUSTOM_BROWSER_PATH = os.getenv("MC_CUSTOM_BROWSER_PATH", "")
CDP_HEADLESS = _env_bool("MC_CDP_HEADLESS", "false")
BROWSER_LAUNCH_TIMEOUT = 60
AUTO_CLOSE_BROWSER = True
SAVE_DATA_OPTION = "memory"
SAVE_DATA_PATH = ""
USER_DATA_DIR = "%s_user_data_dir"
START_PAGE = 1
CRAWLER_MAX_NOTES_COUNT = _env_int("CRAWLER_MAX_NOTES_COUNT", 30)
MAX_CONCURRENCY_NUM = 1
ENABLE_GET_MEIDAS = False
ENABLE_GET_COMMENTS = True
CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES = _env_int("CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES", 20)
ENABLE_GET_SUB_COMMENTS = False
ENABLE_GET_WORDCLOUD = False
CRAWLER_MAX_SLEEP_SEC = _env_int("CRAWLER_MAX_SLEEP_SEC", 2)
SORT_TYPE = ""
XHS_SPECIFIED_NOTE_URL_LIST = []
XHS_CREATOR_ID_LIST = []
PUBLISH_TIME_TYPE = ""
DY_SPECIFIED_ID_LIST = []
DY_CREATOR_ID_LIST = []
CACHE_TYPE_REDIS = "memory"
# 避免导入 MC 各平台 config 子模块（可选）
try:
    from . import xhs_config
except ImportError:
    pass
'''
    (config_dir / "base_config.py").write_text(content, encoding="utf-8")
    if not (config_dir / "__init__.py").exists():
        (config_dir / "__init__.py").write_text("", encoding="utf-8")
    print("已写入 config 适配")


def write_bundle_var() -> None:
    """覆盖 var.py，去掉 aiomysql 依赖。"""
    content = '''# -*- coding: utf-8 -*-
from contextvars import ContextVar
from typing import List
from asyncio import Task

request_keyword_var: ContextVar[str] = ContextVar("request_keyword", default="")
crawler_type_var: ContextVar[str] = ContextVar("crawler_type", default="")
comment_tasks_var: ContextVar[List[Task]] = ContextVar("comment_tasks", default=[])
source_keyword_var: ContextVar[str] = ContextVar("source_keyword", default="")
'''
    (BUNDLE_DIR / "var.py").write_text(content, encoding="utf-8")
    print("已写入 var.py 适配")


def write_cache_adapter() -> None:
    """写入 cache 模块，供 proxy 导入（MC 需 cache.abs_cache / cache_factory）。"""
    cache_dir = BUNDLE_DIR / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "abs_cache.py").write_text("""# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Any, List, Optional

class AbstractCache(ABC):
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError
    @abstractmethod
    def set(self, key: str, value: Any, expire_time: int) -> None:
        raise NotImplementedError
    @abstractmethod
    def keys(self, pattern: str) -> List[str]:
        raise NotImplementedError
""", encoding="utf-8")
    (cache_dir / "cache_factory.py").write_text("""# -*- coding: utf-8 -*-
import re
from typing import Any, List, Optional
from .abs_cache import AbstractCache

class MemoryCache(AbstractCache):
    def __init__(self) -> None:
        self._store: dict = {}
    def get(self, key: str) -> Optional[str]:
        return self._store.get(key)
    def set(self, key: str, value: Any, expire_time: int) -> None:
        self._store[key] = value
    def keys(self, pattern: str) -> List[str]:
        re_pat = pattern.replace("*", ".*")
        return [k for k in self._store if re.match(re_pat, k)]

class CacheFactory:
    @staticmethod
    def create_cache(cache_type: str = "memory") -> AbstractCache:
        return MemoryCache()
""", encoding="utf-8")
    (cache_dir / "__init__.py").write_text("""# -*- coding: utf-8 -*-
from .abs_cache import AbstractCache
from .cache_factory import CacheFactory, MemoryCache
""", encoding="utf-8")
    # config 里需有 CACHE_TYPE_REDIS，已在 write_bundle_config 的 base_config 中设为 memory
    print("已写入 cache 适配")


def write_xhs_store_adapter() -> None:
    """覆盖 store/xhs：内存收集，供 GetSomeHints 转成 UnifiedPost/UnifiedComment。"""
    xhs_dir = BUNDLE_DIR / "store" / "xhs"
    xhs_dir.mkdir(parents=True, exist_ok=True)
    content = '''# -*- coding: utf-8 -*-
# GetSomeHints 适配：不写 DB，收集到内存列表
from typing import Dict, List

try:
    from var import source_keyword_var
except Exception:
    source_keyword_var = None

# 收集目标（由 runner 设置）
_collector_notes: List[Dict] = []
_collector_comments: List[tuple] = []  # (note_id, comment_item)[]

def set_collector(notes: List[Dict], comments: List[tuple]) -> None:
    global _collector_notes, _collector_comments
    _collector_notes, _collector_comments = notes, comments

def get_video_url_arr(note_item: Dict) -> List[str]:
    if note_item.get("type") != "video":
        return []
    video_dict = note_item.get("video") or {}
    consumer = video_dict.get("consumer", {})
    origin_video_key = consumer.get("origin_video_key") or consumer.get("originVideoKey") or ""
    if origin_video_key:
        return [f"http://sns-video-bd.xhscdn.com/{origin_video_key}"]
    media = video_dict.get("media", {})
    stream = media.get("stream", {})
    videos = stream.get("h264")
    if isinstance(videos, list):
        return [v.get("master_url", "") for v in videos if v.get("master_url")]
    return []

async def update_xhs_note(note_item: Dict) -> None:
    _collector_notes.append(note_item)

async def batch_update_xhs_note_comments(note_id: str, comments: List[Dict]) -> None:
    for c in comments or []:
        await update_xhs_note_comment(note_id, c)

async def update_xhs_note_comment(note_id: str, comment_item: Dict) -> None:
    _collector_comments.append((note_id, comment_item))

async def save_creator(user_id: str, creator: Dict) -> None:
    pass

async def update_xhs_note_image(note_id: str, pic_content: bytes, extension_file_name: str) -> None:
    pass

async def update_xhs_note_video(note_id: str, video_content: bytes, extension_file_name: str) -> None:
    pass
'''
    (xhs_dir / "__init__.py").write_text(content, encoding="utf-8")
    print("已写入 store/xhs 内存适配")


def write_douyin_store_adapter() -> None:
    """覆盖 store/douyin：内存收集，供 GetSomeHints 转成 UnifiedPost/UnifiedComment。"""
    dy_dir = BUNDLE_DIR / "store" / "douyin"
    dy_dir.mkdir(parents=True, exist_ok=True)
    content = '''# -*- coding: utf-8 -*-
# GetSomeHints 适配：不写 DB，收集到内存列表
from typing import Dict, List

_collector_notes: List[Dict] = []
_collector_comments: List[tuple] = []

def set_collector(notes: List[Dict], comments: List[tuple]) -> None:
    global _collector_notes, _collector_comments
    _collector_notes, _collector_comments = notes, comments

async def update_douyin_aweme(aweme_item: Dict) -> None:
    _collector_notes.append(aweme_item)

async def batch_update_dy_aweme_comments(aweme_id: str, comments: List[Dict]) -> None:
    for c in comments or []:
        await update_dy_aweme_comment(aweme_id, c)

async def update_dy_aweme_comment(aweme_id: str, comment_item: Dict) -> None:
    _collector_comments.append((aweme_id, comment_item))

async def save_creator(user_id: str, creator: Dict) -> None:
    pass

async def update_dy_aweme_image(aweme_id: str, pic_content: bytes, extension_file_name: str) -> None:
    pass

async def update_dy_aweme_video(aweme_id: str, video_content: bytes, extension_file_name: str) -> None:
    pass
'''
    (dy_dir / "__init__.py").write_text(content, encoding="utf-8")
    print("已写入 store/douyin 内存适配")


def _write_platform_store_adapter(
    platform: str,
    update_content_name: str,
    update_comment_name: str,
    batch_comments_name: str,
    save_creator_name: str = "save_creator",
    extra_async_noops: Optional[list] = None,
) -> None:
    """通用：写入某平台 store 内存适配（仅 content + comment + creator）。"""
    plat_dir = BUNDLE_DIR / "store" / platform
    plat_dir.mkdir(parents=True, exist_ok=True)
    noops = list(extra_async_noops or [])
    noop_defs = "\n".join([f"async def {n}(*args, **kwargs) -> None:\n    pass" for n in noops])
    content = f'''# -*- coding: utf-8 -*-
# GetSomeHints 适配：内存收集
from typing import Dict, List, Any

_collector_notes: List[Dict] = []
_collector_comments: List[tuple] = []

def set_collector(notes: List[Dict], comments: List[tuple]) -> None:
    global _collector_notes, _collector_comments
    _collector_notes, _collector_comments = notes, comments

def _to_dict(item: Any) -> Dict:
    if isinstance(item, dict):
        return item
    return getattr(item, "__dict__", {{}}) if hasattr(item, "__dict__") else {{}}

async def {update_content_name}(content_item: Any) -> None:
    _collector_notes.append(_to_dict(content_item) if not isinstance(content_item, dict) else content_item)

async def {batch_comments_name}(note_id: str, comments: List[Any]) -> None:
    for c in comments or []:
        await {update_comment_name}(note_id, c)

async def {update_comment_name}(note_id: str, comment_item: Any) -> None:
    _collector_comments.append((note_id, _to_dict(comment_item) if not isinstance(comment_item, dict) else comment_item))

async def {save_creator_name}(*args, **kwargs) -> None:
    pass

{noop_defs}
'''
    (plat_dir / "__init__.py").write_text(content, encoding="utf-8")
    print(f"已写入 store/{platform} 内存适配")


def write_kuaishou_store_adapter() -> None:
    _write_platform_store_adapter(
        "kuaishou",
        "update_kuaishou_video",
        "update_ks_video_comment",
        "batch_update_ks_video_comments",
        extra_async_noops=[],
    )


def write_bilibili_store_adapter() -> None:
    _write_platform_store_adapter(
        "bilibili",
        "update_bilibili_video",
        "update_bilibili_video_comment",
        "batch_update_bilibili_video_comments",
        extra_async_noops=[
            "update_up_info",
            "batch_update_bilibili_creator_fans",
            "batch_update_bilibili_creator_followings",
            "batch_update_bilibili_creator_dynamics",
            "update_bilibili_creator_contact",
            "update_bilibili_creator_dynamic",
        ],
    )


def write_weibo_store_adapter() -> None:
    plat_dir = BUNDLE_DIR / "store" / "weibo"
    plat_dir.mkdir(parents=True, exist_ok=True)
    content = '''# -*- coding: utf-8 -*-
from typing import Dict, List, Any

_collector_notes: List[Dict] = []
_collector_comments: List[tuple] = []

def set_collector(notes: List[Dict], comments: List[tuple]) -> None:
    global _collector_notes, _collector_comments
    _collector_notes, _collector_comments = notes, comments

async def batch_update_weibo_notes(note_list: List[Any]) -> None:
    for n in note_list or []:
        _collector_notes.append(n if isinstance(n, dict) else getattr(n, "__dict__", {}))

async def update_weibo_note(note_item: Any) -> None:
    _collector_notes.append(note_item if isinstance(note_item, dict) else getattr(note_item, "__dict__", {}))

async def batch_update_weibo_note_comments(note_id: str, comments: List[Any]) -> None:
    for c in comments or []:
        await update_weibo_note_comment(note_id, c)

async def update_weibo_note_comment(note_id: str, comment_item: Any) -> None:
    _collector_comments.append((note_id, comment_item if isinstance(comment_item, dict) else getattr(comment_item, "__dict__", {})))

async def save_creator(user_id: str, user_info: Dict) -> None:
    pass

async def update_weibo_note_image(*args, **kwargs) -> None:
    pass
'''
    (plat_dir / "__init__.py").write_text(content, encoding="utf-8")
    print("已写入 store/weibo 内存适配")


def write_tieba_store_adapter() -> None:
    _write_platform_store_adapter(
        "tieba",
        "update_tieba_note",
        "update_tieba_note_comment",
        "batch_update_tieba_note_comments",
        "save_creator",
        extra_async_noops=[],
    )


def write_zhihu_store_adapter() -> None:
    plat_dir = BUNDLE_DIR / "store" / "zhihu"
    plat_dir.mkdir(parents=True, exist_ok=True)
    content = '''# -*- coding: utf-8 -*-
from typing import Dict, List, Any

_collector_notes: List[Dict] = []
_collector_comments: List[tuple] = []

def set_collector(notes: List[Dict], comments: List[tuple]) -> None:
    global _collector_notes, _collector_comments
    _collector_notes, _collector_comments = notes, comments

def _to_dict(o: Any) -> Dict:
    if isinstance(o, dict):
        return o
    return getattr(o, "__dict__", {}) if hasattr(o, "__dict__") else {}

async def batch_update_zhihu_contents(contents: List[Any]) -> None:
    for c in contents or []:
        _collector_notes.append(_to_dict(c))

async def update_zhihu_content(content_item: Any) -> None:
    _collector_notes.append(_to_dict(content_item))

async def batch_update_zhihu_note_comments(comments: List[Any]) -> None:
    for c in comments or []:
        d = _to_dict(c)
        note_id = d.get("content_id") or d.get("note_id") or ""
        _collector_comments.append((str(note_id), d))

async def update_zhihu_content_comment(comment_item: Any) -> None:
    d = _to_dict(comment_item)
    note_id = d.get("content_id") or d.get("note_id") or ""
    _collector_comments.append((str(note_id), d))

async def save_creator(creator: Any) -> None:
    pass
'''
    (plat_dir / "__init__.py").write_text(content, encoding="utf-8")
    print("已写入 store/zhihu 内存适配")


def main() -> None:
    os.chdir(BACKEND_DIR)
    if not run_git_sparse_clone():
        print("请安装 git 后重试，或将 MediaCrawler 所需目录手动放入 backend/mediacrawler_bundle/")
        sys.exit(1)
    write_bundle_config()
    write_bundle_var()
    write_cache_adapter()
    write_xhs_store_adapter()
    write_douyin_store_adapter()
    write_kuaishou_store_adapter()
    write_bilibili_store_adapter()
    write_weibo_store_adapter()
    write_tieba_store_adapter()
    write_zhihu_store_adapter()
    print("完成。请执行: playwright install chromium")


if __name__ == "__main__":
    main()
