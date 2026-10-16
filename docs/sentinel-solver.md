# Sentinel Solver (无头浏览器求解服务) 运维与启用指南

本文档记录 `sentinel-solver` 服务的架构背景、当前策略及后续重新启用方法。

---

## 一、 背景与架构说明

### 1. 作用
`sentinel-solver` 是一个基于无头 Chromium（Playwright/Puppeteer）的独立微服务（代码位于 [`sentinel_solver/`](../sentinel_solver/)）。
它的主要职能是：
- 渲染真实的浏览器环境，解决 OpenAI 网页端网关在遇到高风控 IP 时下发的 Cloudflare Turnstile 人机验证挑战（dx token）。
- 返回与真实浏览器一致的 User-Agent 和求解后的 Turnstile Token。

### 2. 为什么当前默认关闭（单容器模式）
- **Issue #416 说明**：2026 年 10 月 14 ~ 15 日出现的 `/backend-api/conversation` 报空 404 错误，后续已被证实为 OpenAI 官方自身网关更新灰度引发的临时故障，随后官方已自愈。
- **内置本地求解兜底**：本项目原生内置了轻量级 Python 求解模块 [`utils/turnstile.py`](../utils/turnstile.py)；在未配置 `CHATGPT2API_SENTINEL_SOLVER_URL` 时，系统会自动通过本地算法求解。
- **性能与资源优势**：
  - 纯 Python 求解耗时为毫秒级，而拉起 Chromium 会增加 **2 ~ 5 秒**的请求耗时。
  - 关闭后可为服务器节省约 **1GB 共享内存**（`shm_size: 1gb`）及浏览器 CPU 开销。

---

## 二、 后续如果需要改回来（重新启用指南）

如果未来 OpenAI 进一步升级风控策略，强制校验真实 Chromium 指纹导致本地求解失效时，可通过以下步骤一键恢复：

### 1. 修改 `docker-compose.yml`
取消注释 `docker-compose.yml` 中的环境变量和 `sentinel-solver` 容器：

```yaml
services:
  app:
    image: ghcr.io/fxxisme/chatgpt2api_copy:latest
    container_name: chatgpt2api
    restart: unless-stopped
    ports:
      - "3000:80"
    volumes:
      - ./data:/app/data
      - ./config.json:/app/config.json
    environment:
      - STORAGE_BACKEND=json
      # 启用 sentinel-solver 连接配置：
      - CHATGPT2API_SENTINEL_SOLVER_URL=http://sentinel-solver:8080
      - CHATGPT2API_SENTINEL_SOLVER_KEY=change-me
    depends_on:
      - sentinel-solver

  # 启用无头 Chromium 求解服务：
  sentinel-solver:
    image: ghcr.io/fxxisme/chatgpt2api_copy-sentinel-solver:latest
    # 或者本地构建：build: ./sentinel_solver
    container_name: chatgpt2api-sentinel-solver
    restart: unless-stopped
    shm_size: "1gb"
    environment:
      - SENTINEL_SOLVER_KEY=change-me
      # 代理设置：如果主服务使用了出口代理，求解服务也必须保持出口 IP 一致：
      # - SENTINEL_SOLVER_PROXY=http://host:7890
      # 页面时区：建议与代理出口所在地时区一致：
      # - SENTINEL_SOLVER_TIMEZONE=Asia/Shanghai
```

### 2. 重启生效
```bash
docker compose up -d
```

### 3. 验证连通性
主程序启动日志中若出现：
```json
{"event": "sentinel_solver_connected", "url": "http://sentinel-solver:8080"}
```
即表示无头求解服务接管成功。
