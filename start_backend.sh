#!/usr/bin/env bash
# 启动后端 API 服务（默认端口 8000）
set -e
PORT="${API_PORT:-8000}"
cd "$(dirname "$0")/backend"

# 仅当有进程在「监听」该端口时才拒绝启动（不把浏览器等客户端的已关闭连接算作占用）
if command -v lsof &>/dev/null; then
  if lsof -i ":$PORT" -sTCP:LISTEN &>/dev/null; then
    echo "错误: 端口 $PORT 已被占用（有进程在监听），当前后端无法启动。" >&2
    echo "请先停掉监听该端口的进程再启动：" >&2
    echo "  lsof -i :$PORT -sTCP:LISTEN   # 查看监听进程" >&2
    echo "  kill \$(lsof -t -i :$PORT -sTCP:LISTEN)   # 停掉后重跑 ./start_backend.sh" >&2
    lsof -i ":$PORT" -sTCP:LISTEN 2>/dev/null || true
    exit 1
  fi
fi

if command -v conda &>/dev/null && conda info --envs | grep -q getsomehints; then
  eval "$(conda shell.bash hook)"
  conda activate getsomehints
fi
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --reload
