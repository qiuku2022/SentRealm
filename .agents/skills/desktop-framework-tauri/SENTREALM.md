# SentRealm 对 desktop-framework-tauri skill 的覆盖

权威架构仍以仓库 docs / ADR 为准。本文件只约束 Agent 不要把通用「业务全在 Rust command」模板套进本仓库。

## 必须遵守

| 通用 Tauri skill 说法 | 本仓库 |
|----------------------|--------|
| 业务逻辑经 `#[tauri::command]` + `invoke()` | **业务预处理走 HTTP**：React → `127.0.0.1:17300` → FastAPI → `sentrealm_core`（[ADR-006](../../../docs/architecture/adr/006-tauri-spawn-fastapi.md)、[ADR-007](../../../docs/architecture/adr/007-multi-entry-modules.md)） |
| 把 Python / FastAPI 嵌进 Rust（PyO3 等） | **禁止**。Rust 只 spawn / 管理后端子进程 |
| 生产用任意 sidecar / externalBin 方案 | 生产为 **PyInstaller onedir** 资源目录 `resources/sentrealm-api/`（[ADR-008](../../../docs/architecture/adr/008-production-packaging.md)）；安装包细节用 `sentrealm-packaging` skill |
| 为 skill 示例新增 tray / multi-window / mobile | **不要**主动扩 scope；当前是 Windows 主平台桌面壳 |
| 改 packaging 流程时只跟本 skill 的 packaging 章 | 以 `sentrealm-packaging` + [packaging.md](../../../docs/dev/packaging.md) 为准 |

## 仍然适用

- Tauri 2 **capabilities / permissions**（已用 `plugin-fs`、`plugin-dialog`）
- 插件双装：Cargo crate + npm `@tauri-apps/plugin-*`
- `invoke` 仅用于壳层能力（如 `get_api_base_url`、文件导入、后端启动错误查询），不要把断句算法搬进 Rust
- `tauri.conf.json` / `generate_handler!` 注册习惯

## 进程模型速查

| 环境 | 后端 |
|------|------|
| 开发 `pnpm dev` | Tauri spawn：`uv run uvicorn apps.gui.api.main:app --host 127.0.0.1 --port 17300` |
| IDE 调试 | `SENTREALM_SKIP_BACKEND_SPAWN=1` 时不 spawn，前端轮询 `/health` |
| 生产 | spawn sidecar `sentrealm-api.exe`（同端口） |

就绪：前端轮询 `GET /health`（200ms / 30s）；Rust setup **只 spawn、不阻塞等 health**。
