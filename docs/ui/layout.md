# Layout — 应用壳与 Tauri WebView

> 壳层来源：OD `assets/app.css`（`.win` / `.app` / `.cols` / `.drawer`）。  
> 落地文件：`apps/gui/src/styles/app-shell.css`（架构文档称 `app-shell.css`）。

## 结构总览

```mermaid
flowchart TB
  win[win_titlebar_optional]
  app[app]
  appbar[appbar_48px]
  cols[cols_three_columns]
  side[side_248px]
  canvas[canvas_flex]
  right[right_360px]
  fab[fab_floating]
  drawer[drawer_settings_overlay]
  win --> app
  app --> appbar
  app --> cols
  cols --> side
  cols --> canvas
  cols --> right
  canvas --> fab
  app --> drawer
```

| 区域 | OD class | 职责 |
|------|----------|------|
| 窗口装饰 | `.win` / `.win-titlebar` | 原型用自定义标题栏；**Tauri 可用系统装饰**，实现时可省略 `.win` 或仅保留拖拽区 |
| 顶栏 | `.appbar` | 面包屑、快捷键提示、设置入口 |
| 左栏 | `.side` | 品牌、搜索、新建、文稿列表、健康状态、设置 |
| 中栏 | `.canvas` | 文稿标题、导入/预设 pill、编辑器、底部 FAB |
| 右栏 | `.right` | 处理结果列表、统计、一键复制 |
| 设置 | `.drawer` + `.scrim` | 右侧滑出设置；≤960px 变底栏 sheet |

### 分区方式

壳层不再靠左右栏之间的 `1px` 竖线分割三栏，而是用 **gutter + 卡片** 区分区域：

- 页面底：`--shell-bg`（对应 OD `--bg`）；顶栏 `.shell-appbar`、左 `.shell-side`、中 `.shell-canvas`、右 `.shell-right` 均为 `--shell-surface` 卡片（圆角、`border`、`box-shadow: var(--shell-card-shadow)`）。
- 统一 **`--shell-gutter: 12px`**：`.shell-app` 的 `padding` 与顶栏/三栏之间的 `gap`、`.shell-cols` 的 `gap` 均用同一变量（窗边距与卡间距一致）。
- 三栏之间用 grid **`gap`** 露出底色的 gutter，**不再**在左右栏上写 `border-right` / `border-left` 作为分栏线。
- **`.shell-cols.no-right`（桌面折叠结果栏；OD 原型为 `.cols.no-right`）**：仍为三列 grid，末列宽 **`0`**，`.shell-right-inner` **`translateX(100%)`** 滑出（与左栏同用 `grid-template-columns` 过渡）；并用 `margin-left: calc(-1 * var(--shell-gutter))` 吃掉末列前的 gap，避免收起后右侧多出一条 gutter。窄屏 `max-width: 1024px` 仍为固定抽屉（`.shell-right.is-open` + scrim）。

## 网格与断点

| 视口 | 行为 |
|------|------|
| 壳层 gutter | **12px** 全站统一（`--shell-gutter`） |
| 默认（设计宽约 1440） | `248 \| 1fr \| 360` |
| `.shell-cols.no-right` | 桌面：三列末轨 `0` + inner 滑出；窄屏见抽屉行 |
| `.shell-cols.collapsed` | 左栏收至 56px |
| `max-width: 1024px` | 左栏 mini；右栏改为绝对定位抽屉（`.shell-right.is-open` + scrim） |
| `max-width: 960px` | 设置 `.drawer` → 底部 sheet（高约 80vh） |
| `max-width: 800px` 或 `max-height: 600px` | FAB 全宽化；画布内边距缩小 |

**最小可用窗口**：设计按 **≥800×600** 保证主操作可达。Tauri `tauri.conf` 已设 `minWidth: 800` / `minHeight: 600`。

## 快捷键（Wave B 已落地）

| 键 | 行为 |
|----|------|
| `Ctrl+,` | 开/关设置 Drawer |
| `/` | 聚焦侧栏搜索（编辑器/输入框内不触发） |
| `Esc` | 依次关闭：删除确认 → 预设 popover → **规则 Modal**（含脏确认）→ 设置 → 窄屏结果抽屉 |

## 中栏与 FAB

- 编辑器：`.editor` + `.ta`（textarea）；空态 `.editor-empty`。  
- 浮动操作栏：`.fab` 绝对定位于 canvas 底部居中（`bottom: 24px`），含预设切换、状态文案、**编辑规则**、**处理文稿**主按钮。  
- `canvas-body` 底部 padding 需为 FAB 留空：`calc(var(--fab-h) + 32px + 32px)`。

## 设置 Drawer

- 打开：`.scrim` + `.drawer`（宽约 420px 级，见 app.css）。  
- 分区：字数与断句、LLM、隐私（见 [screens.md](./screens.md)）。  
- **不**用 shadcn `Sheet` 替换主设置（ADR-002）；`VerifyPage` 等次要页可用 shadcn Dialog/Sheet。

## Tauri 2 注意点

| 主题 | 约定 |
|------|------|
| 装饰 | 系统标题栏时去掉原型 `.win-titlebar`；保留应用内 `.appbar` |
| WebView | 标准 DOM + CSS；避免依赖浏览器扩展 API |
| 滚动 | `body { overflow: hidden }`；滚动落在 `.side-history` / `.canvas-body` / `.right-body` |
| 剪贴板 | 一键复制走 Tauri / Web Clipboard API（产品 US-06） |
| 文件导入 | `.txt` 经 Tauri 文件对话框（US-02） |
| 后端状态 | 侧栏 `.health` 与顶层 banner 同步 ADR-006 健康检查 |

## 与 React 分层

| 层 | 职责 |
|----|------|
| `app-shell.css` | 三栏几何、壳组件 class、动画 |
| Tailwind + shadcn | 表单控件、toast、次要页、可访问性原语 |
| 业务组件 | 调 `gui/api` HTTP；**不含**断句逻辑（ADR-007） |

## 相关

- [foundations.md](./foundations.md) · [screens.md](./screens.md)  
- [overview.md](../architecture/overview.md) · [ADR-001](../architecture/adr/001-tauri-desktop-shell.md) · [ADR-006](../architecture/adr/006-tauri-spawn-fastapi.md)
