# -*- coding: utf-8 -*-
"""抖音内存收集器：不写 DB，只收集到列表供上层使用。"""
from typing import Dict, List

_collector_notes: List[Dict] = []
_collector_comments: List[tuple] = []


def set_collector(notes: List[Dict], comments: List[tuple]) -> None:
    global _collector_notes, _collector_comments
    _collector_notes, _collector_comments = notes, comments


async def update_douyin_aweme(aweme_item: Dict) -> None:
    _collector_notes.append(aweme_item)


async def update_dy_aweme_comment(aweme_id: str, comment_item: Dict) -> None:
    _collector_comments.append((aweme_id, comment_item))


async def batch_update_dy_aweme_comments(aweme_id: str, comments: List[Dict]) -> None:
    for c in comments or []:
        await update_dy_aweme_comment(aweme_id, c)


async def save_creator(user_id: str, creator: Dict) -> None:
    pass


async def update_dy_aweme_image(aweme_id: str, pic_content: bytes, extension_file_name: str) -> None:
    pass


async def update_dy_aweme_video(aweme_id: str, video_content: bytes, extension_file_name: str) -> None:
    pass


def _extract_note_image_list(aweme_item: Dict) -> List[str]:
    """从 aweme 中提取图片 URL 列表（图文笔记）。"""
    out: List[str] = []
    for img in aweme_item.get("images") or []:
        url_list = img.get("url_list") or []
        if url_list:
            out.append(url_list[-1])
    return out


def _extract_video_download_url(aweme_item: Dict) -> str:
    """从 aweme 中提取视频下载 URL。"""
    v = aweme_item.get("video") or {}
    for key in ("play_addr_h264", "play_addr_256", "play_addr"):
        url_list = (v.get(key) or {}).get("url_list") or []
        if len(url_list) >= 2:
            return url_list[-1]
    return ""
