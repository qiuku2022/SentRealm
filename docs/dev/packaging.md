# Windows 安装包构建（ADR-008）

> 将 FastAPI 打成 PyInstaller sidecar，再由 Tauri 打出 NSIS 安装包。终端用户无需本机 Python / uv。

**平台**：Windows 10/11 x86_64（`x86_64-pc-windows-msvc`）。macOS / Linux 另议。

## 前置

与 [setup.md](./setup.md) 相同，另需：

| 项 | 说明 |
|----|------|
| `uv sync --group packaging` | 安装 PyInstaller（构建脚本会自动 sync） |
| WebView2 / Rust / pnpm | 同 Tauri 桌面构建 |

## 一键打安装包

在仓库根：

```powershell
pwsh -File scripts/build_installer.ps1
```

步骤：

1. `scripts/build_sidecar.ps1` → PyInstaller → `apps/gui/src-tauri/binaries/sentrealm-api-x86_64-pc-windows-msvc.exe`
2. `apps/gui` 下 `pnpm build`（`tauri build`，目标 NSIS）

产物目录（默认）：

```text
apps/gui/src-tauri/target/release/bundle/nsis/*.exe
```

若环境设置了 `CARGO_TARGET_DIR`，产物在该目录下的 `release/bundle/nsis/`；`build_installer.ps1` 会再镜像一份到上述默认路径。
## 仅重建 sidecar

```powershell
pwsh -File scripts/build_sidecar.ps1
```

## 开发 vs 生产

| | 开发（`pnpm dev`） | 生产（安装包） |
|--|-------------------|----------------|
| 后端 | `uv run uvicorn …` | 同目录 `sentrealm-api.exe`（sidecar） |
| 分支 | `cfg!(debug_assertions)` | release 走 sidecar |

相关实现：`apps/gui/src-tauri/src/backend.rs`、`packaging/sentrealm-api.spec`、[ADR-008](../architecture/adr/008-production-packaging.md)。

## 冒烟清单（干净机）

1. 安装 NSIS 包 → 启动 SentRealm
2. 粘贴样例口播稿 → 处理 → 复制结果
3. 关闭应用后，任务管理器无残留 `sentrealm-api` / python
4. 端口 17300 未被占用时可再次启动

## 注意

- `binaries/` 与 `packaging/dist/` **不入 git**（见根 `.gitignore`）
- 每次发版前务必重打 sidecar，避免 NSIS 打进旧二进制
- 代码签名 / SmartScreen 不阻塞内部包；对外分发前再补
- cli / mcp **不**随桌面安装包分发
