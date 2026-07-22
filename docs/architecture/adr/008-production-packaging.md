# ADR-008: 生产打包（PyInstaller sidecar）

## 状态

已接受

## 背景

[ADR-006](./006-tauri-spawn-fastapi.md) 规定开发与生产采用同一进程模型：由 Tauri spawn 并管理 FastAPI 子进程。开发环境通过 `uv sync` + `uv run uvicorn ...` 启动；**终端用户安装包不能依赖本机 uv / Python**。

[路线图 M3](../../planning/03-roadmap.md)（可分发 MVP / `1.0.0`）要求：干净 Windows 上安装即可完成主流程。需选定如何把 `apps/gui/api`（及其所依赖的 `sentrealm_core`）打进 Tauri 安装包，并明确与开发 spawn 的差异。

触发条件已满足：Phase 1 MVP 核心完成；准备 `pnpm build` / `tauri build` 安装包。

## 选项

### A. PyInstaller 打成 sidecar 可执行文件（本决策选中）

用 PyInstaller（或等价）将 FastAPI 入口打成单文件/目录式可执行文件；Tauri 2 通过 `bundle.externalBin` 嵌入，生产环境用 `shell().sidecar(...)` spawn；仍监听 `127.0.0.1:17300`，就绪检查逻辑与开发一致。

- 优点：与 [Tauri 2 Embedding External Binaries](https://v2.tauri.app/develop/sidecar/) 官方路径一致；用户无需安装 Python；开发/生产均为「壳 + 独立后端进程 + 本地 HTTP」，边界清晰
- 缺点：安装包体积增大；需维护 `.spec` 与 hiddenimports；PyInstaller onefile 在 Windows 上杀进程时注意 bootloader 与子进程关系；每次后端变更需重打 sidecar

### B. 安装包内嵌完整 Python venv

安装目录携带 CPython + site-packages，Tauri spawn `python -m uvicorn ...`。

- 优点：更接近开发体验；改依赖有时不必重打「整棵解释器」若做成可替换目录
- 缺点：体积通常更大；路径/权限/杀软更敏感；与「不要求用户懂 Python」心智仍接近，但运维面更宽；非 Tauri 一等公民模式

### C. PyO3 / 内嵌解释器于 Rust 同进程

- 优点：无第二进程
- 缺点：与 ADR-006 已选子进程模型冲突；调试与 FastAPI/uvicorn 生态脱节；否决

### D. 安装时联网下载 Python 运行时

- 优点：安装包本体小
- 缺点：离线不可用、供应链与失败面大；否决（MVP）

## 决策

采用 **选项 A：PyInstaller（或团队等价工具）打包 FastAPI 后端为 Tauri sidecar**。

### 范围（首发 Windows x64）

| 项 | 约定 |
|----|------|
| 目标平台 | Windows 10/11 **x86_64**（`x86_64-pc-windows-msvc`）；macOS/Linux 打包另议 |
| Sidecar 名 | 建议 `sentrealm-api`（具体以 `tauri.conf.json` `externalBin` 为准） |
| 二进制命名 | Tauri 要求：`{name}-{TARGET_TRIPLE}.exe`，例如 `sentrealm-api-x86_64-pc-windows-msvc.exe` |
| 放置路径 | `apps/gui/src-tauri/binaries/`（构建产物，默认不入 git，见根 `.gitignore`） |
| 监听 | 生产仍为 `127.0.0.1:17300`；被占用则启动失败（与 ADR-006 一致，暂不自动换端口） |
| 就绪 | 沿用 `GET /health` 轮询（200ms / 30s） |
| 配置与文稿 | 仍写用户目录：`%APPDATA%/SentRealm/settings.db`、`Documents/SentRealm/`；不打进安装包 |
| 密钥 | 仍仅环境变量 / 用户本机配置；安装包**不**内置 API key |
| cli / mcp | **不**随桌面安装包分发（开发者继续用源码 + uv）；桌面 MVP 只交付 gui |

### 开发 vs 生产 spawn

| | 开发 | 生产 |
|--|------|------|
| 后端启动 | `uv run uvicorn apps.gui.api.main:app --host 127.0.0.1 --port 17300`（`uv sync` 后） | sidecar 可执行文件（内含解释器与依赖） |
| Python 来源 | uv 项目 `.venv` | PyInstaller 捆绑 |
| 包管理 | uv sync | 打 sidecar 时冻结进产物 |
| 通信 | 本地 HTTP `/api/v1` | 同左 |

Rust 侧应用启动/退出钩子在开发与生产共用生命周期语义；**仅命令与二进制来源分支**（可用 `cfg!(debug_assertions)` 或显式配置）。

### 构建流水线（约定）

1. 在 `uv sync` 后的项目 `.venv` 中：用 PyInstaller + 项目 `.spec` 产出 sidecar（需纳入 `sentrealm_core` 数据文件如 `break_lexicon/`）
2. 复制/重命名到 `src-tauri/binaries/` 带 TARGET_TRIPLE 后缀
3. `pnpm` / `tauri build` 打 NSIS（或 MSI）安装包
4. 干净机冒烟：安装 → 打开 → 处理样例 → 复制；确认退出无残留后端进程

具体脚本路径与 CI 在实现 M3 时落仓库，不在本 ADR 钉死文件名。

### 明确不做（本 ADR）

- 安装包内分发 cli/mcp 入口
- 自动换端口
- 代码签名 / SmartScreen 策略的最终方案（实现阶段补充运维清单；不阻塞架构选型）
- macOS/Linux sidecar 与公证（后续 ADR 或修订本 ADR）

## 后果

### 正面

- 与 ADR-006 进程模型、ADR-003 本地 HTTP、ADR-007 模块边界一致
- 终端用户无需 uv/Python
- 官方 sidecar 文档与社区 FastAPI+Tauri 实践可对齐，降低探索成本

### 负面

- 需维护 PyInstaller spec、体积与杀软误报风险（路线图已列）
- 后端每次发版多一步「打 sidecar」
- onefile 模式下结束进程需按 PyInstaller 特性验证（避免残留）
- 开发机仍双轨（uv 开发 vs 偶发本地验证 sidecar）

### 后续工作

- 实现：`.spec`、binaries 构建脚本、Rust 生产分支、`tauri.conf.json` `externalBin`
- 文档：更新 [用户手册](../../user/README.md) 分发状态与安装步骤；[路线图](../../planning/03-roadmap.md) M3 DoD
- 修订 [ADR-006](./006-tauri-spawn-fastapi.md)「生产打包待定」指向本文

## 相关文档

- [ADR-006：Tauri 管理 FastAPI 子进程](./006-tauri-spawn-fastapi.md)
- [架构概览](../overview.md)
- [路线图 M3](../../planning/03-roadmap.md)
- [setup.md](../../dev/setup.md)（开发环境为 uv，见 [ADR-011](./011-uv-python-environment.md)）
- Tauri 2：[Embedding External Binaries](https://v2.tauri.app/develop/sidecar/)
