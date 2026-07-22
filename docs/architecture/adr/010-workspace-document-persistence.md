# ADR-010: 文稿与项目本地持久化

## 状态

已接受

## 背景

Phase 1 MVP 将文稿正文与处理结果仅保存在内存中，退出应用后丢失。Phase 2 需要：

- 项目 / 文稿 CRUD 与侧栏切换
- 编辑自动保存与重启恢复
- 最近一次处理结果缓存（`result.json`）
- 与现有全局 `Settings`（ADR-004）分离，避免配置与资产混存

cli、mcp 本期不接入工作区管理，仅 gui 通过 HTTP API 读写。

## 选项

### A. 全部写入 `%APPDATA%/SentRealm/`

与 `settings.db` 同目录，用 SQLite 或 JSON 存文稿。

- 优点：单根目录，备份简单
- 缺点：用户「文档」资产与系统配置混在一起；大文本进 SQLite 不必要

### B. 用户「文档」目录 + 文件夹落盘（本决策选中）

Windows 默认 `%USERPROFILE%/Documents/SentRealm/`；每项目、每文稿独立文件夹；元数据 JSON + `source.txt` + 可选 `result.json`。

- 优点：用户可直接在资源管理器查看/备份；与 ADR-004 设置库职责清晰
- 缺点：需处理路径非法字符（UUID 目录名规避）；无跨设备同步

### C. 仅 SQLite 存文稿 BLOB

单库多表存 `source` 与 `result`。

- 优点：查询与事务统一
- 缺点：大文本与文件导出体验差；与「本地文档」心智不符

## 决策

采用 **选项 B**，具体约定：

| 项 | 决策 |
|----|------|
| 工作区根路径 | `Documents/SentRealm/`（`default_workspace_path()`）；与 `default_config_path()` 分离 |
| 元数据 | `workspace.json`、`project.json`、`document.json`；`schema_version: 1` |
| 正文 | `source.txt`（UTF-8，无 BOM） |
| 处理结果 | 每文稿仅保留最近一次 `result.json`（不含 `original`，可从 `source.txt` 重算） |
| 全局设置 | 仍用 ADR-004 SQLite；处理参数首期**仅**读全局设置 |
| 删除 | `shutil.rmtree` 物理删除；无回收站、无多版本历史 |
| HTTP | `/api/v1/workspace`、`/projects`、`/documents`；`POST /preprocess` 语义不变、不自动写盘 |
| 迁移 | 首次 `ensure_initialized()` 建默认结构；`repair_meta()` 修正活动项指向已删资源；Phase 1 内存草稿不迁移 |

活动项与 `recent_*` 损坏时：`repair_meta()` 回退到最新 `updated_at` 文稿，或创建空白文稿。

## 后果

### 正面

- 文稿与处理结果可跨会话恢复；用户可在资源管理器备份项目文件夹
- 设置库与文稿资产解耦，ADR-004 边界保持
- core `WorkspaceStore` / `ProjectStore` / `DocumentStore` 可供 api 单测；测试注入 `tmp_path`

### 负面

- 无文件监视（Phase 2.1 可选）：外部修改 `source.txt` 需重新打开文稿才同步
- 无项目级 `Settings` 覆盖、无 CLI/MCP 项目管理（后续 Phase）
- Windows 以外平台路径为占位，跨平台时需对齐

## 相关文档

- [ADR-004：SQLite 持久化用户配置](./004-sqlite-user-settings.md)
- [ADR-005：LLM 集成与隐私边界](./005-llm-integration-privacy.md)
- [数据流与模块边界](../data-flow.md)
- [OpenAPI workspace 契约](../../api/openapi.yaml)
