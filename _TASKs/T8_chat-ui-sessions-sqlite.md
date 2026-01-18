<Task>
  <Header>
    <Title>TASK: ChatGPT 风格聊天 UI 重构 + 后端 SQLite 会话存储（Route B 一步到位）</Title>
    <Overview>
      <Purpose>
        <Label>Purpose:</Label>
        <Text>将当前单会话 /chat 改造为 ChatGPT 风格：左侧 Sidebar（会话列表/搜索/知识库入口/用户设置），右侧主面板（多轮对话）。后端新增 SQLite 持久化会话与消息，实现多 session 分离、可查询、可删除、可重命名，并提供对话 turn API。</Text>
      </Purpose>
      <Usage>
        <Label>How to use:</Label>
        <Text>按 Phase 顺序执行：P0 需求与契约 → P1 数据层（SQLite）→ P2 Chat API（CRUD+turn）→ P3 AppShell + Sidebar → P4 前端接入后端会话 → P5 Documents 风格统一 → P6 测试/迁移/收尾。每个 Phase 都提供明确的 edits/commands/tests/exit criteria。</Text>
      </Usage>
    </Overview>
  </Header>

  <Section id="meta">
    <Heading>0) META</Heading>
    <Meta>
      <TaskId>T8</TaskId>
      <Title>ChatGPT 风格聊天 UI 重构 + 后端 SQLite 会话存储（Route B）</Title>
      <RepoRoot>./</RepoRoot>
      <Branch>feature/T8-chat-ui-sessions-sqlite</Branch>
      <Status>in-progress</Status>
      <Goal>实现多会话（session/thread）聊天：前端支持会话列表/切换/搜索/新建/删除/重命名，后端使用 SQLite 持久化会话与消息；/documents 与 /chat UI 风格统一且侧边栏提供快捷入口；设置入口位于左下角用户区域。</Goal>
      <NonGoals>
        <Item>不做用户登录/权限系统（默认单用户）。</Item>
        <Item>不在首版实现真正 token-level streaming（可在后续 Phase 作为增强）。</Item>
        <Item>不实现复杂的团队协作/共享会话。</Item>
        <Item>不做全文检索的高级索引（可选用 SQLite FTS5 作为后续增强）。</Item>
      </NonGoals>
      <Dependencies>
        <Item>前端：React + Vite + React Router + Zustand + React Query（现有）。</Item>
        <Item>后端：FastAPI + asyncio（现有），SQLite（标准库 sqlite3）。</Item>
        <Item>测试：pytest（后端已有），Playwright/Vitest（前端已有）。</Item>
      </Dependencies>
      <Constraints>
        <Item>API 兼容：保留现有 `/api/query/*`（尤其 `/api/query/conversation`）以避免破坏旧客户端；新 UI 走 `/api/chat/*`。</Item>
        <Item>数据一致性：对话写入需要原子性（同一 turn user+assistant 两条消息要么都写入，要么都不写）。</Item>
        <Item>性能/稳定：避免 SQLite “database is locked”，启用 WAL、设置 busy_timeout、每次操作独立连接。</Item>
        <Item>可扩展：为未来多用户预留 user_id 字段/过滤逻辑（本任务不实现鉴权）。</Item>
      </Constraints>
      <AcceptanceCriteria>
        <Criterion>AC1: 左侧 Sidebar 包含：New chat、Search chats、Library（知识库/文档管理入口）、Chats（会话列表），底部用户区包含 Settings 与 Theme 切换。</Criterion>
        <Criterion>AC2: `/chat/:sessionId` 可打开指定会话；切换会话后消息完全隔离；刷新页面不会丢会话（从后端重新拉取）。</Criterion>
        <Criterion>AC3: 后端新增 SQLite（默认 `backend/data/chat.db`）存储 `chat_sessions` 与 `chat_messages`，并提供会话 CRUD 与 turn API。</Criterion>
        <Criterion>AC4: 发送一条消息会在该 session 下产生一条 user message 和一条 assistant message，并且在后端可回放（GET session messages）。</Criterion>
        <Criterion>AC5: `/documents/*` 页面在同一 AppShell 内渲染（风格统一），且 Sidebar 有快捷入口可直达 Library；原有功能（上传、索引、图谱、文档列表）不被破坏。</Criterion>
        <Criterion>AC6: 提供可执行的验收步骤（启动命令 + 手动点测清单）；关键 API 提供 pytest 覆盖；前端提供至少 1 条 Playwright 流程用例。</Criterion>
      </AcceptanceCriteria>
      <TestStrategy>
        - Backend: pytest 单元测试（ChatStore CRUD、turn 写入原子性），FastAPI TestClient 集成测试（router）。
        - Frontend: Vitest（store/actions），Playwright e2e（新建会话→发送消息→切换会话→验证隔离）。
      </TestStrategy>
      <Rollback>
        - 后端：移除 `backend/routers/chat.py`、`backend/services/chat_store.py`、`backend/models/chat.py`，并从 `backend/main.py` 移除 `/api/chat` router；删除 `backend/data/chat.db`。
        - 前端：回滚 Layout（恢复现有 `Header + ModeSwitch`），恢复 `/chat` 单页面实现与本地 store。
      </Rollback>
      <Owner>@codex</Owner>
    </Meta>
  </Section>

  <Section id="context">
    <Heading>1) CONTEXT（现状 vs 目标）</Heading>
    <List type="bullet">
      <Item>
        <Label>现状（前端 /chat）：</Label>
        <Text>单会话，消息存于 `frontend/src/store/chatStore.ts`（localStorage persist），发送时把 messages 作为 history POST 到 `/api/query/conversation`；无 sessionId、无会话列表。</Text>
      </Item>
      <Item>
        <Label>现状（后端）：</Label>
        <Text>`/api/query/conversation` 完全无 session 存储，history 由客户端传入；无 chats CRUD。</Text>
      </Item>
      <Item>
        <Label>目标（截图风格）：</Label>
        <Text>AppShell：左侧 Sidebar（会话列表/搜索/知识库/用户设置），右侧主面板；聊天支持多 session/thread 隔离；会话与消息后端持久化（SQLite）。</Text>
      </Item>
      <Item>
        <Label>关键触点（需要改动的核心文件）：</Label>
        <Text>前端：`frontend/src/App.tsx`、`frontend/src/components/layout/*`、`frontend/src/views/ChatView.tsx`、`frontend/src/store/chatStore.ts`、新增 `frontend/src/api/chat.ts`。后端：新增 `backend/routers/chat.py`、新增 `backend/services/chat_store.py`、新增 `backend/models/chat.py`、修改 `backend/main.py`、可选修改 `backend/config.py`。</Text>
      </Item>
      <Item>
        <Label>风险提示：</Label>
        <Text>SQLite 并发写锁；长对话/大量会话导致列表与消息加载变慢（需要分页/limit）；turn API 重试导致重复消息（需要幂等性）；前后端类型不一致（需统一契约）；multimodal base64 入库导致 DB 膨胀（应落盘存路径）。</Text>
      </Item>
    </List>
  </Section>

  <Section id="architecture">
    <Heading>2) ARCHITECTURE（数据模型 & API 契约）</Heading>

    <Subsection id="2.1">
      <Title>2.1 数据库（SQLite）</Title>
      <List type="bullet">
        <Item>
          <Label>DB 文件：</Label>
          <Text>默认 `backend/data/chat.db`（可通过 env `CHAT_DB_PATH` 覆盖）。</Text>
        </Item>
        <Item>
          <Label>表 1：chat_sessions</Label>
          <Text>字段建议：`id TEXT PRIMARY KEY`, `title TEXT NOT NULL`, `created_at TEXT`, `updated_at TEXT`, `deleted_at TEXT NULL`（建议从一开始就支持软删除），`user_id TEXT NULL`（预留），`metadata_json TEXT NULL`。</Text>
        </Item>
        <Item>
          <Label>表 2：chat_messages</Label>
          <Text>字段建议：`id TEXT PRIMARY KEY`, `session_id TEXT`, `role TEXT CHECK(user|assistant|system)`, `content TEXT`, `created_at TEXT`, `token_count INTEGER NULL`（用于 history 截断），`metadata_json TEXT NULL`（存 mode / attachments / error / idempotency 等），`user_id TEXT NULL`（预留）。索引：`(session_id, created_at)`。</Text>
        </Item>
        <Item>
          <Label>表 3（推荐）：chat_turns（幂等性/去重）</Label>
          <Text>字段建议：`id TEXT PRIMARY KEY`（request_id / idempotency key），`session_id TEXT`, `user_message_id TEXT`, `assistant_message_id TEXT`, `status TEXT`, `created_at TEXT`。唯一性建议：`UNIQUE(session_id, id)` 或直接全局唯一 id。</Text>
        </Item>
        <Item>
          <Label>索引建议：</Label>
          <Text>`sessions(user_id, updated_at DESC)`（未来多用户）、`sessions(updated_at DESC)`（列表排序）、`messages(session_id, created_at)`（回放/分页）。软删除过滤时可以用 partial index：`WHERE deleted_at IS NULL`。</Text>
        </Item>
        <Item>
          <Label>并发配置：</Label>
          <Text>PRAGMA：`journal_mode=WAL`，`synchronous=NORMAL`，`foreign_keys=ON`；连接级 busy_timeout（例如 30000ms）。每次操作短连接，避免跨线程复用同一 connection。注意：不要在持锁事务内等待 `rag_service.query()`（LLM 可能耗时很久），否则极易导致 locked；采用“补偿写入”模式（先写 user → LLM → 写 assistant，失败则标记/回滚）。</Text>
        </Item>
        <Item>
          <Label>Multimodal 持久化策略：</Label>
          <Text>允许 turn API 接收 `img_base64`，但必须先落盘到 `uploads/query_images/*` 并仅在 DB 的 `metadata_json` 中存 `img_path`；禁止把 base64 直接写入 SQLite。</Text>
        </Item>
      </List>
    </Subsection>

    <Subsection id="2.2">
      <Title>2.2 新增 API（/api/chat）</Title>
      <List type="bullet">
        <Item>
          <Label>Sessions CRUD：</Label>
          <Text>
            - `POST /api/chat/sessions` → create（返回 `id`）
            - `GET /api/chat/sessions?limit=&cursor=&q=` → list（按 updated_at desc，支持分页与搜索；cursor 为上一页返回的 next_cursor，Base64(JSON): {updated_at,id}）
            - `GET /api/chat/sessions/{session_id}` → get session meta
            - `GET /api/chat/sessions/{session_id}/messages?limit=&cursor=` → list messages（支持分页；cursor 为上一页返回的 next_cursor，Base64(JSON): {created_at,id}）
            - `PATCH /api/chat/sessions/{session_id}` → rename/title update
            - `DELETE /api/chat/sessions/{session_id}` → delete（MVP 可软删除：写 deleted_at；可选提供 `?hard=true` 做物理删除）
          </Text>
        </Item>
        <Item>
          <Label>对话 Turn：</Label>
          <Text>
            - `POST /api/chat/sessions/{session_id}/turn`
              入参：`request_id`（幂等用，前端每次发送生成 uuid），`query`, `mode`, `multimodal_content?`, `max_tokens?`, `temperature?`, `history_limit?`, `max_history_tokens?`
              服务端：
              1) 幂等检查：若 `request_id` 已存在且 status=completed 且 payload_hash 一致，则直接返回已生成的 messages；若 payload_hash 不一致或 status=pending，则返回 409
              2) 写入 user message（短事务，不持锁等待 LLM）
              3) 从 DB 取最近消息（按 limit/token budget 截断）组装 history → 调用现有 `rag_service.query(...)`
              4) 写入 assistant message + 更新 session.updated_at/title
              5) 失败补偿：将该 turn 标记 failed，或将 user message 标记 failed（metadata），避免“半写入”不可解释
          </Text>
        </Item>
        <Item>
          <Label>兼容策略：</Label>
          <Text>保留 `/api/query/conversation` 不动；新前端统一走 `/api/chat/.../turn`。后续可在 `/api/query/conversation` 内部复用同一组装逻辑（非必须）。</Text>
        </Item>
        <Item>
          <Label>错误码约定（建议在 P0 冻结）：</Label>
          <Text>
            - 400：空 query、request_id 缺失、mode 非法、payload 超限、multimodal 参数非法
            - 404：session 不存在/已删除
            - 409：幂等冲突（同 request_id 但 payload 不一致）或 title 重名冲突（若启用）
            - 422：Pydantic 校验失败（自动）
            - 500：rag_service/存储内部错误（需要结构化 detail）
          </Text>
        </Item>
      </List>
    </Subsection>

    <Subsection id="2.3">
      <Title>2.3 前端路由与状态（目标形态）</Title>
      <List type="bullet">
        <Item>
          <Label>路由：</Label>
          <Text>`/chat`（空态/自动创建新会话）与 `/chat/:sessionId`（指定会话）；`/documents/library|upload|graph` 作为 AppShell 子页面；（可选）`/settings` 或继续沿用 SettingsModal。</Text>
        </Item>
        <Item>
          <Label>会话来源：</Label>
          <Text>Route B：会话与消息来自后端；前端仅缓存（React Query cache + 少量 UI state），不再把全部消息 persist 到 localStorage。</Text>
        </Item>
        <Item>
          <Label>UI 结构：</Label>
          <Text>新增 AppShell Layout：左侧 Sidebar（会话列表/搜索/导航/用户设置），右侧 Outlet 渲染当前页面。</Text>
        </Item>
      </List>
    </Subsection>
  </Section>

  <Section id="high_level_plan">
    <Heading>3) HIGH-LEVEL PLAN（Phases 概览）</Heading>
    <Phases>
      <Phase>
        <Id>P0</Id>
        <Name>契约与验收</Name>
        <Summary>冻结 API/DB schema/UX 行为与验收清单，避免中途返工。</Summary>
      </Phase>
      <Phase>
        <Id>P1</Id>
        <Name>SQLite 数据层</Name>
        <Summary>实现 ChatStore（CRUD + 事务 + 并发配置）与数据模型。</Summary>
      </Phase>
      <Phase>
        <Id>P2</Id>
        <Name>Chat API Router</Name>
        <Summary>实现 `/api/chat/*`（sessions/messages/turn）并加 pytest 集成测试。</Summary>
      </Phase>
      <Phase>
        <Id>P3</Id>
        <Name>前端 AppShell + Sidebar</Name>
        <Summary>替换现有 Header/ModeSwitch 为 Sidebar Layout，挂载 documents/chat 导航与设置入口。</Summary>
      </Phase>
      <Phase>
        <Id>P4</Id>
        <Name>前端接入后端会话</Name>
        <Summary>实现会话列表/新建/删除/重命名/切换；ChatView 改为 session-aware，并调用 `/api/chat/.../turn`。</Summary>
      </Phase>
      <Phase>
        <Id>P5</Id>
        <Name>Documents 风格统一</Name>
        <Summary>移除 documents 独立“页面壳”，统一到 AppShell；Sidebar 增加 Library 快捷入口。</Summary>
      </Phase>
      <Phase>
        <Id>P6</Id>
        <Name>测试与收尾</Name>
        <Summary>补齐 Playwright e2e、类型对齐、文档与迁移策略、回归检查。</Summary>
      </Phase>
      <Phase>
        <Id>P7 (Optional)</Id>
        <Name>搜索与流式增强</Name>
        <Summary>SQLite FTS5 搜索 chats；SSE 流式输出（若 provider 支持）。</Summary>
      </Phase>
    </Phases>
  </Section>

  <Section id="phases">
    <Heading>4) PHASES（可执行计划）</Heading>

    <PhaseBlock>
      <PhaseHeading>Phase P0 — 契约与验收（冻结范围）</PhaseHeading>
      <FreezeStatus>
        <Completed>2026-01-11</Completed>
        <FrozenScope>
          API endpoints (request/response shape)、SQLite DDL、分页约定、幂等性策略、错误响应 schema、默认值配置。
          后续 P1-P6 实现必须严格遵循本契约；如需变更须先更新本节并记录 Breaking Change。
        </FrozenScope>
      </FreezeStatus>
      <Plan>
        <Intent>明确并冻结：DB schema、API request/response、前端路由与关键交互，输出验收脚本与边界条件。</Intent>

        <!-- ═══════════════════════════════════════════════════════════════════
             P0.1  默认值与配置（Frozen Defaults）
        ═══════════════════════════════════════════════════════════════════ -->
        <FrozenDefaults>
          <Default key="HISTORY_LIMIT" value="20">turn API 默认取最近 N 条 messages 组装 history</Default>
          <Default key="MAX_HISTORY_TOKENS" value="8000">动态截断 history 的 token 上限（含 system prompt）</Default>
          <Default key="SESSIONS_DEFAULT_LIMIT" value="20">GET /sessions 默认每页条数</Default>
          <Default key="MESSAGES_DEFAULT_LIMIT" value="50">GET /messages 默认每页条数</Default>
          <Default key="BUSY_TIMEOUT_MS" value="30000">SQLite 连接 busy_timeout（毫秒）</Default>
          <Default key="SESSION_TITLE_MAX_LEN" value="100">自动生成 title 的最大字符数（截断）</Default>
          <Default key="CHAT_DB_PATH" value="backend/data/chat.db">默认数据库路径（可通过 env 覆盖）</Default>
        </FrozenDefaults>

        <!-- ═══════════════════════════════════════════════════════════════════
             P0.2  SQLite Schema DDL（Frozen）
        ═══════════════════════════════════════════════════════════════════ -->
        <SQLiteSchema>
          <Description>
            所有 id 采用 UUID (TEXT)；时间戳采用 ISO8601 字符串（UTC）；metadata 以 JSON 字符串存储。
          </Description>
          <DDL><![CDATA[
-- ===== PRAGMA（每次连接时执行） =====
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 30000;

-- ===== TABLE: chat_sessions =====
CREATE TABLE IF NOT EXISTS chat_sessions (
    id              TEXT PRIMARY KEY,                           -- UUID
    title           TEXT NOT NULL DEFAULT 'New Chat',           -- 会话标题
    user_id         TEXT NULL,                                  -- 预留多用户
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at      TEXT NULL,                                  -- 软删除时间戳
    metadata_json   TEXT NULL                                   -- 扩展字段 JSON
);

-- 索引：列表按 updated_at DESC 分页
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON chat_sessions(updated_at DESC);
-- 索引：软删除过滤（partial index）
CREATE INDEX IF NOT EXISTS idx_sessions_active ON chat_sessions(updated_at DESC) WHERE deleted_at IS NULL;
-- 索引：预留多用户查询
CREATE INDEX IF NOT EXISTS idx_sessions_user ON chat_sessions(user_id, updated_at DESC) WHERE user_id IS NOT NULL;

-- ===== TABLE: chat_messages =====
CREATE TABLE IF NOT EXISTS chat_messages (
    id              TEXT PRIMARY KEY,                           -- UUID
    session_id      TEXT NOT NULL,                              -- FK → chat_sessions.id
    role            TEXT NOT NULL CHECK(role IN ('user', 'assistant', 'system')),
    content         TEXT NOT NULL,                              -- 消息正文
    token_count     INTEGER NULL,                               -- 用于 history 截断
    user_id         TEXT NULL,                                  -- 预留多用户
    created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    metadata_json   TEXT NULL,                                  -- mode, img_path, error, etc.
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
);

-- 索引：按 session 分页回放
CREATE INDEX IF NOT EXISTS idx_messages_session_created ON chat_messages(session_id, created_at DESC);

-- ===== TABLE: chat_turns（幂等性去重） =====
CREATE TABLE IF NOT EXISTS chat_turns (
    id                      TEXT PRIMARY KEY,                   -- request_id（由前端生成 UUID）
    session_id              TEXT NOT NULL,
    payload_hash            TEXT NOT NULL,                      -- SHA256(canonical JSON of turn request body)
    user_message_id         TEXT NULL,                          -- FK → chat_messages.id
    assistant_message_id    TEXT NULL,                          -- FK → chat_messages.id
    status                  TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'failed')),
    error_detail            TEXT NULL,                          -- 失败时的错误描述
    created_at              TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    completed_at            TEXT NULL,
    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_message_id) REFERENCES chat_messages(id) ON DELETE SET NULL,
    FOREIGN KEY (assistant_message_id) REFERENCES chat_messages(id) ON DELETE SET NULL
);

-- 索引：按 session 查询 turn 历史
CREATE INDEX IF NOT EXISTS idx_turns_session ON chat_turns(session_id, created_at DESC);
          ]]></DDL>
        </SQLiteSchema>

        <!-- ═══════════════════════════════════════════════════════════════════
             P0.3  分页 Cursor 约定（Frozen）
        ═══════════════════════════════════════════════════════════════════ -->
        <PaginationContract>
          <Description>
            采用 (timestamp, id) 组合游标，避免同一时间戳多条记录时的漏数据问题。
            游标编码为 Base64(JSON)，客户端视为不透明字符串。
          </Description>

          <SessionsPagination>
            <SortOrder>updated_at DESC, id DESC</SortOrder>
            <QueryParams>
              <Param name="limit" type="int" optional="true" default="20">每页条数，max=100</Param>
              <Param name="cursor" type="string" optional="true">上一页返回的 next_cursor</Param>
              <Param name="q" type="string" optional="true">模糊搜索 title（LIKE %q%）</Param>
            </QueryParams>
            <CursorPayload>{"updated_at": "ISO8601", "id": "UUID"}</CursorPayload>
            <ResponseShape>
              {
                "sessions": [...],
                "next_cursor": "base64..." | null,
                "has_more": boolean
              }
            </ResponseShape>
          </SessionsPagination>

          <MessagesPagination>
            <SortOrder>created_at DESC, id DESC（返回时需 reverse 为 ASC 顺序展示）</SortOrder>
            <QueryParams>
              <Param name="limit" type="int" optional="true" default="50">每页条数，max=200</Param>
              <Param name="cursor" type="string" optional="true">上一页返回的 next_cursor（向历史翻页）</Param>
            </QueryParams>
            <CursorPayload>{"created_at": "ISO8601", "id": "UUID"}</CursorPayload>
            <ResponseShape>
              {
                "messages": [...],          // 按 created_at ASC 排序（便于前端直接渲染）
                "next_cursor": "base64..." | null,
                "has_more": boolean
              }
            </ResponseShape>
          </MessagesPagination>
        </PaginationContract>

        <!-- ═══════════════════════════════════════════════════════════════════
             P0.4  幂等性约定（Frozen）
        ═══════════════════════════════════════════════════════════════════ -->
        <IdempotencyContract>
          <RequestIdLocation>Request body field: "request_id" (required, UUID string)</RequestIdLocation>
          <PayloadHashAlgorithm>SHA256 of canonical JSON: sorted keys, no whitespace, UTF-8 encoded</PayloadHashAlgorithm>
          <Behavior>
            <Case condition="request_id not found in chat_turns">正常执行 turn，写入 chat_turns</Case>
            <Case condition="request_id found AND payload_hash matches AND status=completed">
              返回 200 + 已有的 user/assistant messages（幂等重放）
            </Case>
            <Case condition="request_id found AND payload_hash differs">
              返回 409 Conflict（payload 不一致冲突）
            </Case>
            <Case condition="request_id found AND status=pending">
              返回 409 Conflict（turn 正在进行中）
            </Case>
            <Case condition="request_id found AND status=failed">
              返回 200 + turn 失败信息，允许前端选择生成新 request_id 重试
            </Case>
          </Behavior>
          <ConflictResponse409>
            {
              "detail": {
                "code": "IDEMPOTENCY_CONFLICT",
                "message": "request_id已存在但payload不一致或turn正在进行中",
                "existing_status": "pending" | "completed",
                "expected_hash": "sha256...",
                "received_hash": "sha256..."
              }
            }
          </ConflictResponse409>
        </IdempotencyContract>

        <!-- ═══════════════════════════════════════════════════════════════════
             P0.5  错误响应 Schema（Frozen）
        ═══════════════════════════════════════════════════════════════════ -->
        <ErrorResponseSchema>
          <UnifiedShape>
            {
              "detail": {
                "code": "ERROR_CODE",         // 机器可读错误码
                "message": "Human readable",  // 用户可读描述
                "extra": { ... }              // 可选：附加上下文
              }
            }
          </UnifiedShape>

          <ErrorCodes>
            <Code status="400" code="BAD_REQUEST">通用请求格式错误</Code>
            <Code status="400" code="EMPTY_QUERY">query 字段为空或仅空白</Code>
            <Code status="400" code="MISSING_REQUEST_ID">turn 请求缺少 request_id</Code>
            <Code status="400" code="INVALID_MODE">mode 值不在允许列表</Code>
            <Code status="400" code="INVALID_CURSOR">cursor 解码失败或格式非法</Code>
            <Code status="400" code="MULTIMODAL_INVALID">multimodal 参数格式错误或 base64 非法</Code>
            <Code status="404" code="SESSION_NOT_FOUND">session_id 不存在或已删除</Code>
            <Code status="404" code="MESSAGE_NOT_FOUND">message_id 不存在</Code>
            <Code status="409" code="IDEMPOTENCY_CONFLICT">幂等冲突（见 P0.4）</Code>
            <Code status="422" code="VALIDATION_ERROR">Pydantic 字段校验失败（自动生成）</Code>
            <Code status="429" code="RATE_LIMITED">请求过于频繁（可选实现）</Code>
            <Code status="500" code="INTERNAL_ERROR">未捕获的服务端错误</Code>
            <Code status="500" code="LLM_ERROR">rag_service / LLM 调用失败</Code>
            <Code status="500" code="STORAGE_ERROR">SQLite 写入/读取失败</Code>
          </ErrorCodes>
        </ErrorResponseSchema>

        <!-- ═══════════════════════════════════════════════════════════════════
             P0.6  API Endpoints 契约（Frozen）
        ═══════════════════════════════════════════════════════════════════ -->
        <APIContract>
          <!-- ─────────────────────────────────────────────────────────────
               POST /api/chat/sessions — 创建会话
          ───────────────────────────────────────────────────────────── -->
          <Endpoint method="POST" path="/api/chat/sessions">
            <Description>创建新会话</Description>
            <RequestBody>
              {
                "title": "string (optional, max 100 chars, default: 'New Chat')",
                "metadata": { ... }   // optional, 任意 JSON
              }
            </RequestBody>
            <ResponseBody status="201">
              {
                "id": "uuid",
                "title": "string",
                "created_at": "ISO8601",
                "updated_at": "ISO8601",
                "deleted_at": null,
                "metadata": { ... } | null
              }
            </ResponseBody>
            <Errors>
              <Error status="422">title 超长或格式非法</Error>
            </Errors>
          </Endpoint>

          <!-- ─────────────────────────────────────────────────────────────
               GET /api/chat/sessions — 列出会话（分页+搜索）
          ───────────────────────────────────────────────────────────── -->
          <Endpoint method="GET" path="/api/chat/sessions">
            <Description>列出会话（按 updated_at DESC 分页，过滤已软删除）</Description>
            <QueryParams>
              <Param name="limit" type="int" optional="true" default="20" max="100"/>
              <Param name="cursor" type="string" optional="true"/>
              <Param name="q" type="string" optional="true">标题模糊搜索</Param>
            </QueryParams>
            <ResponseBody status="200">
              {
                "sessions": [
                  {
                    "id": "uuid",
                    "title": "string",
                    "created_at": "ISO8601",
                    "updated_at": "ISO8601",
                    "deleted_at": null,
                    "metadata": { ... } | null,
                    "message_count": int,           // 该会话消息数（可选，便于 UI 展示）
                    "last_message_preview": "string" | null  // 最后一条消息预览（截断 50 字符）
                  },
                  ...
                ],
                "next_cursor": "base64..." | null,
                "has_more": boolean
              }
            </ResponseBody>
            <Errors>
              <Error status="400">INVALID_CURSOR</Error>
            </Errors>
          </Endpoint>

          <!-- ─────────────────────────────────────────────────────────────
               GET /api/chat/sessions/{session_id} — 获取会话详情
          ───────────────────────────────────────────────────────────── -->
          <Endpoint method="GET" path="/api/chat/sessions/{session_id}">
            <Description>获取单个会话元信息</Description>
            <PathParams>
              <Param name="session_id" type="string" required="true">UUID</Param>
            </PathParams>
            <ResponseBody status="200">
              {
                "id": "uuid",
                "title": "string",
                "created_at": "ISO8601",
                "updated_at": "ISO8601",
                "deleted_at": null,
                "metadata": { ... } | null,
                "message_count": int
              }
            </ResponseBody>
            <Errors>
              <Error status="404">SESSION_NOT_FOUND</Error>
            </Errors>
          </Endpoint>

          <!-- ─────────────────────────────────────────────────────────────
               GET /api/chat/sessions/{session_id}/messages — 列出消息（分页）
          ───────────────────────────────────────────────────────────── -->
          <Endpoint method="GET" path="/api/chat/sessions/{session_id}/messages">
            <Description>列出会话消息（分页，向历史翻页）</Description>
            <PathParams>
              <Param name="session_id" type="string" required="true">UUID</Param>
            </PathParams>
            <QueryParams>
              <Param name="limit" type="int" optional="true" default="50" max="200"/>
              <Param name="cursor" type="string" optional="true"/>
            </QueryParams>
            <ResponseBody status="200">
              {
                "messages": [
                  {
                    "id": "uuid",
                    "session_id": "uuid",
                    "role": "user" | "assistant" | "system",
                    "content": "string",
                    "token_count": int | null,
                    "created_at": "ISO8601",
                    "metadata": {
                      "mode": "string" | null,
                      "img_path": "string" | null,
                      "error": "string" | null,
                      ...
                    } | null
                  },
                  ...
                ],
                "next_cursor": "base64..." | null,
                "has_more": boolean
              }
            </ResponseBody>
            <Notes>
              - messages 按 created_at ASC 排序返回（便于前端直接渲染）
              - cursor 用于向历史翻页（加载更早的消息）
            </Notes>
            <Errors>
              <Error status="404">SESSION_NOT_FOUND</Error>
              <Error status="400">INVALID_CURSOR</Error>
            </Errors>
          </Endpoint>

          <!-- ─────────────────────────────────────────────────────────────
               PATCH /api/chat/sessions/{session_id} — 更新会话
          ───────────────────────────────────────────────────────────── -->
          <Endpoint method="PATCH" path="/api/chat/sessions/{session_id}">
            <Description>更新会话（目前仅支持 title 和 metadata）</Description>
            <PathParams>
              <Param name="session_id" type="string" required="true">UUID</Param>
            </PathParams>
            <RequestBody>
              {
                "title": "string (optional, max 100 chars)",
                "metadata": { ... }   // optional, merge with existing
              }
            </RequestBody>
            <ResponseBody status="200">
              {
                "id": "uuid",
                "title": "string",
                "created_at": "ISO8601",
                "updated_at": "ISO8601",
                "deleted_at": null,
                "metadata": { ... } | null
              }
            </ResponseBody>
            <Errors>
              <Error status="404">SESSION_NOT_FOUND</Error>
              <Error status="422">title 超长或格式非法</Error>
            </Errors>
          </Endpoint>

          <!-- ─────────────────────────────────────────────────────────────
               DELETE /api/chat/sessions/{session_id} — 删除会话
          ───────────────────────────────────────────────────────────── -->
          <Endpoint method="DELETE" path="/api/chat/sessions/{session_id}">
            <Description>删除会话（默认软删除，可选硬删除）</Description>
            <PathParams>
              <Param name="session_id" type="string" required="true">UUID</Param>
            </PathParams>
            <QueryParams>
              <Param name="hard" type="boolean" optional="true" default="false">
                true: 物理删除（CASCADE 删除 messages + turns）；false: 软删除（设置 deleted_at）
              </Param>
            </QueryParams>
            <ResponseBody status="200">
              {
                "id": "uuid",
                "deleted": true,
                "hard": boolean,
                "deleted_at": "ISO8601" | null   // 软删除时返回时间戳，硬删除返回 null
              }
            </ResponseBody>
            <Errors>
              <Error status="404">SESSION_NOT_FOUND</Error>
            </Errors>
          </Endpoint>

          <!-- ─────────────────────────────────────────────────────────────
               POST /api/chat/sessions/{session_id}/turn — 对话轮次
          ───────────────────────────────────────────────────────────── -->
          <Endpoint method="POST" path="/api/chat/sessions/{session_id}/turn">
            <Description>发送用户消息并获取助手回复（幂等）</Description>
            <PathParams>
              <Param name="session_id" type="string" required="true">UUID</Param>
            </PathParams>
            <RequestBody>
              {
                "request_id": "uuid (REQUIRED, 前端生成，用于幂等)",
                "query": "string (REQUIRED, 用户消息内容)",
                "mode": "string (optional, default: 'hybrid')",
                "multimodal_content": {
                  "img_base64": "string (optional, 将落盘存储，不入 DB)",
                  "img_mime_type": "string (optional, e.g. 'image/png')"
                } | null,
                "max_tokens": "int (optional)",
                "temperature": "float (optional)",
                "history_limit": "int (optional, default: 20)",
                "max_history_tokens": "int (optional, default: 8000)"
              }
            </RequestBody>
            <ResponseBody status="200">
              {
                "turn_id": "uuid (= request_id)",
                "status": "completed" | "failed",
                "user_message": {
                  "id": "uuid",
                  "role": "user",
                  "content": "string",
                  "created_at": "ISO8601",
                  "metadata": { "mode": "...", "img_path": "..." } | null
                },
                "assistant_message": {
                  "id": "uuid",
                  "role": "assistant",
                  "content": "string",
                  "created_at": "ISO8601",
                  "token_count": int | null,
                  "metadata": { "mode": "...", "sources": [...] } | null
                } | null,
                "error": {
                  "code": "LLM_ERROR",
                  "message": "..."
                } | null
              }
            </ResponseBody>
            <Notes>
              - 幂等：同 request_id 且 payload_hash 一致时返回已有结果
              - 失败补偿：LLM 错误时 status=failed，user_message 已写入，assistant_message=null
              - 自动更新 session.updated_at
              - 首条消息时自动更新 session.title（截断 query 前 100 字符）
            </Notes>
            <Errors>
              <Error status="400">EMPTY_QUERY, MISSING_REQUEST_ID, INVALID_MODE, MULTIMODAL_INVALID</Error>
              <Error status="404">SESSION_NOT_FOUND</Error>
              <Error status="409">IDEMPOTENCY_CONFLICT</Error>
              <Error status="500">LLM_ERROR, STORAGE_ERROR</Error>
            </Errors>
          </Endpoint>
        </APIContract>

        <!-- ═══════════════════════════════════════════════════════════════════
             P0.7  原有 WorkItems（保留）
        ═══════════════════════════════════════════════════════════════════ -->
        <WorkItems>
          <Item>确认单用户假设：暂不引入 auth，但 DB/接口预留 `user_id` 字段（默认 NULL）。</Item>
          <Item>确定 history 限制策略：服务端默认取最近 `N=20` 条消息，同时支持 `max_history_tokens`（默认 8000）用于动态截断；turn API 支持 `history_limit/max_history_tokens` 可选参数。</Item>
          <Item>确定幂等性策略：turn API 要求前端提供 `request_id`（uuid），后端用 `chat_turns` 去重；定义冲突行为（同 request_id 但 payload 不一致 → 409）。</Item>
          <Item>确定分页策略：`GET /sessions` 与 `GET /messages` 均必须支持 `limit + cursor`（MVP 即支持），避免长列表全量加载。</Item>
          <Item>确定会话标题策略：MVP 使用"第一条 user message 截断"生成 title；后续可用 LLM 生成摘要标题。</Item>
          <Item>确定删除语义：建议从 MVP 起就软删除（`deleted_at`），避免误删不可恢复；可选提供 `hard=true` 才物理删除。</Item>
          <Item>确定 documents 快捷入口：Sidebar 主入口为 Library（最常用），其余 Upload/Graph 可作为子项。</Item>
        </WorkItems>
        <Commands>
          <Command>bash&gt; cat _TASKs/T8_chat-ui-sessions-sqlite.md</Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>Spec review</Name>
            <Expectation>团队/自己 review 通过，关键字段与接口不再变更。</Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>冻结接口列表、字段命名、默认值与错误码（400/404/409/422/500，必要时 429）。</Criterion>
          <Criterion>冻结分页参数与 response shape（next_cursor 的格式）。</Criterion>
          <Criterion>冻结幂等性约定（request_id 的传递方式、冲突判定与返回）。</Criterion>
          <Criterion>冻结 SQLite DDL（表结构、索引、PRAGMA）。</Criterion>
          <Criterion>冻结错误响应 schema（统一 detail 结构）。</Criterion>
          <Criterion>冻结默认值配置（history_limit、tokens、limits 等）。</Criterion>
        </ExitCriteria>
      </Plan>
    </PhaseBlock>

    <PhaseBlock>
      <PhaseHeading>Phase P1 — SQLite 数据层（ChatStore）</PhaseHeading>
      <Plan>
        <Intent>新增 SQLite 存储层，负责：初始化表、CRUD sessions/messages、turn 原子写入、并发配置。</Intent>
        <Edits>
          <Edit>
            <Path>backend/services/chat_store.py</Path>
            <Operation>add</Operation>
            <Rationale>封装 sqlite3 访问模式，提供可测试、可复用的存储层。</Rationale>
            <Method>
              - 连接工厂：`sqlite3.connect(db_path, timeout=30)`，`row_factory=sqlite3.Row`
              - init_db：创建 `chat_sessions/chat_messages/chat_turns` + 索引 + PRAGMA（WAL + busy_timeout）
              - API：create_session/list_sessions/get_session/update_session/delete_session
              - messages：append_message/list_messages/delete_messages_by_session
              - turn 写入：避免“持锁等待 LLM”——采用补偿写入：先写 user（短事务）→ LLM → 写 assistant（短事务）→ 失败则标记 turn/message failed（metadata）或清理 user message
            </Method>
          </Edit>
          <Edit>
            <Path>backend/models/chat.py</Path>
            <Operation>add</Operation>
            <Rationale>集中定义 Pydantic 模型（request/response），保持契约一致。</Rationale>
            <Method>定义 ChatSession、ChatMessage，以及 CRUD/turn 的 request/response models。</Method>
          </Edit>
          <Edit>
            <Path>backend/config.py</Path>
            <Operation>modify</Operation>
            <Rationale>提供 `CHAT_DB_PATH` 配置入口，便于部署与数据目录管理。</Rationale>
            <Method>在 BackendConfig 增加 `chat_db_path` 字段，并在 from_env 中读取并 `os.path.abspath`。</Method>
          </Edit>
          <Edit>
            <Path>backend/tests/test_chat_store.py</Path>
            <Operation>add</Operation>
            <Rationale>覆盖 ChatStore 的关键数据一致性与并发边界，避免后续演进破坏。</Rationale>
            <Method>
              - 覆盖：create/list/get/delete（软删过滤）、append_message 更新 session.updated_at、list_messages 分页 cursor
              - 幂等：chat_turns 写入与查找（同 request_id 重放）
              - 失败补偿：标记 failed 的消息/turn 仍可解释（不影响后续继续对话）
              - 并发：并发 append/turn 不应频繁报 locked（WAL + busy_timeout）
            </Method>
          </Edit>
        </Edits>
        <Commands>
          <Command>bash&gt; python -c "import sqlite3; print(sqlite3.sqlite_version)"</Command>
          <Command>bash&gt; pytest -q backend/tests</Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>unit: ChatStore init + CRUD</Name>
            <Expectation>创建 session、追加消息、列出消息、删除 session 均通过；并发场景不会频繁 locked。</Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>ChatStore 可在干净环境初始化 DB 并完成 CRUD（有测试覆盖）。</Criterion>
        </ExitCriteria>
      </Plan>
    </PhaseBlock>

    <PhaseBlock>
      <PhaseHeading>Phase P2 — Chat API Router（/api/chat）</PhaseHeading>
      <Plan>
        <Intent>实现会话 CRUD + messages listing + turn API，并接入现有 rag_service。</Intent>
        <Edits>
          <Edit>
            <Path>backend/routers/chat.py</Path>
            <Operation>add</Operation>
            <Rationale>提供面向前端的 chats/session API。</Rationale>
            <Method>
              - `POST /sessions`：创建会话（返回 id/title）
              - `GET /sessions?limit=&cursor=&q=`：按 updated_at 排序返回（分页 + 搜索 + 软删除过滤）
              - `PATCH /sessions/{id}`：更新 title
              - `DELETE /sessions/{id}`：默认软删除（写 deleted_at），可选 `?hard=true` 物理删除（级联）
              - `GET /sessions/{id}/messages?limit=&cursor=`：消息分页（cursor-based；支持回放长对话）
              - `POST /sessions/{id}/turn`：要求 `request_id` 幂等；流程：幂等检查 → 写 user（短事务）→ 取 history（limit + token 截断）→ 调 rag_service（不持 DB 锁）→ 写 assistant + 更新 session.updated_at/title → 写 turn 状态（completed/failed）
            </Method>
          </Edit>
          <Edit>
            <Path>backend/routers/__init__.py</Path>
            <Operation>modify</Operation>
            <Rationale>确保 `from backend.routers import chat` 可用，保持 router 组织方式一致。</Rationale>
            <Method>在 `__all__` 与 import 列表中加入 `chat`。</Method>
          </Edit>
          <Edit>
            <Path>backend/main.py</Path>
            <Operation>modify</Operation>
            <Rationale>注册 `/api/chat` router，并将 ChatStore 实例放入 app.state（或按请求创建）。</Rationale>
            <Method>在 lifespan startup 初始化 ChatStore，`app.include_router(chat.router, prefix=\"/api/chat\")`。</Method>
          </Edit>
          <Edit>
            <Path>backend/tests/test_chat_api.py</Path>
            <Operation>add</Operation>
            <Rationale>保证 API 行为可回归、可持续演进。</Rationale>
            <Method>
              - 使用 FastAPI TestClient（或 httpx AsyncClient）
              - mock rag_service.query 返回固定字符串（避免真实模型调用）
              - 覆盖：create session → list sessions（分页）→ turn（带 request_id）→ list messages（分页）→ rename → delete（软删）→ hard delete（可选）
              - 覆盖错误码：400（空 query / request_id 缺失 / mode 非法）、404（session 不存在）、409（request_id 冲突）、422（字段校验）
              - 幂等验证：同 request_id 重放应返回同一结果（不新增 messages）
              - 失败补偿：rag_service 抛错时，turn 状态为 failed，且不会产生“重复 assistant”或不可解释的半成品状态（策略需在 P0 冻结：删除 user vs 标记 failed）
            </Method>
          </Edit>
        </Edits>
        <Commands>
          <Command>bash&gt; pytest -q backend/tests/test_chat_api.py</Command>
          <Command>bash&gt; uvicorn backend.main:app --host 0.0.0.0 --port 8000</Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>manual: curl turn</Name>
            <Expectation>创建 session 后 turn 返回 assistant response，且 messages endpoint 能读回。</Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>API docs `/docs` 出现 Chat endpoints；pytest 通过；手动请求可用。</Criterion>
        </ExitCriteria>
      </Plan>
    </PhaseBlock>

    <PhaseBlock>
      <PhaseHeading>Phase P3 — 前端 AppShell + Sidebar（结构改造）</PhaseHeading>
      <Plan>
        <Intent>把现有“顶部 Header + ModeSwitch”重构为“左侧 Sidebar + 右侧主面板 Outlet”，并把 Settings 移到左下角用户区。</Intent>
        <Edits>
          <Edit>
            <Path>frontend/src/components/layout/AppShell.tsx</Path>
            <Operation>add</Operation>
            <Rationale>提供全局页面壳：Sidebar + Main content。</Rationale>
            <Method>CSS 使用 Tailwind；Sidebar 固定宽度、可滚动；Main 占满剩余；移动端可折叠（可后续增强）。</Method>
          </Edit>
          <Edit>
            <Path>frontend/src/components/layout/Sidebar.tsx</Path>
            <Operation>add</Operation>
            <Rationale>实现左侧导航（chat list、documents shortcut、settings/user）。</Rationale>
            <Method>复用 shadcn Button/Input/DropdownMenu；底部 user 区放 SettingsModal Trigger + ThemeToggle。</Method>
          </Edit>
          <Edit>
            <Path>frontend/src/components/layout/Layout.tsx</Path>
            <Operation>modify</Operation>
            <Rationale>从现有 Layout 改为 AppShellLayout；不再渲染 Header/ModeSwitch。</Rationale>
            <Method>`Layout` 仅负责 `<AppShell><Outlet/></AppShell>`。</Method>
          </Edit>
          <Edit>
            <Path>frontend/src/App.tsx</Path>
            <Operation>modify</Operation>
            <Rationale>更新路由：新增 `/chat/:sessionId`，documents 保持但外观由 AppShell 管。</Rationale>
            <Method>lazy import 新 views；/chat index 进入空态或自动新建。</Method>
          </Edit>
        </Edits>
        <Commands>
          <Command>bash&gt; cd frontend &amp;&amp; npm test</Command>
          <Command>bash&gt; cd frontend &amp;&amp; npm run dev</Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>manual: layout smoke</Name>
            <Expectation>访问 /chat 与 /documents/library 均在同一 AppShell 内显示，Sidebar 常驻，主面板正常滚动。</Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>Sidebar/主面板结构稳定；Settings/Theme 可从左下角访问。</Criterion>
        </ExitCriteria>
      </Plan>
    </PhaseBlock>

    <PhaseBlock>
      <PhaseHeading>Phase P4 — 前端接入后端会话（核心功能）</PhaseHeading>
      <Plan>
        <Intent>前端完成：会话列表（来自后端）、新建/删除/重命名、切换会话；聊天发送改为调用 `/api/chat/.../turn`。</Intent>
        <Edits>
          <Edit>
            <Path>frontend/src/api/chat.ts</Path>
            <Operation>add</Operation>
            <Rationale>封装 `/api/chat` 请求（axios client）。</Rationale>
            <Method>create/list(分页+search)/get/messages(分页)/rename/delete(软删+可选硬删)/turn(携带 request_id)；错误统一抛 APIException，并在 409/404 时提供可读 detail。</Method>
          </Edit>
          <Edit>
            <Path>frontend/src/api/index.ts</Path>
            <Operation>modify</Operation>
            <Rationale>保持 API 导出入口一致，供 Settings/Sidebar 等模块统一引用。</Rationale>
            <Method>在 `frontend/src/api/index.ts` 增加 `export * from './chat';`。</Method>
          </Edit>
          <Edit>
            <Path>frontend/src/types/chat.ts</Path>
            <Operation>modify</Operation>
            <Rationale>补齐多会话所需的类型：ChatSession、ChatMessage（服务端字段）、分页响应等。</Rationale>
            <Method>新增 `ChatSession`、`ChatMessageDTO`、`ListSessionsResponse`、`ListMessagesResponse`、`ChatTurnRequest/Response`（与后端 Pydantic 对齐）。</Method>
          </Edit>
          <Edit>
            <Path>frontend/src/types/index.ts</Path>
            <Operation>modify</Operation>
            <Rationale>保证 types 有统一出口。</Rationale>
            <Method>导出新增的 chat session types。</Method>
          </Edit>
          <Edit>
            <Path>frontend/src/hooks/useChatSessions.ts</Path>
            <Operation>add</Operation>
            <Rationale>React Query：拉取 sessions、mutation（create/rename/delete）。</Rationale>
            <Method>queryKey 设计：`['chatSessions']`、`['chatMessages', sessionId]`。</Method>
          </Edit>
          <Edit>
            <Path>frontend/src/hooks/index.ts</Path>
            <Operation>modify</Operation>
            <Rationale>保持 hooks 统一导出。</Rationale>
            <Method>新增导出：`useChatSessions`（以及可能的 `useChatMessages`）。</Method>
          </Edit>
          <Edit>
            <Path>frontend/src/hooks/useChat.ts</Path>
            <Operation>modify</Operation>
            <Rationale>从本地 store 单会话改为 session-aware，且 history 由后端维护。</Rationale>
            <Method>
              sendMessage(sessionId, ...) → 生成 `request_id = crypto.randomUUID()` → optimistic append user + placeholder assistant → 调 turn → 用返回的 messages 更新 React Query cache。若收到 409（request_id 冲突且 payload 不一致）提示用户重试；若收到“已完成的幂等命中”则直接用后端返回结果覆盖本地 placeholder。
            </Method>
          </Edit>
          <Edit>
            <Path>frontend/src/store/chatStore.ts</Path>
            <Operation>modify</Operation>
            <Rationale>将“服务端状态（messages/sessions）”迁移到 React Query；Zustand 仅保留 UI 状态，避免双写与不一致。</Rationale>
            <Method>移除 `messages` 持久化与相关 action；保留/迁移 `currentMode`、输入草稿、sidebar 折叠等 UI 状态（如需要）。</Method>
          </Edit>
          <Edit>
            <Path>frontend/src/views/ChatView.tsx</Path>
            <Operation>modify</Operation>
            <Rationale>支持 `/chat/:sessionId`；无 session 时显示空态并引导新建。</Rationale>
            <Method>使用 `useParams()` 获取 sessionId；Sidebar “New chat” 触发 createSession 并 navigate。</Method>
          </Edit>
          <Edit>
            <Path>frontend/src/components/layout/Sidebar.tsx</Path>
            <Operation>modify</Operation>
            <Rationale>Sidebar 中渲染会话列表 + 搜索框 + rename/delete 菜单。</Rationale>
            <Method>长列表用滚动容器；会话列表支持分页（load more）与 search（debounce）；活跃 session 高亮；rename 用 Dialog/Inline input；delete 默认软删并从列表移除。</Method>
          </Edit>
        </Edits>
        <Commands>
          <Command>bash&gt; cd frontend &amp;&amp; npm run dev</Command>
          <Command>bash&gt; curl -s http://localhost:8000/docs | head</Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>manual: multi-session isolation</Name>
            <Expectation>创建 A 会话发送消息；创建 B 会话发送消息；切回 A 仍只看到 A 的消息。</Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>前端完全不依赖 localStorage 保存 messages；刷新后从后端恢复会话与消息。</Criterion>
          <Criterion>turn 请求具备幂等性（重复发送同 request_id 不会产生重复消息）。</Criterion>
        </ExitCriteria>
      </Plan>
    </PhaseBlock>

    <PhaseBlock>
      <PhaseHeading>Phase P5 — Documents 风格统一 + Sidebar 快捷入口</PhaseHeading>
      <Plan>
        <Intent>让 `/documents/*` 与 `/chat/*` 在同一视觉系统内；Sidebar 提供 Library 快捷入口；设置入口位于用户区。</Intent>
        <Edits>
          <Edit>
            <Path>frontend/src/views/DocumentView.tsx</Path>
            <Operation>modify</Operation>
            <Rationale>移除 documents 独立页面背景与大标题壳，避免“两个产品”割裂。</Rationale>
            <Method>把 Header/SecondaryNav 移到主面板顶部（轻量），或者将 Upload/Graph/Library 入口移到 Sidebar。</Method>
          </Edit>
          <Edit>
            <Path>frontend/src/components/documents/SecondaryNav.tsx</Path>
            <Operation>modify</Operation>
            <Rationale>与 Sidebar 导航合并/复用，保持一致。</Rationale>
            <Method>可改为可复用的 `SubNavTabs`，或直接弃用并在 Sidebar 展示 documents 子项。</Method>
          </Edit>
        </Edits>
        <Commands>
          <Command>bash&gt; cd frontend &amp;&amp; npm run dev</Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>manual: documents navigation</Name>
            <Expectation>Sidebar 一键进入 Library；Upload/Graph 仍可访问且功能不变。</Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>Documents 页面与 Chat 共享同一 AppShell 与统一的 spacing/typography。</Criterion>
        </ExitCriteria>
      </Plan>
    </PhaseBlock>

    <PhaseBlock>
      <PhaseHeading>Phase P6 — 测试、迁移与收尾</PhaseHeading>
      <Plan>
        <Intent>补齐测试覆盖与验收脚本；处理类型一致性；提供迁移/降级策略与文档更新。</Intent>
        <WorkItems>
          <Item>
            后端：补齐 ChatStore/Chat API 测试（建议至少覆盖）：
            - sessions：create/list(分页)/get/rename/delete(软删)/hard-delete(可选)
            - messages：append/list(分页)
            - turn：正常写入两条消息、幂等重放（同 request_id 不重复写）、409 冲突（同 request_id 不同 payload）、rag_service 抛错时的失败补偿（无重复 assistant / 状态可解释）
            - 并发：并发 append/turn 不应频繁出现 `database is locked`（WAL + busy_timeout 生效）
          </Item>
          <Item>前端：Playwright e2e：create new session → send message → rename → delete；multi-session isolation；refresh 后会话仍存在；sidebar navigation 到 documents library 可达。</Item>
          <Item>类型对齐：统一后端 Pydantic `ConversationResponse` 与前端 TS types；新 `/api/chat` 类型对齐。</Item>
          <Item>文档更新：README 增加 Chat API 说明与本地开发验收步骤。</Item>
          <Item>迁移策略（可选）：提供一次性按钮/脚本把旧 localStorage 单会话导入为一个后端 session。</Item>
        </WorkItems>
        <Commands>
          <Command>bash&gt; pytest -q</Command>
          <Command>bash&gt; cd frontend &amp;&amp; npm run test</Command>
          <Command>bash&gt; cd frontend &amp;&amp; npx playwright test</Command>
        </Commands>
        <TestsExpected>
          <Test>
            <Name>full smoke</Name>
            <Expectation>后端与前端启动后可完成：upload 文档→进入 Library→新建会话→问答→切换会话。</Expectation>
          </Test>
        </TestsExpected>
        <ExitCriteria>
          <Criterion>满足 AC1-AC6；回归测试通过；文档可按步骤复现。</Criterion>
        </ExitCriteria>
      </Plan>
    </PhaseBlock>

    <PhaseBlock>
      <PhaseHeading>Phase P7（可选）— 搜索与流式增强</PhaseHeading>
      <Plan>
        <Intent>增强体验：会话搜索（FTS5）与 SSE 流式输出（如果 provider 支持真 streaming）。</Intent>
        <WorkItems>
          <Item>搜索：为 chat_messages 创建 FTS5 virtual table（或使用 LIKE 作为 MVP），新增 `GET /api/chat/search?q=`。</Item>
          <Item>流式：新增 `POST /api/chat/sessions/{id}/turn:stream`（SSE），前端使用 `updateLastMessage` 实时更新 assistant content。</Item>
          <Item>停止生成：前端 AbortController；后端取消任务（best-effort）。</Item>
        </WorkItems>
        <ExitCriteria>
          <Criterion>可在不破坏 P0-P6 功能前提下逐步上线。</Criterion>
        </ExitCriteria>
      </Plan>
    </PhaseBlock>
  </Section>

  <Section id="acceptance_runbook">
    <Heading>5) RUNBOOK（验收步骤：可直接执行）</Heading>
    <List type="bullet">
      <Item>
        <Label>启动：</Label>
        <Text>
          1) `bash scripts/start_all.sh`（或分别启动后端 `uvicorn backend.main:app --reload` 与前端 `cd frontend &amp;&amp; npm run dev`）
          2) 打开 `http://localhost:5173`
        </Text>
      </Item>
      <Item>
        <Label>验收清单（手动）：</Label>
        <Text>
          - Sidebar 可见：New chat / Search / Library / Chats list / User+Settings
          - 新建会话：点击 New chat → URL 变为 `/chat/&lt;id&gt;`
          - A 会话发送 1 条消息 → 出现 assistant 回复
          - 新建 B 会话发送消息 → 切回 A 仍只显示 A 的消息
          - Library 入口可进入 documents library，上传/图谱/列表仍可用
          - Settings 从左下角打开，health/config 正常显示
        </Text>
      </Item>
      <Item>
        <Label>验收清单（API）：</Label>
        <Text>
          - `POST /api/chat/sessions` 创建
          - `POST /api/chat/sessions/{id}/turn` 对话
          - `GET /api/chat/sessions/{id}/messages` 回放
          - `PATCH /api/chat/sessions/{id}` 重命名
          - `DELETE /api/chat/sessions/{id}` 删除
        </Text>
      </Item>
    </List>
  </Section>

  <Section id="claude_review">
    <Heading>6) Claude Code Review（协作反馈）</Heading>
    <Callout>已完成 Claude Code 评审（SESSION_ID: 00df120e-6d0e-49ae-b153-5383d25ae401）；并在补齐 P0 契约冻结时协作使用 Claude Code（SESSION_ID: 0baa22d1-e392-4fe0-92b0-ff9600423e4a）。以下为要点摘录；详细原文可在 Claude 输出中回溯。</Callout>
    <Review>
      <Reviewer>claude-opus-4-5-20251101</Reviewer>
      <Status>completed</Status>
      <Findings>
        <Item><Label>P0 严重：</Label><Text>不要在 SQLite 持锁事务内等待 `rag_service.query()`（LLM 可能耗时很久）——会导致 `database is locked` 与长尾延迟；应改为“补偿写入”模式。</Text></Item>
        <Item><Label>P0 严重：</Label><Text>turn API 缺少幂等性设计：网络重试会产生重复消息对；建议引入 `request_id`/`X-Idempotency-Key` + `chat_turns` 去重表。</Text></Item>
        <Item><Label>P0 高：</Label><Text>错误码与触发条件需要冻结：至少覆盖 400/404/409/422/500（必要时 429），并明确前端处理策略。</Text></Item>
        <Item><Label>P1 高：</Label><Text>会话列表与消息列表需要从 MVP 起支持分页；否则长对话/大量会话会导致首屏慢与内存占用高。</Text></Item>
        <Item><Label>P1 中：</Label><Text>multimodal_content 的 base64 不应入库（DB 膨胀）；应落盘存路径；并补充索引（sessions.updated_at 等）与 soft-delete 字段。</Text></Item>
      </Findings>
      <Suggestions>
        <Item>Schema：增加 `deleted_at`（软删）、`metadata_json`、messages `token_count`，sessions/messages 添加必要索引；可选添加 FTS5。</Item>
        <Item>turn：拆分为“写 user（短事务）→ LLM（无锁）→ 写 assistant（短事务）→ 失败补偿（标记 failed/清理）”。</Item>
        <Item>API：sessions/messages 提供 `limit + cursor`；turn 强制 `request_id` 幂等；冲突（同 request_id 不同 payload）返回 409。</Item>
        <Item>前端：用 React Query 管服务端数据；Zustand 仅保留 UI 状态（mode/sidebar collapsed 等）；optimistic update + 409/404 处理要清晰。</Item>
        <Item>测试：补齐并发、分页、幂等、失败补偿与多会话隔离的 pytest + Playwright 用例。</Item>
      </Suggestions>
      <Verdict>request-changes（已在本计划中吸收：补偿写入、幂等性、分页、soft-delete、multimodal 落盘策略与更完整测试清单）</Verdict>
    </Review>
  </Section>
</Task>
