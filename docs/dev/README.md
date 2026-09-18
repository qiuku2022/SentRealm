# 开发指南

> 环境搭建、本地运行与测试约定。技术架构见 [docs/architecture/](../architecture/README.md)；HTTP 契约见 [docs/api/](../api/README.md)；cli/mcp 见 [cli-mcp.md](../cli-mcp.md)。

## 文档地图

| 文档 | 说明 |
|------|------|
| [setup.md](./setup.md) | 前置依赖、Python/Node 环境、首次安装与验证 |
| [running-locally.md](./running-locally.md) | 一键启动、IDE 调试（F5）、独立调试 API / cli / mcp、常见问题 |
| [packaging.md](./packaging.md) | Windows NSIS 安装包（PyInstaller sidecar + `tauri build`） |
| [testing.md](./testing.md) | 单元测试、API 测试、LLM mock、集成测试约定 |
| [implementation-status.md](./implementation-status.md) | 工作区代码树与文档的对照状态 |
| [cli-mcp.md](../cli-mcp.md) | CLI 命令与 MCP tool 契约（参数、输出、Cursor 配置） |

## 实现阶段说明

**Phase 0 脚手架已验收**（M1）；**Phase 1 MVP 核心已完成**（M2）；**可分发 MVP 已完成**（M3）。当前桌面壳 **`1.0.0`**。`apps/` / `packages/` 已落地；按 [setup.md](./setup.md) → [running-locally.md](./running-locally.md) 即可 `pnpm dev`。实现与文档对照见 [implementation-status.md](./implementation-status.md)。下一优先见 [路线图](../planning/03-roadmap.md)（干净机 / 签名 / 公开发布）。

## 推荐阅读顺序

1. [setup.md](./setup.md) — 配置开发环境
2. [running-locally.md](./running-locally.md) — 启动应用与各入口
3. [testing.md](./testing.md) — 运行测试与 mock 约定

## 与相邻文档的分工

| 目录 | 回答的问题 |
|------|------------|
| [docs/planning/](../planning/README.md) | 产品范围与 MVP 边界、路线图 |
| [docs/architecture/](../architecture/README.md) | 架构、模块边界、ADR |
| [docs/api/](../api/README.md) | HTTP 端点与 OpenAPI |
| [docs/cli-mcp.md](../cli-mcp.md) | CLI 命令与 MCP tool 契约 |
| [docs/user/](../user/README.md) | 终端用户使用说明 |
| **docs/dev/**（本目录） | 开发者如何搭建、运行、测试 |
