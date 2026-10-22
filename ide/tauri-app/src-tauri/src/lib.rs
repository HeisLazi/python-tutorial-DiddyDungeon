use std::fs::{self, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent, Url, WebviewWindow};

/// Preferred port for the desktop app. Kept apart from the browser launcher
/// (7331) so per-origin settings such as the active view stay with the app.
const APP_PORT: &str = "7345";

struct Backend(Mutex<Option<Child>>);

/// The Quest Lab checkout to run: `QUESTLAB_HOME` wins, otherwise the checkout
/// this binary was built from (src-tauri lives at <repo>/ide/tauri-app/src-tauri).
fn repo_root() -> PathBuf {
    let root = std::env::var_os("QUESTLAB_HOME")
        .map(PathBuf::from)
        .unwrap_or_else(|| Path::new(env!("CARGO_MANIFEST_DIR")).join("../../.."));
    root.canonicalize().unwrap_or(root)
}

fn python_for(root: &Path) -> PathBuf {
    let venv = root.join(".venv/bin/python");
    if venv.exists() { venv } else { PathBuf::from("python3") }
}

fn log_path() -> PathBuf {
    let base = std::env::var_os("XDG_STATE_HOME")
        .map(PathBuf::from)
        .or_else(|| std::env::var_os("HOME").map(|home| PathBuf::from(home).join(".local/state")))
        .unwrap_or_else(std::env::temp_dir);
    let dir = base.join("QuestLab");
    let _ = fs::create_dir_all(&dir);
    dir.join("desktop.log")
}

fn js_string(text: &str) -> String {
    serde_json::to_string(text).unwrap_or_else(|_| "\"\"".into())
}

fn show_failure(window: &WebviewWindow, message: &str) {
    let _ = window.eval(format!("window.questlabFailed && window.questlabFailed({})", js_string(message)));
}

fn spawn_backend(window: WebviewWindow) -> Option<Child> {
    let root = repo_root();
    let log = log_path();
    let mut log_file = OpenOptions::new().create(true).append(true).open(&log).ok();
    let stderr = log_file
        .as_ref()
        .and_then(|file| file.try_clone().ok())
        .map(Stdio::from)
        .unwrap_or_else(Stdio::null);

    let spawned = Command::new(python_for(&root))
        .args(["-m", "ide.quest", "--app", "--no-browser", "--backend-port", APP_PORT])
        .current_dir(&root)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(stderr)
        .spawn();

    let mut child = match spawned {
        Ok(child) => child,
        Err(error) => {
            show_failure(&window, &format!("Could not start the Quest Lab backend in\n{}\n\n{error}", root.display()));
            return None;
        }
    };

    let stdout = child.stdout.take()?;
    thread::spawn(move || {
        let mut ready = false;
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            if let Some(file) = log_file.as_mut() {
                let _ = writeln!(file, "{line}");
            }
            if let Some(url) = line.strip_prefix("QUESTLAB_READY ") {
                ready = true;
                match Url::parse(url.trim()) {
                    Ok(url) => { let _ = window.navigate(url); }
                    Err(error) => show_failure(&window, &format!("Backend reported a bad URL: {error}")),
                }
            } else if line.starts_with("QUESTLAB_FAILED") {
                show_failure(&window, &format!("{line}\n\nDetails: {}", log.display()));
            } else if !ready && line.contains("building:") {
                let _ = window.eval("window.questlabStatus && window.questlabStatus('Forging the UI…')");
            }
        }
        if !ready {
            show_failure(&window, &format!("The Quest Lab backend stopped before it was ready.\n\nDetails: {}", log.display()));
        }
    });
    Some(child)
}

/// Ask the launcher to stop (it forwards shutdown to uvicorn and the PTYs),
/// then force it if it has not exited after a short grace period.
fn stop_backend(child: &mut Child) {
    #[cfg(unix)]
    {
        let _ = Command::new("kill").args(["-TERM", &child.id().to_string()]).status();
        let deadline = Instant::now() + Duration::from_secs(4);
        while Instant::now() < deadline {
            if matches!(child.try_wait(), Ok(Some(_))) {
                return;
            }
            thread::sleep(Duration::from_millis(100));
        }
    }
    let _ = child.kill();
    let _ = child.wait();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            let window = app.get_webview_window("main").expect("main window is configured");
            let child = spawn_backend(window);
            app.manage(Backend(Mutex::new(child)));
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(mut child) = handle.state::<Backend>().0.lock().ok().and_then(|mut slot| slot.take()) {
                stop_backend(&mut child);
            }
        }
    });
}
