# Architecture Decision Records (ADR)

记录重要技术决策：背景、选项、结论、后果。

## 索引

| ADR | 标题 | 状态 |
|-----|------|------|
| [001](./001-tauri-desktop-shell.md) | 桌面壳选用 Tauri 2 | 已接受 |
| [002](./002-shadcn-ui.md) | 前端 UI 选用 shadcn/ui | 已接受 |
| [003](./003-local-http-decoupling.md) | 前后端本地 HTTP 解耦 | 已接受 |
| [004](./004-sqlite-user-settings.md) | SQLite 持久化用户配置 | 已接受 |
| [005](./005-llm-integration-privacy.md) | LLM 集成与隐私边界 | 已接受（含发送池修订） |
| [006](./006-tauri-spawn-fastapi.md) | Tauri 管理 FastAPI 子进程 | 已接受 |
| [007](./007-multi-entry-modules.md) | 多入口模块化（core / cli / gui / mcp） | 已接受 |
| [008](./008-production-packaging.md) | 生产打包（PyInstaller sidecar） | 已接受 |
| [010](./010-workspace-document-persistence.md) | 文稿与项目本地持久化 | 已接受 |
| [011](./011-uv-python-environment.md) | uv 管理 Python 开发环境 | 已接受 |
| [012](./012-natural-boundary-segmentation.md) | 基于自然边界的全局规则断句 | 已接受 |

## 后续 ADR

以下 ADR 待触发条件满足后撰写（规划占位，尚无文件）：

| ADR | 标题 | 触发条件 |
|-----|------|----------|
| 009 | uv workspace 物理拆包 | 流水线稳定，决定拆分为独立 Python 包 |

MCP settings tools、CLI `config` 子命令等二期能力见 [架构文档索引](../README.md)。允许断点字词表 v1 见 [产品定义](../../planning/01-product-definition-and-mvp.md#允许断点字词表)。

## 模板

新建 ADR 时复制 [000-template.md](./000-template.md)，按编号命名（如 `001-tauri-desktop-shell.md`）。
