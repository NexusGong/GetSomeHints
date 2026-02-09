# -*- coding: utf-8 -*-
"""Analysis API: stats, distribution, trends, top-authors (match frontend)."""
from typing import Any, List

from fastapi import APIRouter, HTTPException, Query

from app.services.task_manager import task_manager

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/stats")
async def analysis_stats(task_id: str = Query(..., alias="task_id")):
    """Get aggregate stats for a task's results."""
    t = task_manager.get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    posts = t.results
    total_posts = len(posts)
    authors = set((p.author.author_id, p.platform) for p in posts)
    total_authors = len(authors)
    platform_stats: List[dict] = []
    for platform in sorted(set(p.platform for p in posts)):
        pl_posts = [p for p in posts if p.platform == platform]
        platform_stats.append({
            "platform": platform,
            "post_count": len(pl_posts),
            "comment_count": 0,
            "author_count": len(set(p.author.author_id for p in pl_posts)),
            "avg_likes": sum(p.like_count for p in pl_posts) / len(pl_posts) if pl_posts else 0,
            "avg_comments": sum(p.comment_count for p in pl_posts) / len(pl_posts) if pl_posts else 0,
        })
    return {
        "total_posts": total_posts,
        "total_comments": 0,
        "total_authors": total_authors,
        "platform_stats": platform_stats,
        "time_range": {},
    }


@router.post("/distribution")
async def analysis_distribution(task_id: str = Query(..., alias="task_id")):
    """Get platform distribution (count per platform)."""
    t = task_manager.get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    return t.by_platform


@router.post("/trends")
async def analysis_trends(
    task_id: str = Query(..., alias="task_id"),
    interval: str = Query("day", alias="interval"),
):
    """Get time trends (stub: return empty)."""
    t = task_manager.get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    return {}


@router.post("/top-authors")
async def analysis_top_authors(
    task_id: str = Query(..., alias="task_id"),
    limit: int = Query(10, alias="limit"),
):
    """Get top authors by post count. Response shape matches frontend: { author: { author_id, author_name, platform }, post_count }."""
    t = task_manager.get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    from collections import Counter
    author_counts: Counter = Counter()
    author_info: dict = {}  # (author_id, platform) -> author dict
    for p in t.results:
        key = (p.author.author_id, p.platform)
        author_counts[key] += 1
        if key not in author_info:
            author_info[key] = {
                "author_id": p.author.author_id,
                "author_name": p.author.author_name or p.author.author_id,
                "platform": p.platform,
            }
    top = author_counts.most_common(limit)
    return [
        {"author": author_info[k], "post_count": c}
        for k, c in top
    ]
