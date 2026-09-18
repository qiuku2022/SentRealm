# Foundations — 设计 token 与 shadcn 映射

> **配色 SSOT**：`.local/od-modern-colors/`（Open Design `sentrealm-modern-colors` 配色文档）+ 仓库生产副本 [`apps/gui/src/styles/tokens-modern.css`](../../apps/gui/src/styles/tokens-modern.css)。  
> **布局原型**：Open Design `sentrealm-modern-ui`（boards / 壳层结构）。  
> **实现**：Tauri WebView 内 React；主题 **light-only**（Modern 冷中性浅底 + indigo accent）。

改色流程：先改 `.local/od-modern-colors/assets/colors.css`（及文档页），再 sync `tokens-modern.css`；[`globals.css`](../../apps/gui/src/styles/globals.css) / [`app-shell.css`](../../apps/gui/src/styles/app-shell.css) **只做别名映射**，禁止再各自硬编码第二套 hex。

## 设计语言摘要

| 维度 | 约定 |
|------|------|
| 主题 | 浅灰底 `#f7f8fc`、白表面、**indigo 主操作** `#4f46e5` |
| 状态色 | 成功绿 / 警告琥珀（超长行）/ 错误红 |
| 密度 | 桌面工具偏紧：正文 UI **14px**；标准控件高 **`--shell-control-h` = 32px**（与 Win11 常用控件高对齐，保证 4px 半径相对曲率一致）；FAB 条高 = 控件高 + 24px（避免矮条 + 8px 读成胶囊） |
| 网格 | Modern spacing（4 / 8 / 12 / 16 / 20 / 24 / 32 / 48） |
| 阴影 | 三栏/顶栏用 `--shell-card-shadow`；**FAB** 用 `--shell-fab-shadow`（介于 card 与 elev）；**菜单 / Drawer** 用更重的 `--shell-elev-raised` |
| 焦点 | indigo soft ring `0 0 0 4px rgba(79,70,229,0.24)` |

## 1. Primitive（`tokens-modern.css`）

### 表面与线

| Token | Hex / 值 | 用途 |
|-------|----------|------|
| `--bg` / `--shell-bg` | `#f7f8fc` | 应用底 / gutter 露出面 |
| `--surface` / `--shell-surface` | `#ffffff` | 侧栏、右栏、FAB、浮层 |
| `--surface-warm` / `--shell-surface-warm` | `#eef1ff` | 选中项、accent 浅底 |
| `--border` / `--shell-border` | `#dfe3ed` | 默认分割线 |
| `--border-soft` / `--shell-border-soft` | `#eef1f7` | 更弱分割 |
| `--accent` / `--shell-accent` | `#4f46e5` | 主操作、焦点 |
| `--accent-on` / `--shell-accent-on` | `#ffffff` | accent 上的字 |

### Soft 填充（文档公式）

| Token | 公式 |
|-------|------|
| `--success-soft` / `--shell-ok-soft` | `color-mix(in oklab, var(--success) 14%, var(--surface))` |
| `--warn-soft` / `--shell-warn-soft` | `color-mix(in oklab, var(--warn) 16%, var(--surface))` |
| `--danger-soft` / `--shell-err-soft` | `color-mix(in oklab, var(--danger) 12%, var(--surface))` |
| `--accent-soft` / `--shell-accent-soft` | `color-mix(in oklab, var(--accent) 10%, var(--surface))` |
| `--accent-hover` | `color-mix(in oklab, var(--accent), black 8%)` |

### 文字与状态

| Token | Hex | 用途 |
|-------|-----|------|
| `--fg` / `--shell-fg` | `#111827` | 主文字 |
| `--fg-2` / `--shell-fg-2` | `#374151` | 次主文字 |
| `--muted` / `--shell-muted` | `#6b7280` | 辅助 |
| `--success` / `--shell-ok` / `--shell-success` | `#10b981` | 健康就绪、复制成功 |
| `--warn` / `--shell-warn` | `#f59e0b` | **超长标记行** |
| `--danger` / `--shell-err` / `--shell-danger` | `#ef4444` | 错误、危险 |

文档映射表额外别名（与旧名并存）：`--shell-fg-muted`、`--shell-fg-secondary`、`--shell-accent-fg`、`--shell-surface-muted`、`--shell-border-subtle`。

### 圆角与布局

壳层圆角对齐 **Windows 11 Fluent**（[Geometry](https://learn.microsoft.com/windows/apps/design/signature-experiences/geometry)），不再跟 Modern 文档页的 10/16/24。

| Token | 值 | 用途 |
|-------|-----|------|
| `--shell-r-md` | **4px** | 页内控件（按钮、输入、列表项、菜单项）；可点击 chip / 信息状态条（含 `.shell-pill*`、`.shell-right-live`、`.shell-drawer-key-pill`——类名可含 pill，曲率仍按 4px，不再做胶囊造型）；页内嵌套面（如 `.shell-editor`） |
| `--shell-control-h` | **32px** | 标准控件高度；文字按钮 / chip / 主路径图标按钮统一此高度，避免「同 4px、不同高 → 相对曲率不一」 |
| 实心主按钮描边 | `1px solid` 同色边 | `.shell-btn-go` / `.shell-btn-copy` / `.shell-drawer-btn-primary` 等与描边按钮共用同一 border-box，避免实心填色看起来更圆 |
| `--shell-r-lg` / `--shell-r-xl` | **8px** | 顶层容器（悬浮卡片、FAB、Drawer）；与 Win11 窗口默认曲率一致 |
| shadcn `--radius` | `0.5rem`（8px） | 容器基准：`rounded-lg` / `rounded-xl` → 8px |
| shadcn `--radius-sm` / `--radius-md` | `0.25rem`（4px） | 控件：`rounded-sm` / `rounded-md` → 4px（与 `--shell-r-md` 一致） |
| 允许 `999px` / 全圆 | 仅几何圆 | 状态圆点（`.dot`）、Toggle 开关轨道/拇指、滚动条拇指 |
| 禁止 | **6px / 10 / 16 / 24**；营销式胶囊按钮 | 中间档与 OD 大圆角不用于生产 GUI；chip 不得用 `999px` |
| 嵌套圆角 | 见下 | **不靠改 radius token 对齐观感**；用相对曲率（同高）、border-box、边框与阴影 |
| `--shell-sidebar-w` | 248px | |
| `--shell-right-w` | 320px | |
| `--shell-fab-h` | `calc(32px + 24px)` = **56px** | 悬浮条；内边距 12px + `1px` border + `--shell-fab-shadow`，使 8px 顶层圆角读成矮卡片而非胶囊 |
| `--shell-fab-shadow` | 双层，轻于 elev | 仅 FAB；菜单 / Drawer 仍用 `--shell-elev-raised` |
| `--shell-topbar-h` | 40px | |
| `--shell-gutter` | 12px | 窗边距与卡间距 |

**嵌套圆角**：

- **有 ≥8px gutter**（如 `.shell-editor` 在 canvas `padding: 20px` 内）：内面用 `--shell-r-md`；不要套 `outer − padding`（会为负）。
- **贴边嵌套**（如 `.shell-meta-bar` 贴编辑区底）：父级 `overflow: hidden`，子底角 `0`，由父圆角裁切，避免双半径叠缝。

### 字体

| Token | 栈 |
|-------|-----|
| `--font-ui` / `--font-body` | `Inter, "Microsoft YaHei UI", …, system-ui, sans-serif` |
| `--font-mono` | `"Geist Mono", ui-monospace, Menlo, …` |

## 2. Semantic → shadcn / Tailwind

[`globals.css`](../../apps/gui/src/styles/globals.css) 的 `@theme` **直接绑定 Primitive**（`--color-primary: var(--accent)` 等），不再维护第二套 HSL hex。

| Tailwind / shadcn | 绑定 | 对应 Primitive |
|-------------------|------|----------------|
| `bg-background` | `--color-background` | `--bg` |
| `text-foreground` | `--color-foreground` | `--fg` |
| `bg-card` / popover | `--color-card` | `--surface` |
| `bg-primary` | `--color-primary` | `--accent` |
| `text-primary-foreground` | `--color-primary-foreground` | `--accent-on` |
| `bg-muted` | `--color-muted` | `--border-soft`（面） |
| `text-muted-foreground` | `--color-muted-foreground` | `--muted`（字） |
| `bg-accent`（hover 面） | `--color-accent` | `--surface-warm`（**勿**与品牌 `--accent` 混淆） |
| `bg-destructive` | `--color-destructive` | `--danger` |
| `text-success` / `text-warning` | success / warn | `--success` / `--warn` |
| `--radius` | `0.5rem`（8px） | Win11 顶层容器；`rounded-md`/`rounded-sm` → 4px |

主按钮为 **indigo 底白字**。

## 3. Component token（壳层专用）

| 组件 | 关键 token / class |
|------|-------------------|
| 三栏 `.shell-side` / `.shell-canvas` / `.shell-right` | 悬浮卡片：`border` + `border-radius: var(--shell-r-lg)` + `box-shadow: var(--shell-card-shadow)`；壳层 `--shell-gutter: 12px` |
| 主按钮 `.shell-btn-go` / `.shell-drawer-btn-primary` | `bg: var(--shell-accent)`；hover → `--shell-accent-hover`；字 `--shell-accent-on`；`1px` 同色边 + `box-sizing: border-box` |
| 超长行 `.shell-result-line.is-long` | `background: var(--shell-warn-soft)`；**禁止** danger |
| FAB | `--shell-surface` + `1px` border + `var(--shell-fab-shadow)`；半径仍 `--shell-r-xl` |
| Toast（Sonner） | light theme；变量绑 Primitive（见 `app-shell.css` 末尾） |

## 4. 禁令

- 勿引入第二套品牌色；强调只加深/减淡 `--accent` 或用 semantic。
- 超长行只用 `--warn` / warn-soft，不用 `--danger` / destructive。
- 组件层禁止写死 hex。
- 主按钮 hover：加深底色并保持 `--accent-on`。

## 5. 实现核对清单

- [x] `tokens-modern.css` 与 `.local` colors.css 对齐  
- [x] `app-shell.css` / `globals.css` 仅别名，无第二 hex 源  
- [x] 主按钮 indigo；超长行 warn  
- [x] Sonner 去掉 `richColors`  
- [ ] 需要时对照 OD board / 配色文档 swatch 做视觉 diff  

## 相关

- [layout.md](./layout.md) · [components.md](./components.md)  
- [ADR-002](../architecture/adr/002-shadcn-ui.md)  
- 配色文档：`.local/od-modern-colors/` · 布局原型：`sentrealm-modern-ui`
