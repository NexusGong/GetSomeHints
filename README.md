# GetSomeHints

多平台爬虫搜索工具：按关键词与搜索条件，对多个平台（小红书、抖音、快手、B站、微博、贴吧、知乎等）进行数据抓取，支持帖子、视频、图文、评论等；内置代理池与防封策略。

**当前版本**：抖音、小红书已接入 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)（Playwright + 登录态 + 代理池），有 `mediacrawler_bundle` 且安装 Playwright 后为真实抓取；其余平台为示例桩。Playwright 安装、登录态、代理池与数据保存见 [docs/playwright_login.md](docs/playwright_login.md)。

## 结构

- **backend**：Python FastAPI 服务，提供搜索 API、任务管理、代理池、各平台爬虫。
- **frontend**：React + Vite + TypeScript，像素风 UI，与后端 API 契约一致。
- **docs**：代理配置（proxy_setup.md）、防封策略（anti_block.md）、Playwright 与登录态（playwright_login.md）。

## 环境

- Python 3.11（推荐 Conda）
- Node.js >= 16（前端）

### Conda 环境

```bash
conda remove -n getsomehints --all -y
conda create -n getsomehints python=3.11 -y
conda activate getsomehints
cd backend && pip install -r requirements.txt
```

### 后端配置

复制 `backend/.env.example` 为 `backend/.env`，按需填写（如快代理 KDL_*）。详见 [docs/proxy_setup.md](docs/proxy_setup.md)。

## 运行

项目根目录下提供 Bash 启动脚本：

| 脚本 | 说明 |
|------|------|
| `./start_backend.sh` | 启动后端（自动激活 conda 环境 getsomehints，端口 8000） |
| `./start_frontend.sh` | 启动前端（若无 node_modules 会先 npm install，端口 5173） |
| `./start_all.sh` | 先后台启动后端，再前台启动前端；Ctrl+C 退出时一并结束后端 |

也可手动运行：

```bash
# 后端
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 前端（另开终端）
cd frontend
npm install && npm run dev
```

浏览器访问前端（默认 http://localhost:5173），API 请求会发往 http://127.0.0.1:8000。

### 搜索「无反应」或「前端有 task_id 但后端无日志」时排查

**若前端有响应但后端无日志**：多半是前端连到了别的进程（例如之前用 8080 时被占）。现在默认用 **8000** 端口，一般不会冲突。

1. **只用一个方式启动后端**：`./start_backend.sh`（默认 8000）。  
2. **确认是同一进程在响应**：浏览器打开 `http://127.0.0.1:8000/api/debug/whoami`，看返回的 `pid` 与 `crawler_debug.log` 里启动时的 `pid=` 是否一致。
3. **再点搜索**  
   看 `/tmp/getsomehints_debug.log` 或 `backend/crawler_debug.log` 是否出现 `[Request] POST /api/search/start` 和 `[Crawler] run_search_task started`。有则说明请求和任务都在当前后端跑。
4. **抖音/小红书真实抓取**：需先 `cd backend && python scripts/sync_mediacrawler.py` 拉取 MediaCrawler 代码，再 `playwright install chromium`。登录态、代理池等见 [docs/playwright_login.md](docs/playwright_login.md)。未拉取或未安装 Playwright 时会返回 mock 数据。
5. **WebSocket 日志流**：实时日志使用 `ws://127.0.0.1:8000/api/ws/logs`（由 API 地址派生）。控制台出现 `WebSocket connection to '...' failed` 的常见原因：**① 后端未启动**（先执行 `./start_backend.sh` 再开前端）、**② 先打开前端后启动后端**（前端已发起连接但 8000 端口尚未监听）。前端会延迟约 0.8 秒再连并在断开后自动重试，后端就绪后一般会连上；若持续失败请确认端口与 `VITE_API_BASE_URL` 一致。

## 搜索结果保存在哪里？

- **当前任务**：后端内存中（`task_manager`），通过 `GET /api/search/results/{task_id}` 返回；前端轮询并展示，任务完成后会写入历史。
- **历史记录**：前端 `localStorage`（key: `getsomehints-history`），每条记录包含当次关键词、平台、结果列表与评论等；删除或清空历史会同步从 localStorage 移除，无单独文件或数据库。

## API 契约（与前端一致）

详见 [docs/api.md](docs/api.md)。简要：

- `POST /api/search/start`：发起搜索，返回 `task_id`
- `GET /api/search/status/{task_id}`：任务状态
- `GET /api/search/results/{task_id}`：搜索结果
- `POST /api/search/stop/{task_id}`：停止任务
- `GET /api/search/comments/{platform}/{post_id}`：帖子评论
- `POST /api/analysis/stats` 等：分析接口（query 参数 `task_id`）

## 代理与防封

- 代理：支持快代理 DPS 私密代理，通过环境变量配置；见 [docs/proxy_setup.md](docs/proxy_setup.md)。
- 防封：随机延迟、UA 池、代理轮换、失败换 IP、连续失败熔断；见 [docs/anti_block.md](docs/anti_block.md)。

## 免责声明

仅供学习与研究使用，请遵守各平台使用条款与 robots.txt，控制请求频率与数据量，不用于商业与非法用途。
