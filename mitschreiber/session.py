# mitschreiber/session.py
from __future__ import annotations

import json
import os
import signal
import time
import uuid
import fcntl
from dataclasses import dataclass, asdict
from datetime import timezone, datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .paths import WAL_DIR, SESS_DIR
from .util import now_iso  # Single Source of Truth für Zeitstempel

# Rust-Bindings (pyo3): in src/lib.rs als _mitschreiber exportiert
# und über das Python-Paket als "mitschreiber" importierbar
from mitschreiber import (
    start_session as rs_start,
    stop_session as rs_stop,
    poll_state as rs_poll,
)


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    """
    Hängt ein Objekt zeilweise (JSONL) an und schützt per flock
    gegen Konkurrenzzugriffe.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")
        fcntl.flock(f, fcntl.LOCK_UN)


@dataclass
class SessionConfig:
    clipboard_allowed: bool = False
    screenshots_allowed: bool = False
    poll_interval_ms: int = 500
    embeddings_enabled: bool = False  # Schritt 3
    embed_min_interval_s: float = 10.0
    embed_min_chars: int = 12


@dataclass
class SessionHandle:
    id: str
    wal_path: Path
    cfg: SessionConfig
    pid: int
    started_ts: str


def start(cfg: SessionConfig) -> SessionHandle:
    sid = str(uuid.uuid4())
    rs_cfg = asdict(cfg)
    # Rust-Session starten (PyDict/Mapping genügt)
    rs_start(sid, rs_cfg)
    wal_path = WAL_DIR / f"session-{sid}.jsonl"
    return SessionHandle(
        id=sid,
        wal_path=wal_path,
        cfg=cfg,
        pid=os.getpid(),
        started_ts=now_iso(),
    )


def stop(session_id: str) -> None:
    try:
        rs_stop(session_id)
    finally:
        # Platz für spätere lokale Aufräumarbeiten
        pass


def run_loop(h: SessionHandle) -> None:
    _stop = {"flag": False}

    def _graceful(_signum, _frame):
        _stop["flag"] = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _graceful)

    # kleiner Takt-Puffer
    poll_sleep = max(h.cfg.poll_interval_ms, 50) / 1000.0

    # Embeddings evtl. per ENV aktivieren (Fallback, wenn CLI-Flag noch fehlt)
    if not h.cfg.embeddings_enabled:
        h.cfg.embeddings_enabled = os.getenv("MITSCHREIBER_EMBED", "0").lower() in (
            "1",
            "true",
            "yes",
        )

    # Embedding-Guards
    last_embed_hash: Optional[str] = None
    last_embed_ts: float = 0.0

    # Lazy import (nur wenn benötigt)
    if h.cfg.embeddings_enabled:
        from .embed import build_embed_event  # noqa: WPS433 (local import by design)

    try:
        while not _stop["flag"]:
            # Die Rust-Funktion liefert Option[str] (JSON-String) oder None
            raw = rs_poll(h.id)
            if raw:
                # JSON string → dict
                try:
                    state = json.loads(raw)
                except json.JSONDecodeError:
                    # defensiv: nächster Takt
                    time.sleep(poll_sleep)
                    continue

                # Schema-Form für state-Event ergänzen
                event = {
                    "ts": now_iso(),
                    "source": "os.context.state",
                    "session": h.id,
                    "app": state.get("app", ""),
                    "window": state.get("window", ""),
                    "meta": {
                        "sampler": "rust",
                        "clipboard_observed": bool(state.get("clipboard")),
                    },
                }
                append_jsonl(h.wal_path, event)

                # Embeddings (opt-in)
                if h.cfg.embeddings_enabled:
                    app = state.get("app", "") or ""
                    window = state.get("window", "") or ""
                    clip = state.get("clipboard")
                    chunks = [window.strip()]
                    if clip and isinstance(clip, str):
                        chunks.append(clip.strip())
                    text = "\n\n".join([c for c in chunks if c])

                    if text and len(text) >= h.cfg.embed_min_chars:
                        now_t = time.monotonic()
                        if (now_t - last_embed_ts) >= h.cfg.embed_min_interval_s:
                            embed_evt, text_hash = build_embed_event(
                                text=text,
                                session=h.id,
                                app=app,
                                window=window,
                            )
                            if text_hash != last_embed_hash:
                                append_jsonl(h.wal_path, embed_evt)
                                last_embed_hash = text_hash
                                last_embed_ts = now_t

            time.sleep(poll_sleep)
    finally:
        stop(h.id)


def _write_audit_and_active(h: SessionHandle) -> None:
    sess_dir = SESS_DIR / h.id
    sess_dir.mkdir(parents=True, exist_ok=True)
    (sess_dir / "audit.json").write_text(
        json.dumps(
            {
                "session": h.id,
                "ts_started": h.started_ts,
                "pid": h.pid,
                "wal_path": str(h.wal_path),
                "config": asdict(h.cfg),
                "sampler": "rust",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    active = {
        "session": h.id,
        "pid": h.pid,
        "wal_path": str(h.wal_path),
        "config": asdict(h.cfg),
    }
    tmp = (SESS_DIR / "active.json").with_suffix(".tmp")
    tmp.write_text(json.dumps(active, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(SESS_DIR / "active.json")


def start_interactive_session(cfg: SessionConfig) -> None:
    """
    Startet eine sichtbare Session im Vordergrund (blocking).
    Schreibt Audit + active.json für CLI-Status/Stop.
    """
    # env-fallbacks (falls User nur ENV setzt)
    if not cfg.embeddings_enabled:
        cfg.embeddings_enabled = os.getenv("MITSCHREIBER_EMBED", "0").lower() in (
            "1",
            "true",
            "yes",
        )

    h = start(cfg)
    _write_audit_and_active(h)
    print(
        f"session {h.id} active  "
        f"(clipboard={cfg.clipboard_allowed}, "
        f"screenshots={cfg.screenshots_allowed}, "
        f"embed={cfg.embeddings_enabled})"
    )
    print(f"wal: {h.wal_path}")
    try:
        run_loop(h)
    finally:
        # best-effort cleanup
        try:
            (SESS_DIR / "active.json").unlink(missing_ok=True)
        except Exception:
            # Ignore errors during cleanup; file may not exist or be locked
            pass
        print("session stopped.")
