# 代理配置说明

## 快代理（KuaiDaili）私密代理

本项目支持通过快代理 DPS（私密代理）接口获取 IP，用于爬虫请求的代理轮换。

**已配置**：`backend/.env` 中已写入快代理订单鉴权（用户名密码 + 订单 API 密钥明文验证），并默认开启 `ENABLE_IP_PROXY=true`。若额度为 0，代理池拉取失败时会自动降级为无代理继续爬取。

### 1. 获取 API 密钥

1. 登录 [快代理](https://www.kuaidaili.com/)
2. 进入已购买的 DPS 订单页 → **API 密钥 / API-secret** 标签
3. 获取：
   - **SecretId**
   - **Signature**（若使用 token 鉴权，需先调用「获取密钥令牌」接口得到当次 signature）

### 2. 鉴权方式

私密代理需鉴权，二选一：

- **用户名 + 密码**：在会员中心为订单设置代理用户名、密码；请求时使用 `http://user:pass@ip:port`
- **IP 白名单**：绑定本机公网 IP（仅适合固定出口 IP 环境）

### 3. 环境变量配置

在项目根目录或 `backend/` 下创建 `.env`（勿提交到 Git），例如：

```bash
# 快代理 DPS
KDL_SECRET_ID=你的SecretId
KDL_SIGNATURE=你的Signature或密钥令牌
KDL_USER_NAME=代理用户名
KDL_USER_PWD=代理密码

# 启用代理
ENABLE_IP_PROXY=true
IP_PROXY_POOL_COUNT=2
```

也可使用小写：`kdl_secret_id`、`kdl_signature`、`kdl_user_name`、`kdl_user_pwd`。

### 4. 代理池行为

- 首次请求或池空时调用快代理 `getdps` 接口拉取 IP
- 每个 IP 在过期前约 5 秒即视为失效，避免请求中途断开
- 可选：请求前对 IP 做可用性校验（`proxy_ip_pool` 中 `enable_validate_ip`）
- 遇到 403/502/503 时调用 `invalidate_current()`，下次请求自动换新 IP

### 5. 隧道代理（可选）

若使用快代理隧道代理（固定域名 + 端口），无需调用 getdps，可在配置中直接填写隧道 URL，并在爬虫中固定使用该代理。当前实现以私密代理 + 代理池为主。

### 6. 限频与注意

- getdps 接口最快 1 秒 10 次
- 同一订单 1 分钟内可调用的 IP 数有限制，池子按需分批取，不要一次取过多
