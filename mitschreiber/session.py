# mitschreiber/session.py
from __future__ import annotations
import json, os, signal, time, uuid, fcntl, math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from .paths import WAL_DIR, SESS_DIR
# Rust-Bindings (pyo3): in src/lib.rs als _mitschreiber exportiert
from mitschreiber import start_session as rs_start, stop_session as rs_stop, poll_state as rs_poll

ISO = "%Y-%m-%dT%H:%M:%S.%fZ"

def now_iso() -> str:
     return datetime.now(timezone.utc).strftime(ISO)

def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    with open(path, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(line + "\n")
        finally:
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
    audit_path: Path
    cfg: SessionConfig

STATUS_FILE = SESS_DIR / "status.json"

def write_status(payload: Dict[str, Any]) -> None:
    tmp = STATUS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(STATUS_FILE)

def start(cfg: SessionConfig) -> SessionHandle:
    sid = str(uuid.uuid4())
    wal = WAL_DIR / f"session-{sid}.jsonl"
    audit = SESS_DIR / sid / "audit.json"
    (SESS_DIR / sid).mkdir(parents=True, exist_ok=True)

    # Rust-Session starten (PyDict/Mapping genügt)
    rs_start(sid, {
        "clipboard_allowed": cfg.clipboard_allowed,
        "screenshots_allowed": cfg.screenshots_allowed,
        "poll_interval_ms": cfg.poll_interval_ms,
    })

    audit_obj = {
        "session": sid,
        "started_at": now_iso(),
        "cfg": asdict(cfg),
        "host": os.uname().nodename if hasattr(os, "uname") else os.getenv("HOSTNAME", ""),
        "pid": os.getpid(),
    }
    audit.write_text(json.dumps(audit_obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    write_status({"active": True, "session": sid, "since": audit_obj["started_at"]})
    return SessionHandle(sid, wal, audit, cfg)

def stop(sid: str) -> None:
    try:
        rs_stop(sid)
    finally:
        # status aktualisieren
        st = {"active": False, "last_session": sid, "stopped_at": now_iso()}
        write_status(st)

def run_loop(h: SessionHandle) -> None:
    """Blockierender Poll-Loop. Ctrl+C oder SIGTERM beendet sauber."""
    _stop = {"flag": False}

    def _graceful(_signum, _frame):
        _stop["flag"] = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, _graceful)

    # kleiner Takt-Puffer
    poll_sleep = max(h.cfg.poll_interval_ms, 50) / 1000.0

    # Embeddings evtl. per ENV aktivieren (Fallback, wenn CLI-Flag noch fehlt)
    if not h.cfg.embeddings_enabled:
        h.cfg.embeddings_enabled = os.getenv("MITSCHREIBER_EMBED", "0").lower() in ("1", "true", "yes")

    # Embedding-Guards
    last_embed_hash: Optional[str] = None
    last_embed_ts: float = 0.0

    # Lazy import (nur wenn benötigt)
    if h.cfg.embeddings_enabled:
        from .embed import build_embed_event

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
                    "meta": {"sampler": "rust", "clipboard_observed": bool(state.get("clipboard"))},
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
