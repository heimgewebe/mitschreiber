# mitschreiber/session.py
from __future__ import annotations

import json
import os
import signal
import time
import uuid
import fcntl
import hashlib
from dataclasses import dataclass, asdict
from datetime import timezone, datetime
from pathlib import Path
from typing import Optional, Dict, Any

from .paths import WAL_DIR, SESS_DIR
from .util import now_iso  # Single Source of Truth für Zeitstempel
from .embedding import build_embed_record

# Rust-Bindings (pyo3): in src/lib.rs als _mitschreiber exportiert
# und über das Python-Paket als "mitschreiber" importierbar
from mitschreiber import (
    start_session as rs_start,
    stop_session as rs_stop,
    poll_state as rs_poll,
)

STATE_ROOT = Path.home()/".local/share/mitschreiber"
SESSIONS = STATE_ROOT/"sessions"
SESSIONS.mkdir(parents=True, exist_ok=True)
ACTIVE_FILE = STATE_ROOT/"active.json"


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
    rs_stop(session_id)

def _text_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def _write_json(path: Path, obj: Dict[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

def _remove_silent(path: Path):
    try:
        path.unlink()
    except FileNotFoundError:
        # File does not exist; nothing to remove. Exception intentionally ignored.
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
    last_window: Optional[str] = None
    last_clip_fp: Optional[str] = None

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

                    trigger_embed = False
                    if window and window != last_window:
                        trigger_embed = True
                        last_window = window

                    clip_fp = None
                    if isinstance(clip, str) and clip.strip():
                        clip_fp = _text_fingerprint(clip)
                        if clip_fp != last_clip_fp:
                            trigger_embed = True
                            last_clip_fp = clip_fp

                    if trigger_embed:
                        text_material = " ".join(t for t in (window, clip or "") if t).strip()
                        if text_material:
                            embed_evt = build_embed_record(
                                ts_iso=event["ts"],
                                session=h.id,
                                app=app,
                                window=window,
                                text=text_material,
                                dim=32,  # keep >= schema min
                            )
                            append_jsonl(h.wal_path, embed_evt)

            time.sleep(poll_sleep)
    finally:
        stop(h.id)


def _write_audit_and_active(h: SessionHandle) -> None:
    sess_dir = SESSIONS / h.id
    sess_dir.mkdir(parents=True, exist_ok=True)
    audit_file = sess_dir / "audit.json"
    started_at = now_iso()
    pid = os.getpid()
    audit = {
        "session": h.id,
        "started_at": started_at,
        "pid": pid,
        "flags": {
            "clipboard": h.cfg.clipboard_allowed,
            "screenshots": h.cfg.screenshots_allowed,
            "embed": h.cfg.embeddings_enabled,
            "poll_ms": h.cfg.poll_interval_ms,
        },
        "wal_path": str(h.wal_path),
    }
    _write_json(audit_file, audit)
    _write_json(ACTIVE_FILE, {**audit, "active": True})


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

    clip_status = "on" if h.cfg.clipboard_allowed else "off"
    embed_status = "on" if h.cfg.embeddings_enabled else "off"
    screenshots_status = "on" if h.cfg.screenshots_allowed else "off"

    print(f"Session {h.id} active "
          f"(clipboard={clip_status}, screenshots={screenshots_status}, embed={embed_status})")
    print(f"WAL → {h.wal_path}")

    try:
        run_loop(h)
    finally:
        # best-effort cleanup
        try:
            (SESSIONS / h.id / "audit.json").rename(SESSIONS / h.id / "audit.finished.json")
            active = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
            if active.get("pid") == h.pid:
                _remove_silent(ACTIVE_FILE)
        except Exception:
            # Ignore errors during cleanup; file may not exist or be locked
            pass
        print("session stopped.")
