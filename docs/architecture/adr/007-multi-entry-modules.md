# ADR-007: 多入口模块化（core / cli / gui / mcp）

## 状态

已接受

## 背景

SentRealm 需要支持多种使用场景：

- **gui**：桌面应用，提供文稿预览、对照、复制等完整 MVP 体验（主产品形态）
- **cli**：命令行处理文稿，便于脚本集成与管道操作
- **mcp**：MCP Server，供 Cursor 等 Agent 在写稿流程中调用预处理

预处理流水线（去标点、空格规范化、规则断句、LLM 断句、超长行标记）逻辑复杂。若在 gui、cli、mcp 各入口分别实现，会导致：

- 单元测试分散、覆盖困难
- 各入口行为不一致，难以保证与 [产品定义](../../planning/01-product-definition-and-mvp.md) 对齐
- 修复 bug 需改多处，维护成本高

因此需要将**业务内核**与**入口适配**分离，并明确模块边界与依赖关系。

## 选项

### A. 单体 FastAPI 后端

所有能力经 HTTP 暴露；cli、mcp 也通过调用本地 FastAPI（`127.0.0.1`）使用。

- 优点：入口统一，仅维护一套 API
- 缺点：cli/mcp 依赖 gui 侧 api 进程是否运行；多一层 HTTP 开销；离线脚本场景需先启动服务

### B. 逻辑全堆在 gui

预处理逻辑放在 React 或 Tauri 内嵌 Python 中，不设独立 `core` 包。

- 优点：初期目录简单
- 缺点：cli/mcp 无法复用；业务逻辑与 UI 耦合；难以独立测试流水线

### C. 四模块 + core 内核（本决策选中）

- **core**：纯 Python 库，承载流水线与配置存储
- **gui**：Tauri + React + `gui/api`（薄 FastAPI，仅服务 WebView）
- **cli**：Typer 命令行，直接调 `core`
- **mcp**：stdio MCP server，直接调 `core`

- 优点：单测集中在 core；各入口可独立运行；gui 未启动时 cli/mcp 仍可用
- 缺点：模块与目录多于单体，需文档约束边界

### D. 脚手架阶段即 uv workspace 四包

与 C 相同的核心思想，但从 Day 1 拆分为独立 Python 包与 workspace。

- 优点：边界从一开始物理隔离
- 缺点：脚手架工作量更大，流水线未验证前过早拆包

## 决策

采用 **选项 C**，并按 **方案 A 两阶段** 落地目录：

| 阶段 | 做法 |
|------|------|
| 阶段 0（脚手架 / MVP） | **目录约定已落地**：单仓库内逻辑分层（`packages/core`、`packages/cli`、`packages/mcp`、`apps/gui`），共用根 `pyproject.toml`。历史步骤见 [modules.md § Phase 0 落地步骤](../modules.md#phase-0-落地步骤) |
| 阶段 1（流水线稳定后） | 拆 uv workspace，各包独立 `pyproject.toml`（正式决策见待写 ADR-009） |

阶段 0 目录约定**已落地**；实现与延期项对照见 [implementation-status.md](../../dev/implementation-status.md)。

### 模块划分

| 模块 | 职责 |
|------|------|
| **core** | 8 步预处理流水线；`Settings` / `PreprocessResult`；`SettingsStore`；`LlmClient` 抽象 |
| **gui** | Tauri + React + `apps/gui/api`（FastAPI）；不承载断句逻辑 |
| **cli** | `sentrealm preprocess`（`-i` / `-o` / `--stdin` / `--preset`） |
| **mcp** | `preprocess_text` tool（MVP 仅此一个） |

**`gui/api` 不是第五个大模块**：它是 gui 的 HTTP 适配层，位于 `apps/gui/api/`，不单独拆为仓库级 `api` 包。

### 依赖铁律

| 模块 | 允许 | 禁止 |
|------|------|------|
| **core** | 流水线、领域模型、`SettingsStore`、LLM 客户端抽象 | HTTP、MCP、Tauri、React 依赖 |
| **gui/ui** | HTTP 调用 `gui/api` | import Python core |
| **gui/api** | FastAPI 路由；委托 `core` 与 `store` | 断句业务逻辑 |
| **cli** | 命令行解析；直接调 `core` + `store` | HTTP 调 gui/api |
| **mcp** | MCP tool 注册；直接调 `core` + `store` | HTTP 调 gui/api |

### 配置：共用 SQLite，无例外

gui、cli、mcp **始终共用同一 SQLite 文件**，不允许某入口使用独立配置文件或独立配置库。

- 路径由 `core.store.default_config_path()` 统一约定（Windows 已定稿；macOS/Linux 占位见 [ADR-004](./004-sqlite-user-settings.md)）
- 三入口均通过 `SettingsStore` 读写
- mcp 的 `preset` / `max_chars` 参数仅覆盖**当次请求**的处理参数，不改变持久化配置来源；LLM 等设置仍从共用库读取

### MVP 边界

| 模块 | MVP 交付 | 不做 |
|------|----------|------|
| **core** | 完整流水线 + Settings + SQLite store + LlmClient 抽象 | HTTP、CLI 解析、MCP 注册 |
| **gui** | Tauri + React + `gui/api` | 断句逻辑 |
| **cli** | `sentrealm preprocess` | `config` 子命令；批量 |
| **mcp** | `preprocess_text` | settings tools；批量 |

设计细节见 [多入口模块化架构](../modules.md)、[数据流与模块边界](../data-flow.md)。

## 后果

### 正面

- 预处理逻辑单点实现，测试与产品规则对齐成本低
- cli、mcp 不依赖 gui 是否运行，适合自动化与 Agent 集成
- gui 经 HTTP 与 api 解耦，便于 Apifox 调试与前端独立开发
- 阶段 0 先约定逻辑分层与落地顺序，降低 MVP 脚手架成本；阶段 1 再物理拆包风险可控

### 负面

- 初期目录结构比单体 FastAPI 更复杂，需严格遵循依赖铁律
- 阶段 0 → 阶段 1 迁移 workspace 需一次集中重构
- `modules.md`、本 ADR 与实现目录须保持同步，否则易出现误把 `gui/api` 当成独立产品模块，或误把「目标目录」写成「已落地」

## 相关文档

- [多入口模块化架构](../modules.md)（含 Phase 0 落地步骤）
- [数据流与模块边界](../data-flow.md)
- [架构概览](../overview.md)
- [实现对照状态](../../dev/implementation-status.md)
