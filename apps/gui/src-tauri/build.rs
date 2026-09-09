use std::path::Path;

fn main() {
    ensure_sidecar_resource_dir();
    tauri_build::build()
}

/// `tauri.conf.json` 的 `bundle.resources` 在 `tauri dev` 时也会被 tauri-build 校验。
/// 真实 onedir 是打包产物（gitignore），开发走 `uv run uvicorn`，只需占位目录存在。
fn ensure_sidecar_resource_dir() {
    let dir = Path::new("resources/sentrealm-api");
    let exe = dir.join("sentrealm-api.exe");
    let profile = std::env::var("PROFILE").unwrap_or_default();

    if profile == "release" && !exe.is_file() {
        panic!(
            "缺少生产 sidecar：{}。请先运行 `pwsh -File scripts/build_sidecar.ps1`（或 `scripts/build_installer.ps1`）。",
            exe.display()
        );
    }

    if !dir.exists() {
        std::fs::create_dir_all(dir).unwrap_or_else(|err| {
            panic!("无法创建 {}（tauri-build 要求 bundle.resources 路径存在）：{err}", dir.display())
        });
    }
}
