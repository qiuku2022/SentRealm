use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use reqwest::blocking::Client;

pub const API_HOST: &str = "127.0.0.1";
pub const API_PORT: u16 = 17300;
const HEALTH_POLL_MS: u64 = 200;
const HEALTH_TIMEOUT_SECS: u64 = 30;

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

fn wait_for_health(timeout: Duration, interval: Duration) -> bool {
    let started = Instant::now();
    while started.elapsed() < timeout {
        if is_health_ok() {
            return true;
        }
        std::thread::sleep(interval);
    }
    false
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

/// 生产 sidecar 路径：与主程序同目录的 `sentrealm-api.exe`（Tauri `externalBin`）。
#[cfg(not(debug_assertions))]
fn sidecar_exe() -> Result<PathBuf, String> {
    let mut path = std::env::current_exe().map_err(|err| format!("无法解析当前可执行文件路径：{err}"))?;
    path.pop();
    path.push("sentrealm-api.exe");
    if !path.is_file() {
        return Err(format!(
            "找不到后端 sidecar：{}。请确认安装完整或重新安装。",
            path.display()
        ));
    }
    Ok(path)
}

#[cfg(debug_assertions)]
fn spawn_backend(repo_root: &Path) -> Result<Child, String> {
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
fn spawn_backend(_repo_root: &Path) -> Result<Child, String> {
    let exe = sidecar_exe()?;
    let mut cmd = Command::new(&exe);
    // Discard stdio: piped stderr is never drained and can stall the sidecar.
    cmd.stdout(Stdio::null()).stderr(Stdio::null());

    if let Some(dir) = exe.parent() {
        cmd.current_dir(dir);
    }

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        // Sidecar is a console EXE; hide the flash console when spawned by the GUI.
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

/// 终止子进程及其后代（Windows 上 kill 仅 uv 会残留 uvicorn/python）。
fn kill_process_tree(child: &mut Child) {
    let pid = child.id();

    #[cfg(windows)]
    {
        let _ = Command::new("taskkill")
            .args(["/PID", &pid.to_string(), "/T", "/F"])
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status();
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
}

impl BackendManager {
    pub fn new() -> Self {
        Self {
            child: Mutex::new(None),
            spawned_by_us: Mutex::new(false),
            startup_error: Mutex::new(None),
        }
    }

    pub fn ensure_started(&self) {
        if is_health_ok() {
            *self.spawned_by_us.lock().expect("spawn lock") = false;
            return;
        }

        if skip_backend_spawn() {
            let ready = wait_for_health(
                Duration::from_secs(HEALTH_TIMEOUT_SECS),
                Duration::from_millis(HEALTH_POLL_MS),
            );
            if !ready {
                *self.startup_error.lock().expect("error lock") = Some(
                    "外部后端未就绪（SENTREALM_SKIP_BACKEND_SPAWN=1）。请先启动「FastAPI（uvicorn · 断点）」或手动 uvicorn。"
                        .to_string(),
                );
            }
            return;
        }

        let root = repo_root();
        match spawn_backend(&root) {
            Ok(child) => {
                *self.child.lock().expect("child lock") = Some(child);
                *self.spawned_by_us.lock().expect("spawn lock") = true;
            }
            Err(message) => {
                *self.startup_error.lock().expect("error lock") = Some(message);
                return;
            }
        }

        let ready = wait_for_health(
            Duration::from_secs(HEALTH_TIMEOUT_SECS),
            Duration::from_millis(HEALTH_POLL_MS),
        );

        if !ready {
            *self.startup_error.lock().expect("error lock") = Some(
                "后端 health 检查超时（30s）。端口 17300 可能被占用，或 uvicorn 启动失败。"
                    .to_string(),
            );
        }
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
