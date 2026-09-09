# SentRealm

面向视频创作者的**文稿预处理**桌面工具：在将文本粘贴到剪映「文稿匹配」之前，自动完成去标点、智能断句与分行，减少字幕轨返工。

**产品形态**：Tauri 2 桌面应用 + React 前端 + Python（FastAPI）后端；文稿本地处理，LLM 断句为可选能力。

> **当前状态**：**Phase 1 MVP 核心已完成**（M2）。下一优先：可分发安装包（见 [路线图](./docs/planning/03-roadmap.md)）。

## 文档索引

| 文档 | 说明 |
|------|------|
| [AGENTS.md](./AGENTS.md) | AI / 自动化协作约定 |
| [docs/user/](./docs/user/README.md) | **用户使用手册**（写稿 → 处理 → 剪映） |
| [docs/planning/](./docs/planning/README.md) | 产品规划与路线图 |
| [docs/architecture/](./docs/architecture/README.md) | 架构与技术决策 |
| [docs/api/](./docs/api/README.md) | HTTP API 与 OpenAPI |
| [docs/cli-mcp.md](./docs/cli-mcp.md) | CLI 与 MCP 契约 |
| [docs/dev/](./docs/dev/README.md) | 开发指南 |
| [docs/ui/](./docs/ui/README.md) | GUI 设计→实现契约（tokens、三栏壳、组件映射、状态） |

## 开发者快速开始

前置：Windows（Phase 0 主平台）、**uv** **0.12.1**（项目 `.venv` 使用 Python **3.12.13**）、Node **24.18.1**、pnpm **11.15.0**、Rust **1.97.1**。系统 Python 版本不作为项目基准，详见 [docs/dev/setup.md](./docs/dev/setup.md)。

```bash
uv sync
pnpm install
pnpm dev
```

- 一键启动后 Tauri 自动拉起 FastAPI（`127.0.0.1:17300`），无需第二个终端
- IDE 断点调试（F5）：见 [docs/dev/running-locally.md](./docs/dev/running-locally.md) 的「IDE 调试」一节
- 仅调试 API：`uv run uvicorn apps.gui.api.main:app --host 127.0.0.1 --port 17300`
- 测试：`uv run pytest`

## 核心能力（MVP 目标）

| 能力 | 说明 |
|------|------|
| 标点分级与去除 | 句末符号形成自然句；逗号等仅在超长时作为候选；引号/括号只删除；默认保留 `%` `％` `.` |
| 空格规范化 | 保留英词间、英中文间空格 |
| 规则 + LLM 断句 | 横屏 15 字 / 竖屏 10 字预设；规则层按候选边界全局选点并修复短行；超长行可选 LLM 语义切分 |
| 对照预览 | 右侧栏断句结果、行数统计、超长行高亮 |
| 多入口 | gui（桌面）、cli（脚本）、mcp（Agent 工具）共用配置 |

产品细节见 [产品定义与 MVP](./docs/planning/01-product-definition-and-mvp.md)。
