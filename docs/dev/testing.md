# 测试

> LLM mock 与隐私边界见 [ADR-005](../architecture/adr/005-llm-integration-privacy.md)；流水线行为见 [data-flow.md](../architecture/data-flow.md)。

## 命令速查

```bash
# 默认测试集（不含 integration）
uv run pytest

# 仅运行集成测试（需配置 SENTREALM_LLM_API_KEY 与 LLM endpoint/model）
uv run pytest -m integration

# 前端（待配置时可跳过）
pnpm test
pnpm lint
```

## 测试分层

| 层级 | 范围 | 工具 | 默认 CI |
|------|------|------|---------|
| 单元测试 | `packages/core` 各 `pipeline/*.py` 步骤；`line_count`；`Settings` 校验；`MockLlmClient` | pytest | 运行 |
| Store 测试 | `SqliteSettingsStore`、工作区 store（`tmp_path` 注入） | pytest | 运行 |
| API 测试 | `GET /health`、`settings` round-trip、`POST /preprocess`、workspace CRUD | FastAPI `TestClient` | 运行 |
| 集成测试 | 真实 LLM API 调用 | pytest `@pytest.mark.integration` | **跳过** |
| 手工验收 | `pnpm dev` 完整主流程；剪映粘贴抽样 | 人工 | — |
| 前端测试 | React 组件（若已配置） | vitest / testing-library | 待配置 |

## LLM Mock 约定

| 原则 | 说明 |
|------|------|
| 依赖注入 | 单元测试向 `preprocess()` 注入 `MockLlmClient`，不访问网络 |
| 无全局 mock 开关 | 不使用 `SENTREALM_LLM_MOCK=1` 类环境变量静默 mock |
| 未启用 / 未配置 LLM | `llm_enabled=false` 或缺少 endpoint/model/密钥时，跳过流水线步骤 6，超长行进入标记（与生产行为一致） |
| HTTP API | MVP 不提供 API 层 mock 模式；mock 在 `core` 层完成 |
| 发送池 / 质检 | 单测须覆盖：批量 ≤10、低于 `min_chars` 或其他语义质检不合格时回池、满 3 次放弃标记；`llm_quality_ok` 与 `MockLlmClient.break_lines` |

`MockLlmClient` 应返回**确定性**切分结果，便于断言 `flagged_lines` 与行内容。

## 黄金样例

Phase 1 起，`tests/` 应至少包含：

1. **无 LLM**：去标点、空格规范化、规则断句、标记超长行
2. **有 mock LLM**：规则断句后仍超长的行经发送池 / mock 切分；含质检通过与返工放弃路径
3. **字词表**：`test_break_lexicon.py`（词表加载、受保护词检测）
4. **各步骤边界**：见 [data-flow.md 黄金样例](../architecture/data-flow.md)
   - [去标点并换行](../architecture/data-flow.md)
   - [空格规范化](../architecture/data-flow.md)
   - [规则断句](../architecture/data-flow.md)

产品成功标准（剪映粘贴抽样）见 [产品定义与 MVP](../planning/01-product-definition-and-mvp.md#成功标准)。

## 集成测试（可选）

```bash
# .env 中配置 SENTREALM_LLM_API_KEY，并在 settings 中配置 endpoint/model 后
uv run pytest -m integration
```

- 标记：`@pytest.mark.integration`
- 默认 `uv run pytest` **不**收集或跳过 integration（在 `pyproject.toml` 中配置 `addopts = "-m 'not integration'"` 或等价方式）
- CI nightly 或本地手动运行，避免 PR 依赖真实 API 密钥

## 当前最小测试集

默认 `uv run pytest` 至少覆盖：

| 文件 | 内容 |
|------|------|
| `tests/test_store.py` | Settings 读写、默认路径、preset 联动 |
| `tests/test_workspace_store.py` | 工作区初始化、`repair_meta`、原子写 |
| `tests/test_project_store.py` | 项目 CRUD |
| `tests/test_document_store.py` | 文稿 CRUD、`result.json` |
| `tests/test_api_workspace.py` | workspace HTTP 集成 |
| `tests/test_preprocess.py` | 流水线（含空文稿、`EmptyTextError`、换行规范化） |
| `tests/test_api.py` | health、settings round-trip、preprocess |
| `tests/test_cli.py` | `--help`、stdin 管道、退出码 |
| `tests/test_mcp.py` | MCP `preprocess_text` 契约 |
| `tests/test_llm.py` | Mock / 批解析等 |
| `tests/test_phase0_acceptance.py` | 三入口共用 Settings 等验收 |
| `tests/test_pipeline_*.py` / `test_break_lexicon.py` | 各步骤与字词表（Phase 1） |

验收：`uv run pytest` 通过。

## 相关文档

- [开发环境搭建](./setup.md)
- [本地运行](./running-locally.md)
- [API Mock 策略](../api/README.md)
- [数据流与模块边界](../architecture/data-flow.md)
