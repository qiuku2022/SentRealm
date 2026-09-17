# 壳层悬浮卡片 — 设计说明

**日期**：2026-09-17  
**状态**：已实现  
**范围**：GUI 主壳层视觉（顶栏 + 三栏），不改业务逻辑 / API / 断句规则

## 目标

用统一间距的悬浮卡片替代三栏 `1px` 分割线，减轻「靠线硬切」的廉价感，同时保持现有布局几何与响应式行为。

## 已确认决策

| 项 | 选择 |
|----|------|
| 卡片区域 | 顶栏 + 左栏 + 中栏 + 右栏（方案 B） |
| 视觉强度 | 中：色差 + 淡描边 + 克制阴影 |
| 间距 | 统一 gutter **12px**（窗边↔卡、卡↔卡） |
| 实现方式 | 方案 1：现有壳层 CSS 直接改造，不加 React Card 包装层 |

## 视觉规格

### 结构

```
[ 页面底 --bg ]
  gutter 12px
  [ appbar 卡 --surface ]          ← 全宽
  gap 12px
  [ side 卡 ] 12px [ canvas 卡 ] 12px [ right 卡 ]
  gutter 12px
```

- 去掉 `.shell-side` 的 `border-right`、`.shell-right` 的 `border-left`（及同类「只作分割」的线）。
- 四块区域各自成为完整边框卡片，不再靠相邻边框拼出分区。

### Token / 数值

| 属性 | 值 | 说明 |
|------|-----|------|
| 页面底 | `--bg` / `--shell-bg` | 保持近黑 |
| 卡片面 | `--surface` | 略亮于页面底 |
| 圆角 | `--r-lg`（12px） | 与编辑器卡片一致 |
| 描边 | `1px solid` `--border` / `--shell-border` | 四边完整 |
| 阴影 | `0 4px 16px rgba(0,0,0,0.28)` | 弱于 FAB（`0 12px 32px …0.45`） |
| gutter / gap | `12px` | 外圈与卡间统一 |

可在 `app-shell.css` 增加壳层变量（如 `--shell-gutter`、`--shell-card-shadow`），避免魔法数散落。

### 状态与响应式

| 场景 | 行为 |
|------|------|
| `.cols.no-right` | 桌面：保留三列，末列 `0` + inner `translateX` 滑出；负 margin 吸收 trailing gap；窄屏 media 仍用抽屉 |
| `.cols.collapsed` | 左卡变窄（约 56px），仍为同一张卡（圆角/描边/阴影不变） |
| `≤1024px` 右栏抽屉 | 右栏继续用现有绝对定位 + scrim；壳层卡片样式作用于仍嵌入网格的面板 |
| FAB / Drawer | 层级与阴影保持现状，不被壳层卡片盖过 |

## 非目标

- 不引入第二套 UI 色板或随意 hex
- 不把主设置 Drawer / FAB 改成 shadcn `Card`
- 不做 light 主题
- 不改断点逻辑本身（仅适配卡片外观）

## 实现落点

| 文件 | 改动 |
|------|------|
| `apps/gui/src/styles/app-shell.css` | 主改：gutter、卡片面、去分割线、阴影/描边 |
| `docs/ui/layout.md` | 更新壳层描述：卡片分区替代分割线 |
| `docs/ui/foundations.md` | 更新「壳层默认几乎无阴影」——壳层主面板允许本 spec 的克制阴影 |

原则上不改 `AppShell.tsx` 等 JSX，除非现有 DOM 无法挂 gutter（例如需要给 `.shell-app` / `.shell-cols` 加一层 padding 容器时做最小结构调整）。

## 验收

- [ ] 默认桌面宽（约 1440）：可见四张卡 + 统一 12px 间距，无三栏硬分割线
- [ ] 空态 / 无右栏：中卡拓宽，无残留分割线或错位 gutter
- [ ] 左栏 collapsed：左卡变窄仍完整
- [ ] FAB、设置 Drawer、窄屏结果抽屉叠层正常
- [ ] 视觉仍符合 dark-only、白主按钮、token 约束（无 ad-hoc 色）

> **未勾选原因**：Task 1–3 未启动 GUI（`pnpm` / Tauri dev）目视；CSS 与 `layout.md` / `foundations.md` 已按本 spec 落地，静态核对见 Task 1 Select-String。

## 相关

- [docs/ui/layout.md](../../ui/layout.md)
- [docs/ui/foundations.md](../../ui/foundations.md)
- 落地样式：`apps/gui/src/styles/app-shell.css`
