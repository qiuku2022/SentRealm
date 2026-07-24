mod backend;

use backend::{api_base_url, BackendManager};
use tauri::{Manager, RunEvent};

#[tauri::command]
fn get_api_base_url() -> String {
    api_base_url()
}

#[tauri::command]
fn get_backend_startup_error(state: tauri::State<'_, BackendManager>) -> Option<String> {
    state.startup_error()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_dialog::init())
        .manage(BackendManager::new())
        .invoke_handler(tauri::generate_handler![
            get_api_base_url,
            get_backend_startup_error
        ])
        .setup(|app| {
            #[cfg(not(debug_assertions))]
            {
                use tauri::path::BaseDirectory;
                let sidecar = app
                    .path()
                    .resolve("sentrealm-api/sentrealm-api.exe", BaseDirectory::Resource)
                    .map_err(|err| -> Box<dyn std::error::Error> {
                        format!("无法解析 sidecar 资源路径：{err}").into()
                    })?;
                app.state::<BackendManager>().set_sidecar_path(sidecar);
            }

            let manager = app.state::<BackendManager>();
            manager.ensure_started();
            Ok(())
        })
        .on_window_event(|window, event| {
            if matches!(event, tauri::WindowEvent::CloseRequested { .. }) {
                if let Some(manager) = window.app_handle().try_state::<BackendManager>() {
                    manager.shutdown();
                }
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            if matches!(event, RunEvent::ExitRequested { .. } | RunEvent::Exit) {
                if let Some(manager) = app_handle.try_state::<BackendManager>() {
                    manager.shutdown();
                }
            }
        });
}
