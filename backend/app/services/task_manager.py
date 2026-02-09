# -*- coding: utf-8 -*-
"""In-memory task state and results storage."""
import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.schemas import UnifiedPost, UnifiedComment


@dataclass
class TaskState:
    """Single search task state."""
    task_id: str
    status: str  # pending, running, completed, failed, stopped
    total_found: int = 0
    by_platform: Dict[str, int] = field(default_factory=dict)
    progress: int = 0
    message: str = ""
    results: List[UnifiedPost] = field(default_factory=list)
    comments_cache: Dict[str, List[UnifiedComment]] = field(default_factory=dict)  # key: f"{platform}_{post_id}"
    stop_requested: bool = False


class TaskManager:
    """Singleton task manager: create task, update status/results, stop."""

    def __init__(self) -> None:
        self._tasks: Dict[str, TaskState] = {}
        self._lock = asyncio.Lock()

    def create_task(self) -> str:
        """Create a new task, return task_id."""
        task_id = str(uuid.uuid4())
        self._tasks[task_id] = TaskState(
            task_id=task_id,
            status="pending",
            by_platform={},
        )
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskState]:
        return self._tasks.get(task_id)

    async def set_running(self, task_id: str) -> None:
        async with self._lock:
            t = self._tasks.get(task_id)
            if t:
                t.status = "running"
                t.progress = 0

    async def set_progress(self, task_id: str, total_found: int, by_platform: Dict[str, int], progress: int = 0) -> None:
        async with self._lock:
            t = self._tasks.get(task_id)
            if t:
                t.total_found = total_found
                t.by_platform = dict(by_platform)
                if progress >= 0:
                    t.progress = progress

    async def append_results(self, task_id: str, posts: List[UnifiedPost]) -> None:
        async with self._lock:
            t = self._tasks.get(task_id)
            if t:
                seen = {p.post_id for p in t.results}
                for p in posts:
                    if p.post_id not in seen:
                        seen.add(p.post_id)
                        t.results.append(p)

    async def set_completed(self, task_id: str, total_found: int, by_platform: Dict[str, int]) -> None:
        async with self._lock:
            t = self._tasks.get(task_id)
            if t:
                t.status = "completed"
                t.progress = 100
                t.total_found = total_found
                t.by_platform = dict(by_platform)
                t.message = "completed"

    async def set_failed(self, task_id: str, message: str = "failed") -> None:
        async with self._lock:
            t = self._tasks.get(task_id)
            if t:
                t.status = "failed"
                t.message = message

    async def set_stopped(self, task_id: str) -> None:
        async with self._lock:
            t = self._tasks.get(task_id)
            if t:
                t.status = "stopped"
                t.message = "stopped"

    def request_stop(self, task_id: str) -> None:
        t = self._tasks.get(task_id)
        if t:
            t.stop_requested = True

    def is_stop_requested(self, task_id: str) -> bool:
        t = self._tasks.get(task_id)
        return t.stop_requested if t else True

    def get_results(self, task_id: str, platform: Optional[str] = None) -> List[UnifiedPost]:
        t = self._tasks.get(task_id)
        if not t:
            return []
        if platform:
            return [p for p in t.results if p.platform == platform]
        return list(t.results)

    def get_status_response(self, task_id: str) -> Optional[dict]:
        t = self._tasks.get(task_id)
        if not t:
            return None
        return {
            "task_id": t.task_id,
            "status": t.status,
            "total_found": t.total_found,
            "by_platform": t.by_platform,
            "progress": t.progress,
            "message": t.message,
        }

    def cache_comments(self, task_id: str, platform: str, post_id: str, comments: List[UnifiedComment]) -> None:
        t = self._tasks.get(task_id)
        if t:
            key = f"{platform}_{post_id}"
            t.comments_cache[key] = comments

    def get_cached_comments(self, task_id: str, platform: str, post_id: str) -> Optional[List[UnifiedComment]]:
        t = self._tasks.get(task_id)
        if not t:
            return None
        key = f"{platform}_{post_id}"
        return t.comments_cache.get(key)


task_manager = TaskManager()
