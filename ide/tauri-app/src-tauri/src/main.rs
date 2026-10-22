// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
  // WebKitGTK renders blank or flickers on some Wayland compositors (Hyprland
  // included). Run through XWayland with compositing off unless the player has
  // chosen their own values.
  #[cfg(target_os = "linux")]
  for (key, value) in [("GDK_BACKEND", "x11"), ("WEBKIT_DISABLE_COMPOSITING_MODE", "1")] {
    if std::env::var_os(key).is_none() {
      // SAFETY: called before any other thread exists.
      unsafe { std::env::set_var(key, value) };
    }
  }
  app_lib::run();
}
