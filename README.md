# Arona

Arona 是一个前后端分离的 RAG 系统：

- **Backend**：FastAPI（默认 `http://localhost:8000`）
- **Frontend**：React + Vite（默认 `http://localhost:5173`）

本仓库已经整理为 **一条命令启动前后端**，并尽量减少需要手动设置的环境变量。

---

## 快速开始（开发模式）

### 1) 安装依赖

后端（推荐使用 `uv`）：

```bash
uv sync
```

或使用 pip（不推荐，但可用）：

```bash
pip install -r requirements-backend.txt
```

> 注：默认配置使用本地 Qwen3-VL Embedding/Reranker（见 `env.example`）。
> 对于 GTX 1080 Ti（Pascal），推荐使用 CUDA 11.8 的 PyTorch wheels；具体安装方式见 `requirements-backend.txt` 的注释。

前端：

```bash
cd frontend
npm install
cd ..
```

### 2) 配置

推荐：只维护一个根目录配置文件：

```bash
cp env.example .env
```

然后编辑 `.env`，填入你的 `LLM_*` / `EMBEDDING_*` 等关键配置。

> 兼容旧方案：后端仍支持 `.env.backend`（见 `env.backend.example`）。

> 说明：当前 `env.example` 的默认 embedding/reranker 预设为本地 Qwen3-VL（便于离线/本地部署）。
> 如果你希望使用 OpenAI/自建 OpenAI-compatible API，请把 `EMBEDDING_PROVIDER` / `RERANKER_PROVIDER` 改回 `openai/custom` 等并填写对应 API Key。

### 3) 一键启动

```bash
bash scripts/start_all.sh
```

默认是 **dev 模式**：
- 后端：`--reload`
- 前端：`vite dev`（热更新）
- 前端 API 请求默认走 Vite 代理：`/api -> backend`

打开：
- Frontend：`http://localhost:5173`
- Backend：`http://localhost:8000`
- API Docs：`http://localhost:8000/docs`

停止：`Ctrl-C`（会自动清理前后端进程，不再残留后台进程）。

> 小提示：如果你的环境里设置了 `http_proxy` / `https_proxy`（但没配置 `NO_PROXY=127.0.0.1,localhost`），
> 手动 `curl http://127.0.0.1:8000/...` 可能会错误地走代理导致 502。脚本内部的健康检查已强制绕过代理；
> 你手动调试时可以用 `curl --noproxy '*' ...` 或设置 `NO_PROXY`。

---

## Production-like 本地预览

```bash
bash scripts/start_all.sh prod
```

说明：
- 前端会先 `npm run build`，再 `vite preview`
- 跨域/不同域部署时请设置 `VITE_BACKEND_URL`

---

## 单独启动

只启动后端：

```bash
bash scripts/start_backend.sh
```

只启动前端：

```bash
bash scripts/start_frontend.sh
```

---

## 配置规则（重要）

- 后端会优先读取根目录 `.env`，如果不存在则读取 `.env.backend`。
- 前端只有 `VITE_` 前缀的环境变量会被注入到浏览器端；**不要用 `VITE_` 前缀保存任何密钥**。
- dev 模式下，前端默认使用 Vite proxy（见 `frontend/vite.config.ts`），因此通常不需要配置 `VITE_BACKEND_URL`。

---

## Chat API（多会话管理）

Arona 支持多会话持久化管理，会话与消息存储在 SQLite（`backend/data/chat.db`）。

### 端点概览

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/chat/sessions` | 创建新会话 |
| GET | `/api/chat/sessions` | 列出会话（支持分页 `?limit=20&cursor=...`、搜索 `?q=...`） |
| GET | `/api/chat/sessions/{id}` | 获取单个会话详情 |
| PATCH | `/api/chat/sessions/{id}` | 更新会话（重命名） |
| DELETE | `/api/chat/sessions/{id}` | 删除会话（`?hard=true` 硬删除） |
| GET | `/api/chat/sessions/{id}/messages` | 获取会话消息（支持分页） |
| POST | `/api/chat/sessions/{id}/turn` | 发送消息并获取 AI 回复（幂等，需 `request_id`） |

### Turn API 示例

```bash
# 创建会话
curl -X POST http://localhost:8000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Chat"}'

# 发送消息（需要 request_id 保证幂等）
curl -X POST http://localhost:8000/api/chat/sessions/{session_id}/turn \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "unique-uuid-here",
    "query": "What is RAG?",
    "mode": "hybrid"
  }'
```

> **迁移说明**：目前不提供从旧 localStorage 迁移到后端的脚本（future work）。

---

## 验收步骤（本地开发）

1. **启动服务**
   ```bash
   bash scripts/start_all.sh
   ```

2. **打开浏览器** `http://localhost:5173`

3. **验收清单**
   - [x] Sidebar 可见：New chat / Search / Chats 列表 / Documents / Settings
   - [x] 点击 "+" 新建会话 → URL 变为 `/chat/<id>`
   - [x] 发送消息 → 显示 AI 回复
   - [x] 新建第二个会话 → 切换回第一个 → 消息隔离正确
   - [x] 刷新页面 → 会话列表与消息仍存在
   - [x] 点击 Sidebar "Documents" → 进入 `/documents/library`
   - [x] Settings 可打开，health/config 显示正常

---

## 运行测试

```bash
# 后端测试
pytest -q

# 前端单元测试（非 watch 模式）
cd frontend && npm run test:run

# 前端 E2E 测试
cd frontend && npx playwright test
```
