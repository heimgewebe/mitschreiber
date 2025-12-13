use pyo3::prelude::*;
use pyo3::types::PyDict;
use serde::{Serialize, Deserialize};

use once_cell::sync::Lazy;
use parking_lot::Mutex;
use std::collections::HashMap;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::thread::{self, JoinHandle};
use std::time::Duration;
use crossbeam_channel::{unbounded, Sender, Receiver};

#[cfg(feature = "x11")]
use crate::x11::X11Sampler;

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct OsContextState {
    pub ts: String,
    pub app: String,
    pub window: String,
    pub clipboard: Option<String>,
}

trait Sampler: Send {
    fn probe(&mut self, counter: u64) -> OsContextState;
}

struct StubSampler;
impl Sampler for StubSampler {
    fn probe(&mut self, counter: u64) -> OsContextState {
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
}

#[cfg(feature = "x11")]
struct X11SamplerWrapper(X11Sampler);

#[cfg(feature = "x11")]
impl Sampler for X11SamplerWrapper {
    fn probe(&mut self, _counter: u64) -> OsContextState {
        self.0.get_state()
    }
}

/// Per-session controller, holding the communication channel
struct Session {
    alive: Arc<AtomicBool>,
    // The receiver is now stored here to be polled
    rx: Receiver<OsContextState>,
    // The handle to the background thread
    handle: Option<JoinHandle<()>>,
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

    let mut sessions = SESSIONS.lock();
    if sessions.contains_key(&sid) {
        return Ok(()); // Already running
    }

    let (tx, rx): (Sender<OsContextState>, Receiver<OsContextState>) = unbounded();
    let alive = Arc::new(AtomicBool::new(true));
    let thread_alive = Arc::clone(&alive);

    // Background thread owns the sender
    let handle = thread::spawn(move || {
        let mut counter: u64 = 0;

        #[allow(unused_mut)]
        let mut sampler: Box<dyn Sampler> = {
            #[cfg(feature = "x11")]
            {
                match X11Sampler::new() {
                    Ok(s) => Box::new(X11SamplerWrapper(s)),
                    Err(e) => {
                        // Use println/eprintln as simple logging fallback if env_logger not init
                        eprintln!("Warning: Failed to initialize X11 sampler, falling back to Stub. Error: {}", e);
                        Box::new(StubSampler)
                    }
                }
            }
            #[cfg(not(feature = "x11"))]
            {
                Box::new(StubSampler)
            }
        };

        let poll_interval = Duration::from_millis(poll_interval_ms);
        while thread_alive.load(Ordering::SeqCst) {
            let state = sampler.probe(counter);
            if tx.send(state).is_err() {
                // Stop if the receiver has been dropped
                break;
            }
            counter = counter.wrapping_add(1);
            thread::sleep(poll_interval);
        }
    });

    sessions.insert(
        sid.clone(),
        Session {
            alive,
            rx,
            handle: Some(handle),
        },
    );

    Ok(())
}

/// Marks a session as not alive, causing its background thread to exit.
#[pyfunction]
pub fn stop_session(_py: Python, session_id: &str) -> PyResult<()> {
    if let Some(mut session) = SESSIONS.lock().remove(session_id) {
        session.alive.store(false, Ordering::SeqCst);
        if let Some(handle) = session.handle.take() {
            // It's fine to block here for a moment, to ensure clean shutdown.
            handle.join().ok();
        }
    }
    Ok(())
}

/// Non-blockingly polls all buffered states from the receiver channel.
#[pyfunction]
pub fn poll_state(_py: Python, session_id: &str) -> PyResult<Vec<String>> {
    let sessions = SESSIONS.lock();
    if let Some(session) = sessions.get(session_id) {
        // Collect all available events from the channel
        let mut events = Vec::new();
        for state in session.rx.try_iter() {
            let json = serde_json::to_string(&state)
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("JSON serialization error: {}", e)))?;
            events.push(json);
        }
        Ok(events)
    } else {
        // Session not found
        Ok(Vec::new())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn start_stop_cycle() {
        let sid = "test-session-1";
        pyo3::Python::with_gil(|py| {
            let cfg = PyDict::new(py);
            cfg.set_item("poll_interval_ms", 10u64).unwrap();

            // Start session
            start_session(py, sid, cfg).unwrap();

            // Allow some events to be generated
            std::thread::sleep(std::time::Duration::from_millis(50));

            // Poll a few times to see if we get data
            let mut received_state = false;
            for _ in 0..5 {
                if let Ok(events) = poll_state(py, sid) {
                    if !events.is_empty() {
                        received_state = true;
                        break;
                    }
                }
                std::thread::sleep(std::time::Duration::from_millis(15));
            }
            assert!(received_state, "Did not receive state from the session");

            // Stop session
            stop_session(py, sid).unwrap();

            // Verify the session is gone
            assert!(SESSIONS.lock().get(sid).is_none(), "Session was not removed after stopping");
        });
    }
}
