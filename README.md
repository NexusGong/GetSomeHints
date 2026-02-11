<div align="center">

![GetSomeHints Logo](logo.png)

**GetSomeHints** — 多平台内容搜索与线索分析工具

</div>

---

## 目录

| 章节 | 说明 |
|------|------|
| [简介](#简介) | 项目概述与特性 |
| [快速开始](#快速开始) | 环境、安装、运行 |
| [项目结构](#项目结构) | 目录与数据存储 |
| [API 接口](#api-接口) | 前后端接口约定 |
| [大模型分析](#大模型分析) | 场景与配置 |
| [Playwright 与登录态](#playwright-与登录态) | 浏览器与登录配置 |
| [代理与防封](#代理与防封) | 快代理 DPS、防封策略 |
| [免责声明](#免责声明) | 使用须知 |

---

## 简介

GetSomeHints 支持按**关键词与条件**对多平台进行内容抓取（帖子、视频、图文、评论），内置代理池与防封策略，并对爬取结果支持**大模型分析**（潜在买家/卖家、潜在热销品、热度话题等场景）。

| 项目 | 说明 |
|------|------|
| **爬虫** | 抖音、小红书：Playwright + 登录态 + 代理池（真实抓取）；其余平台为示例桩。 |
| **后端** | Python 3.11 + FastAPI，搜索 / 分析 API，任务管理，代理池。 |
| **前端** | React + Vite + TypeScript，像素风 UI，与后端接口约定一致。 |

---

## 快速开始

### 环境要求

| 依赖 | 版本 |
|------|------|
| Python | 3.11（推荐 Conda） |
| Node.js | ≥ 16 |

### 安装与配置

```bash
# 后端
conda create -n getsomehints python=3.11 -y
conda activate getsomehints
cd backend && pip install -r requirements.txt
cp .env.example .env   # 按需填写，见下方各配置章节
```

```bash
# 前端
cd frontend && npm install
```

### 运行

| 方式 | 命令 | 说明 |
|------|------|------|
| 推荐 | `./start_backend.sh` + `./start_frontend.sh` | 后端 8000，前端 5173 |
| 一键 | `./start_all.sh` | 先后端再前端，Ctrl+C 结束 |
| 手动 | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000` | 另开终端 `cd frontend && npm run dev` |

访问 **http://localhost:5173**，API **http://127.0.0.1:8000**。

### 一键部署（空环境）

| 系统 | 命令 |
|------|------|
| Linux | `bash scripts/oneclick-linux.sh` |
| Windows | 双击 `scripts\oneclick-windows.bat` 或 PowerShell：`powershell -ExecutionPolicy Bypass -File scripts\oneclick-windows.ps1` |

停止：Linux `kill $(cat .backend.pid) $(cat .frontend.pid)`；Windows 在任务管理器中结束对应进程。

### 常见排查

1. 仅用一种方式启动后端（默认 8000）。
2. 检查 http://127.0.0.1:8000/api/debug/whoami 与日志 pid 一致。
3. 真实抓取抖音/小红书需：`cd backend && playwright install chromium`。
4. WebSocket 日志：`ws://127.0.0.1:8000/api/ws/logs`，确保先启后端且前端 `VITE_API_BASE_URL` 一致。

---

## 项目结构

```
GetSomeHints/
├── backend/          # FastAPI，搜索/分析 API，爬虫，代理池
├── frontend/          # React + Vite，像素风 UI
├── scripts/          # 一键部署、清除登录态等
├── logo.png
└── README.md
```

- **browser_data**、**node_modules** 已 `.gitignore`，勿提交。新环境在 `frontend` 下执行 `npm install`。若曾误提交 `backend/browser_data`，执行 `git rm -r --cached backend/browser_data`。

### 数据存储

| 数据 | 位置 | 说明 |
|------|------|------|
| 当前任务 | 后端内存 | `GET /api/search/results/{task_id}`，前端轮询后写入历史 |
| 历史爬取 | 前端 localStorage | key：`getsomehints-history` |
| 大模型分析 | 前端 localStorage | key：`getsomehints-llm-analysis`，详情页可导出 CSV/JSON |

---

## API 接口

前端 `frontend/src/services/api.ts` 与后端 `backend/app/routers/` 对接，请求/响应 JSON，字段 **snake_case**。Base URL 默认 `http://127.0.0.1:8000`，CORS 允许 localhost:5173 / 3000。

### 搜索 `/api/search`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/search/start | 发起搜索，Body：keywords, platforms, max_count 等 |
| GET | /api/search/status/{task_id} | 任务状态 |
| GET | /api/search/results/{task_id} | 搜索结果，可选 ?platform= |
| POST | /api/search/stop/{task_id} | 停止任务 |
| GET | /api/search/comments/{platform}/{post_id} | 帖子评论，可选 ?task_id= |

### 分析 `/api/analysis`

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/analysis/stats | 统计，Query：task_id |
| POST | /api/analysis/distribution | 平台分布 |
| POST | /api/analysis/trends | 趋势 |
| POST | /api/analysis/top-posts | 高互动帖子 |
| POST | /api/analysis/top-authors | 热门作者，Query：task_id, limit |
| GET | /api/analysis/llm-scenarios | 大模型分析场景列表 |
| POST | /api/analysis/llm-leads | 大模型分析，Body：posts / task_id, model, scene |

### 其他

- **GET /api/health** — 健康检查  
- **GET /api/config/proxy** — 代理配置状态（不含密钥）  
- **WebSocket /api/ws/logs** — 实时日志流  

---

## 大模型分析

对爬取结果（当前任务或历史记录）按场景调用 DeepSeek 做结构化分析，结果在侧边栏「大模型分析」页；点开单条可**导出 CSV/JSON**。

### 场景

| 场景 id | 说明 |
|---------|------|
| sell_buy | 潜在买家/卖家：推广/留联系方式账号与询价、种草等意向用户 |
| hot_products | 潜在热销品：多帖提及、求链接、种草集中的商品/品类 |
| hot_topics | 热度话题：讨论集中、声量大的话题/关键词/事件 |

联系方式主体以「昵称（平台号）」完整展示（如 张三（抖音号））。

### 配置 `backend/.env`

| 变量 | 说明 | 默认 |
|------|------|------|
| DEEPSEEK_API_KEY | DeepSeek API Key | 空（未配置则接口 400） |
| DEEPSEEK_API_BASE | API 地址 | https://api.deepseek.com |
| DEEPSEEK_ENABLE_SEARCH | 联网搜索 | false |

后端用 **httpx** 请求 `{DEEPSEEK_API_BASE}/v1/chat/completions`，超时 90s，日志前缀 `[LLM分析]`、`[llm-leads]`。

---

## Playwright 与登录态

抖音/小红书爬虫基于 Playwright：**浏览器登录 → 保存登录态 → 带 Cookie 请求**，无需逆向签名。

### 安装

```bash
cd backend && playwright install chromium
```

### 模式与登录

| 模式 | 说明 |
|------|------|
| 标准 | Playwright 启动 Chromium，打开目标站登录，同一上下文请求 |
| CDP | `.env` 设 `MC_ENABLE_CDP_MODE=true`，Chrome `--remote-debugging-port=9222`，爬虫连接已有浏览器 |

**登录态目录**：默认 `backend/browser_data/{platform}_user_data_dir`，可设环境变量 `BROWSER_DATA_DIR` 改为项目外路径。  
**登录方式**：qrcode（默认）或 cookie（`MC_LOGIN_TYPE=cookie`、`MC_COOKIES=...`）。重新登录：`python scripts/clear_mc_login.py --platform dy|xhs|--all`。

### Playwright 配置

| 变量 | 说明 | 默认 |
|------|------|------|
| BROWSER_DATA_DIR | 浏览器数据根目录 | 空 |
| MC_HEADLESS | 无头模式 | false |
| MC_SAVE_LOGIN_STATE | 保存登录态 | true |
| MC_LOGIN_TYPE | qrcode / cookie | qrcode |
| MC_COOKIES | Cookie 字符串 | 空 |
| MC_ENABLE_CDP_MODE | CDP 连接已有浏览器 | false |
| CRAWLER_MAX_NOTES_COUNT | 单次最大条数 | 30 |

---

## 代理与防封

### 快代理 DPS

1. 登录 [快代理](https://www.kuaidaili.com/) → DPS 订单 → API 密钥 获取 SecretId、Signature。  
2. 鉴权二选一：**用户名+密码**（会员中心设置）或 **IP 白名单**。

在 `backend/.env` 中配置（勿提交）：

```bash
KDL_SECRET_ID=你的SecretId
KDL_SIGNATURE=你的Signature
KDL_USER_NAME=代理用户名
KDL_USER_PWD=代理密码
ENABLE_IP_PROXY=true
IP_PROXY_POOL_COUNT=2
```

小写变量名同样支持。额度为 0 时拉取失败会降级为无代理。

### 防封策略

| 项 | 说明 |
|------|------|
| 随机延迟 | `CRAWLER_MIN_SLEEP_SEC`～`CRAWLER_MAX_SLEEP_SEC`（默认 1～3 秒） |
| 并发 | `MAX_CONCURRENCY_NUM=1`，串行 |
| 单次数量 | `CRAWLER_MAX_NOTES_COUNT`、`CRAWLER_MAX_COMMENTS_COUNT` 限制 |
| 代理 | `ENABLE_IP_PROXY` 后按需取代理，403/429/502/503 时换 IP |
| UA/请求头 | `app/crawler/anti_block.py` 中 `USER_AGENTS`、`get_random_ua()` |
| 熔断 | 同一任务连续失败 3 次停止后续平台 |

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

本工具仅供**学习与研究**使用，请遵守各平台使用条款与 robots.txt，控制频率与数据量，不用于商业与非法用途。
