//! Minimaler Smoke-Test für `/metrics`.
//!
//! Dieser Test ist bewusst als `#[ignore]` markiert, damit reguläre CI-Läufe
//! nicht scheitern, wenn kein Server läuft. Er kann gezielt aktiviert werden:
//!
//! ```bash
//! HAUSKI_TEST_BASE_URL="http://127.0.0.1:8080" \
//!   cargo test -p hauski-core --test metrics_smoke -- --ignored --nocapture
//! ```
//!
//! Erwartung: Ein laufender hausKI-Server (z. B. `hauski-cli serve`) exponiert
//! Prometheus-Metriken unter GET /metrics (Content-Type text/plain; version=0.0.4).

use http::StatusCode;
use reqwest::header::{ACCEPT, CONTENT_TYPE};
use std::time::Duration;

fn base_url() -> String {
    std::env::var("HAUSKI_TEST_BASE_URL")
        .ok()
        .unwrap_or_else(|| "http://127.0.0.1:8080".to_string())
}

#[tokio::test]
#[ignore] // nur on-demand ausführen
async fn metrics_endpoint_exposes_prometheus_text() {
    let url = format!("{}/metrics", base_url().trim_end_matches('/'));
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .expect("failed to build reqwest client");
    let resp = client
        .get(&url)
        .header(ACCEPT, "text/plain; version=0.0.4")
        .send()
        .await
        .expect("request to /metrics failed");

    assert_eq!(resp.status(), StatusCode::OK, "unexpected status for /metrics");

    // Content-Type sollte Prometheus-Textformat sein
    let ctype = resp
        .headers()
        .get(CONTENT_TYPE)
        .and_then(|v| v.to_str().ok())
        .unwrap_or_default()
        .to_lowercase();
    assert!(
        ctype.starts_with("text/plain") && ctype.contains("version=0.0.4"),
        "unexpected content-type: {}",
        ctype
    );

    let body = resp.text().await.expect("reading response body failed");
    // Heuristik: Prometheus-Textformat enthält i. d. R. HELP/TYPE-Zeilen
    let preview = {
        let bytes = body.as_bytes();
        let len = bytes.len().min(64);
        format!("{:?}", &bytes[..len])
    };
    assert!(
        body.contains("# HELP") || body.contains("# TYPE"),
        "unexpected /metrics payload (length={}): first bytes: {}",
        body.len(),
        preview
    );
}

