# 开发环境搭建

> **职责划分**：
>
> | 工具 | 负责 | 不负责 |
> |------|------|--------|
> | **uv** | Python **解释器**（`.python-version`）、项目 **`.venv`**、依赖锁（`uv.lock`）、`uv sync` / `uv run` | Node / Rust |
> | **pnpm** | Node 包依赖 | — |
>
> 不用 pip 直接装业务依赖；不用 Miniconda / conda；不用 npm / yarn。Agent 侧约束见 [AGENTS.md](../../AGENTS.md)。

**状态**：Phase 0（M1）脚手架与 Phase 1（M2）MVP 核心已完成；以下命令可直接使用。

## 锁定版本

Phase 0 起，开发环境与 CI 对齐以下版本（小版本补丁可随安全更新浮动，大版本变更须同步本文档）：

| 工具 | 锁定版本 |
|------|----------|
| Python（由 uv 管理） | **3.12.13**（见根目录 `.python-version`） |
| [uv](https://docs.astral.sh/uv/) | **0.11.28** |
| [Node.js](https://nodejs.org/) | **24.18.0** LTS |
| [pnpm](https://pnpm.io/) | **11.15.0** |
| [Rust](https://www.rust-lang.org/tools/install) | **1.97.0**（`stable` 通道） |

## 前置依赖

| 工具 | 用途 | 版本 |
|------|------|------|
| [uv](https://docs.astral.sh/uv/) | Python 解释器、虚拟环境、包依赖与脚本入口 | **0.11.28** |
| [Node.js](https://nodejs.org/) | 前端与 Tauri 构建 | **24.18.0** LTS |
| [pnpm](https://pnpm.io/) | Node 包管理 | **11.15.0** |
| [Rust](https://www.rust-lang.org/tools/install) | Tauri 2 桌面壳构建 | **1.97.0**（`stable`）；满足 [Tauri 2 前置要求](https://v2.tauri.app/start/prerequisites/) |
| Windows 额外 | Tauri 桌面构建 | [WebView2](https://developer.microsoft.com/microsoft-edge/webview2/)（Win10/11 通常已预装） |

**主开发平台（Phase 0）**：**Windows**。Phase 0 验收以 Windows 为准。

macOS / Linux 可作为开发环境尝试，但以下项为 **ADR 占位**，跨平台验证后再补全文档与实现：

| 项 | 状态 |
|----|------|
| SQLite 路径（`default_config_path()`） | Windows 已定稿；macOS / Linux 见 [ADR-004](../architecture/adr/004-sqlite-user-settings.md) |
| Tauri 构建与 WebView 前置 | 待验证 |
| 本地运行说明 | [running-locally.md](./running-locally.md) 以 Windows 为例 |

## 克隆与目录

```bash
git clone <repository-url> SentRealm
cd SentRealm
```

目标仓库结构见 [多入口模块化架构](../architecture/modules.md)。

## Python 环境与依赖

**一步完成**：uv 按 `.python-version` 准备解释器，在仓库根创建 `.venv` 并同步依赖。

```bash
# 安装 uv（若尚未安装）：https://docs.astral.sh/uv/getting-started/installation/
uv sync
```

| 项 | 约定 |
|----|------|
| Python 版本 | **3.12.13**（`.python-version` + `pyproject.toml` `requires-python`） |
| 虚拟环境 | 仓库根 **`.venv/`**（`uv sync` 创建；不入 git） |
| 依赖安装 / 更新 | `uv sync`（读 `uv.lock`） |
| 运行入口 | `uv run <命令>`（或 IDE 选用 `.venv` 解释器） |
| 可编辑包 | `sentrealm-core`、`sentrealm-cli`、`sentrealm-mcp`（Phase 0 起） |

> 日常 Python 命令优先 `uv run …`，确保使用项目 `.venv` 与锁文件版本。Tauri spawn 后端同样走 `uv run uvicorn …`（见 [ADR-006](../architecture/adr/006-tauri-spawn-fastapi.md)）。

选型背景见 [ADR-011](../architecture/adr/011-uv-python-environment.md)。

## Node 依赖

```bash
# 安装前端与 Tauri 相关依赖
pnpm install
```

> 若 `pnpm install` 提示 `Ignored build scripts: esbuild`，在仓库根执行 `pnpm approve-builds --all` 后重试。

工作区包含 `apps/gui`（见 `pnpm-workspace.yaml`）。根 `package.json` 含 `"packageManager": "pnpm@11.15.0"`。

## 环境变量

复制根目录 `.env.example` 为 `.env`（**勿提交 git**）：

```bash
# Windows PowerShell
Copy-Item .env.example .env
```

| 变量 | 说明 |
|------|------|
| `SENTREALM_LLM_API_KEY` | LLM API 密钥；Phase 0 可不配置；Phase 1 集成测试时需要 |

密钥与 endpoint/model 分工见 [ADR-004](../architecture/adr/004-sqlite-user-settings.md)、[ADR-005](../architecture/adr/005-llm-integration-privacy.md)。

## 验证

首次安装或环境变更后，逐项确认：

```bash
uv sync
uv run python --version
uv run python -c "import sentrealm_core; print('ok')"
uv run pytest --version

# Node
pnpm --version
node --version

# Rust / Tauri（在 apps/gui 初始化后）
rustc --version
cd apps/gui && pnpm exec tauri --version
```

| 检查项 | 期望 |
|--------|------|
| `uv run python --version` | `Python 3.12.13` |
| `uv --version` | `0.11.28` |
| `node --version` | `v24.18.0` |
| `pnpm --version` | `11.15.0` |
| `rustc --version` | `1.97.0`（stable） |
| `uv sync` | 无报错；`.venv/` 已创建 |
| `uv run pytest` | 可执行（Phase 0 起有测试用例） |
| `pnpm install` | `apps/gui` 依赖安装完成 |
| WebView2（Windows） | 系统已安装，Tauri 可启动 WebView |

## 相关文档

- [本地运行](./running-locally.md)
- [测试](./testing.md)
- [ADR-006：Tauri spawn FastAPI](../architecture/adr/006-tauri-spawn-fastapi.md)
- [ADR-011：uv 管理 Python 环境](../architecture/adr/011-uv-python-environment.md)
