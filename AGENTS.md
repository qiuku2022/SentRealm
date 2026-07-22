# SentRealm — Agent Instructions

AI Agent **协作约定**（行为与边界）。产品范围、架构、API、命令、用户说明等**不以本文为准**——见下方 [事实来源](#事实来源ssot)；**能引用对应 docs 就不在此重复细节**。

**优先级**：用户指令 > 本文件 > 仓库内嵌套 `AGENTS.md`（若有）。

**项目一句话**：面向视频创作者的本地文稿预处理桌面工具（剪映「文稿匹配」前去标点、断句分行）；形态为 Tauri 2 + React + FastAPI，另有 cli / mcp 入口。当前阶段与下一步见 [路线图](./docs/planning/03-roadmap.md)。

---

## 事实来源（SSOT）

冲突时以对应文档为准。

| 类别 | 问题 | 读哪里 |
|------|------|--------|
| 产品 | 做什么 / 不做 / 处理规则 | [产品定义与 MVP](./docs/planning/01-product-definition-and-mvp.md) |
| 产品 | 用户故事 / 验收场景 | [02-user-stories.md](./docs/planning/02-user-stories.md) |
| 产品 | 终端用户怎么用 | [用户手册](./docs/user/README.md) |
| 架构 | 分层、进程与通信 | [架构概览](./docs/architecture/overview.md) |
| 架构 | 模块职责与依赖铁律 | [modules.md](./docs/architecture/modules.md) |
| 架构 | 流水线步骤、隐私边界 | [data-flow.md](./docs/architecture/data-flow.md) |
| 架构 | 为何选某技术 | [docs/architecture/adr/](./docs/architecture/adr/)（已接受 ADR；生产打包见 [ADR-008](./docs/architecture/adr/008-production-packaging.md)） |
| 契约 | HTTP | [docs/api/README.md](./docs/api/README.md) + [openapi.yaml](./docs/api/openapi.yaml) |
| 契约 | CLI / MCP | [docs/cli-mcp.md](./docs/cli-mcp.md) |
| 开发 | 环境、安装、运行、测试 | [docs/dev/](./docs/dev/README.md)（[setup](./docs/dev/setup.md) / [running](./docs/dev/running-locally.md) / [testing](./docs/dev/testing.md)） |
| 开发 | 本工作区是否有完整代码 | [implementation-status.md](./docs/dev/implementation-status.md) |
| UI | GUI / token 与组件落地 | [docs/ui/](./docs/ui/README.md)（视觉源自 Open Design；选型见 [ADR-002](./docs/architecture/adr/002-shadcn-ui.md)） |
| 变更 | 版本上改了什么 | [CHANGELOG.md](./CHANGELOG.md) |
| 索引 | 文档总览 | [README.md](./README.md) |

**技术栈与锁定版本**在 [setup.md](./docs/dev/setup.md) 与根 [README.md](./README.md)，**不在**本文件维护。主开发平台为 **Windows**。

---

## 行为准则

**严谨** — 不猜不编；不确定说清缺什么；结论先行，论证跟上。

**先搜后答** — 本地（代码 / docs / 命令输出）→ 需要外部版本或资料时再用 Tavily（`tavily_search` / `tavily_research`）→ 综合判断。搜到的命令能跑就验证。

**思考** — 拆解问题，先思路后答案；复杂时说清推理。

**沟通** — 简体中文（注释、commit message、项目文档）；标识符 / 命令 / 路径用英文；少废话，长文结构化。

**边界** — 能查的不问；读文件 / 搜索 / 本地验证大胆做；**commit / push / 部署**仅在用户明确要求时做。

**判断** — 有偏好说理由；用户定稿后执行。

---

## 项目约束

### 改动范围

- **最小改动** — 只改任务相关文件；不顺手重构、不扩 scope、不批量写未请求的 md。
- **不从其他项目抄架构** — 模块边界与选型以本仓库 ADR / modules 为准。

### 包管理与环境

- **Python 环境**：**uv**（解释器 `.python-version`、项目 `.venv`、`uv sync`、锁文件 `uv.lock`、`uv run` 入口）；不用 Miniconda / conda；不用 pip 直接装业务依赖。
- **Node 依赖**：**pnpm**；不用 npm / yarn。
- 开发 Python 命令用 **`uv run …`** 或 IDE 选用 `.venv` 解释器（细则见 [setup.md](./docs/dev/setup.md)）。

### 模块与契约（摘要，细则见 docs）

- 业务断句逻辑只在 **`packages/core`**；`gui/api` 为薄 HTTP 层；cli / mcp **直连 core**，不经 gui HTTP（细则见 [modules.md](./docs/architecture/modules.md)；脚手架回仓时再看同文「Phase 0 落地步骤」）。
- 改 HTTP：同步 [openapi.yaml](./docs/api/openapi.yaml) 与 [docs/api/README.md](./docs/api/README.md)。
- 改 CLI / MCP 行为：同步 [docs/cli-mcp.md](./docs/cli-mcp.md)。
- 改产品规则 / 范围：同步 [产品定义](./docs/planning/01-product-definition-and-mvp.md)；用户可见用法同步 [用户手册](./docs/user/README.md)。
- 架构或选型变更：更新对应主文档与 ADR（见 [架构维护约定](./docs/architecture/README.md#维护约定)）。
- 用户可见功能变更：写入 [CHANGELOG.md](./CHANGELOG.md) 的 `[Unreleased]`（或发版小节）。

### LLM 与密钥

- 测试默认注入 **`MockLlmClient`**，不访问真实网络；无「全局 mock 环境变量」开关（[testing.md](./docs/dev/testing.md)、[ADR-005](./docs/architecture/adr/005-llm-integration-privacy.md)）。
- 密钥仅环境变量 **`SENTREALM_LLM_API_KEY`**；不硬编码、不入 SQLite、不提交。
- 默认 `uv run pytest` **不**跑 `@pytest.mark.integration`。

### 提交

- 仅用户明确要求时 commit / push。
- **commit message 信息全用中文**（标题与正文均是；专有名词 / 路径 / 命令可保留原文），说清 **why**，不写英文 Conventional Commits 式前缀（如 `feat:` / `fix:`）。
- 不 force push `main`；不 skip hooks（除非用户明确要求）。

---

## 完成前

按任务触及面核对（详见 [testing.md](./docs/dev/testing.md)）：

1. 相关测试通过；至少默认集 **`uv run pytest`**（勿把未配置密钥的 integration 当成必过项）。
2. 若改了 API / CLI / MCP / 产品规则 / 用户流程：对应 **docs 与 CHANGELOG** 已同步。
3. 无 secrets、无临时调试残留（硬编码密钥、丢弃用的 print/日志开关等）。

---

## 维护

- **改 Agent 行为 / 本约定** → 改本文件。
- **改产品 / 架构 / API / 命令 / 用户说明 / 开发流程** → 改对应 docs，细节不抄进 AGENTS.md。
- Cursor 项目技能在 `.cursor/skills/`；若新增面向 Agent 的文件规则，放 `.cursor/rules/*.mdc` 并在此提及入口（当前以本文件 + docs 为主）。
