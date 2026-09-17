# SentRealm 对 pydantic skill 的覆盖

## 必须遵守

- 用于 API / 配置 / core 的数据模型与校验；不要顺手引入 **SQLModel** 或 Pydantic AI（本仓库未采用）
- HTTP 契约变更时同步 `docs/api/openapi.yaml` 与 `docs/api/README.md`
- 与 FastAPI 联用时先读 `.agents/skills/fastapi/SENTREALM.md`
