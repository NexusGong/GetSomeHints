# Playwright 与登录态、代理池、数据保存

本项目的抖音/小红书爬虫基于 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) 的 Playwright 方案：**浏览器自动化登录 → 保存登录态 → 带 Cookie 请求接口**，无需逆向签名。以下说明如何接入 Playwright、登录态与代理池，以及数据如何保存。

## 1. Playwright 安装与使用

### 1.1 安装浏览器驱动

爬虫运行前需安装 Playwright 的 Chromium 驱动：

```bash
cd backend
# 若使用 conda/venv，先激活环境
playwright install chromium
# 或使用 uv
uv run playwright install chromium
```

未安装时，启动任务会报错或无法打开浏览器。

### 1.2 运行时的浏览器行为

- **标准模式**（默认）：由 Playwright 启动 Chromium，打开目标站（抖音/小红书），完成登录后在同一浏览器上下文中请求接口。
- **CDP 模式**：连接本机已打开的 Chrome（需带 `--remote-debugging-port=9222`），复用已有登录态。在 `backend/.env` 中设置 `MC_ENABLE_CDP_MODE=true` 并先手动打开 Chrome 后再运行爬虫即可。

浏览器相关配置（均在 `backend/.env` 或环境变量中）：

| 变量 | 说明 | 默认 |
|------|------|------|
| MC_HEADLESS | 是否无头模式 | false（有头，便于扫码登录） |
| MC_SAVE_LOGIN_STATE | 是否保存登录态到本地目录 | true |
| MC_ENABLE_CDP_MODE | 是否使用 CDP 连接已有浏览器 | false |
| MC_LOGIN_TYPE | 登录方式：qrcode / cookie | qrcode |
| MC_COOKIES | 使用 cookie 登录时的 cookie 字符串 | 空 |
| MC_CUSTOM_BROWSER_PATH | 自定义 Chrome/Edge 路径（CDP 时） | 空 |

## 2. 登录态

实现方式与 MediaCrawler 一致：**首次扫码/填 cookie 登录，之后复用同一浏览器数据目录，避免每次扫码**。

### 2.1 登录方式

- **qrcode**（默认）：启动后弹出浏览器，打开平台登录页，用户扫码或密码登录；登录成功后 Cookie 会写入「浏览器数据目录」。
- **cookie**：在 `.env` 中设置 `MC_LOGIN_TYPE=cookie` 和 `MC_COOKIES=...`，由 MC 将 cookie 注入浏览器上下文，不再弹扫码页。

### 2.2 登录态保存目录

当 `MC_SAVE_LOGIN_STATE=true` 时，MC 使用 **持久化浏览器上下文**（`launch_persistent_context`），数据目录为：

```
backend/mediacrawler_bundle/browser_data/{platform}_user_data_dir
```

例如抖音为 `browser_data/dy_user_data_dir`，小红书为 `browser_data/xhs_user_data_dir`。同一目录下次启动会复用，无需重复登录。注意：运行爬虫时当前工作目录会切到 `mediacrawler_bundle`，因此上述路径相对于 `backend/mediacrawler_bundle/`。

### 2.3 清除登录态（重新登录 / 排除登录问题）

若需要**重新扫码或重新过验证**，可先清除已保存的浏览器数据：

```bash
# 在项目根目录或 backend 目录执行
python backend/scripts/clear_mc_login.py --platform dy    # 仅抖音
python backend/scripts/clear_mc_login.py --platform xhs   # 仅小红书
python backend/scripts/clear_mc_login.py --all            # 全部
```

清除后，下次运行抖音/小红书爬虫会重新打开登录页，由 MediaCrawler 原版登录流程（扫码/验证码中间页等）处理。

### 2.4 与 MediaCrawler 的对应关系

- 登录逻辑：`media_platform/douyin/login.py`、`media_platform/xhs/login.py` 等，支持 qrcode/cookie。
- 浏览器启动与持久化：各平台 `core.py` 中的 `launch_browser()`，在 `SAVE_LOGIN_STATE=True` 时使用 `chromium.launch_persistent_context(user_data_dir=...)`。
- **媒体下载**：MC 配置 `ENABLE_GET_MEIDAS=False`（默认），即不下载笔记图片/视频，只抓取标题、作者、评论等元数据；若开启需在 bundle 的 `config/base_config.py` 中改为 `True`。

## 3. 代理池

代理池与 MediaCrawler 一致：通过 **快代理（或其它 MC 支持的 provider）拉取 IP**，供 Playwright 与 httpx 使用。

### 3.1 启用代理

在 `backend/.env` 中：

```bash
ENABLE_IP_PROXY=true
IP_PROXY_POOL_COUNT=2
```

爬虫启动时会从 app 配置读取上述两项并注入 MC 的 `config`（`ENABLE_IP_PROXY`、`IP_PROXY_POOL_COUNT`），MC 内部会调用 `proxy.proxy_ip_pool.create_ip_pool()`，再通过 `tools.crawler_util.format_proxy_info()` 转为 Playwright 与 httpx 所需的格式。

### 3.2 快代理配置

与 [docs/proxy_setup.md](proxy_setup.md) 一致，在 `.env` 中配置快代理 DPS 鉴权：

```bash
KDL_SECRET_ID=你的SecretId
KDL_SIGNATURE=你的Signature
KDL_USER_NAME=代理用户名
KDL_USER_PWD=代理密码
```

MC 的 `proxy/proxy_ip_pool.py` 会按 `IP_PROXY_PROVIDER`（默认 kuaidaili）选择 provider，拉取 IP 并注入到浏览器与请求中。额度为 0 时拉取失败会降级为无代理。

### 3.3 代理与登录态

- Playwright 启动浏览器时若传入 `playwright_proxy`，则浏览器流量走代理。
- 登录态保存在本地 `browser_data` 目录，与代理无关；换代理不换目录时，仍可复用同一登录态。

## 4. 数据保存

### 4.1 本项目（GetSomeHints）的数据流

- **不落盘、不写 MC 的 CSV/DB**：爬虫结果通过 MC 的 **store 内存适配** 收集在内存中（见 `mediacrawler_bundle/store/douyin`、`store/xhs` 等），任务结束后由 `app/crawler/douyin.py`、`xhs.py` 转为 `UnifiedPost` / `UnifiedComment` 通过 API 返回给前端。
- **持久化**：若需要，可在后端 API 层将返回结果写入数据库或文件，与 MC 的 store 解耦。

### 4.2 MediaCrawler 原生的数据保存

MediaCrawler 原生支持 CSV、JSON、Excel、SQLite、MySQL 等（见其 [数据存储指南](https://github.com/NanmiCoder/MediaCrawler)）。本项目中 MC 的 store 已被替换为「只写内存列表」的适配器，因此 **不会** 写入 MC 的 data 目录或数据库。若需沿用 MC 的存储方式，需要保留或恢复 MC 的 store 实现，并在配置中指定 `SAVE_DATA_OPTION` 等（当前为 `memory`，仅内存）。

## 5. 配置汇总（环境变量）

| 变量 | 说明 | 默认 |
|------|------|------|
| ENABLE_IP_PROXY | 是否启用代理池 | false |
| IP_PROXY_POOL_COUNT | 代理池预取数量 | 2 |
| MC_LOGIN_TYPE | 登录方式 qrcode/cookie | qrcode |
| MC_COOKIES | Cookie 登录时的字符串 | 空 |
| MC_HEADLESS | 无头模式 | false |
| MC_SAVE_LOGIN_STATE | 保存登录态到 browser_data | true |
| MC_ENABLE_CDP_MODE | 使用 CDP 连接已有浏览器 | false |
| CRAWLER_MAX_NOTES_COUNT | 单次搜索最大条数 | 30 |
| CRAWLER_MAX_COMMENTS_COUNT_SINGLENOTES | 单条内容最大评论数 | 20 |
| CRAWLER_MAX_SLEEP_SEC | 请求间隔（秒） | 2 |

以上与 [MediaCrawler 配置](https://github.com/NanmiCoder/MediaCrawler) 中的 `config/base_config.py` 行为一致，本项目中由 `mediacrawler_bundle/config/base_config.py` 从环境变量读取，并在运行爬虫前由 app 注入 `ENABLE_IP_PROXY`、`IP_PROXY_POOL_COUNT` 等。

## 6. 参考

- MediaCrawler 仓库：<https://github.com/NanmiCoder/MediaCrawler>
- 本项目代理配置：[docs/proxy_setup.md](proxy_setup.md)
- 防封与限频：[docs/anti_block.md](anti_block.md)
