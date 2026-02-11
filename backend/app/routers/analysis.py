# -*- coding: utf-8 -*-
"""Analysis API: stats, distribution, trends, top-authors (match frontend)."""
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from app.schemas import UnifiedPost
from app.services.task_manager import task_manager

router = APIRouter(prefix="/analysis", tags=["analysis"])


def _post_content_type(p: UnifiedPost) -> str:
    """根据帖子推断内容类型: video | image_text | link。"""
    if p.video_url:
        return "video"
    if p.image_urls and len(p.image_urls) > 0:
        return "image_text"
    return "link"


def _parse_publish_date(publish_time: str) -> str | None:
    """从 publish_time 解析出 YYYY-MM-DD，用于趋势聚合。"""
    if not publish_time or not isinstance(publish_time, str):
        return None
    s = publish_time.strip()
    # 纯数字视为 Unix 时间戳（秒或毫秒）
    if re.match(r"^\d+$", s):
        try:
            ts = int(s)
            if ts > 1e12:
                ts = ts // 1000
            dt = datetime.utcfromtimestamp(ts)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, OSError):
            return None
    # ISO 或 YYYY-MM-DD 前缀
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        try:
            datetime.strptime(s[:10], "%Y-%m-%d")
            return s[:10]
        except ValueError:
            pass
    return None


@router.post("/stats")
async def analysis_stats(task_id: str = Query(..., alias="task_id")):
    """Get aggregate stats for a task's results."""
    t = task_manager.get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    posts = t.results
    total_posts = len(posts)
    total_comments = sum(p.comment_count for p in posts)
    authors = set((p.author.author_id, p.platform) for p in posts)
    total_authors = len(authors)
    platform_stats: List[dict] = []
    for platform in sorted(set(p.platform for p in posts)):
        pl_posts = [p for p in posts if p.platform == platform]
        platform_stats.append({
            "platform": platform,
            "post_count": len(pl_posts),
            "comment_count": sum(p.comment_count for p in pl_posts),
            "author_count": len(set(p.author.author_id for p in pl_posts)),
            "avg_likes": sum(p.like_count for p in pl_posts) / len(pl_posts) if pl_posts else 0,
            "avg_comments": sum(p.comment_count for p in pl_posts) / len(pl_posts) if pl_posts else 0,
        })
    # 内容类型分布（供决策）
    content_type_dist: Dict[str, int] = Counter(_post_content_type(p) for p in posts)
    # 互动区间分布：点赞/评论分段
    like_buckets = {"0-100": 0, "101-1k": 0, "1k-10k": 0, "10k+": 0}
    comment_buckets = {"0-10": 0, "11-100": 0, "101-1k": 0, "1k+": 0}
    for p in posts:
        if p.like_count <= 100:
            like_buckets["0-100"] += 1
        elif p.like_count <= 1000:
            like_buckets["101-1k"] += 1
        elif p.like_count <= 10000:
            like_buckets["1k-10k"] += 1
        else:
            like_buckets["10k+"] += 1
        if p.comment_count <= 10:
            comment_buckets["0-10"] += 1
        elif p.comment_count <= 100:
            comment_buckets["11-100"] += 1
        elif p.comment_count <= 1000:
            comment_buckets["101-1k"] += 1
        else:
            comment_buckets["1k+"] += 1
    return {
        "total_posts": total_posts,
        "total_comments": total_comments,
        "total_authors": total_authors,
        "platform_stats": platform_stats,
        "time_range": {},
        "content_type_distribution": dict(content_type_dist),
        "like_buckets": like_buckets,
        "comment_buckets": comment_buckets,
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
    """Get time trends: 按日聚合发布数量，返回 { "YYYY-MM-DD": count }。"""
    t = task_manager.get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    counts: Dict[str, int] = {}
    for p in t.results:
        day = _parse_publish_date(p.publish_time)
        if day:
            counts[day] = counts.get(day, 0) + 1
    return dict(sorted(counts.items()))


@router.post("/top-authors")
async def analysis_top_authors(
    task_id: str = Query(..., alias="task_id"),
    limit: int = Query(10, alias="limit"),
):
    """Get top authors by post count. Response shape matches frontend: { author: { author_id, author_name, platform }, post_count }."""
    t = task_manager.get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
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


@router.post("/top-posts")
async def analysis_top_posts(
    task_id: str = Query(..., alias="task_id"),
    limit: int = Query(10, alias="limit"),
    sort_by: str = Query("likes", alias="sort_by"),  # likes | comments
):
    """获取高互动帖子，供决策参考。返回简要字段列表。"""
    t = task_manager.get_task(task_id)
    if not t:
        raise HTTPException(status_code=404, detail="task not found")
    posts = list(t.results)
    if sort_by == "comments":
        posts = sorted(posts, key=lambda p: p.comment_count, reverse=True)
    else:
        posts = sorted(posts, key=lambda p: p.like_count, reverse=True)
    out: List[dict] = []
    for p in posts[:limit]:
        out.append({
            "post_id": p.post_id,
            "platform": p.platform,
            "title": (p.title or p.content or "")[:80],
            "like_count": p.like_count,
            "comment_count": p.comment_count,
            "content_type": _post_content_type(p),
        })
    return out
