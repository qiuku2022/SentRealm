# CLI 与 MCP 契约

> 多入口架构见 [ADR-007](./architecture/adr/007-multi-entry-modules.md)；模块职责见 [modules.md](./architecture/modules.md)。  
> **适用范围**：`packages/cli`、`packages/mcp` 直连 `core`，**不走** [HTTP API](./api/README.md)。

## 单一事实来源

| 文档 | 说明 |
|------|------|
| **本文档** | CLI 命令、MCP tool 入参/返回、退出码、配置覆盖规则 |
| [docs/api/README.md](./api/README.md) | gui/ui ↔ gui/api 的 HTTP 契约（`Settings`、`PreprocessResponse` 字段定义与之对齐） |

## 共用约定

| 项 | 约定 |
|----|------|
| 配置存储 | `SettingsStore.load()` 读取共用 SQLite（路径见 [ADR-004](./architecture/adr/004-sqlite-user-settings.md)）；含 `break_lexicon` 断句词表 |
| 处理核心 | `core.preprocess(text, settings, llm_client=None)` |
| 当次参数覆盖 | CLI `--preset` / `--max-chars`、MCP `preset` / `max_chars` **仅影响当次请求**，不写 SQLite |
| LLM 配置 | `llm_endpoint`、`llm_model` 始终从 SQLite 读取；密钥从 `SENTREALM_LLM_API_KEY` 读取 |
| 与 gui 一致性 | 相同 `Settings` 与输入文稿时，三入口处理结果须一致（Phase 1 验收项） |

三入口共用 ADR-012 的自然边界规则：句末符号结束自然句，逗号等只在超长时作为候选，引号/括号只删除；无法自然切开的局部超长行保留在 `processed` 并列入 `flagged_lines`。

---

## CLI：`sentrealm preprocess`

入口：`uv run sentrealm preprocess`（控制台脚本 `sentrealm` → `sentrealm_cli.main:app`）。

### 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-i`, `--input` | 与 `--stdin` 二选一 | 输入 `.txt` 文件路径 |
| `-o`, `--output` | 否 | 输出文件路径；省略则写入 **stdout** |
| `--stdin` | 与 `-i` 二选一 | 从标准输入读取文稿 |
| `--preset` | 否 | `landscape` \| `portrait`；覆盖当次 `preset`（并联动 `max_chars` 为 15 / 10） |
| `--max-chars` | 否 | 正整数；覆盖当次 `max_chars`，隐含 `preset=custom` |

`-i` 与 `--stdin` 不可同时使用；均未提供时退出码 `1`。

### 配置合并逻辑

1. `settings = SettingsStore.load()`
2. 若指定 `--preset`：设置 `settings.preset`，并按 preset 设置 `max_chars`（`landscape`→15，`portrait`→10）
3. 若指定 `--max-chars`：设置 `settings.max_chars`，`settings.preset = custom`
4. 调用 `preprocess(text, settings)`

（不写回 SQLite。）

### 输出

| 流 | 内容 |
|----|------|
| **stdout** 或 **`-o` 文件** | `processed` 纯文本，行以 `\n` 分隔，无空行 |
| **stderr** | 单行 JSON 元数据：`{"line_count": 42, "flagged_lines": [3, 7]}` |

stderr 仅在成功时输出；便于脚本解析标记行而不污染主输出。

**示例**

```bash
uv run sentrealm preprocess -i draft.txt -o out.txt
# out.txt ← processed 文本
# stderr  → {"line_count":12,"flagged_lines":[2]}
```

```bash
uv run sentrealm preprocess --stdin --preset portrait < draft.txt
```

### 退出码

| 码 | 含义 |
|----|------|
| `0` | 成功 |
| `1` | 输入/参数错误（文件不存在、互斥参数、空文稿等） |
| `2` | 处理失败（流水线或 IO 异常） |

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

配置合并逻辑与 CLI 相同（从 SQLite 加载后应用可选覆盖）。

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

| 概念 | HTTP | CLI | MCP |
|------|------|-----|-----|
| 配置读取 | `GET /api/v1/settings` | `SettingsStore.load()` | 同左 |
| 配置写入 | `PUT /api/v1/settings` | MVP 不支持 | MVP 不支持 |
| 当次 settings 覆盖 | `POST /preprocess` 请求体 `settings` | `--preset` / `--max-chars` | `preset` / `max_chars` 参数 |
| 处理结果 | `PreprocessResponse` JSON | stdout + stderr 元数据 | `PreprocessResponse` JSON |

## 相关文档

- [本地运行：CLI / MCP](./dev/running-locally.md)
- [ADR-007：多入口模块化](./architecture/adr/007-multi-entry-modules.md)
- [API 文档](./api/README.md)
