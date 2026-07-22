# SentRealm UI 文档

> **设计源**：Open Design 项目「SentRealm · Codex 高保真 UI」（`5560a61d-6179-4db6-b6c9-9b19ee004fa1`）。  
> **实现栈**：Tauri 2 WebView + React + TypeScript + shadcn/ui + Tailwind CSS（[ADR-002](../architecture/adr/002-shadcn-ui.md)）。  
> **本目录角色**：GUI **设计 → 实现契约**（tokens、布局、组件映射、屏幕与状态）。产品规则、架构、用户操作说明不以本文为准。

## 阅读顺序

1. [foundations.md](./foundations.md) — 配色、字体、间距、语义 token ↔ shadcn/Tailwind  
2. [layout.md](./layout.md) — 三栏壳、`app-shell`、响应式与 Tauri 注意点  
3. [components.md](./components.md) — OD 控件 → shadcn / 自定义映射  
4. [screens.md](./screens.md) — 主界面与设置结构  
5. [states.md](./states.md) — 处理流、后端健康、超长行、复制反馈等状态机  

## 与相邻文档的分工

| 目录 / 文档 | 回答的问题 |
|-------------|------------|
| [docs/planning/](../planning/) | **做什么** — 产品规则与用户故事 |
| [docs/architecture/](../architecture/) | **怎么做** — 进程、模块、ADR（含 [ADR-002](../architecture/adr/002-shadcn-ui.md)） |
| **docs/ui/**（本目录） | **长什么样、怎么落地组件** — 视觉与交互契约 |
| [docs/user/](../user/) | **终端用户怎么用** — 文案与操作步骤 |
| [docs/dev/](../dev/) | **如何跑起来** — 环境与测试 |

冲突时：**产品规则**以规划文档为准；**组件库选型**以 ADR-002 为准；**色值与壳层布局**以本目录（源自 OD `assets/app.css`）为准。

## 设计源与落地路径

| 项 | 约定 |
|----|------|
| OD 共享壳 CSS | `assets/app.css`（六块 board 共用） |
| 仓库落地文件名 | `apps/gui/src/styles/app-shell.css`（与架构文档中的 `app-shell.css` 对齐） |
| OD boards | `01-new` … `06-settings` → 见 [screens.md](./screens.md) / [states.md](./states.md) |
| shadcn 组件目录 | `apps/gui/src/components/ui/` |

## 工作区状态

`apps/gui` 已实现 OD 三栏壳（Phase 1 核心 + **OD Wave A** 高保真对齐 + **OD Wave B**）。Wave B 已落地：侧栏搜索、折叠、文稿重命名/删除确认、快捷键 `Ctrl+,`（设置）与 `/`（聚焦搜索）等。主入口为 `AppShell`；`Phase0Shell` 为遗留调试组件（非主路径）。

## 已知设计与产品漂移

| 点 | OD 原型 | 产品 / 架构 SSOT | UI 落地建议 |
|----|---------|------------------|-------------|
| 会话持久化 | 侧栏提示「仅本机会话，退出清除」 | [ADR-010](../architecture/adr/010-workspace-document-persistence.md)：`Documents/SentRealm/` | **跟 ADR-010**；侧栏文案勿照抄 ephemeral 提示 |
| 设置面板 | 自定义 `.drawer` | ADR-002：主界面 OD Drawer；基础控件与遗留调试页用 shadcn | 保持 OD Drawer + `app-shell.css` |
| 主按钮色 | 白底深字（`--accent: #fff`） | — | 映射到 shadcn `--primary`（见 foundations） |

## 维护

- 改配色 / 布局 / 组件映射 → 先改 OD 或本目录，再同步实现。  
- 改产品能力或文案 → 同步 [用户手册](../user/README.md) 与 [CHANGELOG](../../CHANGELOG.md)。  
- 改组件库选型 → 更新 ADR-002，再回写本目录。
