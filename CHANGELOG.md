# Changelog

本文档记录 SentRealm **对用户与协作者有意义的变更**。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。  
在首次公开发布（`1.0.0`）之前，`0.x` 对应内部里程碑：**0.1.x ≈ Phase 0（M1）**，**0.2.x ≈ Phase 1（M2）**。

产品范围与能力边界以 [产品定义与 MVP](./docs/planning/01-product-definition-and-mvp.md) 为准；阶段规划见 [路线图](./docs/planning/03-roadmap.md)。

---

## [Unreleased]

---

## [0.5.1] - 2026-08-10 — M3 内部构建

### Changed

- **品牌图标**：按 Windows 11 窗口圆角规范（8px @ 96 DPI）重新裁切圆角并生成全套桌面 / 安装包 / 侧栏图标；小尺寸（32×32）圆角加强至 12px@48px 等效，避免桌面快捷方式仍显示为方角

---

## [0.5.0] - 2026-08-09 — M3 内部构建

### Changed

- **品牌图标**：桌面程序、安装包、浏览器页签与应用侧栏统一使用新版圆角 SentRealm 图标
- **桌面窗口**：默认尺寸由 `1280×800` 调整为 `1440×900`，首次打开时提供更宽裕的编辑空间
- **LLM 断句最短行长**：提示词与质检现均使用 `min_chars`；低于设置值的碎句不再写回，并进入既有的最多 3 次返工流程
- **出厂断句词表 v3**：保留四类可编辑结构，默认内容收敛为高置信度通用切点；移除 `的/地/得/了/有/在/找/非常` 等易受上下文影响的切点，规则无法可靠切分的超长行交由已启用的 LLM（已有 SQLite 自定义配置不自动覆盖）
- **安装包 sidecar 改为 PyInstaller onedir**：经 `bundle.resources` 嵌入 `sentrealm-api/`，避免 onefile 每次解压 `%TEMP%\_MEI*`，缩短冷启动与退出（见 [packaging.md](./docs/dev/packaging.md)）
- **生产退出**：不再调用会弹黑框的 `taskkill`，改为直接终止 onedir 单进程；sidecar 改为无控制台子系统，避免启动闪窗
- **启动体验**：Rust `setup` 不再同步等待 `/health`，窗口可立即绘制；就绪改由前端 `waitForHealth` +「启动中」提示承接

### Fixed

- **保留标点**：默认改为 `%` 与 `.`，避免小数和模型版本号被拆开；保留列表优先于去除列表，GUI 支持按单个字符编辑并提供主题一致的「恢复默认」按钮
- **安装包无法连接后端**：生产 WebView 源为 `https://tauri.localhost`，原先 CORS 仅允许 Vite `1420` 且 sidecar 关闭了 CORS，导致 `fetch /health` 一直失败
- **安装包后端未监听**：PyInstaller windowed sidecar 不再初始化依赖控制台流的 Uvicorn 默认日志，避免进程停在启动阶段而未监听 17300

### Added

- **启动动画**：桌面应用启动时播放 SentRealm 品牌动画；播放失败或超时自动进入主界面，并遵循系统“减少动态效果”设置
- **Windows 安装包构建**（ADR-008）：PyInstaller sidecar + Tauri NSIS；`pwsh -File scripts/build_installer.ps1`（见 [packaging.md](./docs/dev/packaging.md)）
- GUI（OD Wave A）：设置中可开关「去除标点」并编辑保留标点列表（US-11）
- GUI：后端不可达、启动中、处理失败等分型错误提示条（可关闭，不伪造 health 状态）
- GUI：结果栏行号、每行字数、分栏统计；导出 `.txt`（默认写入当前文稿目录，亦可另选路径）
- GUI：FAB 预设 popover、处理耗时、done 态「重新处理」；编辑器 meta-bar 显示 LLM 未配置提示
- GUI（OD Wave B）：侧栏搜索、折叠、文稿重命名/删除确认、空态；快捷键 `Ctrl+,` 开设置、`/` 聚焦搜索
- GUI：窄屏结果栏抽屉与桌面收起右栏；处理完成后窄屏自动打开结果预览
- GUI：启用 LLM 断句时，「处理文稿」前预检 LLM 连通性；失败弹窗提示
- GUI：处理过程中右栏实时刷新断句结果（SSE 流式）
- HTTP：`GET /api/v1/break-lexicon/defaults` 读取内置断句词表默认
- GUI：FAB「编辑规则」打开断句词表 Modal（左四类 / 右编辑；恢复默认、保存至 Settings）
- HTTP：`POST /api/v1/preprocess/stream` SSE 推送 preprocess 中间进度

### Fixed

- GUI：禁用 WebView 默认右键菜单（非产品功能）
- **开发启动**：避开损坏的 `pnpm@11.12.0`（`@pnpm/exe` 无二进制），锁定改为 `pnpm@11.15.0`，恢复 `pnpm dev` / F5
- **LLM 连通性预检**：`ping` 改为轻量 `max_tokens=1` 请求，不再走完整断句 prompt，避免 Qwen 等思考模型在 10s 内误报超时
- **LLM 断句**：请求增加 `max_tokens` 上限与 `enable_thinking: false` 提示，降低思考模型无限生成导致超时 / 空 `content` 的概率
- **LLM 断句**：修复响应解析——兼容无 `###` 编号的多行输出与行尾 `### N`；OpenAI 客户端逐条调用；GUI/CLI 启动时加载 `.env`
- 关闭桌面应用时正确终止 FastAPI 子进程树（Windows 上 `uv run uvicorn` 不再残留占用 17300 端口的 python/uvicorn 进程）

### Changed

- **Python 开发环境**：改为 uv 统一管理解释器（`.python-version`）、`.venv` 与依赖；不再要求 Miniconda / conda（[ADR-011](./docs/architecture/adr/011-uv-python-environment.md)、[setup.md](./docs/dev/setup.md)）
- **IDE 调试**：F5 compound 由 debugpy + `.venv` 提供 uvicorn；Tauri 设 `SENTREALM_SKIP_BACKEND_SPAWN=1` 等待外部 `/health`（见 [running-locally.md](./docs/dev/running-locally.md#ide-调试cursor--vs-code)）
- **实现**：LLM 断句对齐发送池契约——每批 ≤10、`break_lines`、质检（太长/太短/句意守恒）、每行最多 3 次返工后标记（`llm_quality` / `llm_break` / Mock·OpenAI）
- **出厂断句词表 v2**：扩充 `break_lexicon/*.txt`（连接词 / 介词短语 / 助词与受保护词 Tier 1）；新安装与「恢复默认」生效，已有 SQLite 配置不变直至用户保存或恢复默认
- **Settings**：新增 `break_lexicon`（四类字词表，持久化 SQLite）；schema v2 自动迁移；规则断句从 Settings 读取词表
- 规则断句：切分左右段最短字数与 LLM 共用 `min_chars`（不含去标点换行）
- **文档**：LLM 断句契约升级为发送池 + 质检返工；同步产品定义、ADR-005、data-flow、用户手册等
- 规则断句：选点由「左段贪心填满」改为按最少行数均分（`ideal = total / ceil(total / max_chars)` 取最近合法切点），减少一长一短
- GUI：可编辑文稿标题（blur 保存）；处理完成后 FAB 与 meta-bar 信息密度对齐 Open Design
- GUI：结果栏标题改为「处理结果」；超长行标签含「复制前请检查」提示
- GUI：设置 Drawer 增加取消/保存底栏；自定义字数仅在 preset=custom 时显示
- GUI：侧栏列表显示「最近文稿」与相对更新时间；设置按钮显示 `Ctrl ,` 提示

### Added

- Phase 0 脚手架：**§1 目录落位** — `packages/{core,cli,mcp}`、`apps/gui/{src,src-tauri,api}`、根单 `pyproject.toml`、`pnpm-workspace.yaml`
- Phase 0 **§2 core** — `sentrealm_core`：`Settings` / `PreprocessResult`、`SqliteSettingsStore`、`default_config_path()`、`LlmClient` / `MockLlmClient`、`preprocess()` stub；`tests/test_store.py`、`tests/test_preprocess.py`
- Phase 0 **§3 gui/api** — FastAPI @ `127.0.0.1:17300`：`/health`、`/api/v1/settings`、`/api/v1/preprocess`；`tests/test_api.py`
- Phase 0 **§4 cli/mcp** — `sentrealm preprocess`、`sentrealm-mcp`（`preprocess_text`）；`tests/test_cli.py`、`tests/test_mcp.py`
- Phase 0 **§5 gui UI** — Tauri 2 + React + shadcn/ui + Tailwind：`pnpm dev` 一键启动；Rust spawn `uv run uvicorn`（ADR-006）；`get_api_base_url` / `get_backend_startup_error`；Phase 0 调试页（health → settings / preprocess）
- Phase 0 **§6 验收** — `tests/test_phase0_acceptance.py`（三入口共用 SQLite、字段契约）；默认 pytest **37** 项
- Phase 1 **M2 MVP 核心** — 完整 8 步 `preprocess()`、`break_lexicon/` 规则断句、可选 LLM + 超长标记、workspace HTTP（ADR-010）、OD 三栏 `AppShell`；`GET /api/v1/settings/llm-key-status`；默认 pytest **98** 项

### 文档

- 对齐 M2 实现与 OD Wave B / SSE 等：消除「回仓前 / Wave B 未做 / 工作区可选」过时表述；同步用户手册、data-flow 目录树、api 端点一览、UI 状态与 [implementation-status](./docs/dev/implementation-status.md)（默认 pytest **149**）
- 澄清四模块分离：在 [modules.md](./docs/architecture/modules.md) 增补 Phase 0 落地步骤；修正「目录已落地」误述；对齐 [ADR-007](./docs/architecture/adr/007-multi-entry-modules.md) 与 [implementation-status](./docs/dev/implementation-status.md)
- 新增 [docs/ui/](./docs/ui/README.md)：从 Open Design 高保真稿落地 tokens、三栏壳、组件映射与状态机（Tauri + React + shadcn/Tailwind）
- 新增根目录本 Changelog，作为版本变更的单一记录入口
- 新增 [产品路线图](./docs/planning/03-roadmap.md)（里程碑、依赖、风险）
- 新增 [用户使用手册](./docs/user/README.md)（主流程、参数、剪映对接、FAQ）
- 清理文档索引中指向不存在文件的断链（规划占位、`.local/implementation` 等）
- 明确 Miniconda 管 Python 环境、uv 只管包依赖（[setup.md](./docs/dev/setup.md)、[AGENTS.md](./AGENTS.md)）
- 对齐存储边界：SQLite 仅 Settings；gui 文稿见 ADR-010（[overview](./docs/architecture/overview.md)）
- ADR-004/005 补齐 `llm_enabled`，与 API/OpenAPI 启用条件一致
- 开发启动改为 conda-first（ADR-006 / running-locally），不再以 `.venv` 作为 Python 来源
- API README 补工作区约定；Apifox 在线链接改为「待补充（非阻塞）」
- Phase 0 stub / 状态行改为历史或 M1+M2 当前表述（data-flow / testing / running）
- 新增 [用户故事](./docs/planning/02-user-stories.md)
- 新增根 [.gitignore](./.gitignore)、[.env.example](./.env.example)
- 新增并接受 [ADR-008 生产打包](./docs/architecture/adr/008-production-packaging.md)（PyInstaller sidecar）
- 更新 [实现对照状态](./docs/dev/implementation-status.md)（Phase 1 / M2 已落地）

---

## [0.2.0] - 2026-07 — Phase 1 MVP 核心（M2）

> 状态说明：仓库文档将本阶段标为 **已完成**。交付物为可运行的开发构建（`pnpm dev`）；正式 Windows 安装包按 [ADR-008](./docs/architecture/adr/008-production-packaging.md) 实现中（路线图 M3）。

### Added

- **完整 8 步预处理流水线**（`sentrealm_core`）
  - 去标点并在去除位置换行（默认保留 `%` / `％`；规则可配置）
  - 空格规范化（英词间、英中文间等，见产品定义）
  - 多轮字数检测；规则断句（字词表白名单，禁止硬切）
  - 可选 LLM 断句（仅处理规则后仍超长的行；不改写用词）
  - 最终仍超限行进入 `flagged_lines` 标记
- **字词表驱动的规则断句**：`break_lexicon/`（受保护词 / 后可断 / 前可断等）
- **GUI**：对照预览、行数统计、超长行高亮、一键复制；主界面 OD 三栏布局
- **参数**：横屏 15 / 竖屏 10 / 自定义 `max_chars`；去标点保留与去除列表；LLM endpoint / model（密钥走环境变量）
- **多入口一致处理**：gui（HTTP）/ cli（`sentrealm preprocess`）/ mcp（`preprocess_text`）共用 `Settings` 与流水线
- **测试**：流水线黄金样例、字词表、`MockLlmClient`；默认 CI 不跑真实 LLM（`integration` 标记）

### Changed

- Phase 0 的 preprocess **stub** 替换为真实流水线语义；OpenAPI / CLI / MCP 字段结构保持对齐

### Security / Privacy

- 文稿默认本地处理；LLM 仅接收规则断句后仍超长的**少量行**（见 [ADR-005](./docs/architecture/adr/005-llm-integration-privacy.md)）
- API 密钥仅环境变量 `SENTREALM_LLM_API_KEY`，不入 SQLite、不入 git

---

## [0.1.0] - 2026-06 — Phase 0 脚手架（M1）

> 状态说明：脚手架与契约已验收；流水线在本阶段可为 stub，但 HTTP / CLI / MCP **字段契约**已对齐。

### Added

- **仓库与模块骨架**：`packages/core`、`packages/cli`、`packages/mcp`、`apps/gui`（Tauri 2 + React + FastAPI）
- **进程模型**：Tauri spawn FastAPI（`127.0.0.1:17300`），`GET /health` 就绪检查（[ADR-006](./docs/architecture/adr/006-tauri-spawn-fastapi.md)）
- **本地 HTTP API**：`/api/v1/settings`、`/api/v1/preprocess` 及 OpenAPI（[ADR-003](./docs/architecture/adr/003-local-http-decoupling.md)）
- **SQLite 用户配置**：gui / cli / mcp 共用 `%APPDATA%/SentRealm/settings.db`（Windows）（[ADR-004](./docs/architecture/adr/004-sqlite-user-settings.md)）
- **CLI**：`sentrealm preprocess`（`-i` / `-o` / `--stdin` / `--preset` / `--max-chars`）；stdout 正文 + stderr JSON 元数据
- **MCP**：stdio server，`preprocess_text` tool
- **前端基础**：shadcn/ui + Tailwind（[ADR-002](./docs/architecture/adr/002-shadcn-ui.md)）；桌面壳 Tauri 2（[ADR-001](./docs/architecture/adr/001-tauri-desktop-shell.md)）
- **开发文档**：setup / running-locally / testing；架构概览、模块、数据流与首批 ADR
- **产品定义**：MVP 范围、处理规则、断句流程与成功标准

### Notes

- Phase 0 验收以 **Windows** 为主平台；macOS / Linux 路径与打包为后续占位

---

## 版本对照

| 版本 | 内部里程碑 | 一句话 |
|------|------------|--------|
| `0.1.0` | Phase 0 / M1 | 能跑通三入口与契约，流水线可 stub |
| `0.2.0` | Phase 1 / M2 | 完整断句流水线 + MVP GUI 核心体验 |
| `0.5.0` | M3 内部构建 | Windows NSIS 安装包；公开发布与签名仍待完成 |
| `0.5.1` | M3 内部构建 | 品牌图标圆角裁切与全套平台图标更新 |
| `Unreleased` | — | 后续未发布变更 |
| `1.0.0`（计划） | 首个安装包发布 | 见 [路线图](./docs/planning/03-roadmap.md) |

---

## 维护约定

1. **有用户可见变更就写**：功能、破坏性变更、安全修复、重要文档入口；纯内部重构可省略或并入 Changed 一句。
2. **发版时**：把 `[Unreleased]` 下条目移到新版本号，并写上日期 `YYYY-MM-DD`。
3. **分类**：`Added` / `Changed` / `Deprecated` / `Removed` / `Fixed` / `Security`；文档类可用 `### 文档`。
4. **不写**：密钥、未合并实验、与用户无关的琐碎 commit 列表。
