# -*- coding: utf-8 -*-
"""Anti-block: random delay, UA pool, and helpers for crawlers."""
import asyncio
import random
from typing import List

from app.config import settings

# Common browser User-Agent strings (pool for rotation)
USER_AGENTS: List[str] = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]


def get_random_ua() -> str:
    """Return a random User-Agent from pool."""
    return random.choice(USER_AGENTS)


async def random_sleep() -> None:
    """Sleep a random duration between CRAWLER_MIN_SLEEP_SEC and CRAWLER_MAX_SLEEP_SEC."""
    lo = settings.CRAWLER_MIN_SLEEP_SEC
    hi = settings.CRAWLER_MAX_SLEEP_SEC
    delay = random.uniform(lo, hi)
    await asyncio.sleep(delay)


def should_switch_ip_on_response(status_code: int) -> bool:
    """Return True if we should switch proxy after this response (403, 502, 503, etc.)."""
    return status_code in (403, 429, 502, 503)
