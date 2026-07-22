# ADR-002: 前端 UI 选用 shadcn/ui

## 状态

已接受

## 背景

SentRealm gui 模块的前端（`apps/gui/src`）需实现 MVP 界面能力，包括：

- 文稿输入（文本框粘贴、`.txt` 导入后的展示）
- 参数配置（横竖屏预设、自定义字数、去标点规则、LLM 设置）
- 原文与处理后**对照预览**、行数统计、**超长标记行高亮**
- 一键复制、设置持久化反馈

根据 [架构概览](../overview.md) 与 [setup.md](../../dev/setup.md)，前端技术栈为 **React + TypeScript**，样式为 **Tailwind CSS**。需选定 UI 组件方案，在脚手架阶段统一交互与视觉基础，避免后续混用多套设计系统。

> **说明**：本 ADR 为**回顾性记录**——前端栈已在架构概览与 setup 中确定；本文档补全与其他组件库的对比与落地约定。

## 选项

### A. Material UI (MUI)

基于 Emotion 的完整 React 组件库。

- 优点：组件齐全、文档成熟
- 缺点：默认视觉偏 Material Design，定制剪映工具风 UI 成本高；运行时样式方案与 Tailwind 混用易产生冲突

### B. Ant Design

企业级 React 组件库。

- 优点：表格、表单等开箱即用
- 缺点：设计语言固定；包体积与主题覆盖成本较高；与 Tauri 桌面「轻量工具」气质不完全匹配

### C. Chakra UI / Mantine

现代 React 组件库，主题系统完善。

- 优点：开发效率高、可访问性较好
- 缺点：以 npm 依赖包形式引入，深度定制需覆盖主题层；与「组件源码进仓库」的维护模型不同

### D. shadcn/ui + Tailwind CSS（本决策选中）

基于 **Radix UI** 原语 + **Tailwind** 样式；通过 CLI 将组件**源码**复制到项目中（`components/ui/`）。

- 优点：组件可随意改；与 Tailwind 一致；Radix 提供无障碍与交互基础；无「黑盒」大依赖
- 缺点：组件需自行维护升级；复杂页面仍需组合与布局工作

### E. 从零手写组件

仅用 Tailwind，不用组件库。

- 优点：依赖最少
- 缺点：对话框、下拉、可访问焦点等重复造轮子；MVP 周期拉长

## 决策

采用 **选项 D：shadcn/ui**，样式层统一使用 **Tailwind CSS**。

### 落地约定

| 项 | 约定 |
|----|------|
| 组件来源 | 通过 [shadcn/ui CLI](https://ui.shadcn.com) 添加至 `apps/gui/src/components/ui/` |
| 基础原语 | Radix UI（由 shadcn 组件间接依赖） |
| 样式 | Tailwind utility + 项目 `tailwind.config` 中的 design token |
| 禁止 | MVP 阶段**不引入**第二套完整 UI 库（如 MUI、Ant Design），除非用户明确要求 |
| 定制 | 直接修改 `components/ui/` 内源码；不 fork 整库 |
| 与 Tauri | UI 仅通过 HTTP 调 `gui/api`；系统能力（文件、剪贴板）经 Tauri API / command |

### MVP 界面与组件映射（建议）

| 产品能力 | 建议 shadcn 组件（按需添加） |
|----------|------------------------------|
| 文稿输入 | `Textarea` |
| 预设 / 参数 | `Select`、`RadioGroup`、`Input`、`Label` |
| 设置面板 | `Dialog` 或 `Sheet`、`Form`（MVP 主界面采用 OD 自定义 Drawer + `app-shell.css`；`VerifyPage` 等仍用 shadcn） |
| 对照预览 | 自定义布局 + `ScrollArea`；标记行用 Tailwind 高亮 |
| 操作按钮 | `Button` |
| 状态提示 | `Alert`、`Toast`（sonner） |
| 复制反馈 | `Button` + toast |

具体页面结构、线框与状态机见 [docs/ui/](../../ui/README.md)（设计源自 Open Design「SentRealm · Codex 高保真 UI」）；本 ADR 仅规定组件库选型。

### 选型理由（摘要）

1. **可定制**：文稿对照、标记行高亮等布局较灵活，源码级组件更易调
2. **与 Tailwind 一致**：项目前端已约定 Tailwind，避免 CSS-in-JS 双轨
3. **体积可控**：按需添加组件，不整包引入大型库
4. **桌面 WebView**：标准 DOM + Tailwind，与 Tauri WebView 兼容性好

## 后果

### 正面

- 组件代码归项目所有，长期定制与审计方便
- Radix 提供键盘导航、焦点管理等 a11y 基础
- 与社区 shadcn 生态（图表、blocks）可渐进引入
- 前端边界清晰：仅 UI + HTTP client，不含预处理逻辑（ADR-007）

### 负面

- shadcn 升级需手动对比合并 `components/ui` 变更
- 复杂数据表格等需自行组合，无 Ant Design 式一站式方案
- 设计一致性依赖项目内 Tailwind token 约束，需避免 ad-hoc 样式

## 相关文档

- [docs/ui/](../../ui/README.md) — GUI 设计→实现契约
- [架构概览](../overview.md)
- [ADR-001：桌面壳选用 Tauri 2](./001-tauri-desktop-shell.md)
- [ADR-007：多入口模块化](./007-multi-entry-modules.md)
- [数据流与模块边界](../data-flow.md)
- [产品定义与 MVP](../../planning/01-product-definition-and-mvp.md)
- [AGENTS.md](../../../AGENTS.md)
