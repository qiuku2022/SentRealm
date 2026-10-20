# MCP 契约

> 多入口架构见 [ADR-007](./architecture/adr/007-multi-entry-modules.md)；模块职责见 [modules.md](./architecture/modules.md)。  
> **适用范围**：`packages/mcp` 直连 `core`，**不走** [HTTP API](./api/README.md)。

## 单一事实来源

| 文档 | 说明 |
|------|------|
| **本文档** | MCP tool 入参/返回、配置覆盖规则 |
| [docs/api/README.md](./api/README.md) | gui/ui ↔ gui/api 的 HTTP 契约（`Settings`、`PreprocessResponse` 字段定义与之对齐） |

## 共用约定

| 项 | 约定 |
|----|------|
| 配置存储 | `SettingsStore.load()` 读取共用 SQLite（路径见 [ADR-004](./architecture/adr/004-sqlite-user-settings.md)）；含 `break_lexicon` 断句词表 |
| 处理核心 | `core.preprocess(text, settings, llm_client=None)` |
| 当次参数覆盖 | MCP `preset` / `max_chars` **仅影响当次请求**，不写 SQLite |
| LLM 配置 | `llm_endpoint`、`llm_model` 始终从 SQLite 读取；密钥从 `SENTREALM_LLM_API_KEY` 读取 |
| 与 gui 一致性 | 相同 `Settings` 与输入文稿时，两入口处理结果须一致 |

多入口共用 ADR-012 的自然边界规则：句末符号结束自然句，逗号等只在超长时作为候选，引号/括号只删除；无法自然切开的局部超长行保留在 `processed` 并列入 `flagged_lines`。

---

## MCP：`preprocess_text`

入口：`uv run sentrealm-mcp`（stdio 传输）。

MVP 仅注册 **`preprocess_text`** 一个 tool；settings 读写 tools 为二期能力。

### 入参

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `text` | string | 是 | 待处理文稿；空白或仅空格时 tool 返回错误 |
| `preset` | string | 否 | `landscape` \| `portrait`；仅当次覆盖 |
| `max_chars` | integer | 否 | `>= 1`；仅当次覆盖，指定时隐含 `preset=custom` |

### 配置合并逻辑

1. `settings = SettingsStore.load()`
2. 若指定 `preset`：设置 `settings.preset`，并按 preset 设置 `max_chars`（`landscape`→15，`portrait`→10）
3. 若指定 `max_chars`：设置 `settings.max_chars`，`settings.preset = custom`
4. 调用 `preprocess(text, settings)`

（不写回 SQLite。）

### 返回

与 HTTP `POST /api/v1/preprocess` 的 **`PreprocessResponse`** 同结构：

```json
{
  "original": "原始文稿……",
  "processed": "处理后文本\n按行分隔……",
  "line_count": 42,
  "flagged_lines": [3, 7]
}
```

| 字段 | 说明 |
|------|------|
| `original` | 请求中的 `text` |
| `processed` | 处理后文本 |
| `line_count` | 处理后行数 |
| `flagged_lines` | 仍超长行号（**0-based**） |

### Cursor MCP 配置示例

在 Cursor 设置 → MCP 中添加（`cwd` 为仓库根目录）：

```json
{
  "mcpServers": {
    "sentrealm": {
      "command": "uv",
      "args": ["run", "sentrealm-mcp"],
      "cwd": "D:/Work/SentRealm"
    }
  }
}
```

Windows 下请将 `cwd` 改为本机仓库绝对路径。须已在仓库根执行 `uv sync`（`uv` 在 PATH 中）。

---

## 与 HTTP API 的字段对照

| 概念 | HTTP | MCP |
|------|------|-----|
| 配置读取 | `GET /api/v1/settings` | `SettingsStore.load()` |
| 配置写入 | `PUT /api/v1/settings` | MVP 不支持 |
| 当次 settings 覆盖 | `POST /preprocess` 请求体 `settings` | `preset` / `max_chars` 参数 |
| 处理结果 | `PreprocessResponse` JSON | `PreprocessResponse` JSON |

## 相关文档

- [本地运行：MCP](./dev/running-locally.md)
- [ADR-007：多入口模块化](./architecture/adr/007-multi-entry-modules.md)
- [API 文档](./api/README.md)
