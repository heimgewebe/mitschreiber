use x11rb::connection::Connection;
use x11rb::rust_connection::RustConnection;
use x11rb::protocol::xproto::{ConnectionExt, AtomEnum};
use crate::sampler::OsContextState;
use std::error::Error;

/// Parses a raw `WM_CLASS` property value into an application name.
///
/// `WM_CLASS` stores `"instance\0class\0"` (two NUL-terminated strings).
/// We use the **last** non-empty part, which is the class name when both
/// parts are present, or the instance name when only one part exists.
/// Returns an empty string when the value is empty or contains only NUL bytes.
fn parse_wm_class(raw: &[u8]) -> String {
    raw.split(|&b| b == 0)
        .filter(|p| !p.is_empty())
        .last()
        .map(|cls| String::from_utf8_lossy(cls).into_owned())
        .unwrap_or_default()
}

pub struct X11Sampler {
    conn: RustConnection,
    root: u32,
    atom_net_active_window: u32,
    atom_net_wm_name: u32,
    atom_wm_name: u32,
    atom_wm_class: u32,
    atom_utf8_string: u32,
}

impl X11Sampler {
    pub fn new() -> Result<Self, Box<dyn Error>> {
        let (conn, screen_num) = RustConnection::connect(None)?;
        let root = conn.setup().roots[screen_num].root;

        let atom_net_active_window = conn.intern_atom(false, b"_NET_ACTIVE_WINDOW")?.reply()?.atom;
        let atom_net_wm_name = conn.intern_atom(false, b"_NET_WM_NAME")?.reply()?.atom;
        let atom_wm_name = conn.intern_atom(false, b"WM_NAME")?.reply()?.atom;
        let atom_wm_class = conn.intern_atom(false, b"WM_CLASS")?.reply()?.atom;
        let atom_utf8_string = conn.intern_atom(false, b"UTF8_STRING")?.reply()?.atom;

        Ok(Self {
            conn,
            root,
            atom_net_active_window,
            atom_net_wm_name,
            atom_wm_name,
            atom_wm_class,
            atom_utf8_string,
        })
    }

    pub fn get_state(&self) -> OsContextState {
        let ts = chrono::Utc::now().to_rfc3339();

        let mut app = String::new();
        let mut window = String::new();

        // Helper to perform property get
        let get_active = || -> Result<(String, String), Box<dyn Error>> {
            let reply = self.conn.get_property(
                false,
                self.root,
                self.atom_net_active_window,
                AtomEnum::WINDOW,
                0,
                1
            )?.reply()?;

            if let Some(active_window) = reply.value32().and_then(|mut v| v.next()) {
                let mut w_title = String::new();

                // 1. Try _NET_WM_NAME (UTF8)
                let reply_utf8 = self.conn.get_property(
                    false,
                    active_window,
                    self.atom_net_wm_name,
                    self.atom_utf8_string,
                    0,
                    1024
                )?.reply()?;

                if !reply_utf8.value.is_empty() {
                    w_title = String::from_utf8_lossy(&reply_utf8.value).to_string();
                } else {
                    // 2. Try WM_NAME (Legacy)
                    let reply_legacy = self.conn.get_property(
                        false,
                        active_window,
                        self.atom_wm_name,
                        AtomEnum::ANY,
                        0,
                        1024
                    )?.reply()?;
                    if !reply_legacy.value.is_empty() {
                        w_title = String::from_utf8_lossy(&reply_legacy.value).to_string();
                    }
                }

                // 3. Get WM_CLASS
                let reply_class = self.conn.get_property(
                    false,
                    active_window,
                    self.atom_wm_class,
                    AtomEnum::STRING,
                    0,
                    1024
                )?.reply()?;

                // WM_CLASS contains [instance, class] separated by NUL.
                // Use the last non-empty part (class when both present, instance when only one).
                let w_app = parse_wm_class(&reply_class.value);

                Ok((w_app, w_title))
            } else {
                Ok(("".to_string(), "".to_string()))
            }
        };

        if let Ok((a, w)) = get_active() {
            if !a.is_empty() { app = a; }
            if !w.is_empty() { window = w; }
        }

        if app.is_empty() { app = "Unknown".to_string(); }
        if window.is_empty() { window = "Unknown".to_string(); }

        OsContextState {
            ts,
            app,
            window,
            clipboard: None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::parse_wm_class;

    #[test]
    fn wm_class_two_parts_returns_class() {
        // Normal case: "instance\0class\0" — prefer the class name (last part).
        assert_eq!(parse_wm_class(b"firefox\0Firefox\0"), "Firefox");
    }

    #[test]
    fn wm_class_single_part_returns_instance() {
        // Some apps provide only one NUL-terminated entry; return that entry.
        assert_eq!(parse_wm_class(b"code\0"), "code");
    }

    #[test]
    fn wm_class_empty_returns_empty_string() {
        // Empty value and NUL-only value both map to the empty string.
        assert_eq!(parse_wm_class(b""), "");
        assert_eq!(parse_wm_class(b"\0\0"), "");
    }
}
