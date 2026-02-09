# -*- coding: utf-8 -*-
"""调试日志：同时写 backend/crawler_debug.log 与 /tmp/getsomehints_debug.log（固定路径，排除多进程/路径歧义）."""
import os
import sys
from datetime import datetime
from pathlib import Path

_BACKEND_LOG = Path(__file__).resolve().parent.parent / "crawler_debug.log"
_FIXED_LOG = Path("/tmp/getsomehints_debug.log")  # 固定路径，任何进程都写同一文件
_PID = os.getpid()


def debug_log(msg: str) -> None:
    try:
        line = f"{datetime.now().isoformat()} pid={_PID} {msg}\n"
        sys.stderr.write(line)
        sys.stderr.flush()
        for p in (_BACKEND_LOG, _FIXED_LOG):
            try:
                with open(p, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception:
                pass
    except Exception:
        pass
