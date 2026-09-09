# SentRealm 对官方 FastAPI skill 的覆盖

权威架构仍以仓库 docs / ADR 为准。本文件只约束 Agent 不要把官方 skill 里的全栈默认套进本仓库。

## 必须遵守

| 官方 skill 说法 | 本仓库 |
|-----------------|--------|
| `app.frontend()` / `router.frontend()` 托管前端 | **禁止**。前端由 Tauri WebView 加载（开发 Vite，生产 `frontendDist`） |
| `fastapi dev` / `fastapi run` | **不要**作为 gui 开发入口。开发：`pnpm dev` → Tauri spawn `uv run uvicorn apps.gui.api.main:app --host 127.0.0.1 --port 17300` |
| SQLModel 做数据库 | **不要**引入。用户配置是 SQLite + 现有 `SettingsStore`（[ADR-004](../../../docs/architecture/adr/004-sqlite-user-settings.md)） |
| `EventSourceResponse` 作为 SSE 默认 | 现有实现用 `StreamingResponse` + `text/event-stream`（`apps/gui/api/routes.py`）。未迁移前不要为「对齐 skill」而改类型 |
| Ruff / ty / Asyncer | 本仓库尚未采用；不要为 skill 新增这些依赖 |

## 仍然适用

- `Annotated[..., Depends(...)]`、路由级 `prefix` / `tags`
- 返回类型 / `response_model`、不要用 `...` / `RootModel`
- 不确定时用同步 `def`（gui/api 已是同步编排 core）
- HTTPX 仅用于测试客户端（已有 `httpx`）

## 模块边界

`gui/api` 是薄 HTTP 层：校验、鉴权无、委托 `sentrealm_core`。断句逻辑不进 FastAPI。改契约时同步 `docs/api/openapi.yaml` 与 `docs/api/README.md`。
