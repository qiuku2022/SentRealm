# 壳层悬浮卡片 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 GUI 顶栏 + 左/中/右三栏从分割线分区改成统一 12px gutter 的中档悬浮卡片，去掉廉价硬切线。

**Architecture:** 纯 CSS 改造 `app-shell.css`：在 `:root` 增加 gutter/阴影变量；`.shell-app` 用 padding + gap 形成外圈与顶栏↔三栏间距；`.shell-cols` 用 `gap` 分隔三栏；四块区域共享卡片面（`--shell-surface`、圆角、完整描边、克制阴影）。不新增 React Card 包装。同步 `docs/ui/layout.md` 与 `foundations.md`。

**Tech Stack:** Tauri WebView + React 壳层；样式 SSOT 为 `apps/gui/src/styles/app-shell.css`（OD 移植）；文档在 `docs/ui/`。

**Spec:** [docs/superpowers/specs/2026-09-17-shell-floating-cards-design.md](../specs/2026-09-17-shell-floating-cards-design.md)

## Global Constraints

- 只改壳层视觉与对应 UI 文档；不改业务逻辑 / API / 断句规则
- 卡片区域：顶栏 + 左 + 中 + 右；强度「中」；统一 gutter **12px**
- Token：页面底 `--shell-bg`；卡片面 `--shell-surface`；圆角 `--shell-r-lg`（12px）；描边 `1px solid var(--shell-border)`；阴影 `0 4px 16px rgba(0,0,0,0.28)`（可用 `hsl(0 0% 0% / 0.28)` 以与文件内写法一致）
- 禁止业务组件写死随意 hex；不引入第二套色板；不做 light 主题
- FAB / Drawer 阴影与 z-index 保持强于壳层卡片
- 本仓库 **仅在用户明确要求时 commit**；计划中的 Commit 步骤默认跳过，除非用户说「提交」
- commit message 若执行：全文中文，说清 why（无 `feat:` 等英文前缀）

## File map

| 文件 | 职责 |
|------|------|
| `apps/gui/src/styles/app-shell.css` | 变量、gutter、卡片面、去分割线、`no-right` 网格、≤1024 右栏 top/inset 适配 |
| `docs/ui/layout.md` | 壳层结构描述：卡片分区替代分割线 |
| `docs/ui/foundations.md` | 阴影约定：主面板允许本 spec 克制阴影 |
| `docs/superpowers/specs/2026-09-17-shell-floating-cards-design.md` | 实现后把状态改为「已实现」（可选，随 Task 3） |

---

### Task 1: 壳层 CSS — 变量、gutter、四卡样式

**Files:**
- Modify: `apps/gui/src/styles/app-shell.css`（`:root`、`.shell-app`、`.shell-appbar`、`.shell-cols`、`.shell-side` / `.shell-canvas` / `.shell-right` 及相关 `no-right`）

**Interfaces:**
- Consumes: 现有 `--shell-bg`、`--shell-surface`、`--shell-border`、`--shell-r-lg`、`--shell-topbar-h`、`--shell-sidebar-w`、`--shell-right-w`
- Produces: `--shell-gutter`、`--shell-card-shadow`；四区域视觉卡片；`.shell-cols` 的 `gap`

- [ ] **Step 1: 在 `:root` 增加 gutter / 卡片阴影变量**

在现有 `:root` 块内（约 `--shell-r-xl` 附近）追加：

```css
  --shell-gutter: 12px;
  --shell-card-shadow: 0 4px 16px hsl(0 0% 0% / 0.28);
```

- [ ] **Step 2: `.shell-app` 加统一外圈 padding，并用 flex `gap` 分隔顶栏与三栏**

将 `.shell-app` 改为（保留其余属性）：

```css
.shell-app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
  background: var(--shell-bg);
  color: var(--shell-fg);
  color-scheme: dark;
  font-family: var(--font-ui);
  padding: var(--shell-gutter);
  gap: var(--shell-gutter);
  box-sizing: border-box;
}
```

- [ ] **Step 3: 抽取并应用四卡共享样式；去掉侧栏分割线**

把 `.shell-appbar` 的 `background: var(--shell-bg)` 改为卡片面，并加圆角/描边/阴影；对 `.shell-side`、`.shell-canvas`、`.shell-right` 同样处理；**删除** `.shell-side` 的 `border-right` 与 `.shell-right` 的 `border-left`（及 `no-right` 里仅用于「透明分割线」的 `border-left-color` 逻辑可删或改为无害）。

推荐写成共享规则，避免四处复制：

```css
.shell-appbar,
.shell-side,
.shell-canvas,
.shell-right {
  background: var(--shell-surface);
  border: 1px solid var(--shell-border);
  border-radius: var(--shell-r-lg);
  box-shadow: var(--shell-card-shadow);
  min-height: 0;
}

.shell-appbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--shell-topbar-h);
  padding: 0 16px;
  flex-shrink: 0;
  /* 勿再设 background: var(--shell-bg) */
}

.shell-side,
.shell-canvas,
.shell-right {
  display: flex;
  flex-direction: column;
  /* 勿再设 border-right / border-left 分割线 */
}

.shell-canvas {
  position: relative;
}

.shell-right {
  overflow: hidden;
  min-width: 0;
}
```

若原文件里 `.shell-side, .shell-canvas, .shell-right { min-height; display; flex-direction }` 与 border 规则分开，合并时以「无分割线 + 共享卡片」为准，保留各自特有属性（如 canvas 的 `position: relative`）。

- [ ] **Step 4: `.shell-cols` 加 `gap`，并修正 `no-right` 为两列，避免右侧悬空 12px**

```css
.shell-cols {
  display: grid;
  grid-template-columns: var(--shell-sidebar-w) minmax(0, 1fr) var(--shell-right-w);
  flex: 1;
  min-height: 0;
  gap: var(--shell-gutter);
  transition:
    grid-template-columns 0.22s cubic-bezier(0.2, 0.7, 0.2, 1),
    filter 0.18s ease;
}

.shell-cols.no-right {
  grid-template-columns: var(--shell-sidebar-w) minmax(0, 1fr);
}

.shell-cols.no-right .shell-right {
  display: none; /* 或保持现有 slide 动画方案：见下一步说明 */
}
```

**动画取舍（必须选一并写进代码注释一行）：**

- **A（推荐，简单）**：`no-right` 时 `.shell-right { display: none; }`，放弃右栏滑出动画，避免 `0` 列 + `gap` 留白。
- **B**：保留三列动画则需把 `gap` 在 `no-right` 时改为 `gap: var(--shell-gutter) var(--shell-gutter) 0` 或临时 `column-gap` 处理，并继续 `0` 列宽——更脆。

默认实现 **A**。若现有 E2E/视觉依赖 slide，再改 B。

同步检查 `is-collapsed` 的 `grid-template-columns`（含 `is-collapsed.no-right`）：在有 `gap` 后仍应使用 `var(--shell-sidebar-collapsed-w)`，且 `no-right` 时同样两列。

- [ ] **Step 5: 适配 ≤1024px 固定右栏的 `top` / 边距**

当前：

```css
.shell-right {
  position: fixed;
  top: var(--shell-topbar-h);
  right: 0;
  bottom: 0;
  ...
}
```

改为与卡片 gutter 对齐（仍为抽屉浮层，可用更强阴影覆盖卡片阴影）：

```css
@media (max-width: 1024px) {
  .shell-cols,
  .shell-cols.is-collapsed,
  .shell-cols.no-right,
  .shell-cols.is-collapsed.no-right {
    grid-template-columns: var(--shell-sidebar-w) 1fr;
  }

  .shell-cols.is-collapsed {
    grid-template-columns: var(--shell-sidebar-collapsed-w) 1fr;
  }

  .shell-right {
    display: flex; /* 覆盖 no-right 的 display:none：窄屏靠 is-open 抽屉，不依赖 cols 第三列 */
    position: fixed;
    top: calc(var(--shell-gutter) + var(--shell-topbar-h) + var(--shell-gutter));
    right: var(--shell-gutter);
    bottom: var(--shell-gutter);
    width: min(360px, calc(92vw - var(--shell-gutter)));
    z-index: 30;
    overflow: visible;
    transform: translateX(calc(100% + var(--shell-gutter)));
    transition: transform 0.22s cubic-bezier(0.2, 0.7, 0.2, 1);
    box-shadow: -16px 0 40px hsl(0 0% 0% / 0.55);
    /* 保持卡片圆角/描边；抽屉打开时仍用 is-open */
  }

  .shell-right.is-open {
    transform: translateX(0);
  }
}
```

注意：若桌面 `no-right` 用了 `display: none`，窄屏媒体查询必须把 `.shell-right` 设回可显示（`display: flex`），否则「结果」抽屉打不开。桌面有右栏时不要 `display: none`。

更稳妥写法：

```css
.shell-cols.no-right .shell-right {
  display: none;
}

@media (max-width: 1024px) {
  .shell-cols.no-right .shell-right {
    display: flex; /* 窄屏始终用 fixed 抽屉；是否可见由 .is-open / transform 控制 */
  }
}
```

- [ ] **Step 6: 静态核对**

在仓库根目录运行：

```powershell
Select-String -Path "apps/gui/src/styles/app-shell.css" -Pattern "border-right:\s*1px solid var\(--shell-border\)|border-left:\s*1px solid var\(--shell-border\)"
Select-String -Path "apps/gui/src/styles/app-shell.css" -Pattern "--shell-gutter|--shell-card-shadow"
```

Expected：

- 第一条：`.shell-side` / `.shell-right` **主栏分割线**不应再匹配（若其它组件如 rules-nav 仍有 `border-right` 可保留）
- 第二条：两处变量均命中

目视（`pnpm --filter` / 文档中的 GUI dev 命令，见 `docs/dev/running-locally.md`）：

- 约 1440 宽：四张卡、间距均匀、无三栏硬线
- 无右栏：两卡 + 顶栏，右侧无 12px 空缝
- 收起左栏：左卡变窄仍完整
- 开 FAB / 设置 Drawer / 窄屏结果：叠层正常

- [ ] **Step 7: Commit（仅用户要求时）**

```bash
git add apps/gui/src/styles/app-shell.css
git commit -m "$(cat <<'EOF'
壳层主面板改为统一 gutter 的悬浮卡片，去掉三栏硬分割线。

EOF
)"
```

---

### Task 2: 同步 UI 文档

**Files:**
- Modify: `docs/ui/layout.md`
- Modify: `docs/ui/foundations.md`

**Interfaces:**
- Consumes: Task 1 已落地的 gutter / 卡片行为
- Produces: 文档与实现一致

- [ ] **Step 1: 更新 `docs/ui/layout.md`**

在「结构总览」表格或紧随其后增加「分区方式」说明，替换任何「靠 border 分割三栏」的暗示。写入要点：

- 页面底 `--shell-bg`；顶栏 / 左 / 中 / 右为 `--shell-surface` 卡片
- 统一 `--shell-gutter: 12px`（窗边与卡间）
- 三栏之间用 grid `gap`，不再用左右 `1px` 分割线
- `no-right`：两列网格，右卡隐藏（窄屏除外，见 media）

可在「网格与断点」表中补一行：`壳层 gutter | 12px 全站统一`。

- [ ] **Step 2: 更新 `docs/ui/foundations.md`**

将设计语言摘要中：

> 阴影 | 壳层默认几乎无阴影；**FAB / Drawer / 窄屏右栏**允许克制阴影

改为：

> 阴影 | 壳层主面板（顶栏 + 三栏卡片）使用克制阴影 `0 4px 16px …0.28`；**FAB / Drawer / 窄屏右栏抽屉**可用更强阴影以保持叠层

在「Component token」表为壳层主面板补一行，例如：

| 壳层主面板 `.shell-appbar` / `.shell-side` / `.shell-canvas` / `.shell-right` | `bg: var(--surface)`；`border`；`shadow: var(--shell-card-shadow)`；`radius: --r-lg` |

- [ ] **Step 3: Commit（仅用户要求时）**

```bash
git add docs/ui/layout.md docs/ui/foundations.md
git commit -m "$(cat <<'EOF'
同步 UI 文档：壳层改为 gutter 卡片分区，并更新阴影约定。

EOF
)"
```

---

### Task 3: Spec 状态与验收勾选

**Files:**
- Modify: `docs/superpowers/specs/2026-09-17-shell-floating-cards-design.md`

**Interfaces:**
- Consumes: Task 1–2 完成结果
- Produces: spec 状态「已实现」+ 验收清单勾选

- [ ] **Step 1: 将 spec 头部 `状态：待实现` 改为 `状态：已实现`**

- [ ] **Step 2: 按实际目视结果勾选「验收」中的 checkbox**（未验证的项保持未勾选并在文内一行注明原因）

- [ ] **Step 3: Commit（仅用户要求时）**

```bash
git add docs/superpowers/specs/2026-09-17-shell-floating-cards-design.md
git commit -m "$(cat <<'EOF'
将壳层悬浮卡片设计说明标为已实现并更新验收勾选。

EOF
)"
```

---

## Self-review (plan vs spec)

| Spec 要求 | 对应任务 |
|-----------|----------|
| 四卡 + 统一 12px gutter | Task 1 |
| 中档描边 + 克制阴影 | Task 1 |
| 去掉分割线 | Task 1 |
| `no-right` / collapsed / ≤1024 / FAB·Drawer | Task 1 Step 4–6 |
| layout.md / foundations.md | Task 2 |
| 验收清单 | Task 3 |
| 不改 JSX（除非必要） | 本计划默认不改 `AppShell.tsx`；若 padding 导致高度问题用 `box-sizing: border-box` 已覆盖 |

无 TBD；`no-right` 动画取舍已默认 A 并写明窄屏 `display` 恢复。
