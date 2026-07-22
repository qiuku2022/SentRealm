# ADR-004: SQLite 持久化用户配置

## 状态

已接受

## 背景

根据 [ADR-007](./007-multi-entry-modules.md)，gui、cli、mcp **共用同一 SQLite 文件**持久化用户配置，且**无例外**。产品 MVP 需要记住：

- 横屏/竖屏/自定义单行最大字数
- 去标点保留/去除规则
- LLM 端点、模型等非敏感连接信息

若配置散落在多文件或各入口独立存储，会导致行为不一致、难以测试与备份。需明确存储位置、schema 与访问边界。

**不在本 ADR 范围**：LLM API 密钥存储与调用隐私（见 [ADR-005](./005-llm-integration-privacy.md)）。gui 文稿与处理结果持久化见 [ADR-010](./010-workspace-document-persistence.md)；cli/mcp 仍不接入工作区。

## 选项

### A. 各入口独立 JSON 配置文件

cli、gui、mcp 各自读写不同路径的 JSON。

- 优点：实现简单
- 缺点：违反 ADR-007 共用库决策；配置易分叉

### B. 操作系统偏好 / 注册表

使用 Windows 注册表、macOS UserDefaults 等。

- 优点：与 OS 集成
- 缺点：跨平台实现分裂；不利于单元测试与备份

### C. SQLite 单行 JSON（本决策选中）

单库单表单行，`settings_json` 存完整 `Settings` 对象。

- 优点：嵌入式、单文件易备份；三入口共用；MVP 够用
- 缺点：JSON 不便 SQL 查询（MVP 无此需求）

### D. 规范化多表 schema

预设、标点规则、LLM 配置分表存储。

- 优点：字段级查询与约束强
- 缺点：MVP 过度设计；迁移成本高

## 决策

采用 **选项 C**。实现位于 `packages/core/src/sentrealm_core/store/`。

### 数据库路径

由 `default_config_path()` 返回统一路径，三入口均使用此函数。返回路径前须**确保父目录存在**（不存在则创建）。

| 平台 | 路径（约定） | 状态 |
|------|--------------|------|
| Windows | `%APPDATA%/SentRealm/settings.db` | **已定稿**（Phase 0 主目标平台） |
| macOS | `~/Library/Application Support/SentRealm/settings.db` | 占位，待跨平台验证时定稿 |
| Linux | `$XDG_CONFIG_HOME/sentrealm/settings.db`（未设置 `XDG_CONFIG_HOME` 时默认 `~/.config/sentrealm/settings.db`） | 占位，待跨平台验证时定稿 |

路径**不可**由各入口自行指定（ADR-007 无例外）。

### Schema（概念）

```sql
-- 概念示意，非最终实现
CREATE TABLE app_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  schema_version INTEGER NOT NULL,
  settings_json TEXT NOT NULL
);
```

- 仅允许 `id = 1` 的单行记录
- `schema_version`：当前 settings JSON 结构版本，用于迁移
- `settings_json`：序列化后的 `Settings` 对象（UTF-8 JSON）

### Settings JSON 字段（MVP）

| 字段 | 类型（概念） | 说明 |
|------|--------------|------|
| `preset` | string | `landscape` / `portrait` / `custom` |
| `max_chars` | integer | 自定义单行最大字数（`preset=custom` 时生效） |
| `min_chars` | integer | 规则断句与 LLM 断句的单行最短字数（须 ≤ `max_chars`） |
| `punctuation_remove` | string[] | 去除并在原位置换行的符号 |
| `punctuation_keep` | string[] | 保留不换行的符号 |
| `llm_enabled` | boolean | 是否启用 LLM 断句；关闭时即使已配置 endpoint/model 与密钥也跳过 |
| `llm_endpoint` | string | LLM API 端点 URL |
| `llm_model` | string | 模型名称 |
| `break_lexicon` | object | 规则断句字词表（四类 string[]；见 [产品定义](../planning/01-product-definition-and-mvp.md#允许断点字词表)） |

默认值与 [产品定义：去标点规则与单行最大字数](../../planning/01-product-definition-and-mvp.md) 对齐：

| 字段 | 默认值 |
|------|--------|
| `preset` | `landscape` |
| `max_chars` | `15`（横屏）；`preset=portrait` 时为 `10`；`preset=custom` 时由用户指定 |
| `min_chars` | `5`（用户可改；切换预设导致 `max_chars` 变小时自动夹紧到 ≤ `max_chars`） |
| `punctuation_remove` | 全角/半角标点、引号、括号、`…` 等（完整列表见产品文档） |
| `punctuation_keep` | `%`、`％` |
| `llm_enabled` | `false` |
| `llm_endpoint` / `llm_model` | 空字符串（未配置 LLM） |
| `break_lexicon` | 与打包 `data/break_lexicon/*.txt` 一致（四类列表） |

### API 密钥：不入 SQLite

**LLM API 密钥不写入数据库**。

- 通过环境变量 **`SENTREALM_LLM_API_KEY`** 读取（详见 [ADR-005](./005-llm-integration-privacy.md)）
- 本地开发可使用根目录 `.env`（参考 `.env.example`，**不入 git**）
- SQLite 仅存 `llm_enabled`、`llm_endpoint`、`llm_model` 等非敏感项

### 访问层

| 组件 | 职责 |
|------|------|
| `Settings` | 领域模型（Pydantic 等），对应 JSON 结构 |
| `SettingsStore` | 协议：`load() -> Settings`、`save(settings)` |
| `SqliteSettingsStore` | 默认实现，读写 `app_settings` 表 |
| `default_config_path()` | 返回共用 DB 文件路径 |

`gui/api`、cli、mcp 均通过 `core` 的 `SettingsStore` 访问，不直接拼 SQL。

### 存储 / 不存储

| 存储 | 不存储 |
|------|--------|
| 去标点规则 | 文稿正文 |
| 字数预设 | 处理结果 |
| `llm_enabled`、LLM endpoint、model | 处理历史 |
| | **API 密钥** |

### 迁移策略

- 当前 `schema_version` 为 **2**（v1 仅含 preset / 标点 / LLM 等；v2 增加 `break_lexicon`）
- 应用或 `SettingsStore` 首次加载时：若库不存在则建表并写入默认 `Settings`
- 若 `schema_version === 1`：自动补全 `break_lexicon`（来自内置 txt）并写回 v2
- 若 `schema_version` 高于代码支持的版本：报错，需升级应用
- 未来字段变更时递增版本号并添加迁移步骤

### 与 ADR-005 的边界

| ADR-004（本文档） | [ADR-005](./005-llm-integration-privacy.md) |
|-------------------|-------------------|
| SQLite 路径、schema、Settings 字段 | LLM SDK 选型、调用方式 |
| 密钥不入库，仅 env | 请求体范围、mock、超时、隐私策略 |
| `SettingsStore` 读写 | `LlmClient` 实现 |

## 后果

### 正面

- gui / cli / mcp 配置行为一致，符合 ADR-007
- 单文件便于用户备份与迁移
- core 层可单测（内存库或临时文件）
- 单行 JSON 便于 MVP 快速迭代字段

### 负面

- JSON 列无法高效做字段级 SQL 查询
- 需维护 `schema_version` 与迁移逻辑
- 密钥与配置分离，用户需同时配置 DB 设置与环境变量

## 相关文档

- [ADR-007：多入口模块化](./007-multi-entry-modules.md)
- [多入口模块化架构](../modules.md)
- [架构概览](../overview.md)
- [数据流与模块边界](../data-flow.md)
