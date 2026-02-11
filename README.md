# GetSomeHints

多平台爬虫搜索：按关键词与条件对多平台（目前是小红书、抖音，快手、B站、微博、贴吧、知乎等暂停开发）抓取帖子、视频、图文、评论等；内置代理池与防封策略。

**当前版本**：抖音、小红书使用 Playwright + 登录态 + 代理池，安装 Playwright 后为真实抓取；其余平台为示例桩。

## 结构

- **backend**：Python FastAPI，搜索 API、任务管理、代理池、各平台爬虫。
- **frontend**：React + Vite + TypeScript，像素风 UI，与后端 API 契约一致。

克隆后 **browser_data**、**node_modules** 已由 `.gitignore` 忽略，请勿提交；新环境需在 frontend 下执行 `npm install` 或 `npm ci`。若 `backend/browser_data` 曾被提交过，需执行 `git rm -r --cached backend/browser_data` 才能从仓库中移除（本地目录保留）。

## 环境

- Python 3.11（推荐 Conda）
- Node.js >= 16

```bash
conda create -n getsomehints python=3.11 -y
conda activate getsomehints
cd backend && pip install -r requirements.txt
```

复制 `backend/.env.example` 为 `backend/.env`，按需填写（见下方代理配置、Playwright 配置）。

## 运行

| 脚本 | 说明 |
|------|------|
| `./start_backend.sh` | 启动后端（conda getsomehints，端口 8000） |
| `./start_frontend.sh` | 启动前端（无 node_modules 会先 npm install，端口 5173） |
| `./start_all.sh` | 先后台后端再前台前端；Ctrl+C 一并结束 |

或手动：`cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000`；另开终端 `cd frontend && npm run dev`。浏览器访问 http://localhost:5173，API 为 http://127.0.0.1:8000。

### 一键部署（空环境，点开链接即用）

适用于**没有任何环境**的 Windows 或 Linux：自动安装/检测 Python、Node，安装依赖并启动服务，最后打开浏览器。

| 系统 | 操作 |
|------|------|
| **Linux** | 在项目根目录执行：`bash scripts/oneclick-linux.sh`（Debian/Ubuntu 等会提示安装 python3、node、npm） |
| **Windows** | 双击运行 `scripts\oneclick-windows.bat`，或在项目根目录打开 PowerShell 执行：<br>`powershell -ExecutionPolicy Bypass -File scripts\oneclick-windows.ps1` |

完成后终端会提示访问 **http://localhost:5173**，浏览器一般会自动打开；未打开则手动粘贴该链接即可使用。  
停止服务：Linux 执行 `kill $(cat .backend.pid) $(cat .frontend.pid)`；Windows 在任务管理器中结束对应 python/node 进程。

### 排查（无反应 / 后端无日志）

1. 仅用一种方式启动后端（默认 8000）。
2. 打开 http://127.0.0.1:8000/api/debug/whoami 核对 `pid` 与日志中一致。
3. 搜索后查看是否出现 `POST /api/search/start`、`run_search_task started`。
4. 抖音/小红书真实抓取需 `cd backend && playwright install chromium`（见下方 Playwright 与登录态）。
5. WebSocket 日志：`ws://127.0.0.1:8000/api/ws/logs`。若连接失败，先启动后端再开前端，或确认端口与前端 `VITE_API_BASE_URL` 一致。

## 数据与存储

- **当前任务**：后端内存，`GET /api/search/results/{task_id}`；前端轮询，结束后写入历史。
- **历史**：前端 localStorage（`getsomehints-history`），无单独库/文件。

---

## API 契约

前端 `frontend/src/services/api.ts` 与后端 `backend/app/routers/` 对接。请求/响应均为 JSON，字段 **snake_case**。

- **Base URL**：默认 `http://127.0.0.1:8000`（前端 `API_BASE_URL`）
- **CORS**：允许 `localhost:5173`、`localhost:3000`、`127.0.0.1:5173`、`127.0.0.1:3000`

### 搜索 API（/api/search）

| 方法 | 路径 | 前端方法 | 说明 |
|------|------|----------|------|
| POST | /api/search/start | searchApi.startSearch | 发起搜索 |
| GET | /api/search/status/{task_id} | searchApi.getSearchStatus | 任务状态 |
| GET | /api/search/results/{task_id} | searchApi.getSearchResults | 搜索结果（可选 ?platform=） |
| POST | /api/search/stop/{task_id} | searchApi.stopSearch | 停止任务 |
| GET | /api/search/comments/{platform}/{post_id} | searchApi.getPostComments | 帖子评论（可选 ?task_id=） |

- **POST /api/search/start**：Body 见 `SearchStartRequest`（keywords, platforms, max_count, enable_comments, time_range, content_types 等）。Response：`SearchResponse`（task_id, status, total_found, by_platform, progress, message）。
- **GET /api/search/status/{task_id}**：Response 同上。
- **GET /api/search/results/{task_id}**：Response 为 `UnifiedPost[]`（含 platform, post_id, title, content, author, publish_time, like_count, comment_count, url, image_urls, video_url, platform_data）。
- **GET /api/search/comments/{platform}/{post_id}**：Response 为 `UnifiedComment[]`（comment_id, post_id, platform, content, author, comment_time, like_count, parent_comment_id, sub_comment_count）。

### 分析 API（/api/analysis）

| 方法 | 路径 | 前端方法 |
|------|------|----------|
| POST | /api/analysis/stats | analysisApi.getStats |
| POST | /api/analysis/distribution | analysisApi.getDistribution |
| POST | /api/analysis/trends | analysisApi.getTrends |
| POST | /api/analysis/top-authors | analysisApi.getTopAuthors |

以上 POST 均带 Query：`task_id`（必填）；top-authors 另有 `limit`（默认 10）。Response 类型见前端 `types/index.ts`（AnalysisStats、平台分布、趋势、热门作者）。

### 其他

- **GET /api/health**：`{ "status": "ok" }`
- **GET /api/config/proxy**：代理配置状态（不含密钥）
- **WebSocket /api/ws/logs**：实时日志流

---

## Playwright 与登录态

抖音/小红书爬虫基于 Playwright：**浏览器登录 → 保存登录态 → 带 Cookie 请求**，无需逆向签名。

### 安装

```bash
cd backend
playwright install chromium
```

### 浏览器与登录态

- **标准模式**：Playwright 启动 Chromium，打开目标站完成登录，同一上下文请求接口。
- **CDP 模式**：`.env` 设 `MC_ENABLE_CDP_MODE=true`，Chrome 带 `--remote-debugging-port=9222` 启动后，爬虫连接已有浏览器复用登录态。

**登录态目录**：默认 `backend/browser_data/{platform}_user_data_dir`（如 `dy_user_data_dir`、`xhs_user_data_dir`）。可设置环境变量 **BROWSER_DATA_DIR** 改为项目外路径（如 `~/.getsomehints/browser_data`）。

**登录方式**：qrcode（默认，弹窗扫码）或 cookie（`.env` 中 `MC_LOGIN_TYPE=cookie`、`MC_COOKIES=...`）。需重新登录时可在 `backend` 下运行 `python scripts/clear_mc_login.py --platform dy` 或 `--platform xhs` 或 `--all` 清除对应浏览器数据。

### 数据流

爬虫结果经内存 store 收集，由 `app/crawler/douyin.py`、`xhs.py` 转为 UnifiedPost/UnifiedComment 通过 API 返回前端，不写 MC 的 CSV/DB。

### Playwright 相关配置

| 变量 | 说明 | 默认 |
|------|------|------|
| BROWSER_DATA_DIR | 浏览器数据根目录 | 空（用 backend/browser_data） |
| MC_HEADLESS | 无头模式 | false |
| MC_SAVE_LOGIN_STATE | 保存登录态 | true |
| MC_LOGIN_TYPE | qrcode / cookie | qrcode |
| MC_COOKIES | Cookie 登录字符串 | 空 |
| MC_ENABLE_CDP_MODE | CDP 连接已有浏览器 | false |
| CRAWLER_MAX_NOTES_COUNT | 单次最大条数 | 30 |

---

## 代理配置（快代理 DPS）

爬虫通过快代理 DPS 获取 IP 做代理轮换。

### 获取密钥

1. 登录 [快代理](https://www.kuaidaili.com/)
2. 进入 DPS 订单页 → **API 密钥** 获取 **SecretId**、**Signature**

### 鉴权方式（二选一）

- **用户名 + 密码**：会员中心为订单设置代理用户名、密码
- **IP 白名单**：绑定本机公网 IP（固定出口环境）

### 环境变量

在 `backend/.env` 中配置（勿提交 Git）：

```bash
KDL_SECRET_ID=你的SecretId
KDL_SIGNATURE=你的Signature
KDL_USER_NAME=代理用户名
KDL_USER_PWD=代理密码
ENABLE_IP_PROXY=true
IP_PROXY_POOL_COUNT=2
```

小写变量名（如 `kdl_secret_id`）同样支持。额度为 0 时拉取失败会降级为无代理。

### 行为简述

- 首次请求或池空时调用 getdps 拉取 IP；过期前约 5 秒视为失效。
- 遇到 403/502/503 时 `invalidate_current()`，下次请求换新 IP。
- getdps 限频约 1 秒 10 次，池子按需取用。

---

## 防封策略

### 请求频率

- **随机延迟**：请求前 `random_sleep()`，间隔 `CRAWLER_MIN_SLEEP_SEC`～`CRAWLER_MAX_SLEEP_SEC`（默认 1～3 秒）。
- **并发**：`MAX_CONCURRENCY_NUM=1`，串行执行各平台。
- **单次数量**：`CRAWLER_MAX_NOTES_COUNT`、`CRAWLER_MAX_COMMENTS_COUNT` 限制单次拉取。

### 代理

- 启用 `ENABLE_IP_PROXY` 后通过 `get_or_refresh_proxy()` 取代理，过期前约 30 秒更换。
- 403/429/502/503 时 `invalidate_current()` 换 IP。

### UA 与请求头

- `app/crawler/anti_block.py` 中 `USER_AGENTS`、`get_random_ua()`；Referer/Accept-Language 建议与目标站一致。

### 熔断

- 同一任务连续失败 3 次后停止后续平台；单次失败换 IP 后继续下一平台。

### 防封相关配置

| 变量 | 说明 | 默认 |
|------|------|------|
| CRAWLER_MIN_SLEEP_SEC | 最小请求间隔（秒） | 1.0 |
| CRAWLER_MAX_SLEEP_SEC | 最大请求间隔（秒） | 3.0 |
| MAX_CONCURRENCY_NUM | 并发数 | 1 |
| CRAWLER_MAX_NOTES_COUNT | 单次最大条数 | 30 |
| ENABLE_IP_PROXY | 启用代理池 | false |
| PROXY_BUFFER_SECONDS | 代理提前过期缓冲（秒） | 30 |

---

## 免责声明

仅供学习与研究使用，请遵守各平台使用条款与 robots.txt，控制频率与数据量，不用于商业与非法用途。
