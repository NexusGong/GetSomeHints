# 爬虫防封策略说明

本文档说明本项目中已实现的防封与安全策略，以及推荐配置。

## 1. 请求频率

- **随机延迟**：每次请求前调用 `random_sleep()`，在 `CRAWLER_MIN_SLEEP_SEC`～`CRAWLER_MAX_SLEEP_SEC` 之间随机等待（默认 1～3 秒），避免固定周期被识别。
- **并发控制**：`MAX_CONCURRENCY_NUM` 默认 1，即串行执行各平台，降低单机 QPS。
- **单次数量**：`CRAWLER_MAX_NOTES_COUNT`、`CRAWLER_MAX_COMMENTS_COUNT` 限制单次拉取条数，避免单任务过大。

配置示例（环境变量）：

```bash
CRAWLER_MIN_SLEEP_SEC=1.0
CRAWLER_MAX_SLEEP_SEC=3.0
MAX_CONCURRENCY_NUM=1
CRAWLER_MAX_NOTES_COUNT=30
```

## 2. 代理使用

- **代理池**：启用 `ENABLE_IP_PROXY` 后，每次请求前通过 `get_or_refresh_proxy(buffer_seconds)` 取代理，过期前约 30 秒自动更换。
- **按失败换 IP**：收到 403/429/502/503 时调用 `invalidate_current()`，下次请求使用新 IP；可选重试。
- **单 IP 使用次数**：可在逻辑中扩展「每 N 次请求换 IP」，当前以过期时间为主。

## 3. 请求头与 UA

- **UA 池**：`app/crawler/anti_block.py` 中维护 `USER_AGENTS` 列表，`get_random_ua()` 随机选取。在具体 HTTP 客户端（如 httpx、Playwright）中设置请求头即可。
- **Referer / Accept-Language**：建议与目标平台一致，可在各平台 Crawler 中按需设置。

## 4. 熔断与退避

- **连续失败**：在 `crawler_runner` 中，同一任务内连续失败 `max_failures_before_skip`（默认 3）次后，停止后续平台，避免持续失败。
- **单次失败**：某平台单次异常时，会调用 `proxy_pool.invalidate_current()` 换 IP，并继续下一平台。

## 5. 登录态与并发

- 需要登录的平台：建议使用 Playwright/CDP 保存登录态，同一会话内带 Cookie 请求。
- 多平台：当前为串行执行，避免同一机器多账号同时高频。

## 6. 配置项汇总

| 变量 | 说明 | 默认 |
|------|------|------|
| ENABLE_IP_PROXY | 是否启用代理池 | false |
| IP_PROXY_POOL_COUNT | 代理池预取数量 | 2 |
| CRAWLER_MIN_SLEEP_SEC | 最小请求间隔（秒） | 1.0 |
| CRAWLER_MAX_SLEEP_SEC | 最大请求间隔（秒） | 3.0 |
| MAX_REQUESTS_PER_IP | 单 IP 最大请求次数（预留） | 50 |
| MAX_CONCURRENCY_NUM | 并发数（1=串行） | 1 |
| PROXY_BUFFER_SECONDS | 代理提前过期缓冲（秒） | 30 |
