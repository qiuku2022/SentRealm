# Foundations — 设计 token 与 shadcn 映射

> **视觉 SSOT**：Open Design `assets/app.css` 的 `:root`（Codex-desktop dark、8pt 网格）。  
> **实现**：Tauri WebView 内 React；主题以 **dark-only** 落地（MVP 不做 light 切换，除非产品另行要求）。

## 设计语言摘要

| 维度 | 约定 |
|------|------|
| 主题 | 近黑底、中性灰层级、**白色主操作**（非彩色品牌色） |
| 状态色 | 成功绿 / 警告陶土橙（超长行）/ 错误红 |
| 密度 | 桌面工具偏紧：正文 UI **13px**，编辑区 **15.5px** |
| 网格 | 8pt（`--s-1`…`--s-9`） |
| 阴影 | 壳层默认几乎无阴影；**FAB / Drawer / 窄屏右栏**允许克制阴影 |
| 焦点 | 3px `--accent-soft` 软环，不用彩色 ring |

## 1. Primitive（OD 原始值）

### 表面与线

| Token | Hex / 值 | HSL（约） | 用途 |
|-------|----------|-----------|------|
| `--bg` | `#0d0d0d` | `0 0% 5%` | 应用底 |
| `--surface` | `#171717` | `0 0% 9%` | FAB、浮层底 |
| `--surface-2` | `#1c1c1c` | `0 0% 11%` | 次级块、搜索框底 |
| `--hover` / `--field` / `--pop` | `#1f1f1f` | `0 0% 12%` | 悬停 / 字段 / 弹出 |
| `--input` | `#262626` | `0 0% 15%` | 输入表面（与 border 同级） |
| `--shade` | `rgba(0,0,0,0.55)` | — | scrim |
| `--border` | `#262626` | `0 0% 15%` | 默认分割线 |
| `--border-strong` | `#3a3a3a` | `0 0% 23%` | hover / focus 边框 |
| `--border-soft` | `#1f1f1f` | `0 0% 12%` | 更弱分割 |
| `--win-bg` | `#0a0a0a` | `0 0% 4%` | 标题栏（可略深于 app） |
| `--win-close-hover` | `#c42b1c` | `5 75% 44%` | 关闭按钮悬停 |

### 文字

| Token | Hex | HSL（约） | 用途 |
|-------|-----|-----------|------|
| `--fg` | `#ececec` | `0 0% 93%` | 主文字 |
| `--fg-2` | `#d4d4d4` | `0 0% 83%` | 次主文字、当前 crumb |
| `--muted` | `#a3a3a3` | `0 0% 64%` | 图标、辅助 |
| `--muted-2` | `#737373` | `0 0% 45%` | placeholder、mono 副文 |
| `--muted-3` | `#525252` | `0 0% 32%` | 分隔符、最弱文 |
| `--on-accent` | `#0d0d0d` | `0 0% 5%` | 白底按钮上的字 |
| `--fg-hover` | `#f5f5f5` | — | 主按钮 hover |
| `--fg-active` | `#e8e8e8` | — | 主按钮 active |

### 强调与状态

| Token | 值 | 用途 |
|-------|-----|------|
| `--accent` | `#ffffff` | 主操作「白」 |
| `--accent-soft` | `rgba(255,255,255,0.06)` | 悬停底、选中底、焦点环 |
| `--accent-2` | `rgba(255,255,255,0.10)` | 稍强白叠 |
| `--accent-line` | `rgba(255,255,255,0.16)` | 白描边 |
| `--ok` | `#4ade80` | 健康就绪、复制成功 |
| `--ok-soft` | `rgba(74,222,128,0.14)` | 成功底 |
| `--warn` | `#d97757` | **超长标记行** |
| `--warn-soft` / `--warn-line` | 见 app.css | 标记行底 / 左边线 |
| `--err` | `#f87171` | 后端错误、危险 |
| `--err-soft` | `rgba(248,113,113,0.12)` | 错误底 |

### 圆角

| Token | 值 | 典型用途 |
|-------|-----|----------|
| `--r-xs` | 4px | kbd、微标 |
| `--r-sm` | 6px | 小按钮、图标钮 |
| `--r-md` | 8px | 输入、chip、列表项 |
| `--r-lg` | 12px | 编辑器卡片 |
| `--r-xl` | 14px | FAB |
| `--r-pill` | 999px | pill chip |

### 间距（8pt）

`--s-1` 4 → `--s-2` 8 → `--s-3` 12 → `--s-4` 16 → `--s-5` 20 → `--s-6` 24 → `--s-7` 32 → `--s-8` 40 → `--s-9` 48。

### 布局尺寸

| Token | 值 |
|-------|-----|
| `--topbar-h` | 48px |
| `--sidebar-w` | 248px |
| `--right-w` | 360px |
| `--canvas-pad` | 32px |
| `--fab-h` | 48px |

### 字体

| Token | 栈 |
|-------|-----|
| `--font-ui` / `--font-display` / `--font-zh` | `"Microsoft YaHei UI","Microsoft YaHei","Segoe UI",…,system-ui,sans-serif` |
| `--font-mono` | `Consolas,"JetBrains Mono","SF Mono","Cascadia Code",ui-monospace,…` |

字号锚点（OD `index.html` 规格）：UI 13 / 编辑 15.5 / 文档标题 14–18 / 小标题 mono 12 uppercase / 统计 mono 10.5–11。

## 2. Semantic → shadcn CSS 变量

落地到 `apps/gui` 的 `globals.css`（或等价）时，**仅维护 `.dark`（或把 dark 值写在 `:root`）**。通道用 **HSL 空格分隔**（兼容 Tailwind `hsl(var(--x) / <alpha>)`）；若 CLI 生成 OKLCH，可改写为下列等价色相。

| shadcn 变量 | 建议 HSL 通道 | 对应 OD | Tailwind 示例 |
|-------------|---------------|---------|----------------|
| `--background` | `0 0% 5%` | `--bg` | `bg-background` |
| `--foreground` | `0 0% 93%` | `--fg` | `text-foreground` |
| `--card` | `0 0% 9%` | `--surface` | `bg-card` |
| `--card-foreground` | `0 0% 93%` | `--fg` | `text-card-foreground` |
| `--popover` | `0 0% 12%` | `--pop` | `bg-popover` |
| `--popover-foreground` | `0 0% 93%` | `--fg` | |
| `--primary` | `0 0% 100%` | `--accent` | `bg-primary`（白底主按钮） |
| `--primary-foreground` | `0 0% 5%` | `--on-accent` | `text-primary-foreground` |
| `--secondary` | `0 0% 11%` | `--surface-2` | `bg-secondary` |
| `--secondary-foreground` | `0 0% 83%` | `--fg-2` | |
| `--muted` | `0 0% 11%` | `--surface-2` | `bg-muted` |
| `--muted-foreground` | `0 0% 45%` | `--muted-2` | `text-muted-foreground` |
| `--accent` | `0 0% 12%` | `--hover` / soft 白叠 | hover 面（**勿**与 OD `--accent` 白混淆） |
| `--accent-foreground` | `0 0% 93%` | `--fg` | |
| `--destructive` | `0 91% 71%` | `--err` | `text-destructive` / `bg-destructive` |
| `--destructive-foreground` | `0 0% 5%` | 深底上的对比 | |
| `--border` | `0 0% 15%` | `--border` | `border-border` |
| `--input` | `0 0% 15%` | `--input` | `border-input` |
| `--ring` | `0 0% 100%` / 低透明度 | `--accent-line` | focus；实现可用 soft 白环 |
| `--radius` | `0.5rem`（8px） | `--r-md` | `rounded-md` 基准 |

### 产品扩展色（非 shadcn 默认，需写入 theme）

| 扩展变量 | HSL / 值 | Tailwind 建议 | 用途 |
|----------|----------|---------------|------|
| `--success` | `142 69% 58%` | `text-success` / `bg-success/14` | 后端就绪、复制成功 |
| `--warning` | `15 63% 60%` | `text-warning` / `bg-warning/12` | **超长行**（US-08） |
| `--sidebar` / `--sidebar-*` | 对齐 `--bg` / `--border` | `bg-sidebar` | 左栏（可选 shadcn sidebar 预设） |

在 Tailwind `theme.extend.colors` 中注册 `success` / `warning`；**禁止**在业务组件里写死 `#d97757` 等 hex。

## 3. Component token（壳层专用）

壳层继续用 OD 名，不必全部塞进 shadcn：

| 组件 | 关键 token / class |
|------|-------------------|
| 主按钮 `.btn-go` / `.btn-new` | `bg: var(--fg)`；`color: var(--on-accent)` |
| 超长行 `.result-line.long` | `background: var(--warn-soft)`；左边线 `var(--warn-line)` |
| 健康点 `.health .dot` | `--ok` / `.err`→`--err` / `.warn`→`--warn` |
| FAB | `--surface` + 阴影 `0 12px 32px rgba(0,0,0,0.45)` |

## 4. 实现核对清单

- [ ] `globals.css` 语义色与上表一致；主按钮为白底深字  
- [ ] `app-shell.css` 自 OD `assets/app.css` 移植，保留 layout 尺寸变量  
- [ ] 超长行仅用 `--warning` / `.result-line.long`，不用 destructive 红  
- [ ] 无第二套 UI 库色板；无随意 `bg-blue-500`  
- [ ] 需要时对照 OD board 截图做视觉 diff  


## 相关

- [layout.md](./layout.md) · [components.md](./components.md)  
- [ADR-002](../architecture/adr/002-shadcn-ui.md)  
- OD：`assets/app.css`、`index.html`（token 规格页）
