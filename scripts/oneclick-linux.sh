#!/usr/bin/env bash
# GetSomeHints 一键部署（Linux）
# 适用于：无环境或仅有系统的 Debian/Ubuntu、Fedora/RHEL 等
# 用法：在项目根目录执行 bash scripts/oneclick-linux.sh
# 完成后在浏览器打开提示的链接即可使用

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "========== GetSomeHints 一键部署 (Linux) =========="
echo "项目目录: $REPO_ROOT"
echo ""

# ----- 1. 检测/安装系统依赖 -----
need_install=""
command -v python3 &>/dev/null || need_install="python3"
command -v node &>/dev/null || need_install="${need_install:+$need_install }nodejs"
command -v npm &>/dev/null || need_install="${need_install:+$need_install }npm"

if [[ -n "$need_install" ]]; then
  echo "[1/6] 安装系统依赖: $need_install"
  if command -v apt-get &>/dev/null; then
    sudo apt-get update -qq
    sudo apt-get install -y python3 python3-pip python3-venv nodejs npm 2>/dev/null || \
    sudo apt-get install -y python3 python3-pip python3-venv nodejs 2>/dev/null || true
  elif command -v dnf &>/dev/null; then
    sudo dnf install -y python3 python3-pip nodejs npm 2>/dev/null || sudo dnf install -y python3 nodejs 2>/dev/null || true
  elif command -v yum &>/dev/null; then
    sudo yum install -y python3 python3-pip nodejs npm 2>/dev/null || sudo yum install -y python3 nodejs 2>/dev/null || true
  else
    echo "请先手动安装: Python 3.9+、Node.js 18+、npm。然后重新运行本脚本。"
    exit 1
  fi
else
  echo "[1/6] 系统依赖已满足 (python3, node, npm)"
fi

PYTHON="$(command -v python3.11 2>/dev/null || command -v python3.9 2>/dev/null || command -v python3 2>/dev/null)"
NODE="$(command -v node 2>/dev/null)"
echo "  使用 Python: $PYTHON ($($PYTHON -c 'import sys; print(sys.version.split()[0])' 2>/dev/null || echo '?'))"
echo "  使用 Node:   $NODE ($(node -v 2>/dev/null || echo '未找到'))"
echo ""

# ----- 2. 后端：虚拟环境 + 依赖 -----
echo "[2/6] 配置后端 (Python)"
BACKEND="$REPO_ROOT/backend"
cd "$BACKEND"
if [[ ! -d .venv ]]; then
  "$PYTHON" -m venv .venv
fi
set +e
source .venv/bin/activate
set -e
pip install -q -r requirements.txt
if ! python -c "import playwright" 2>/dev/null; then
  pip install -q playwright
fi
playwright install chromium 2>/dev/null || true
echo "  后端依赖就绪"
echo ""

# ----- 3. 后端 .env -----
if [[ ! -f "$BACKEND/.env" ]]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  # 一键部署使用默认端口 8000，与前端约定一致
  sed -i.bak 's/^API_PORT=.*/API_PORT=8000/' "$BACKEND/.env" 2>/dev/null || true
  echo "[3/6] 已生成 backend/.env（默认端口 8000）"
else
  echo "[3/6] backend/.env 已存在，跳过"
fi
echo ""

# ----- 4. 前端：依赖 -----
echo "[4/6] 配置前端 (Node)"
FRONTEND="$REPO_ROOT/frontend"
cd "$FRONTEND"
if [[ ! -d node_modules ]]; then
  npm install --silent
fi
# 前端 .env 指向后端 8000
printf '%s\n' "VITE_API_BASE_URL=http://localhost:8000" "VITE_WS_BASE_URL=ws://localhost:8000" > "$FRONTEND/.env"
echo "  前端依赖就绪"
echo ""

# ----- 5. 启动服务 -----
echo "[5/6] 启动后端与前端服务"
cd "$REPO_ROOT"
API_PORT="${API_PORT:-8000}"
FRONT_PORT="${FRONT_PORT:-5173}"

# 避免端口占用
for port in $API_PORT $FRONT_PORT; do
  if command -v lsof &>/dev/null && lsof -i ":$port" -sTCP:LISTEN &>/dev/null; then
    echo "警告: 端口 $port 已被占用。若需使用请先停止占用进程后重试。"
    echo "  lsof -i :$port -sTCP:LISTEN"
    exit 1
  fi
done

# 后台启动后端
cd "$BACKEND"
source .venv/bin/activate 2>/dev/null || true
export API_PORT
nohup uvicorn app.main:app --host 0.0.0.0 --port "$API_PORT" --reload > "$REPO_ROOT/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$REPO_ROOT/.backend.pid"

# 等待后端就绪
for i in $(seq 1 15); do
  if curl -s "http://127.0.0.1:$API_PORT/api/debug/whoami" &>/dev/null; then
    break
  fi
  sleep 1
done

# 后台启动前端
cd "$FRONTEND"
nohup npm run dev -- --host 0.0.0.0 --port "$FRONT_PORT" > "$REPO_ROOT/frontend.log" 2>&1 &
FRONT_PID=$!
echo "$FRONT_PID" > "$REPO_ROOT/.frontend.pid"

# 等待前端就绪
for i in $(seq 1 20); do
  if curl -s "http://127.0.0.1:$FRONT_PORT" &>/dev/null; then
    break
  fi
  sleep 1
done
echo "  后端 PID: $BACKEND_PID (端口 $API_PORT)"
echo "  前端 PID: $FRONT_PID (端口 $FRONT_PORT)"
echo ""

# ----- 6. 打开浏览器 -----
echo "[6/6] 部署完成"
APP_URL="http://localhost:$FRONT_PORT"
echo ""
echo "----------------------------------------"
echo "  点开下面链接即可使用："
echo "  $APP_URL"
echo "----------------------------------------"
echo ""
echo "日志: backend.log / frontend.log"
echo "停止: kill \$(cat .backend.pid) \$(cat .frontend.pid)"
echo ""

if command -v xdg-open &>/dev/null; then
  xdg-open "$APP_URL" 2>/dev/null || true
elif command -v sensible-browser &>/dev/null; then
  sensible-browser "$APP_URL" 2>/dev/null || true
fi
