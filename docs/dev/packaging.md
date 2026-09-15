# Windows 安装包构建（ADR-008）

> 将 FastAPI 打成 PyInstaller **onedir** sidecar，再由 Tauri 打出 NSIS 安装包。终端用户无需本机 Python / uv。

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

1. `scripts/build_sidecar.ps1` → PyInstaller onedir → `apps/gui/src-tauri/resources/sentrealm-api/`
2. `apps/gui` 下 `pnpm build`（`tauri build`，目标 NSIS；经 `bundle.resources` 嵌入 sidecar 目录）

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
| 后端 | `uv run uvicorn …` | `$RESOURCE/sentrealm-api/sentrealm-api.exe`（onedir，含 `_internal/`；无控制台子系统） |
| 分支 | `cfg!(debug_assertions)` | release：`BaseDirectory::Resource` 解析后 spawn |

相关实现：`apps/gui/src-tauri/src/backend.rs`、`packaging/sentrealm-api.spec`、[ADR-008](../architecture/adr/008-production-packaging.md)。

## 冒烟清单（干净机）

1. 安装 NSIS 包 → 启动 SentRealm
2. 粘贴样例口播稿 → 处理 → 复制结果
3. 关闭应用后，任务管理器无残留 `sentrealm-api` / python
4. 端口 17300 未被占用时可再次启动
5. 启动后 `%TEMP%` **不应**再出现新的 `_MEI*` 目录（onedir 不再每次解压）

**验收分层**：

| 档位 | 口径 | 状态（2026-09-15） |
|------|------|-------------------|
| 内部（档位 1） | 作者/团队以 NSIS 日常完成主流程（粘贴 → 处理 → 复制 → 剪映） | ✅ 作者工作环境约 1 个月 |
| 正式 `1.0.0` | 干净 Win10/11 上完整跑上表 1–5（含无残留、无新增 `_MEI*`） | 未做 |

## 注意

- `resources/sentrealm-api/` 与 `packaging/dist/` **不入 git**（见根 `.gitignore`）。`tauri dev` 不需要真实 sidecar；`src-tauri/build.rs` 会在目录缺失时创建空占位（`tauri build` / release 仍要求已有 `sentrealm-api.exe`）
- 每次发版前务必重打 sidecar，避免 NSIS 打进旧二进制
- 代码签名 / SmartScreen 不阻塞内部包；对外分发前再补
- cli / mcp **不**随桌面安装包分发
- 旧版 onefile + `externalBin` 布局已废弃；升级安装后请确认安装目录为 `resources/sentrealm-api/` 而非单文件 `sentrealm-api.exe` 旁挂
