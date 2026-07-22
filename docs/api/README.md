# API 文档

> HTTP 契约以 [ADR-003](../architecture/adr/003-local-http-decoupling.md) 为准；`Settings` 字段以 [ADR-004](../architecture/adr/004-sqlite-user-settings.md) 为准。  
> **适用范围**：仅 `gui/ui` ↔ `apps/gui/api`；cli、mcp 直连 `core`，不走本 API。

## 单一事实来源

| 文档 | 说明 |
|------|------|
| **本文档** | 端点、请求/响应约定、错误格式（设计级 SSOT） |
| `docs/api/openapi.yaml` | OpenAPI 3.1 机器可读描述（与实现同步维护） |
| Apifox 项目 | 自 [openapi.yaml](./openapi.yaml) 导入；在线项目链接**待补充（非阻塞）** |

架构决策：[ADR-003](../architecture/adr/003-local-http-decoupling.md)。架构总览见 [docs/architecture/README.md](../architecture/README.md)。

## 基础约定

| 项 | 值 |
|----|-----|
| Base URL（默认） | `http://127.0.0.1:17300` |
| 绑定地址 | `127.0.0.1`（仅本机） |
| 业务路由前缀 | `/api/v1` |
| 健康检查 | `GET /health`（无版本前缀） |
| Content-Type | `application/json` |
| CORS | 生产不启用；开发下为 Vite dev server 允许有限 Origin（`apps/gui/api/main.py`） |

前端通过 Tauri command `get_api_base_url` 获取 base URL，不硬编码。MVP 端口固定为 `17300`；被占用时启动失败，不自动换端口（见 [ADR-006](../architecture/adr/006-tauri-spawn-fastapi.md)）。

### 版本策略

- 当前版本：**v1**（URL 路径 `/api/v1`）
- Breaking change 时递增至 `/api/v2`；v1 与 v2 可短期并存

### 错误响应

FastAPI 默认格式：

```json
{
  "detail": "错误说明"
}
```

校验失败（`422`）时 `detail` 为对象数组。常用状态码：

| 状态码 | 含义 |
|--------|------|
| 400 | 错误请求（如文稿为空） |
| 404 | 资源不存在（项目 / 文稿） |
| 409 | 冲突（如删除最后一个项目、删除活动项） |
| 422 | 请求体验证失败 |
| 500 | 服务器内部错误 |

MVP 不引入独立业务错误码枚举。

**校验失败示例** `422`（`PUT /api/v1/settings`，`max_chars` 非法）：

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "max_chars"],
      "msg": "Input should be greater than or equal to 1",
      "input": 0
    }
  ]
}
```

（`msg` 文案以实现为准；结构为 FastAPI/Pydantic 默认校验错误数组。）

## 端点一览

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查（Rust 轮询，见 ADR-006） |
| GET | `/api/v1/settings` | 读取用户配置 |
| PUT | `/api/v1/settings` | 更新用户配置 |
| GET | `/api/v1/break-lexicon/defaults` | 读取内置断句词表默认（供「恢复默认」） |
| GET | `/api/v1/settings/llm-key-status` | LLM 密钥是否已通过环境变量配置 |
| POST | `/api/v1/settings/llm-test` | 检测 LLM 端点连通性（处理前预检） |
| POST | `/api/v1/preprocess` | 预处理文稿 |
| POST | `/api/v1/preprocess/stream` | 预处理文稿（SSE 流式进度，供 GUI 实时预览） |
| GET | `/api/v1/workspace` | 读取工作区状态（冷启动自动初始化） |
| PUT | `/api/v1/workspace/active` | 切换活动项目与文稿 |
| GET/POST | `/api/v1/projects` | 项目列表 / 新建 |
| GET/PATCH/DELETE | `/api/v1/projects/{project_id}` | 项目详情 / 重命名 / 删除 |
| GET/POST | `/api/v1/projects/{project_id}/documents` | 文稿列表 / 新建 |
| GET/PATCH/DELETE | `/api/v1/projects/{project_id}/documents/{document_id}` | 文稿详情 / 更新 / 删除 |
| PUT | `/api/v1/projects/{project_id}/documents/{document_id}/result` | 写入最近处理结果 |
| POST | `/api/v1/projects/{project_id}/documents/{document_id}/export` | 将处理后文本导出为文稿目录下 `.txt` |

---

## GET /health

**响应** `200 OK`

```json
{
  "status": "ok"
}
```

---

## GET /api/v1/settings

读取 SQLite 中的用户配置（见 ADR-004）。库不存在时由 `SettingsStore` 建库并返回默认 `Settings`。

**响应** `200 OK`

```json
{
  "preset": "landscape",
  "max_chars": 15,
  "min_chars": 5,
  "punctuation_remove": [
    "，", "。", "！", "？", "：", "；", "——", "、",
    ",", ".", "!", "?", ";", ":",
    "“", "”", "‘", "’", "\"", "'",
    "（", "）", "(", ")",
    "…"
  ],
  "punctuation_keep": ["%", "％"],
  "llm_enabled": false,
  "llm_endpoint": "",
  "llm_model": "",
  "break_lexicon": {
    "protected_words": ["就业", "重要", "全方位"],
    "break_after_words": ["不是", "所以", "非常"],
    "break_after_chars": ["了", "到", "有", "的"],
    "break_before_words": ["在", "即将", "找"]
  }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `preset` | string | `landscape` \| `portrait` \| `custom` |
| `max_chars` | integer | 单行最大字数；与 `preset` 联动见下文 |
| `min_chars` | integer | 规则/LLM 断句单行最短字数（≥1 且 ≤ `max_chars`）；默认 `5` |
| `punctuation_remove` | string[] | 去除并在原位置换行的符号 |
| `punctuation_keep` | string[] | 保留不换行的符号 |
| `llm_enabled` | boolean | 是否启用 LLM 断句（默认 `false`） |
| `llm_endpoint` | string | LLM API 端点（未配置时为 `""`） |
| `llm_model` | string | 模型名（未配置时为 `""`） |
| `break_lexicon` | object | 规则断句字词表，见下表 |

#### `break_lexicon` 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `protected_words` | string[] | 受保护词（每项最长 4 字） |
| `break_after_words` | string[] | 整词结束后可换行 |
| `break_after_chars` | string[] | 单字结束后可换行（每项须为单字符） |
| `break_before_words` | string[] | 整词开始前可换行 |

### Settings 默认值

首次 `GET` 或库不存在时返回的默认值（与 [ADR-004](../architecture/adr/004-sqlite-user-settings.md)、[产品定义：去标点规则](../planning/01-product-definition-and-mvp.md) 对齐）：

| 字段 | 默认值 |
|------|--------|
| `preset` | `landscape` |
| `max_chars` | `15` |
| `min_chars` | `5` |
| `punctuation_remove` | 见上方响应示例完整数组 |
| `punctuation_keep` | `["%", "％"]` |
| `llm_enabled` | `false` |
| `llm_endpoint` / `llm_model` | `""`（未配置 LLM） |
| `break_lexicon` | 与内置 `data/break_lexicon/*.txt` 一致 |

API 密钥**不在**响应中返回（仅存于环境变量，见 ADR-004/005）。

---

## GET /api/v1/break-lexicon/defaults

返回打包内置词表（只读，不读 SQLite）。供 GUI「恢复默认」。

**响应** `200 OK` — 结构与 `Settings.break_lexicon` 相同。

---

## PUT /api/v1/settings

更新用户配置并持久化到 SQLite。

**请求体**

与 `GET /api/v1/settings` 响应体同结构；发送需更新的完整 `Settings` 对象（全量替换）。

### `preset` 与 `max_chars` 联动

服务端在写入前校验并**自动修正** `max_chars`，响应体返回修正后的对象：

| `preset` | `max_chars` 行为 |
|----------|------------------|
| `landscape` | 强制为 `15`（请求中其他值被覆盖） |
| `portrait` | 强制为 `10` |
| `custom` | 使用请求中的值，须 `>= 1`；否则 `422` |

`POST /api/v1/preprocess` 请求体中的 `settings`（当次覆盖）**不**经过上述自动修正逻辑，由调用方保证一致性。

**响应** `200 OK`

返回更新后的 `Settings` 对象（同 GET 响应）。

**错误** `422`：字段校验失败（如 `custom` 下 `max_chars: 0`）。`500`：服务器内部错误。

---

## POST /api/v1/settings/llm-test

在启用 LLM 断句时，GUI 于「处理文稿」前调用，验证 endpoint/model/密钥是否可用。

**请求体**：无。

**响应** `200 OK`

```json
{ "ok": true, "skipped": false, "message": null }
```

| 字段 | 说明 |
|------|------|
| `ok` | `true` 表示可继续处理；`false` 表示连接/认证失败 |
| `skipped` | 未完整配置 LLM 时为 `true`（此时 `ok` 亦为 `true`） |
| `message` | `ok=false` 时的用户可读原因 |

---

## POST /api/v1/preprocess

对文稿执行预处理流水线（见 [数据流](../architecture/data-flow.md)）。

**请求体**

```json
{
  "text": "待处理的文稿全文……",
  "settings": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | string | 是 | 文稿正文；空白或仅空格时返回 `400` |
| `settings` | object \| null | 否 | 省略或 `null` 时使用 SQLite 中的配置；提供时**仅当次请求**使用该配置（不写库） |

`settings` 对象结构与 `GET /api/v1/settings` 相同。

**响应** `200 OK`

```json
{
  "original": "原始文稿……",
  "processed": "处理后文本\n按行分隔……",
  "line_count": 12,
  "flagged_lines": [3, 7]
}
```

---

## POST /api/v1/preprocess/stream

与 `POST /preprocess` 请求体相同；响应为 **Server-Sent Events**，供 GUI 实时刷新结果栏。

**SSE 事件**

| `type` | 说明 |
|--------|------|
| `progress` | 中间快照：`processed`、`line_count`、`flagged_lines`、`phase`（`rules` \| `llm`），LLM 阶段含 `llm_current` / `llm_total`（推荐口径：入池条数的终态进度，见 ADR-005） |
| `done` | 最终 `PreprocessResult`（字段同 JSON 接口） |
| `error` | `{ "detail": "…" }` |

**示例**

```
data: {"type":"progress","phase":"rules","processed":"…","line_count":42,...}

data: {"type":"done","original":"…","processed":"…","line_count":574,"flagged_lines":[0]}
```

---

## POST /api/v1/preprocess 响应字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `original` | string | 请求中的原文（便于对照展示） |
| `processed` | string | 处理后文本，行以 `\n` 分隔，无空行 |
| `line_count` | integer | 处理后行数（字幕条数） |
| `flagged_lines` | integer[] | 仍超出字数上限的行号（**0-based**），UI 高亮 |

**错误示例** `400`

```json
{
  "detail": "文稿不能为空"
}
```

---

## 工作区（projects / documents）

> 存储与路径约定以 [ADR-010](../architecture/adr/010-workspace-document-persistence.md) 为准；请求/响应字段以 [openapi.yaml](./openapi.yaml) 的 `workspace` 相关 schema 为准。本文只写行为约定。

**适用范围**：仅 gui。cli / mcp 不调用本组端点。

### 行为摘要

| 约定 | 说明 |
|------|------|
| 根路径 | Windows：`%USERPROFILE%/Documents/SentRealm/`（`default_workspace_path()`） |
| 冷启动 | `GET /api/v1/workspace` 触发 `ensure_initialized()`：无结构则建默认项目/文稿；损坏的活动指针经 `repair_meta()` 回退 |
| 活动项 | `PUT /api/v1/workspace/active` 切换当前项目与文稿 |
| 正文 | 文稿详情含 `source`（对应磁盘 `source.txt`）；更新走 PATCH |
| 处理结果 | `PUT .../documents/{id}/result` 写入最近一次 `result.json` |
| 导出 .txt | `POST .../documents/{id}/export` 将 `processed` 写入文稿目录（文件名由标题生成，不覆盖 `source.txt` / `result.json` / `document.json`） |
| 与 preprocess 关系 | `POST /api/v1/preprocess` **不**自动写工作区；gui 需在需要时另调 result API 落盘 |
| 删除 | 物理删除目录；`409`：删除最后一个项目、或删除当前活动项等冲突（详见 openapi） |
| 常见错误 | `404` 项目/文稿不存在；`409` 冲突；`422` 校验失败 |

### 端点分组

| 组 | 路径前缀 | 能力 |
|----|----------|------|
| 工作区状态 | `/api/v1/workspace` | 读取状态；切换 active |
| 项目 | `/api/v1/projects` | 列表 / 新建 / 详情 / 重命名 / 删除 |
| 文稿 | `/api/v1/projects/{id}/documents` | 列表 / 新建 / 详情 / 更新 / 删除 / 写 result / 导出 txt |

完整 JSON 形状、必填字段与示例见 [openapi.yaml](./openapi.yaml)。

---

## Apifox 调试

1. 启动 gui（`pnpm dev`），确保 FastAPI 子进程在 `127.0.0.1:17300` 运行
2. 在 Apifox 中新建项目，Base URL 设为 `http://127.0.0.1:17300`
3. 从 [openapi.yaml](./openapi.yaml) 导入接口定义
4. LLM 相关行为需：`settings.llm_enabled=true`，配置 endpoint/model，以及环境变量 `SENTREALM_LLM_API_KEY`

在线 Apifox 项目链接**待补充（非阻塞）**；本地导入 openapi 即可调试。

## Mock 策略

| 场景 | 做法 |
|------|------|
| 后端单元测试 | 注入 `MockLlmClient`，不发起真实 LLM 请求（ADR-005） |
| 未启用 / 未配置 LLM | `llm_enabled=false`，或未配置 endpoint/model/密钥时，流水线跳过 LLM 步骤；`flagged_lines` 可能非空 |
| 前端开发 | 对真实本地 API 发请求；或使用 Apifox mock（与实现无关的临时 mock） |
| CI | 默认不运行依赖真实 LLM API 的集成测试 |

HTTP API 本身 MVP 不提供 mock 模式；测试在 `core` 层 mock `LlmClient`。

## 相关文档

- [OpenAPI 规范](./openapi.yaml)
- [ADR-003：前后端本地 HTTP 解耦](../architecture/adr/003-local-http-decoupling.md)
- [ADR-004：SQLite 持久化用户配置](../architecture/adr/004-sqlite-user-settings.md)
- [ADR-005：LLM 集成与隐私边界](../architecture/adr/005-llm-integration-privacy.md)
- [ADR-010：文稿与项目本地持久化](../architecture/adr/010-workspace-document-persistence.md)
- [架构文档索引](../architecture/README.md)
- [架构概览](../architecture/overview.md)
- [数据流与模块边界](../architecture/data-flow.md)
