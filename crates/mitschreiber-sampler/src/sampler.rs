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
use crossbeam_channel::{bounded, Sender, Receiver};

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

    // Use a bounded channel to prevent memory leaks if the consumer (Python) is too slow
    // or stalled. Dropping new events is preferable to OOM.
    let (tx, rx): (Sender<OsContextState>, Receiver<OsContextState>) = bounded(10_000);
    let alive = Arc::new(AtomicBool::new(true));
    let thread_alive = Arc::clone(&alive);
    let thread_sid = sid.clone(); // for drop diagnostics inside the thread

    // Background thread owns the sender
    let handle = thread::spawn(move || {
        let mut counter: u64 = 0;
        let mut drops: u64 = 0;

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
            match tx.try_send(state) {
                Ok(()) => {}
                Err(crossbeam_channel::TrySendError::Full(_)) => {
                    // Intentionally lossy under sustained queue pressure: freshness over
                    // completeness. Blocking here instead would deadlock stop_session():
                    // the thread would be stuck in send() while stop_session() holds the
                    // Receiver alive and waits in join() — neither side can make progress.
                    // TODO: expose `drops` as a Prometheus counter once metrics infra exists.
                    drops = drops.saturating_add(1);
                }
                Err(crossbeam_channel::TrySendError::Disconnected(_)) => {
                    // Receiver dropped – stop the thread.
                    break;
                }
            }
            counter = counter.wrapping_add(1);
            thread::sleep(poll_interval);
        }
        if drops > 0 {
            eprintln!(
                "mitschreiber sampler [{}]: {} event(s) dropped under queue pressure (freshness-over-completeness)",
                thread_sid, drops
            );
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

    /// Regression test for the old `tx.send()` deadlock:
    /// when the channel is full the producer must not block.
    ///
    /// Old behaviour: `send()` blocks until space is available. `stop_session()` then
    /// sets `alive = false` and calls `join()` — but the thread is stuck in `send()`,
    /// the Receiver is still held by the Session (not yet dropped), so nothing can make
    /// progress. → deadlock.
    ///
    /// New behaviour: `try_send()` returns `Full` immediately, the thread keeps looping,
    /// checks `alive` on the next iteration and exits. `join()` returns quickly.
    #[test]
    fn stop_does_not_block_when_queue_is_full() {
        use crossbeam_channel::bounded;
        use std::sync::atomic::{AtomicBool, Ordering};
        use std::sync::Arc;
        use std::time::{Duration, Instant};

        // Capacity 1: pre-fill so every subsequent try_send returns Full.
        let (tx, _rx) = bounded::<OsContextState>(1);
        let alive = Arc::new(AtomicBool::new(true));
        let thread_alive = Arc::clone(&alive);

        tx.try_send(OsContextState {
            ts: "2024-01-01T00:00:00Z".to_string(),
            app: "test".to_string(),
            window: "test".to_string(),
            clipboard: None,
        })
        .unwrap();

        let handle = std::thread::spawn(move || {
            let mut counter: u64 = 0;
            let mut sampler = StubSampler;
            while thread_alive.load(Ordering::SeqCst) {
                let state = sampler.probe(counter);
                match tx.try_send(state) {
                    Ok(()) => {}
                    Err(crossbeam_channel::TrySendError::Full(_)) => { /* drop, keep looping */ }
                    Err(crossbeam_channel::TrySendError::Disconnected(_)) => break,
                }
                counter = counter.wrapping_add(1);
                std::thread::sleep(Duration::from_millis(1));
            }
        });

        // Let the thread spin hitting Full on every iteration.
        std::thread::sleep(Duration::from_millis(20));

        // Signal stop — Receiver (_rx) is still alive, mirroring stop_session() lifecycle.
        let start = Instant::now();
        alive.store(false, Ordering::SeqCst);
        handle.join().expect("thread panicked");
        assert!(
            start.elapsed() < Duration::from_secs(2),
            "shutdown blocked: thread was stuck in send() (deadlock regression)"
        );
    }

    /// A full channel must cause events to be dropped, not cause the producer to block.
    #[test]
    fn full_queue_drops_not_blocks() {
        use crossbeam_channel::bounded;

        let (tx, _rx) = bounded::<OsContextState>(1);
        let state = OsContextState {
            ts: "2024-01-01T00:00:00Z".to_string(),
            app: "a".to_string(),
            window: "b".to_string(),
            clipboard: None,
        };
        assert!(tx.try_send(state.clone()).is_ok(), "first send should succeed");
        let second = tx.try_send(state);
        assert!(
            matches!(second, Err(crossbeam_channel::TrySendError::Full(_))),
            "expected Full on second send to a full channel, got {:?}", second,
        );
    }

    /// When the Receiver is dropped the producer loop exits via Disconnected.
    #[test]
    fn disconnected_receiver_exits_producer_loop() {
        use crossbeam_channel::bounded;
        use std::time::{Duration, Instant};

        let (tx, rx) = bounded::<OsContextState>(4);
        let handle = std::thread::spawn(move || {
            let mut counter: u64 = 0;
            let mut sampler = StubSampler;
            loop {
                let state = sampler.probe(counter);
                match tx.try_send(state) {
                    Ok(()) => {}
                    Err(crossbeam_channel::TrySendError::Full(_)) => {}
                    Err(crossbeam_channel::TrySendError::Disconnected(_)) => break,
                }
                counter = counter.wrapping_add(1);
                std::thread::sleep(Duration::from_millis(1));
            }
        });

        drop(rx); // disconnect — next try_send will return Disconnected
        let start = Instant::now();
        handle.join().expect("thread panicked");
        assert!(
            start.elapsed() < Duration::from_secs(2),
            "thread did not exit after receiver was dropped"
        );
    }
}
