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
