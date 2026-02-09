# -*- coding: utf-8 -*-
"""FastAPI entry: CORS, mount search router."""
import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend dir (when running as uvicorn app.main:app from backend)
_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_env)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s %(message)s",
    stream=sys.stderr,
    force=True,
)
logger = logging.getLogger("app")
# 减少刷屏：轮询接口不记录到 uvicorn.access，否则每次 status/results 轮询都会打一行
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.routers import search, analysis, ws

app = FastAPI(
    title="GetSomeHints API",
    description="Multi-platform crawler search API",
    version="1.0.0",
)

@app.on_event("startup")
def startup():
    import os
    from app.debug_log import debug_log
    pid = os.getpid()
    debug_log(f"[App] backend started PID={pid} on port 8000")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """只记录关键请求，跳过轮询类接口避免刷屏."""
    import os
    from app.debug_log import debug_log
    path = request.url.path
    method = request.method
    pid = os.getpid()
    is_poll = method == "GET" and (
        path.startswith("/api/search/status/") or path.startswith("/api/search/results/")
    )
    if not is_poll:
        debug_log(f"[Request] {method} {path} (pid={pid})")
        logger.info("%s %s", method, path)
    response = await call_next(request)
    response.headers["X-Server-PID"] = str(pid)
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Server-PID"],
)

app.include_router(search.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(ws.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/debug/whoami")
async def debug_whoami():
    """返回当前进程 PID，用于确认是哪个后端在响应（与 crawler_debug.log 里 PID 对比）."""
    import os
    return {"pid": os.getpid(), "msg": "对比 /tmp/getsomehints_debug.log 里的 pid= 可知是否同一进程"}


@app.get("/api/config/proxy")
async def proxy_config_status():
    """代理配置状态（不返回密钥）。"""
    from app.config import settings
    return {
        "enabled": settings.ENABLE_IP_PROXY,
        "provider": settings.IP_PROXY_PROVIDER,
        "pool_count": settings.IP_PROXY_POOL_COUNT,
        "kuaidaili_configured": bool(
            getattr(settings, "KDL_SECRET_ID", "")
            and getattr(settings, "KDL_SIGNATURE", "")
            and getattr(settings, "KDL_USER_NAME", "")
            and getattr(settings, "KDL_USER_PWD", "")
        ),
    }
