use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Serialize, Deserialize};

use once_cell::sync::Lazy;
use parking_lot::Mutex;
use std::collections::HashMap;
use std::thread;
use std::time::Duration;
use crossbeam_channel::{unbounded, Sender, Receiver, TryRecvError};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct OsContextState {
    pub ts: String,
    pub app: String,
    pub window: String,
    pub clipboard: Option<String>,
}

/// Per-session controller, holding the communication channel
struct Session {
    alive: bool,
    // The receiver is now stored here to be polled
    rx: Receiver<OsContextState>,
}

// Global session map
static SESSIONS: Lazy<Mutex<HashMap<String, Session>>> = Lazy::new(|| Mutex::new(HashMap::new()));

/// Spawns a background thread that pushes OsContextState into a channel.
#[pyfunction]
pub fn start_session(_py: Python, session_id: &str, cfg: &PyDict) -> PyResult<()> {
    let sid = session_id.to_string();
    let poll_interval_ms = cfg
        .get_item("poll_interval_ms")?
        .map(|v| v.extract::<u64>())
        .transpose()?
        .unwrap_or(500);

    let (tx, rx): (Sender<OsContextState>, Receiver<OsContextState>) = unbounded();

    {
        let mut sessions = SESSIONS.lock();
        if sessions.contains_key(&sid) {
            return Ok(()); // Already running
        }
        // Store the receiver end for polling
        sessions.insert(sid.clone(), Session { alive: true, rx });
    }

    // Background thread owns the sender
    thread::spawn(move || {
        let mut counter: u64 = 0;
        let poll_interval = Duration::from_millis(poll_interval_ms);
        // The loop condition now checks the `alive` flag in the session map
        while SESSIONS.lock().get(&sid).map_or(false, |s| s.alive) {
            let state = probe_once(counter);
            if tx.send(state).is_err() {
                // Stop if the receiver has been dropped
                break;
            }
            counter = counter.wrapping_add(1);
            thread::sleep(poll_interval);
        }
    });

    Ok(())
}

/// Marks a session as not alive, causing its background thread to exit.
#[pyfunction]
pub fn stop_session(_py: Python, session_id: &str) -> PyResult<()> {
    let mut sessions = SESSIONS.lock();
    if let Some(session) = sessions.get_mut(session_id) {
        session.alive = false;
    }
    // We can also remove the session entirely if we want to clean up immediately
    sessions.remove(session_id);
    Ok(())
}

/// Non-blockingly polls the last known state from the receiver channel.
#[pyfunction]
pub fn poll_state(_py: Python, session_id: &str) -> PyResult<Option<String>> {
    let sessions = SESSIONS.lock();
    if let Some(session) = sessions.get(session_id) {
        // Use try_recv for a non-blocking poll
        match session.rx.try_recv() {
            Ok(state) => {
                let json = serde_json::to_string(&state)
                    .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON serialization error: {}", e)))?;
                Ok(Some(json))
            },
            Err(TryRecvError::Empty) => Ok(None), // No new state available
            Err(TryRecvError::Disconnected) => {
                // The sender (thread) has shut down
                Ok(None)
            }
        }
    } else {
        // Session not found
        Ok(None)
    }
}

/// Simple probe to simulate changing state (replace with real X11/Wayland code)
fn probe_once(counter: u64) -> OsContextState {
    let ts = chrono::Utc::now().to_rfc3339();
    let app = if counter % 3 == 0 { "firefox" } else { "vscode" };
    let window = if counter % 5 == 0 { "README.md" } else { "Editor" };
    OsContextState {
        ts,
        app: app.to_string(),
        window: window.to_string(),
        clipboard: None,
    }
}

// #[cfg(test)]
// mod tests {
//     use super::*;

//     #[test]
//     fn start_stop_cycle() {
//         let sid = "test-session-1";
//         pyo3::Python::with_gil(|py| {
//             let cfg = PyDict::new(py);
//             cfg.set_item("poll_interval_ms", 10u64).unwrap();

//             // Start session
//             start_session(py, sid, cfg).unwrap();

//             // Allow some events to be generated
//             std::thread::sleep(std::time::Duration::from_millis(50));

//             // Poll a few times to see if we get data
//             let mut received_state = false;
//             for _ in 0..5 {
//                 if let Ok(Some(_)) = poll_state(py, sid) {
//                     received_state = true;
//                     break;
//                 }
//                 std::thread::sleep(std::time::Duration::from_millis(15));
//             }
//             assert!(received_state, "Did not receive state from the session");

//             // Stop session
//             stop_session(py, sid).unwrap();

//             // Verify the session is gone
//             assert!(SESSIONS.lock().get(sid).is_none(), "Session was not removed after stopping");
//         });
//     }
// }
