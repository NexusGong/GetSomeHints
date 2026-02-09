# -*- coding: utf-8 -*-
"""Broadcast log messages to all connected WebSocket clients (for real-time log stream)."""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# 所有已连接的 /api/ws/logs 客户端
_connections: Set[WebSocket] = set()
_lock = asyncio.Lock()


async def register(websocket: WebSocket) -> None:
    async with _lock:
        _connections.add(websocket)


async def unregister(websocket: WebSocket) -> None:
    async with _lock:
        _connections.discard(websocket)


async def broadcast(message: str, level: str = "info", platform: str | None = None) -> None:
    """向所有已连接的 WS 客户端推送一条日志。level: info|warning|error|success"""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        "platform": platform,
    }
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
