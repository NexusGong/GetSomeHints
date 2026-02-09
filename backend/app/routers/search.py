# -*- coding: utf-8 -*-
"""Search API: start, status, results, stop, comments (match frontend contract)."""
import asyncio
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.schemas import SearchStartRequest, SearchResponse, UnifiedPost, UnifiedComment
from app.services.task_manager import task_manager
from app.services.crawler_runner import start_search_background

router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger(__name__)


@router.post("/start", response_model=SearchResponse)
async def search_start(body: SearchStartRequest):
    """Start a search task; returns task_id and initial status."""
    from app.debug_log import debug_log
    debug_log(f"[Search] POST /start received keywords={body.keywords!r} platforms={body.platforms}")
    logger.info("search_start keywords=%r platforms=%s", body.keywords, body.platforms)
    if not body.keywords or not body.keywords.strip():
        raise HTTPException(status_code=400, detail="keywords required")
    if not body.platforms:
        raise HTTPException(status_code=400, detail="at least one platform required")

    task_id = task_manager.create_task()
    debug_log(f"[Search] task_id={task_id[:8]}... background task starting")
    start_search_background(
        task_id=task_id,
        keywords=body.keywords.strip(),
        platforms=body.platforms,
        max_count=body.max_count or 100,
        enable_comments=body.enable_comments if body.enable_comments is not None else True,
        enable_sub_comments=body.enable_sub_comments if body.enable_sub_comments is not None else False,
        time_range=body.time_range or "all",
        content_types=body.content_types,
    )
    # 让出事件循环，确保后台任务已启动并写入 debug 日志
    await asyncio.sleep(0)
    resp = task_manager.get_status_response(task_id) or {}
    return SearchResponse(
        task_id=task_id,
        status=resp.get("status", "pending"),
        total_found=resp.get("total_found", 0),
        by_platform=resp.get("by_platform", {}),
        progress=resp.get("progress", 0),
        message=resp.get("message", "started"),
    )


@router.get("/status/{task_id}", response_model=SearchResponse)
async def search_status(task_id: str):
    """Get task status."""
    resp = task_manager.get_status_response(task_id)
    if not resp:
        raise HTTPException(status_code=404, detail="task not found")
    return SearchResponse(**resp)


@router.get("/results/{task_id}", response_model=List[UnifiedPost])
async def search_results(task_id: str, platform: Optional[str] = None):
    """Get search results (optionally filter by platform)."""
    if not task_manager.get_task(task_id):
        raise HTTPException(status_code=404, detail="task not found")
    return task_manager.get_results(task_id, platform)


@router.post("/stop/{task_id}")
async def search_stop(task_id: str):
    """Request stop for the task."""
    if not task_manager.get_task(task_id):
        raise HTTPException(status_code=404, detail="task not found")
    task_manager.request_stop(task_id)
    resp = task_manager.get_status_response(task_id) or {}
    return {"status": "ok", "task_id": task_id, **resp}


@router.get("/comments/{platform}/{post_id}", response_model=List[UnifiedComment])
async def get_post_comments(platform: str, post_id: str, task_id: Optional[str] = None):
    """Get comments for a post. May use task_id for cached comments."""
    if task_id and task_manager.get_task(task_id):
        cached = task_manager.get_cached_comments(task_id, platform, post_id)
        if cached is not None:
            return cached

    from app.crawler.registry import get_crawler
    crawler_cls = get_crawler(platform)
    if not crawler_cls:
        return []
    crawler = crawler_cls()
    comments = await crawler.get_comments(platform, post_id, max_count=20, enable_sub=False)
    if task_id and comments:
        task_manager.cache_comments(task_id, platform, post_id, comments)
    return comments
