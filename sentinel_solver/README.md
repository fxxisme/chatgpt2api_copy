# sentinel 求解服务

从 2026-10-14 起，chatgpt.com 的对话接口（文字和生图）开始严格校验 sentinel：

- `chat-requirements` 必须带上在**真实 chatgpt.com 页面**里算出的 Turnstile token。纯 Python 或 Node 模拟算出的结果会被拒，缺失时返回 403 "Unusual activity"。
- 请求的 TLS 指纹必须是新版 Chrome（主服务默认已改为 curl_cffi `chrome146`）。
- requirements/proof token 里编码的 UA 必须和算 Turnstile 的页面一致。

只要校验质量不够，对话接口不会直接返回 403，而是返回伪装成 404 的 `{"detail":"Model not found"}`。

本服务常驻一个无头 Chromium（带 playwright-stealth），一直开着 chatgpt.com 页面，替主服务计算 Turnstile。主服务不需要打包浏览器。

## 接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/health` | 页面状态及页面使用的 UA（主服务据此生成 requirements/proof token） |
| POST | `/v1/turnstile` | `{"dx", "p"}` → `{"token"}`，dx 取自 prepare 响应，p 是 prepare 请求提交的 requirements token |
| POST | `/v1/so` | `{"collector_dx", "snapshot_dx", "p"}` → `{"token"}`，目前对话接口还不强制要求 |

设置了 `SENTINEL_SOLVER_KEY` 时，请求需要带 `Authorization: Bearer <key>` 头。

## 部署

```bash
docker compose up -d --build sentinel-solver
```

主服务通过环境变量（或 `config.json` 里的 `sentinel_solver_url` / `sentinel_solver_key`）指向本服务：

```
CHATGPT2API_SENTINEL_SOLVER_URL=http://sentinel-solver:8080
CHATGPT2API_SENTINEL_SOLVER_KEY=<与 SENTINEL_SOLVER_KEY 相同>
```

未配置或调用失败时，主服务会退回本地 Turnstile 求解器。本地求解器已跟不上新版挑战程序，对话接口大概率会失败。

环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `SENTINEL_SOLVER_KEY` | 空 | 访问密钥 |
| `SENTINEL_SOLVER_PROXY` | 空 | 浏览器出网代理，应与主服务访问 chatgpt.com 的出口一致 |
| `SENTINEL_SOLVER_USER_AGENT` | 按内置 Chromium 版本生成 | 页面 UA |
| `SENTINEL_SOLVER_TIMEZONE` | 跟随系统 | 页面时区（如 `Asia/Tokyo`），建议与出口 IP 所在地一致 |
| `SENTINEL_SOLVER_REFRESH_SECONDS` | 1800 | 页面定期重开的间隔 |
| `SENTINEL_SOLVER_HEADLESS` | true | 调试时可设为 false |
| `PORT` | 8080 | 监听端口 |

## 注意

- 必须使用完整 Chromium 的新版无头模式（`channel="chromium"`），并加上 stealth；否则页面会停在 Cloudflare「请稍候…」，算出的 token 无效。
- 挑战程序（`vm.js`）移植自 chatgpt.com 前端，OpenAI 更新指令集后需要同步更新。
- 本服务只解决请求质量问题。由脚本批量注册的账号，即使在真实网页里也会提示 "Model not found"，属于账号层面的限制。
