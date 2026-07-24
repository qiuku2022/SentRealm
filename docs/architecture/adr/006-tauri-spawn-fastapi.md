# ADR-006: Tauri 管理 FastAPI 子进程

## 状态

已接受

## 背景

根据 [ADR-007](./007-multi-entry-modules.md)，gui 模块由 Tauri + React + `apps/gui/api`（FastAPI）组成；React 仅经 HTTP 访问后端，不直接 import Python `core`。

需要解决以下问题：

- **一键启动**：用户执行 `pnpm dev` 即可使用，不应手动开两个终端分别启动 Tauri 与 uvicorn
- **生命周期绑定**：FastAPI 子进程须随桌面应用启动而启动、随应用退出而终止，避免残留后台进程
- **就绪感知**：前端在 backend 未就绪时不应调用业务 API，否则出现难以理解的连接错误

cli、mcp 为独立进程、直接调用 `core`，**不在本 ADR 范围**。

## 选项

### A. 用户手动双终端

开发时用户分别执行 `pnpm dev` 与 `uv run uvicorn ...`。

- 优点：实现简单，Rust 无需进程管理
- 缺点：体验差，易忘记启动后端；与「桌面应用一键启动」产品预期不符

### B. Tauri spawn，前端自行重试

Rust 在 `setup` 阶段 spawn FastAPI，但不等待就绪；React 启动后自行重试 API。

- 优点：Rust 实现较简单
- 缺点：就绪逻辑分散在前端；首屏易出现错误态；难以统一超时与错误提示

### C. Tauri spawn + Rust 健康检查（本决策选中）

Rust spawn 子进程后**立即返回**（不阻塞窗口）；前端轮询 `GET /health`，成功后再调用业务 API；失败则 UI 提示后端未就绪。

- 优点：就绪逻辑集中在 Rust；前端契约清晰；dev 与 prod 可共用同一模型
- 缺点：Rust 侧需维护 spawn、轮询、终止逻辑

### D. 内嵌 Python 于 Rust

通过 PyO3 等在 Rust 进程内运行 Python，不使用子进程。

- 优点：无独立后端进程
- 缺点：与 Python 生态（uvicorn、FastAPI 开发模式）脱节；构建与调试复杂度高

## 决策

采用 **选项 C**。开发与生产环境采用**同一进程模型**：均由 Tauri spawn 并管理 FastAPI 子进程；差异仅在启动命令与二进制来源。

### 应用启动

| 环境 | 行为 |
|------|------|
| 开发 | Tauri `setup` 阶段 spawn（工作目录 = 仓库根）：`uv run uvicorn apps.gui.api.main:app --host 127.0.0.1 --port 17300`。须已 `uv sync`（项目 `.venv`）；`uv` 在 PATH 中（见 [setup.md](../../dev/setup.md)、[ADR-011](./011-uv-python-environment.md)） |
| IDE 调试 | 环境变量 `SENTREALM_SKIP_BACKEND_SPAWN=1` 时**跳过 spawn**，仅轮询 `/health` 等待 debugpy uvicorn。见 [running-locally.md § IDE 调试](../../dev/running-locally.md#ide-调试cursor--vs-code) |
| 生产 | 同样由 Tauri spawn 后端可执行体；方案见 [ADR-008](./008-production-packaging.md)（PyInstaller sidecar） |

用户执行 `pnpm dev` 时，Tauri 在后台拉起后端，**无需手动开两个终端**。

### 实现参数（Phase 0）

| 项 | 约定 |
|----|------|
| uvicorn 模块 | `apps.gui.api.main:app` |
| 绑定 | `127.0.0.1:17300` |
| base URL | Tauri command `get_api_base_url` → `http://127.0.0.1:17300` |
| health 轮询 | **前端** `waitForHealth`：间隔 **200ms**，总超时 **30s**。Rust `setup` **只 spawn、不阻塞等 health**（避免空白窗） |
| 前端契约 | `GET /health` 成功前，前端**不调用** `/api/v1/*` 业务接口 |
| 已就绪跳过 | 若启动前 `GET /health` 已成功，跳过 spawn（dev 便利；避免重复绑定 17300） |
| IDE 跳过 spawn | `SENTREALM_SKIP_BACKEND_SPAWN=1`（或 `true` / `yes`）时永不 spawn；由前端轮询 `/health`，超时显示未就绪 |
| 错误透传 | Tauri command `get_backend_startup_error` 返回 **spawn 失败**摘要；health 超时由前端文案提示 |

### 就绪检查

- 前端轮询 `GET http://127.0.0.1:17300/health`（无版本前缀）
- 成功后再调用 `/api/v1/*`；启动中侧栏 / banner 显示「正在连接后端」
- **超时或启动失败**：UI 显示「后端未就绪」

### 端口冲突（MVP）

- 端口 **17300 被占用**时，后端启动失败
- UI 显示明确错误（如「端口 17300 已被占用」）
- **不自动换端口**（避免与 Apifox、前端 base URL 契约漂移）

### 运行中

- 前端通过 `invoke('get_api_base_url')` 获取 base URL，避免硬编码端口
- Rust 监控子进程状态
- **子进程异常退出**：Rust 记录日志；向 WebView 发送 `backend-unavailable` 类事件；UI 显示「后端已停止」并建议重启应用（MVP **不做**自动重启）

### 应用关闭

- Tauri 退出时（`Drop`、`on_window_event` 或等价生命周期钩子）**终止 FastAPI 子进程**
- 确保无残留 `uvicorn` 或 sidecar 进程

### 生产打包

生产环境将 FastAPI 后端打成 **PyInstaller onedir sidecar**，由 Tauri `bundle.resources` 嵌入；开发环境为 uv 项目 `.venv` + `uv run uvicorn`。详见 [ADR-008](./008-production-packaging.md)。

### 与 ADR-007 的关系

- 被 spawn 的对象是 **`apps/gui/api`**（gui 的 HTTP 适配层），不是独立的第五模块
- `core` 由 `gui/api` 在进程内 import 调用；cli、mcp 各自独立进程，不由 Tauri 管理

## 后果

### 正面

- 开发体验与产品形态一致：一键启动桌面应用即可使用
- 子进程生命周期清晰，避免后台残留
- 就绪检查集中在 Rust，前端无需处理「后端何时可用」的复杂重试
- 与 [架构概览](../overview.md) 进程模型、ADR-007 模块化边界一致

### 负面

- Rust 侧需编写并测试进程管理代码（spawn、health poll、kill）
- 生产打包见 [ADR-008](./008-production-packaging.md)（PyInstaller sidecar）
- 端口 17300 被占用时 MVP 直接失败，需用户自行释放端口

## 相关文档

- [架构概览](../overview.md)
- [ADR-007：多入口模块化](./007-multi-entry-modules.md)
- [ADR-008：生产打包](./008-production-packaging.md)
- [多入口模块化架构](../modules.md)
