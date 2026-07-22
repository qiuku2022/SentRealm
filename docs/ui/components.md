# Components — OD → shadcn / 自定义映射

> 选型铁律见 [ADR-002](../architecture/adr/002-shadcn-ui.md)：主壳用 OD/`app-shell.css`；控件优先 shadcn 源码组件；禁止第二套完整 UI 库。

## 映射总表

| 产品能力 / OD 元素 | 落地方式 | 建议 shadcn / 库 | 备注 |
|--------------------|----------|------------------|------|
| 三栏壳、顶栏、侧栏、右栏、FAB | **自定义** `app-shell.css` | — | 勿用 Dashboard 模板硬套 |
| 文稿编辑 `.ta` | 可包一层 | `Textarea` | 字号/行高跟 foundations；class 可挂到壳样式 |
| 导入 .txt | 按钮 + 隐藏 `<input type="file">` | 壳 `.import-btn` | 当前用文件选择器，非 Tauri 对话框 |
| 导出 .txt | `ExportDialog` | — | 文稿目录内走 workspace HTTP；「另存为」走 Tauri dialog/fs |
| 预设 pill / FAB chip | 壳 `.pill-chip` / `.chip-toggle` | 或 `ToggleGroup` | 横屏 15 / 竖屏 10 / 自定义 |
| 处理文稿 `.btn-go` | 壳主按钮 | `Button`（theme primary=白） | 处理中 disabled + spinner；启用 LLM 时先预检 |
| 结果列表 | 自定义 `.result-line` | + `ScrollArea` | 行号、字数、超长行 `.long`；SSE 中可渐进更新 |
| 一键复制 `.btn-copy` | 壳或 | `Button` + **sonner** toast | 成功态 `.copied`（绿） |
| 设置 Drawer | 壳 `.drawer` | — | 窄屏 bottom sheet |
| 设置内分段控件 `.seg` | 壳或 | `ToggleGroup` | 预设三选一 |
| 设置开关 `.toggle-switch` | 壳或 | `Switch` | 去标点开关 |
| 设置输入 | `.input-x` | `Input` + `Label` / `Field` | endpoint、model、字数 |
| LLM 状态条 `.llm-status` | 壳或 | `Alert` | 未配置 / 已就绪 |
| 后端 banner `.banner` | 壳或 | `Alert` | 未就绪 / 已停止 / HTTP 错误 |
| 空态 `.right-empty` / 编辑空 | 壳或 | `Empty`（若已装） | |
| 加载 | `.spinner` | `Spinner` | FAB「正在断句…」 |
| 通知铃（原型） | 可选 | — | MVP 可隐藏 |
| 遗留调试页（如 `Phase0Shell`） | — | shadcn | 非主路径；主入口为 `AppShell` |

## 主按钮语义

OD：**白底 + 深字**（`--fg` / `--on-accent`），不是彩色 primary。

```tsx
// 正确：依赖主题 token
<Button>处理文稿</Button> // bg-primary text-primary-foreground

// 错误：硬编码蓝/紫
<Button className="bg-blue-500">处理文稿</Button>
```

## 超长行（US-08）

| 属性 | 值 |
|------|-----|
| class | `.result-line.long` |
| 底 | `--warn-soft` |
| 左边线 | `--warn-line` |
| 字数色 / 标签 | `--warn` |
| 数据 | API `flagged_lines`（**0-based**） |

**不要**用 `destructive` 红表示超长——红留给后端/系统错误。

## 表单约定（shadcn skill）

设置 Drawer 内若改用 shadcn 表单：

- `FieldGroup` + `Field`；校验 `data-invalid` / `aria-invalid`  
- 选项 2–7 个用 `ToggleGroup`，勿手写一组 `Button` 互斥  
- Toast 用 `sonner`，勿自造 toast 层  

壳层已有完整视觉时，允许 **先移植 HTML/CSS 行为，再渐进替换为 shadcn**，避免一次大爆改。

## 图标

- OD 原型为内联 SVG（描边 1.5–1.8）。  
- 实现可用 **lucide-react**（shadcn 默认）；在 `Button` 内遵循 shadcn `data-icon` 规则，勿额外 `size-4` 覆盖组件内尺寸策略。

## 禁止

- MUI / Ant Design / Chakra 等第二套库  
- 用 `space-y-*` 堆表单（用 `flex flex-col gap-*`）  
- 业务色写死 hex；覆盖 shadcn 组件内部色而非改 CSS 变量  

## 相关

- [foundations.md](./foundations.md) · [states.md](./states.md)  
- [ADR-002](../architecture/adr/002-shadcn-ui.md) · [用户故事](../planning/02-user-stories.md)
