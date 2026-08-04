use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use reqwest::blocking::Client;

pub const API_HOST: &str = "127.0.0.1";
pub const API_PORT: u16 = 17300;

pub fn api_base_url() -> String {
    format!("http://{API_HOST}:{API_PORT}")
}

fn health_url() -> String {
    format!("{}/health", api_base_url())
}

pub fn is_health_ok() -> bool {
    Client::builder()
        .timeout(Duration::from_millis(800))
        .build()
        .ok()
        .and_then(|client| client.get(health_url()).send().ok())
        .map(|response| response.status().is_success())
        .unwrap_or(false)
}

fn repo_root() -> PathBuf {
    let manifest = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let root = manifest.join("..").join("..");
    root.canonicalize().unwrap_or(root)
}

/// IDE 调试时由 debugpy 等外部进程提供 FastAPI，Tauri 不再 spawn `uv run`。
fn skip_backend_spawn() -> bool {
    std::env::var("SENTREALM_SKIP_BACKEND_SPAWN")
        .map(|value| matches!(value.as_str(), "1" | "true" | "TRUE" | "yes" | "YES"))
        .unwrap_or(false)
}

#[cfg(debug_assertions)]
fn spawn_backend(_sidecar: Option<&Path>, repo_root: &Path) -> Result<Child, String> {
    let mut cmd = Command::new("uv");
    cmd.args([
        "run",
        "uvicorn",
        "apps.gui.api.main:app",
        "--host",
        API_HOST,
        "--port",
        &API_PORT.to_string(),
    ])
    .current_dir(repo_root)
    .stdout(Stdio::null())
    .stderr(Stdio::piped());

    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        // 独立进程组，退出时可 kill 整棵子进程树（uv → python/uvicorn）。
        cmd.process_group(0);
    }

    cmd.spawn().map_err(|err| {
        format!(
            "无法 spawn FastAPI（uv run uvicorn …）：{err}。请确认已 `uv sync` 且 `uv` 在 PATH。"
        )
    })
}

#[cfg(not(debug_assertions))]
fn spawn_backend(sidecar: Option<&Path>, _repo_root: &Path) -> Result<Child, String> {
    let exe = sidecar.ok_or_else(|| {
        "未配置生产 sidecar 路径（resources/sentrealm-api/sentrealm-api.exe）。".to_string()
    })?;
    if !exe.is_file() {
        return Err(format!(
            "找不到后端 sidecar：{}。请确认安装完整或重新安装。",
            exe.display()
        ));
    }

    let mut cmd = Command::new(exe);
    // Discard stdio: piped stderr is never drained and can stall the sidecar.
    cmd.stdout(Stdio::null()).stderr(Stdio::null());

    if let Some(dir) = exe.parent() {
        cmd.current_dir(dir);
    }

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        // Belt-and-suspenders if an older console-subsystem sidecar is still installed.
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        cmd.creation_flags(CREATE_NO_WINDOW);
    }

    #[cfg(unix)]
    {
        use std::os::unix::process::CommandExt;
        cmd.process_group(0);
    }

    cmd.spawn()
        .map_err(|err| format!("无法 spawn sidecar（{}）：{err}", exe.display()))
}

/// 终止子进程及其后代。
///
/// - 生产 onedir：单进程，直接 `Child::kill`（避免 `taskkill` 弹黑框、拖慢关窗）
/// - 开发 `uv run`：须杀整棵树，否则会残留 uvicorn/python
fn kill_process_tree(child: &mut Child) {
    let pid = child.id();

    #[cfg(windows)]
    {
        if cfg!(debug_assertions) {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            let _ = Command::new("taskkill")
                .args(["/PID", &pid.to_string(), "/T", "/F"])
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .creation_flags(CREATE_NO_WINDOW)
                .status();
        } else {
            let _ = child.kill();
        }
    }

    #[cfg(unix)]
    {
        // process_group(0) 时 PGID == pid，负号表示杀整组。
        let _ = Command::new("kill")
            .args(["-TERM", &format!("-{pid}")])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
    }

    let _ = child.wait();
}

pub struct BackendManager {
    child: Mutex<Option<Child>>,
    spawned_by_us: Mutex<bool>,
    startup_error: Mutex<Option<String>>,
    /// 生产 onedir：`$RESOURCE/sentrealm-api/sentrealm-api.exe`。
    sidecar_path: Mutex<Option<PathBuf>>,
}

impl BackendManager {
    pub fn new() -> Self {
        Self {
            child: Mutex::new(None),
            spawned_by_us: Mutex::new(false),
            startup_error: Mutex::new(None),
            sidecar_path: Mutex::new(None),
        }
    }

    #[cfg(not(debug_assertions))]
    pub fn set_sidecar_path(&self, path: PathBuf) {
        *self.sidecar_path.lock().expect("sidecar path lock") = Some(path);
    }

    pub fn ensure_started(&self) {
        if is_health_ok() {
            *self.spawned_by_us.lock().expect("spawn lock") = false;
            return;
        }

        // IDE 断点：外部已起 uvicorn；就绪由前端 waitForHealth 轮询，不阻塞窗口首帧。
        if skip_backend_spawn() {
            return;
        }

        let root = repo_root();
        let sidecar = self.sidecar_path.lock().expect("sidecar path lock").clone();
        match spawn_backend(sidecar.as_deref(), &root) {
            Ok(child) => {
                *self.child.lock().expect("child lock") = Some(child);
                *self.spawned_by_us.lock().expect("spawn lock") = true;
            }
            Err(message) => {
                *self.startup_error.lock().expect("error lock") = Some(message);
            }
        }
        // 不等待 /health：setup 阻塞会导致空白窗约数秒；前端 banner「启动中」+ waitForHealth。
    }

    pub fn startup_error(&self) -> Option<String> {
        self.startup_error.lock().expect("error lock").clone()
    }

    pub fn shutdown(&self) {
        if !*self.spawned_by_us.lock().expect("spawn lock") {
            return;
        }
        *self.spawned_by_us.lock().expect("spawn lock") = false;
        if let Some(mut child) = self.child.lock().expect("child lock").take() {
            kill_process_tree(&mut child);
        }
    }
}

impl Drop for BackendManager {
    fn drop(&mut self) {
        self.shutdown();
    }
}
