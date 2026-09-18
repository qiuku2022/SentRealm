# 实现对照状态

> 对照 docs 与仓库**实际代码树**的快照说明。不替代 ADR / 产品定义。进度与下一优先以 [路线图](../planning/03-roadmap.md) 为准。

**核对日期**：2026-09-18  
**工作区根**：`d:\Work\Dev\SentRealm`  
**当前版本**：桌面壳 `1.0.0`（`apps/gui/src-tauri/tauri.conf.json`）

## 结论

**M1 / M2 / M3 已完成。** 桌面壳 **`1.0.0`**。M3 于 2026-09-18 以作者工作环境多次 NSIS 验证关闭。GitHub Releases 已发未签名安装包。正式发版仍待：严格干净机冒烟、代码签名。用户手册安装/分发表述已指向 Releases。ADR-009 物理拆包仍延后。

**流水线已对齐文档**：标点分级（硬边界 / 超长候选 / 仅删除）→ 空格 → 自然边界规则断句（全局选点、短行回并、出厂词表 v3，ADR-012）→ LLM 发送池（可选）→ 标记。发送池：规则后仍超长行入池 → 每批 ≤10 调用 `break_lines` → 硬质检（守恒 + 有效切分 + 有进展）+ 超长/过短软返工 → 合格写回并短行回并；写回后仍长度不合规则祖先整句第二波（最多 2 次，失败保留第一波）；满 3 次硬失败则保留原文并由 `flag_overlength_lines` 标记。见 [产品定义](../planning/01-product-definition-and-mvp.md#llm-发送池与质检返工) 与 [ADR-005](../architecture/adr/005-llm-integration-privacy.md)。

目录 `packages/{core,cli,mcp}`、`apps/gui/{src,src-tauri,api}` **已落地**。默认 `uv run pytest` **164 passed**（本核对日）。

本机笔记目录 `.local/` 已 gitignore，仓库不保证存在。

## Phase 1（M2）进度

| 节 | 状态 | 说明 |
|----|------|------|
| §0 前提 | 完成 | P0 基线绿；范围确认 |
| §1 流水线 1–3 | 完成 | `punctuation` / `whitespace` / `line_count` |
| §2 词表 + 规则断句 | 完成 | `break_lexicon/` + Settings 持久化 + FAB Modal；`rule_break` 自然候选边界全局选点；`short_line_repair` 局部回并 |
| §3 LLM + 标记 | 完成 | 发送池 / `llm_quality_ok` / `break_lines` / 语义质检返工 / `flag_lines` |
| §4 编排 + 三入口 | 完成 | `preprocess()`；gui/cli/mcp 一致 |
| §5 工作区 | 完成 | ADR-010 |
| §6 GUI 核心 | 完成 | 三栏主路径；Wave A/B；词表 Modal；SSE；导出 |
| §7 验收 | 完成 | 默认 pytest 绿；剪映粘贴建议本机手工抽样 |

## M3 已完成 / 正式 1.0.0 仍待

| 项 | 状态 |
|----|------|
| ADR-008 安装包链路 | ✅ `scripts/build_installer.ps1`：onedir sidecar → `resources/sentrealm-api/` → NSIS |
| 开发构建 | ✅ `src-tauri/build.rs` 为 `bundle.resources` 自动建空占位目录；`pnpm dev` 走 `uv run uvicorn` |
| 生产启动 / 退出 | ✅ 窗口首帧不阻塞 `/health`（前端 `waitForHealth`）；onedir 单进程退出；sidecar 无控制台；CORS 允许 `https://tauri.localhost` |
| 桌面壳 | ✅ 默认窗口 `1440×900`；品牌图标（含 0.5.1/0.5.2 圆角）；无启动动画 |
| 作者侧 NSIS 日常验收 | ✅ 约 1 个月工作环境使用，并多次复测；主流程与断句质量作者侧满意（M3 于 2026-09-18 关闭） |
| 干净机冒烟 | 未做（清单见 [packaging.md](./packaging.md)；阻塞正式 1.0） |
| 代码签名 / 正式公开发布 | GitHub Releases 已发 `1.0.0`（未签名）；代码签名未做 |
| 用户手册安装 / 分发表述 | ✅ 2026-09-15 已改写为内部 NSIS 可用 |

## 已存在（core / API）

| 路径 | 说明 |
|------|------|
| `pipeline/punctuation.py` 等 8 步 | 编排在 `pipeline/preprocess.py` |
| `pipeline/llm_quality.py` | `min_chars_for` / `quality_ok` / `llm_quality_ok` / 软码 `still_overlength`·`too_short` |
| `pipeline/llm_break.py` | 发送池编排、批 ≤10、终态进度 |
| `llm.py` | `LlmClient.break_lines`；Mock / OpenAI 批解析；`is_llm_configured` |
| `store/workspace_store.py` | 工作区 JSON（`Documents/SentRealm/`） |
| `GET /health`、`GET/PUT /api/v1/settings` | 健康检查与 Settings |
| `POST /api/v1/preprocess`、`/preprocess/stream` | 同步处理；SSE 中间进度（GUI 实时预览） |
| `GET /api/v1/break-lexicon/defaults` | 内置词表默认 |
| `GET /api/v1/settings/llm-key-status`、`POST …/llm-test` | 密钥是否配置；处理前连通性预检 |
| `/api/v1/workspace`、`/projects`、`/documents` | 工作区 CRUD / 导出 |
| `tests/test_pipeline_*.py`、`test_llm.py`、`test_api*.py` | 质检 / 池 / 返工 / HTTP / 工作区 |

## 已存在（GUI）

主入口 `AppShell`（`Phase0Shell` 为遗留调试页，非主路径）。

| 能力 | 说明 |
|------|------|
| 三栏壳 | OD Wave A/B：输入 / 侧栏 / 结果；设置去标点与保留列表（默认 `%` `.`）；侧栏搜索/折叠/重命名删除；快捷键；分型错误 Banner |
| 断句词表编辑 | `Settings.break_lexicon` + `RulesEditorModal` |
| 结果栏 | 行号、字数、分栏统计；SSE 渐进刷新；导出 `.txt`；点击行定位原文并脉冲高亮 |
| LLM | 启用时处理前预检失败不进入 running；meta-bar「LLM 未配置」提示 |
| 启动与外观 | `waitForHealth`；微软雅黑；侧栏无顶栏品牌块（应用名在窗口标题） |
| 用户可见说明 | [用户手册](../user/README.md)；HTTP 契约见 [api/README](../api/README.md) |

## 仍缺失 / 延后

| 项 | 去向 |
|----|------|
| 干净机冒烟、签名 | 路线图正式 `1.0.0` 剩余项；GitHub 已发未签名包 |
| uv workspace 物理拆包 | ADR-009 |
| 词表穷尽真实语料 | 持续迭代 |
| 剪映粘贴「大致可用」正式 sign-off | 作者侧日常已满意；严格干净机 / 对外发布前可再抽样 |

## 已核对项（§7）

1. **stub 语义已移除**：完整 8 步；三入口一致测试通过
2. **无密钥规则路径**：`llm_enabled=false` 时去标点 + 规则 + 标记可用
3. **LLM 发送池**：`is_llm_configured` + 批 ≤10 + 硬质检（守恒 / 有效切分 / 有进展）+ 超长/过短软返工 + 写回短行回并 + 长度不合规祖先第二波；第一波最多 3 次、第二波最多 2 次；Mock 注入；integration 默认不跑
4. **模块边界**：core 无 FastAPI/cli/mcp 依赖；React 仅 HTTP
5. **Settings 共用**：SQLite @ `%APPDATA%/SentRealm/settings.db`
6. **工作区**：`Documents/SentRealm/`；cli/mcp 不接入
7. **GUI 文案**：与用户手册主路径一致；SSE `llm_current/total` 为终态口径
8. **安装包**：脚本与 sidecar 资源路径在仓库内；作者侧 NSIS 多次验证已覆盖主流程（M3 关闭）；本核对日未在严格干净机重跑 packaging 清单

## 本机执行面

下一优先：干净机冒烟、代码签名。桌面壳版本已为 `1.0.0`，GitHub Releases 已发未签名安装包。

## 相关文档

- [testing.md](./testing.md)
- [packaging.md](./packaging.md)
- [路线图](../planning/03-roadmap.md)
- [modules.md](../architecture/modules.md)
