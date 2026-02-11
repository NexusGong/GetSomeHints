# -*- coding: utf-8 -*-
"""小红书内存收集器：不写 DB，只收集到列表供上层使用。"""
from typing import Dict, List

_collector_notes: List[Dict] = []
_collector_comments: List[tuple] = []


def set_collector(notes: List[Dict], comments: List[tuple]) -> None:
    global _collector_notes, _collector_comments
    _collector_notes, _collector_comments = notes, comments


async def update_xhs_note(note_item: Dict) -> None:
    _collector_notes.append(note_item)


async def update_xhs_note_comment(note_id: str, comment_item: Dict) -> None:
    _collector_comments.append((note_id, comment_item))


async def batch_update_xhs_note_comments(note_id: str, comments: List[Dict]) -> None:
    for c in comments or []:
        await update_xhs_note_comment(note_id, c)


async def save_creator(user_id: str, creator: Dict) -> None:
    pass


async def update_xhs_note_image(note_id: str, pic_content: bytes, extension_file_name: str) -> None:
    pass


async def update_xhs_note_video(note_id: str, video_content: bytes, extension_file_name: str) -> None:
    pass


def get_video_url_arr(note_item: Dict) -> List[str]:
    """从 note 中提取视频 URL 列表。"""
    if note_item.get("type") != "video":
        return []
    video_dict = note_item.get("video") or {}
    consumer = video_dict.get("consumer") or {}
    origin_key = consumer.get("origin_video_key") or consumer.get("originVideoKey") or ""
    if origin_key:
        return [f"http://sns-video-bd.xhscdn.com/{origin_key}"]
    media = video_dict.get("media") or {}
    stream = media.get("stream") or {}
    h264 = stream.get("h264")
    if isinstance(h264, list):
        return [v.get("master_url") for v in h264 if v.get("master_url")]
    return []
