# 实现对照状态

> 对照 docs 与仓库**实际代码树**的快照说明。不替代 ADR / 产品定义。

**核对日期**：2026-07-21  
**工作区根**：`d:\Work\SentRealm`

## 结论

**LLM 发送池契约已落地**：规则后仍超长行入池 → 每批 ≤10 调用 `break_lines` → 语义质检（`llm_quality_ok`：守恒 + 有效切分 + 有进展 + 每段 `≥ min_chars`）→ 不合格回池最多 3 次 → 放弃保留原文并由 `flag_overlength_lines` 标记。见 [产品定义](../planning/01-product-definition-and-mvp.md#llm-发送池与质检返工) 与 [ADR-005](../architecture/adr/005-llm-integration-privacy.md)。

**Phase 1（M2）MVP 核心已对齐文档**：去标点/空格/规则断句（均衡选点）、LLM 发送池、工作区、OD 三栏 GUI（Wave A/B）、断句词表 GUI 编辑、SSE 流式进度、LLM 处理前预检、结果导出等。**ADR-008 安装包链路已落地**（sidecar + NSIS，见 [packaging.md](./packaging.md)）；仍延后：公开发布 / 代码签名、ADR-009 物理拆包。默认 `uv run pytest` **155 passed**（核对日快照）。

**本机修改文档**（gitignore）：[`.local/break-lexicon-editor/`](../../.local/break-lexicon-editor/README.md)（词表 GUI）；[`.local/llm-send-pool/`](../../.local/llm-send-pool/README.md)（发送池回顾）。

## Phase 1 进度

| 节 | 状态 | 说明 |
|----|------|------|
| §0 前提 | 完成 | P0 基线绿；范围确认 |
| §1 流水线 1–3 | 完成 | `punctuation` / `whitespace` / `line_count` |
| §2 词表 + 规则断句 | 完成 | `break_lexicon/` + Settings 持久化 + FAB Modal；`rule_break` 均衡选点 |
| §3 LLM + 标记 | 完成 | 发送池 / `llm_quality_ok` / `break_lines` / 语义质检返工 / `flag_lines` |
| §4 编排 + 三入口 | 完成 | `preprocess()`；gui/cli/mcp 一致 |
| §5 工作区 | 完成 | ADR-010 |
| §6 GUI 核心 | 完成 | 三栏主路径；Wave A/B；词表 Modal；SSE；导出 |
| §7 验收 | 完成 | 默认 pytest 绿；剪映粘贴建议本机手工抽样 |

## 已存在（LLM / API）

| 路径 | 说明 |
|------|------|
| `pipeline/llm_quality.py` | `min_chars_for` / `quality_ok` / `llm_quality_ok` |
| `pipeline/llm_break.py` | 发送池编排、批 ≤10、终态进度 |
| `llm.py` | `LlmClient.break_lines`；Mock / OpenAI 批解析 |
| `POST /api/v1/preprocess/stream` | SSE 中间进度（GUI 实时预览） |
| `POST /api/v1/settings/llm-test` | 处理前连通性预检 |
| `GET /api/v1/break-lexicon/defaults` | 内置词表默认 |
| `tests/test_pipeline_llm_*.py`、`test_llm.py` | 质检 / 池 / 返工 / 批大小 |

## 已存在（GUI）

| 能力 | 说明 |
|------|------|
| OD Wave A/B | 三栏壳、设置去标点、侧栏搜索/折叠、快捷键、错误 Banner 等 |
| 断句词表编辑 | `Settings.break_lexicon` + `RulesEditorModal` |
| 结果栏 | 行号、字数、分栏统计；SSE 渐进刷新；导出 `.txt` |
| LLM 预检 | 启用 LLM 时处理前弹窗失败不进入 running |
| 用户可见说明 | [用户手册](../user/README.md)；HTTP 契约见 [api/README](../api/README.md) |

## 仍缺失 / 延后

| 项 | 去向 |
|----|------|
| Windows 安装包 / sidecar 生产 | ✅ 可本地构建（[packaging.md](./packaging.md)）；正式对外分发 / 签名仍属 M3 |
| uv workspace 物理拆包 | ADR-009 |
| 词表穷尽真实语料 | 持续迭代 |
| 剪映粘贴「大致可用」正式 sign-off | 本机手工抽样 |

## 已核对项（§7）

1. **stub 语义已移除**：完整 8 步；三入口一致测试通过
2. **无密钥规则路径**：`llm_enabled=false` 时去标点 + 规则 + 标记可用
3. **LLM 发送池**：`is_llm_configured` + 批 ≤10 + 质检 + 最多 3 次返工；Mock 注入；integration 默认不跑
4. **模块边界**：core 无 FastAPI/cli/mcp 依赖；React 仅 HTTP
5. **Settings 共用**：SQLite @ `%APPDATA%/SentRealm/settings.db`
6. **工作区**：`Documents/SentRealm/`；cli/mcp 不接入
7. **GUI 文案**：与用户手册主路径一致；SSE `llm_current/total` 为终态口径

## 本机执行面

下一优先：**M3 可分发 MVP**（干净机冒烟、用户手册安装节、对外分发 / 签名）。

## 相关文档

- [testing.md](./testing.md)
- [路线图](../planning/03-roadmap.md)
- [modules.md](../architecture/modules.md)
