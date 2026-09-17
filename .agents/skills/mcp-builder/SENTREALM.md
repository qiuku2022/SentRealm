# SentRealm 对 mcp-builder skill 的覆盖

权威契约见 [docs/cli-mcp.md](../../../docs/cli-mcp.md)。本文件防止 Agent 按「从零新建 MCP 服务器」模板改写现有入口。

## 必须遵守

| 通用 mcp-builder 说法 | 本仓库 |
|----------------------|--------|
| 新建独立 FastMCP / TypeScript MCP 工程 | **不要**另起仓库式脚手架。入口在 `packages/mcp`，脚本 `sentrealm-mcp` |
| MCP 经 HTTP 调 gui FastAPI | **禁止**。mcp **直连** `sentrealm_core`（与 cli 相同，[modules.md](../../../docs/architecture/modules.md)） |
| 默认推荐 TypeScript SDK | 本仓库 MCP 为 **Python**（`mcp` 依赖）；不要无故迁到 Node |
| 随意增删工具名 / 参数 | 改行为须同步 [docs/cli-mcp.md](../../../docs/cli-mcp.md) |

## 仍然适用

- 工具命名清晰、输入用 Pydantic 约束、错误信息可操作
- 本地 stdio 传输；不要为「远程 Streamable HTTP」改默认产品形态（除非产品文档明确要求）
