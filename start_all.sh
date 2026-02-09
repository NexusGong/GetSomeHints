#!/usr/bin/env bash
# 同时启动后端与前端（后端后台运行，前端前台）
set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# 后台启动后端
"$ROOT/start_backend.sh" &
BACKEND_PID=$!
echo "Backend started (PID $BACKEND_PID), waiting for port 8000..."
for i in {1..30}; do
  if curl -s -o /dev/null http://127.0.0.1:8000/api/health 2>/dev/null; then
    echo "Backend ready."
    break
  fi
  sleep 0.5
done

# 前台启动前端（Ctrl+C 会只结束前端）
trap "kill $BACKEND_PID 2>/dev/null || true" EXIT
"$ROOT/start_frontend.sh"
