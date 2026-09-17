# SentRealm 对 uv skill 的覆盖

与 [ADR-011](../../../docs/architecture/adr/011-uv-python-environment.md)、[setup.md](../../../docs/dev/setup.md)、[AGENTS.md](../../../AGENTS.md) 一致。

## 必须遵守

- 解释器与 venv：仓库根 `.venv`，版本见 `.python-version`（**3.12.13**）
- 安装 / 同步：`uv sync`（读 `uv.lock`）；业务依赖不用 pip / conda 直接装
- 运行：`uv run …`；Tauri 开发 spawn 同样走 `uv run uvicorn …`
- 锁定工具版本以 docs 为准（uv **0.12.1** 等）；不要为「skill 推荐」擅自升大版本
