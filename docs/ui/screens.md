# Screens — 屏幕与信息架构

> OD boards：`boards/01-new.html` … `06-settings.html`；总览规格页：`index.html`。

## 主界面（三栏）

对应用户手册「左项目/文稿 · 中编辑与参数 · 右结果预览」。

### 左栏 `.side`

| 块 | 内容 |
|----|------|
| Brand | 标记「S」、SentRealm、折叠钮 |
| Search | 「搜索文稿…」、快捷键 `/` |
| CTA | **新建文稿** |
| History | 分组「最近文稿」+ count；搜索框过滤标题（`/` 聚焦） |
| Foot | `.health`（端口 17300）+ **设置**（`Ctrl ,`） |

**文案漂移**：原型 session-notice 写「仅本机会话、退出清除」。产品已落地工作区持久化——侧栏文案跟用户手册（项目/文稿），勿照抄 ephemeral。

### 中栏 `.canvas`

| 块 | 内容 |
|----|------|
| Head | 可编辑文稿标题、导入 `.txt`、预设 pill（横屏·15 / 竖屏·10）、去标点指示；窄屏时 **结果** 按钮 |
| Body | 大文本编辑区 + 字符/行统计；meta-bar（含 LLM 未配置提示等） |
| FAB | 预设切换、状态（已就绪 / 正在断句… / 耗时）、**编辑规则**、**处理文稿** / **重新处理** |

### 右栏 `.right`

| 块 | 内容 |
|----|------|
| Head | 标题「处理结果」、导出 `.txt`、复制等辅助操作 |
| Body | 分行结果（行号、每行字数）；超长行高亮；处理中可 SSE 渐进刷新 |
| Foot | 行数 / 超限等分栏统计、**复制结果** |

空态：说明「处理完成后在此预览」。导出：下载图标 → `ExportDialog`（文稿目录或另选路径）。

## OD Board ↔ 产品场景

| Board | `data-state` | 标题意图 | 用户故事 |
|-------|--------------|----------|----------|
| `01-new.html` | `new` | 新建文稿空态 | US-01 入口 |
| `02-ready.html` | `ready` | 有文稿、可处理 | US-01/03 |
| `03-running.html` | `running` | 处理中 | US-01 |
| `04-done.html` | `done` | 有结果、可复制、含超长标记 | US-05/06/08 |
| `05-error.html` | `error` | 后端未就绪等 | US-16 |
| `06-settings.html` | `settings-open` | 设置 Drawer | US-03/04/09/10/11 |

## 设置面板（Board 06）

| 分区 | 字段（`data-field`） | 持久化 |
|------|----------------------|--------|
| 字数与断句 | `preset`、`max_chars`、`min_chars`、`punctuation_remove`、`punctuation_keep` | SQLite Settings（ADR-004） |
| LLM | `llm_endpoint`、`llm_model`；密钥仅环境变量展示态 | endpoint/model 入库；密钥 **永不**入 SQLite（ADR-005） |
| 隐私 | 说明本地优先、LLM 仅发送池内超长行（每批 ≤10） | 只读说明 |

主界面变暗（`filter:brightness(0.85)`）+ scrim；关闭后恢复处理。

## 断句规则 Modal（FAB「编辑规则」）

| 区域 | 内容 |
|------|------|
| 左栏 | 四类词表：受保护词 / 后可断·词 / 后可断·字 / 前可断 |
| 右栏 | 类别说明 + textarea（一行一词）+ 条数 |
| 底栏左 | **恢复默认**（读内置 txt，仅 draft） |
| 底栏右 | **取消** / **保存** → `PUT /api/v1/settings` |

居中 overlay（`.shell-dialog-rules`）；不替换三栏布局。Esc / 脏关闭确认。

## 主入口与遗留组件

- **主界面**：`AppShell`（三栏壳）；无独立 `VerifyPage` 路由。
- **遗留**：`Phase0Shell` 为脚手架期调试组件，**非**主路径；ADR-002 仍允许次要/调试页用 shadcn 组合，不强制套三栏壳。

## 相关

- [states.md](./states.md) · [layout.md](./layout.md)  
- [用户手册](../user/README.md) · [02-user-stories.md](../planning/02-user-stories.md)
