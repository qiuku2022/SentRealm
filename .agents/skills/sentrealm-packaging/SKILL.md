---
name: sentrealm-packaging
description: Builds and debugs the SentRealm Windows installer (PyInstaller onedir sidecar + Tauri NSIS). Use when the user mentions 安装包, sidecar, PyInstaller, NSIS, tauri build, pnpm build, build_installer, build_sidecar, resources/sentrealm-api, code signing, SmartScreen, 干净机, or when `pnpm dev` fails with missing `resources/sentrealm-api`.
---

# SentRealm 生产打包

细节以 [packaging.md](../../../docs/dev/packaging.md) 与 [ADR-008](../../../docs/architecture/adr/008-production-packaging.md) 为准。本 skill 只钉容易踩错的边界。

## 何时用

- 打 / 修 Windows 安装包
- `tauri dev` / `pnpm dev` 报 `resource path resources\sentrealm-api doesn't exist`
- 改 `tauri.conf.json` `bundle.resources`、`build.rs`、sidecar spawn、PyInstaller `.spec`

## 命令（仓库根）

```powershell
pwsh -File scripts/build_installer.ps1
```

只重建 sidecar：

```powershell
pwsh -File scripts/build_sidecar.ps1
```

不要发明第二套打包路径。不要用已废弃的 onefile + `externalBin`。

## 开发 vs 生产

| | 开发 `pnpm dev` | 生产安装包 |
|--|------------------|------------|
| 后端 | `uv run uvicorn apps.gui.api.main:app --host 127.0.0.1 --port 17300` | `$RESOURCE/sentrealm-api/sentrealm-api.exe` |
| sidecar 目录 | **不需要**真实 onedir；`apps/gui/src-tauri/build.rs` 会建空占位 | release 构建**必须**已有 `sentrealm-api.exe` |
| 业务逻辑 | 只在 `packages/core` | 同左；Rust 只 spawn / 杀进程 |

`apps/gui/src-tauri/resources/sentrealm-api/` 与 `packaging/dist/` **不入 git**。

## 硬约束

1. **不要**为了让 `pnpm dev` 通过而去跑完整 PyInstaller，除非用户要验证 sidecar。
2. **不要**把 FastAPI 打进 Rust 同进程，或把断句逻辑搬进 `src-tauri`。
3. **不要**把 cli / mcp 打进桌面安装包。
4. sidecar 是 **onedir**（`sentrealm-api.exe` + `_internal/`），`console=False`。干净机冒烟时 `%TEMP%` 不应再出现新的 `_MEI*`。
5. 改 hiddenimports / datas 只动 `packaging/sentrealm-api.spec`；词表必须打进 `sentrealm_core/data/break_lexicon`。
6. `tauri.conf.json` 的 `bundle.resources` 映射：`resources/sentrealm-api/` → `sentrealm-api/`。
7. 生产 spawn 路径：`BaseDirectory::Resource` + `sentrealm-api/sentrealm-api.exe`（见 `apps/gui/src-tauri/src/lib.rs`）。
8. 代码签名 / SmartScreen **不阻塞**内部包；对外分发再按 [Tauri Windows signing](https://v2.tauri.app/distribute/sign/windows/) 补，证书与密钥不入仓库。
9. 发版前重打 sidecar，避免 NSIS 打进旧二进制。
10. 用户手册安装节在公开发布前仍写内部构建；改发版流程时同步 [docs/user/README.md](../../../docs/user/README.md)。

## 冒烟（干净机）

见 [packaging.md 冒烟清单](../../../docs/dev/packaging.md)。关闭后无残留 `sentrealm-api` / python；端口 17300 可再次占用。

## 相关文件

- `scripts/build_sidecar.ps1`、`scripts/build_installer.ps1`
- `packaging/sentrealm-api.spec`、`packaging/sidecar_main.py`
- `apps/gui/src-tauri/build.rs`、`tauri.conf.json`、`src/backend.rs`、`src/lib.rs`
