# ADR-003: 前后端本地 HTTP 解耦

## 状态

已接受

## 背景

根据 [ADR-007](./007-multi-entry-modules.md)，gui 的 React（`gui/ui`）不得直接 import Python `core`；根据 [ADR-006](./006-tauri-spawn-fastapi.md)，Tauri spawn 的 `apps/gui/api`（FastAPI）为 WebView 提供后端能力。

需要明确 **gui/ui 与 gui/api 之间的 HTTP 契约**，以便：

- React 与后端独立开发与测试
- 使用 Apifox 等工具调试 API（在 gui 运行、api 进程存在时）
- 与 cli、mcp 的接入方式区分：后两者**直接调用 core**，不走 HTTP

## 选项

### A. Tauri IPC 替代 HTTP

通过 Tauri `invoke` 自定义 command 在 Rust 与前端间传参，由 Rust 转发至 Python。

- 优点：无 HTTP 端口；无端口冲突问题
- 缺点：无法用 Apifox 调试；契约非标准 REST；与 FastAPI 生态脱节

### B. 前端直连 core

WebView 通过 PyO3、子进程脚本等方式直接调用 `core`。

- 优点：少一层 HTTP
- 缺点：破坏 ADR-007 依赖铁律；前端与 Python 耦合

### C. 本地 HTTP（本决策选中）

`gui/api` 绑定 `127.0.0.1`，暴露 REST API；React 经 HTTP 调用。

- 优点：前后端解耦；Apifox/OpenAPI 友好；后端可独立单测
- 缺点：多一层 HTTP；须约定端口与 base URL

### D. 本地 HTTPS

为 `127.0.0.1` 配置 TLS 证书。

- 优点：传输加密（本地环回意义有限）
- 缺点：MVP 过度设计；证书管理增加复杂度

## 决策

采用 **选项 C**。以下为 MVP HTTP 约定。

### 绑定与 base URL

| 项 | 约定 |
|----|------|
| 协议 | HTTP |
| 绑定地址 | `127.0.0.1`（仅本机，不对外暴露） |
| 默认端口 | **`17300`**（项目约定端口） |
| 端口冲突 | 仅当 `17300` 被占用时通过配置覆盖；Rust spawn 与前端须使用**同一** base URL |
| base URL 来源 | Tauri 注入或环境变量（如 `http://127.0.0.1:17300`）；前端**不硬编码** |

### 路由与版本

| 类型 | 约定 |
|------|------|
| 业务路由前缀 | `/api/v1` |
| 健康检查 | `GET /health`（**无**版本前缀，供 ADR-006 Rust 轮询） |
| 版本策略 | URL 路径版本；breaking change 时递增至 `/api/v2` |

### MVP 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| GET | `/api/v1/settings` | 读取用户配置 |
| PUT | `/api/v1/settings` | 更新用户配置 |
| POST | `/api/v1/preprocess` | 预处理文稿 |

请求/响应体结构见 [API 文档](../../api/README.md) 与 [OpenAPI](../../api/openapi.yaml)。

### CORS

**生产不配置 CORS**。

**开发**（`pnpm dev`）下，Vite 页面为 `http://localhost:1420`，向 `http://127.0.0.1:17300` 发请求构成跨域；`apps/gui/api/main.py` 通过 `CORSMiddleware` 仅允许本地 dev / Tauri 相关 Origin。

- Apifox、curl、pytest `TestClient` 不受 CORS 影响
- 生产打包后 WebView 与 API 的跨域策略见实现；MVP 仍以 Tauri 内嵌页面直连 `127.0.0.1` 为主

### 错误响应

- 格式：FastAPI 默认 JSON，`{ "detail": "..." }`（校验错误时 `detail` 可为数组）
- HTTP 状态码按语义使用：`400` 错误请求、`422` 校验失败、`500` 服务器错误等
- 业务错误码体系 MVP 不单独引入，后续如有需要再增 ADR

### Apifox / OpenAPI

- 可直接对 `http://127.0.0.1:17300` 发请求（需 gui 已启动且 FastAPI 子进程运行）
- Apifox / OpenAPI：[docs/api/README.md](../../api/README.md) 与 [openapi.yaml](../../api/openapi.yaml) 为对外索引；在线 Apifox 项目链接**待补充（非阻塞）**

### 适用范围

| 适用 | 不适用 |
|------|--------|
| `gui/ui` ↔ `apps/gui/api` | cli → core（直连） |
| Apifox 调试 `gui/api` | mcp → core（直连） |

## 后果

### 正面

- 前后端契约清晰，与 [架构概览](../overview.md) 通信方式一致
- 便于 Apifox 调试与后端独立测试
- 与 ADR-006（spawn）、ADR-007（模块化）衔接自然

### 负面

- 须保证 Rust、uvicorn、前端三方端口/base URL 一致
- 多一层 HTTP 序列化开销（本地环回可忽略）
- OpenAPI 文档需与实现同步维护（Phase 0 起）

## 相关文档

- [架构概览](../overview.md)
- [ADR-006：Tauri 管理 FastAPI 子进程](./006-tauri-spawn-fastapi.md)
- [ADR-007：多入口模块化](./007-multi-entry-modules.md)
- [API 文档](../../api/README.md)
