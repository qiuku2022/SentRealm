# ADR-011: uv 管理 Python 开发环境

## 状态

已接受

## 背景

Phase 0–1 曾采用 **Miniconda 提供 Python 解释器 + uv 管理 pip 依赖** 的双工具模型（见历史 [setup.md](../../dev/setup.md) 与 [CHANGELOG.md](../../../CHANGELOG.md)）。实践中出现：

- IDE F5 与终端 `pnpm dev` 环境不一致（conda 未激活时 uv 会在项目根另建 `.venv`）
- 开发者需维护 conda 环境名、`conda activate` 与 uv 两套心智
- Tauri spawn、`uv run`、debugpy 对「当前 Python 来自哪里」的假设容易分叉

项目已统一为 **Python 3.12.13**、锁文件 **`uv.lock`**、入口 **`uv run`**；uv 0.11+ 可一并管理解释器与项目 `.venv`。

## 选项

### A. 维持 Miniconda + uv（原方案）

- 优点：conda 生态成熟、与科学计算栈兼容
- 缺点：双工具；文档与 IDE 配置复杂；易出现 conda / `.venv` 两套 Python

### B. 仅用 pip + venv

- 优点：无额外工具
- 缺点：无等价 `uv.lock` 体验；与现有 `uv.lock`、ADR-009 workspace 规划不一致

### C. 仅用 uv（本决策选中）

- 解释器：`.python-version`（3.12.13）
- 环境：仓库根 `.venv/`（`uv sync`）
- 运行：`uv run`；Tauri 开发 spawn 仍为 `uv run uvicorn …`
- 优点：单一工具链；锁文件与运行环境一致；IDE 指向 `${workspaceFolder}/.venv`
- 缺点：团队须安装 uv；放弃 conda 特有包（本项目 MVP 无此需求）

## 决策

采用 **选项 C**。开发机 **不再要求 Miniconda / conda**。

| 项 | 约定 |
|----|------|
| Python 版本 | **3.12.13**（`.python-version`） |
| 虚拟环境 | 仓库根 `.venv/`（gitignore） |
| 依赖同步 | `uv sync` |
| 命令入口 | `uv run pytest` / `uv run sentrealm` / `uv run uvicorn` 等 |
| IDE | `.vscode/settings.json` → `${workspaceFolder}/.venv/Scripts/python.exe`（Windows） |
| IDE 断点 | compound 启动 `Python: FastAPI` + `Desktop: pnpm dev（断点模式）`；Tauri 设 `SENTREALM_SKIP_BACKEND_SPAWN=1`（见 [running-locally.md](../../dev/running-locally.md)） |

**生产打包**不变：终端用户仍不依赖 uv（[ADR-008](./008-production-packaging.md) PyInstaller sidecar）。

## 后果

### 正面

- 一条命令 `uv sync` 完成环境
- F5、Tauri spawn、CLI/MCP、测试共用同一 `.venv`
- 与 ADR-009（uv workspace 物理拆包）方向一致

### 负面

- 需迁移文档与 AGENTS 约定；已有 conda 用户须改用 uv
- sidecar 构建流水线改为在 `uv sync` 后的 `.venv` 内执行 PyInstaller（实现 M3 时落实）

## 相关文档

- [setup.md](../../dev/setup.md)
- [running-locally.md](../../dev/running-locally.md)
- [ADR-006：Tauri spawn FastAPI](./006-tauri-spawn-fastapi.md)
- [ADR-008：生产打包](./008-production-packaging.md)
