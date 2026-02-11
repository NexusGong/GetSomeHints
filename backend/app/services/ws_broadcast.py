# -*- coding: utf-8 -*-
"""Broadcast log messages to all connected WebSocket clients (for real-time log stream)."""
import asyncio
import json
import logging
import queue
from datetime import datetime, timezone
from typing import List, Set, Tuple

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# 所有已连接的 /api/ws/logs 客户端
_connections: Set[WebSocket] = set()
_lock = asyncio.Lock()

# 供爬虫线程写入的日志队列，主循环定时 drain 并 broadcast（线程安全）
# 项为 (message, level, platform, replace_id|None)，replace_id 表示前端/控制台原地更新该行
_log_queue: queue.Queue[Tuple[str, str, str | None, str | None]] = queue.Queue()


def push_log_sync(
    message: str,
    level: str = "info",
    platform: str | None = None,
    replace_id: str | None = None,
) -> None:
    """从任意线程调用，将一条日志放入队列。replace_id 非空时前端与控制台会原地更新该行。"""
    try:
        _log_queue.put_nowait((message, level, platform, replace_id))
    except Exception:
        pass


def drain_pending_logs() -> List[Tuple[str, str, str | None, str | None]]:
    """主循环调用：取出当前队列中所有日志，返回 [(message, level, platform, replace_id), ...]。"""
    out: List[Tuple[str, str, str | None, str | None]] = []
    try:
        while True:
            out.append(_log_queue.get_nowait())
    except queue.Empty:
        pass
    return out


async def register(websocket: WebSocket) -> None:
    async with _lock:
        _connections.add(websocket)


async def unregister(websocket: WebSocket) -> None:
    async with _lock:
        _connections.discard(websocket)


async def broadcast(
    message: str,
    level: str = "info",
    platform: str | None = None,
    replace_id: str | None = None,
) -> None:
    """向所有已连接的 WS 客户端推送一条日志。replace_id 非空时前端应原地更新该行。"""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        "platform": platform,
    }
    if replace_id is not None:
        payload["replace_id"] = replace_id
    text = json.dumps(payload, ensure_ascii=False)
    async with _lock:
        snapshot = set(_connections)
    dead = set()
    for ws in snapshot:
        try:
            await ws.send_text(text)
        except Exception as e:
            logger.debug("ws broadcast send failed: %s", e)
            dead.add(ws)
    if dead:
        async with _lock:
            for ws in dead:
                _connections.discard(ws)
