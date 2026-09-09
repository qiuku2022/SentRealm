# 本地运行

> 进程模型见 [ADR-006](../architecture/adr/006-tauri-spawn-fastapi.md)：开发环境下由 **Tauri 自动 spawn FastAPI**，一般**无需**手动开第二个终端跑 uvicorn。

**状态**：Phase 0（M1）脚手架与 Phase 1（M2）MVP 核心已完成；以下命令与当前约定一致。

## 一键启动（推荐）

在仓库根目录：

```bash
uv sync
pnpm dev
```

| 行为 | 说明 |
|------|------|
| 启动内容 | Tauri 桌面窗口 + React 前端 |
| 后端 | Rust 在 `setup` 阶段 spawn：`uv run uvicorn apps.gui.api.main:app --host 127.0.0.1 --port 17300`（使用项目 `.venv`，见 [setup.md](./setup.md)、[ADR-006](../architecture/adr/006-tauri-spawn-fastapi.md)） |
| 已就绪跳过 | 若 `GET /health` 已成功，**不重复 spawn**（避免 dev 时端口冲突） |
| 就绪检查 | Rust 仅 spawn；前端 `waitForHealth` 轮询 `GET /health`（200ms 间隔，30s 超时）直至就绪 |
| base URL | 前端经 `invoke('get_api_base_url')` 获取，默认 `http://127.0.0.1:17300` |
| 启动失败 | `invoke('get_backend_startup_error')` 可读取 Rust 侧错误摘要 |

health 成功前，前端不调用 `/api/v1/*` 业务接口。

## IDE 调试（Cursor / VS Code）

仓库根 [`.vscode/launch.json`](../../.vscode/launch.json) 提供 F5 配置。Python 走项目 `.venv` + debugpy；须先 `uv sync`（Python 类配置会自动跑 `uv:sync` task）。

| 配置 | 用途 |
|------|------|
| **▶ Desktop + API 断点**（推荐） | compound：FastAPI 断点 + Desktop（Tauri 不 spawn，等 debugpy） |
| `Desktop: pnpm dev` | 日常调试：Tauri 自动 `uv run uvicorn` |
| `Desktop: pnpm dev（断点模式）` | 仅桌面；须另有 API（如 `Python: FastAPI`） |
| `Python: FastAPI` | 仅后端断点 |
| `Python: pytest` / `CLI` | 单元测试 / CLI |
| `Rust: Tauri` | Rust 断点；须先启动 `Python: FastAPI` |
| `Rust + API 断点` | compound：MSVC + FastAPI |

**断点模式机制**：`SENTREALM_SKIP_BACKEND_SPAWN=1` 时 Tauri 不 spawn 后端；前端轮询 `/health`（最多 30s）。见 `apps/gui/src-tauri/src/backend.rs`。

## 仅调试 HTTP API（可选）

不启动 Tauri、单独验证 FastAPI 时（Apifox、curl、pytest）：

```bash
cd <仓库根>
uv run uvicorn apps.gui.api.main:app --host 127.0.0.1 --port 17300 --reload
```

```bash
# 健康检查
curl http://127.0.0.1:17300/health

# 读取配置
curl http://127.0.0.1:17300/api/v1/settings
```

详见 [API 文档](../api/README.md) 与 [openapi.yaml](../api/openapi.yaml)。

## CLI

```bash
# 帮助
uv run sentrealm preprocess --help

# 文件处理
uv run sentrealm preprocess -i draft.txt -o out.txt --preset landscape

# 管道
uv run sentrealm preprocess --stdin < draft.txt
```

cli 与 gui **共用** SQLite 配置（`%APPDATA%/SentRealm/settings.db`，Windows），见 [ADR-004](../architecture/adr/004-sqlite-user-settings.md)。

**输出约定**（Phase 0 起）：

| 流 | 内容 |
|----|------|
| **stdout** 或 **`-o` 文件** | 处理后纯文本（`processed`），行以 `\n` 分隔 |
| **stderr** | 单行 JSON：`{"line_count": 12, "flagged_lines": [2]}` |

示例：

```bash
uv run sentrealm preprocess -i draft.txt -o out.txt 2> meta.json
# out.txt   ← 可粘贴到剪映的正文
# meta.json ← {"line_count":...,"flagged_lines":[...]}
```

完整参数、退出码见 [cli-mcp.md](../cli-mcp.md)。

## MCP Server

```bash
uv run sentrealm-mcp
```

stdio 传输；MVP 暴露 `preprocess_text` tool。

**Cursor 配置**：在 MCP 设置中添加本地 server，`command` 为 `uv`，`args` 为 `["run", "sentrealm-mcp"]`，`cwd` 为仓库根目录。完整 JSON 片段见 [cli-mcp.md](../cli-mcp.md)。

## 联调要点

| 项 | 值 / 说明 |
|----|-----------|
| 绑定地址 | `127.0.0.1`（仅本机，不对外暴露） |
| 端口 | `17300`（MVP 固定；被占用则启动失败，见 ADR-006） |
| CORS | 生产不启用；**开发**下为 Vite（`localhost:1420`）→ API 允许有限 Origin（见 `apps/gui/api/main.py`） |
| Apifox Base URL | `http://127.0.0.1:17300` |
| 前端代理 | 不经 Vite 代理；直连 Tauri 注入的 base URL |

### 常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| UI 显示「后端不可达」/ `Failed to fetch` | uvicorn 未启动、`/health` 超时，或 Vite 跨域 | 先 `uv sync`；检查端口占用；勿与 `pnpm dev` 同时手动起第二个 uvicorn |
| F5 调试时 UI「后端未就绪」 | 选了断点模式 Desktop 但未启动 FastAPI | 使用 **▶ Desktop + API 断点**，或先启动 `Python: FastAPI` |
| `uv run` / spawn 失败 | 未 `uv sync` 或 `.venv` 损坏 | 删除 `.venv` 后重新 `uv sync` |
| 端口 17300 被占用 | 残留 uvicorn 或其他进程 | 结束占用进程后重启应用（MVP 不自动换端口）；PowerShell：`Get-NetTCPConnection -LocalPort 17300` |
| UI 显示「后端未就绪」 | spawn 失败或 health 超时 | 确认 `uv` 在 PATH 且已 `uv sync` |
| 关闭应用后仍有 uvicorn | 子进程树未正确终止（多见于 Windows） | 重启应用后应已自动清理；若仍占用 17300，PowerShell：`Get-NetTCPConnection -LocalPort 17300` 查 PID 后结束进程 |
| `pnpm dev` 找不到命令 | 未在仓库根执行或未 `pnpm install` | 在根目录 `pnpm install` 后重试 |
| `resource path resources\sentrealm-api doesn't exist` | 生产 sidecar 目录未构建；`tauri dev` 仍校验 `bundle.resources` | 无需先打 sidecar；`src-tauri/build.rs` 会自动建空占位目录。若仍失败，确认已拉到含该修复的代码 |
| `pnpm` 报 `v11.12.0 is a broken release` | 官方将该版本标为损坏（`@pnpm/exe` 无二进制） | 使用仓库锁定的 `pnpm@11.15.0`：`pnpm self-update 11.15.0` 或按 [setup.md](./setup.md) 重装 pnpm |
| LLM 断句不生效 | 未配置密钥或 endpoint/model | 设置 `SENTREALM_LLM_API_KEY` 与 SQLite 中的 `llm_endpoint` / `llm_model` |

## 相关文档

- [开发环境搭建](./setup.md)
- [测试](./testing.md)
- [架构概览](../architecture/overview.md)
- [cli-mcp.md](../cli-mcp.md)
