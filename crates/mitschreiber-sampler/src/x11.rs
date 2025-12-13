use x11rb::connection::Connection;
use x11rb::rust_connection::RustConnection;
use x11rb::protocol::xproto::{ConnectionExt, AtomEnum};
use crate::sampler::OsContextState;
use std::error::Error;

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
                let mut w_app = String::new();

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

                let parts: Vec<&[u8]> = reply_class.value.split(|&b| b == 0).filter(|p| !p.is_empty()).collect();
                if let Some(cls) = parts.last() {
                    w_app = String::from_utf8_lossy(cls).to_string();
                } else if let Some(inst) = parts.first() {
                     w_app = String::from_utf8_lossy(inst).to_string();
                }

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
