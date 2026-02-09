# -*- coding: utf-8 -*-
"""WebSocket for real-time log stream; crawler_runner broadcasts progress here."""
from fastapi import APIRouter, WebSocket

from app.services.ws_broadcast import broadcast, register, unregister

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/logs")
async def ws_logs(websocket: WebSocket):
    """接受前端连接，后端通过 ws_broadcast.broadcast() 推送爬取进度与日志。"""
    await websocket.accept()
    await register(websocket)
    try:
        while True:
            msg = await websocket.receive()
            if msg.get("type") == "websocket.disconnect":
                break
    except Exception:
        pass
    finally:
        await unregister(websocket)
        try:
            await websocket.close()
        except Exception:
            pass
