# 架构文档

> 技术架构与 ADR（Architecture Decision Records）索引。产品范围与 MVP 边界见 [docs/planning/](../planning/)。

## 推荐阅读顺序

1. [系统架构概览](./overview.md) — 分层、进程模型、通信与持久化范围（SQLite + 工作区）
2. [多入口模块化架构](./modules.md) — core / cli / gui / mcp 职责、依赖与 Phase 0 落地步骤
3. [数据流与模块边界](./data-flow.md) — 用户操作流、预处理流水线、隐私边界
4. 按需阅读下方 [ADR 索引](#adr-架构决策记录)

## 文档地图

### 主文档

| 文档 | 说明 |
|------|------|
| [overview.md](./overview.md) | 系统分层、Tauri spawn 进程模型、本地 HTTP 通信、SQLite 与工作区持久化范围 |
| [modules.md](./modules.md) | 四模块划分、依赖铁律、各入口接入方式、目录目标结构与 **Phase 0 落地步骤** |
| [data-flow.md](./data-flow.md) | 端到端数据流、8 步预处理流水线（含 LLM 发送池）、core 边界、隐私与待定项 |

### ADR 架构决策记录

完整索引见 [adr/README.md](./adr/README.md)。

| ADR | 标题 |
|-----|------|
| [001](./adr/001-tauri-desktop-shell.md) | 桌面壳选用 Tauri 2 |
| [002](./adr/002-shadcn-ui.md) | 前端 UI 选用 shadcn/ui |
| [003](./adr/003-local-http-decoupling.md) | 前后端本地 HTTP 解耦 |
| [004](./adr/004-sqlite-user-settings.md) | SQLite 持久化用户配置 |
| [005](./adr/005-llm-integration-privacy.md) | LLM 集成与隐私边界 |
| [006](./adr/006-tauri-spawn-fastapi.md) | Tauri 管理 FastAPI 子进程 |
| [007](./adr/007-multi-entry-modules.md) | 多入口模块化（core / cli / gui / mcp） |
| [008](./adr/008-production-packaging.md) | 生产打包（PyInstaller sidecar） |
| [010](./adr/010-workspace-document-persistence.md) | 文稿与项目本地持久化（`Documents/SentRealm`） |
| [011](./adr/011-uv-python-environment.md) | uv 管理 Python 开发环境 |

## 与相邻文档的分工

| 目录 | 回答的问题 |
|------|------------|
| [docs/planning/](../planning/) | **做什么** — 产品定义与路线图 |
| **docs/architecture/**（本目录） | **怎么做** — 技术架构、模块边界、技术决策 |
| [docs/api/](../api/) | **接口契约** — HTTP 路由、OpenAPI、Apifox 对齐 |
| [docs/cli-mcp.md](../cli-mcp.md) | cli / mcp 命令与 tool 契约 |
| [docs/user/](../user/) | **怎么用** — 终端用户手册 |
| [docs/ui/](../ui/README.md) | **长什么样** — GUI tokens、壳层、组件映射与状态（实现契约） |
| [docs/dev/](../dev/) | **如何跑起来** — 环境搭建、本地运行、测试 |

## 待定 / 后续 ADR

以下事项已有方向，待触发条件满足后再撰写完整 ADR 或回写主文档：

| 项 | 触发条件 | 说明 |
|----|----------|------|
| ADR-009 uv workspace 拆分 | 流水线稳定，决定物理拆包 | workspace members、包间依赖、发布方式 |
| MCP settings / CLI config | 二期立项 | 扩展 [modules.md](./modules.md) 或新 ADR |

## 维护约定

- 架构或技术选型变更时，同步更新相关主文档与 ADR
- 新建 ADR 时复制 [adr/000-template.md](./adr/000-template.md)，并更新 [adr/README.md](./adr/README.md) 索引
- 实现细节以 ADR 为单一事实来源；产品范围以 [产品定义与 MVP](../planning/01-product-definition-and-mvp.md) 为准
