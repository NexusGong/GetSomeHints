# 前后端 API 契约

前端 `frontend/src/services/api.ts` 与后端 `backend/app/routers/` 对接说明。请求/响应均为 **JSON**，字段名为 **snake_case**。

## 基础

- **Base URL**：前端 `API_BASE_URL` 默认 `http://127.0.0.1:8000`
- **CORS**：后端已允许 `localhost:5173`、`localhost:3000`、`127.0.0.1:5173`、`127.0.0.1:3000`

---

## 搜索 API（/api/search）

| 方法 | 路径 | 前端方法 | 说明 |
|------|------|----------|------|
| POST | /api/search/start | searchApi.startSearch | 发起搜索 |
| GET | /api/search/status/{task_id} | searchApi.getSearchStatus | 任务状态 |
| GET | /api/search/results/{task_id} | searchApi.getSearchResults | 搜索结果（可选 ?platform=） |
| POST | /api/search/stop/{task_id} | searchApi.stopSearch | 停止任务 |
| GET | /api/search/comments/{platform}/{post_id} | searchApi.getPostComments | 帖子评论（可选 ?task_id=） |

### POST /api/search/start

**Request body：**
```json
{
  "keywords": "string",
  "platforms": ["xhs", "dy", ...],
  "max_count": 100,
  "enable_comments": true,
  "enable_sub_comments": false,
  "time_range": "all",
  "content_types": ["video", "image_text", "link"]
}
```

**Response：** SearchResponse
```json
{
  "task_id": "uuid",
  "status": "pending|running|completed|failed|stopped",
  "total_found": 0,
  "by_platform": { "xhs": 0, "dy": 0 },
  "progress": 0,
  "message": ""
}
```

### GET /api/search/status/{task_id}

**Response：** 同上 SearchResponse。

### GET /api/search/results/{task_id}

**Query：** `platform`（可选，筛选平台）

**Response：** UnifiedPost[]
- 字段：platform, post_id, title, content, author (UnifiedAuthor), publish_time, like_count, comment_count, share_count, collect_count?, url, image_urls, video_url?, platform_data

### GET /api/search/comments/{platform}/{post_id}

**Query：** `task_id`（可选，用于缓存）

**Response：** UnifiedComment[]
- 字段：comment_id, post_id, platform, content, author, comment_time, like_count, parent_comment_id?, sub_comment_count

---

## 分析 API（/api/analysis）

| 方法 | 路径 | 前端方法 | 说明 |
|------|------|----------|------|
| POST | /api/analysis/stats | analysisApi.getStats | 汇总统计 |
| POST | /api/analysis/distribution | analysisApi.getDistribution | 平台分布 |
| POST | /api/analysis/trends | analysisApi.getTrends | 时间趋势（当前为占位） |
| POST | /api/analysis/top-authors | analysisApi.getTopAuthors | 热门作者 |

以上 POST 均使用 **Query 参数**：`task_id`（必填），top-authors 另有 `limit`（默认 10）。

**getStats Response：** AnalysisStats
```json
{
  "total_posts": 0,
  "total_comments": 0,
  "total_authors": 0,
  "platform_stats": [{ "platform", "post_count", "comment_count", "author_count", "avg_likes", "avg_comments" }],
  "time_range": {}
}
```

**getDistribution Response：** `Record<string, number>`（平台 -> 数量）

**getTrends Response：** `Record<string, number>`（当前返回 {}）

**getTopAuthors Response：** `[{ "author": { "author_id", "author_name", "platform" }, "post_count" }]`

---

## 其他

- **GET /api/health**：`{ "status": "ok" }`
- **GET /api/config/proxy**：代理配置状态（不包含密钥）
- **WebSocket /api/ws/logs**：日志流（可选）
