# ADR-001: 桌面壳选用 Tauri 2

## 状态

已接受

## 背景

根据 [产品定义](../../planning/01-product-definition-and-mvp.md)，SentRealm 的主产品形态为**本地桌面应用**：文稿在本地处理、不上传云端；用户需要粘贴/导入文稿、预览对照、一键复制到剪映。

技术架构还要求：

- **前端**：React 负责文稿输入、参数配置、对照预览等 UI（见 [架构概览](../overview.md)）
- **后端**：Python（FastAPI + 预处理流水线 + SQLite）承载业务逻辑
- **进程模型**：桌面壳需 **spawn 并管理 FastAPI 子进程**、做健康检查、在退出时清理子进程（见 [ADR-006](./006-tauri-spawn-fastapi.md)）
- **系统能力**：`.txt` 文件导入、剪贴板等需访问本机资源

因此需选定桌面容器技术，并在项目早期固定，以便脚手架与打包路径一致。

> **说明**：本 ADR 为**回顾性记录**——桌面形态与栈已在 [产品定义](../../planning/01-product-definition-and-mvp.md)、[setup.md](../../dev/setup.md) 中确定；本文档补全决策依据，供后续评审与 onboarding 查阅。

## 选项

### A. Electron

Chromium + Node.js 打包为桌面应用。

- 优点：生态成熟、文档与案例多；Node 侧可直接 `child_process` 管理 Python
- 缺点：安装包与内存占用偏大；Chromium 捆绑导致体积与更新成本高；对「轻量本地工具」偏重

### B. Tauri 2（本决策选中）

Rust 壳 + 系统 WebView 渲染前端；通过 Rust 命令与插件暴露系统能力。

- 优点：安装包与运行时占用小；Rust 侧适合管理子进程与生命周期；与 React 技术栈自然配合；Tauri 2 插件体系成熟
- 缺点：WebView 行为因平台略有差异，需测试；Rust 侧需少量维护（spawn、健康检查）

### C. Flutter / .NET MAUI 等原生 UI 框架

用 Dart 或 C# 重写整套 UI。

- 优点：原生性能与控件一致性好
- 缺点：与已选 React 前端栈冲突；团队需维护第二套 UI 技术；与现有架构文档（React + shadcn/ui）不一致

### D. 纯 Web / PWA

浏览器或安装为 PWA，本地起 Python 服务。

- 优点：无桌面壳开发
- 缺点：文件系统、一键启动、子进程生命周期管理体验差；不符合「桌面工具」产品定位

### E. Wails（Go + WebView）

Go 后端 + WebView 前端。

- 优点：轻量，类似 Tauri 思路
- 缺点：后端已定为 Python，若用 Wails 需 Go 桥接或仍外挂 Python，架构更绕；生态与团队熟悉度弱于 Tauri + React

## 决策

采用 **选项 B：Tauri 2** 作为桌面壳。

| 维度 | 约定 |
|------|------|
| 版本 | **Tauri 2**（非 Tauri 1） |
| 前端 | React + TypeScript，运行于 Tauri WebView |
| 后端关系 | Tauri **不内嵌** Python 业务逻辑；通过 spawn **独立 FastAPI 子进程**（ADR-006） |
| 系统能力 | 文件导入、API base URL 注入、子进程管理等经 **Tauri Rust 命令 / 插件** 暴露 |
| 与多入口架构 | Tauri 仅属于 **gui** 模块；cli、mcp 为独立进程，不由 Tauri 管理（ADR-007） |

### 选型理由（摘要）

1. **轻量**：面向个人创作者的本地工具，不需要完整 Chromium 运行时
2. **进程管理**：Rust 侧 spawn、轮询 `/health`、退出时 kill 子进程，与 ADR-006 模型匹配
3. **技术栈一致**：保留 React 前端与 Python 后端分工，避免重写 UI
4. **本地优先**：WebView + 本地 HTTP（127.0.0.1）符合隐私与离线核心路径（LLM 步骤可选）

### 明确不选 Electron 的原因（MVP 视角）

- 产品无强依赖 Electron 独有生态（如深度 Node 原生模块集成）
- 更关注安装体积与 idle 占用，Tauri 更贴合
- Python 后端已独立为子进程，Electron 的「内置 Node 跑 Python」优势不明显

生产环境 Python 打包（sidecar / 内嵌解释器）在脚手架阶段另行决策，不改变「Tauri 为壳、Python 为子进程」模型。

## 后果

### 正面

- 安装包与内存占用预期低于 Electron 方案
- gui 模块边界清晰：Tauri = 壳 + 生命周期；业务在 Python `core` 与 `gui/api`
- 与 [ADR-003](./003-local-http-decoupling.md) 本地 HTTP 解耦、Apifox 调试流程兼容
- Rust 侧能力可渐进扩展（文件对话框、单实例等），不污染 Python core

### 负面

- 需维护 `src-tauri` Rust 代码（spawn、health、命令）
- 各平台 WebView 差异需在 UI 测试中覆盖
- 生产打包需额外解决 Python 运行时分发（见 ADR-006 待定项）
- 团队需具备基础 Tauri 配置知识

## 相关文档

- [架构概览](../overview.md)
- [ADR-006：Tauri 管理 FastAPI 子进程](./006-tauri-spawn-fastapi.md)
- [ADR-007：多入口模块化](./007-multi-entry-modules.md)
- [产品定义与 MVP](../../planning/01-product-definition-and-mvp.md)
- [AGENTS.md](../../../AGENTS.md)
