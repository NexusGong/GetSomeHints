#!/usr/bin/env bash
# 启动前端开发服务（默认端口 5173）
set -e
cd "$(dirname "$0")/frontend"
if [[ ! -d node_modules ]]; then
  echo "Installing frontend dependencies..."
  npm install
fi
exec npm run dev
