# mitschreiber/session.py
from __future__ import annotations
from pathlib import Path
import json, fcntl, time
from typing import Dict, Any, Optional

from mitschreiber._mitschreiber import start_session, stop_session, poll_state
from .util import now_iso
from .paths import WAL_DIR, SESS_DIR

# Use SESS_DIR for consistency with paths.py
SESSIONS_DIR = SESS_DIR

class WalWriter:
    def __init__(self, path: Path):
        self.path = path
        self.file = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.file = open(self.path, "a", encoding="utf-8")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()

    def append(self, obj: Dict[str, Any]):
        if not self.file:
            return
        fcntl.flock(self.file, fcntl.LOCK_EX)
        try:
            self.file.write(json.dumps(obj, ensure_ascii=False) + "\n")
            self.file.flush()
        finally:
            fcntl.flock(self.file, fcntl.LOCK_UN)

def _emit_embed(state_evt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Minimaler Stub: bildet ein deterministisches kleines „Embedding“
    # aus app+window Hash – genügt für Pipe-Integration & Schema-Form.
    import hashlib
    text = f"{state_evt.get('app','')}|{state_evt.get('window','')}"
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    # Achtung: Demo-Embedding mit 8 Werten
    vec = [((ord(c) % 17) - 8) / 100.0 for c in h[:8]]
    return {
        "ts": now_iso(),
        "source": "os.context.text.embed",
        "session": state_evt["session"],
        "app": state_evt.get("app"),
        "window": state_evt.get("window"),
        "keyphrases": [w for w in text.split("|") if w],
        "embedding": vec,
        "hash_id": f"sha256:{h}",
        "privacy": {"raw_retained": False},
        "meta": {"model": "demo-embedding-stub"}
    }

def run_session(session_id: str, embed: bool, clipboard: bool, poll_ms: int):
    cfg = {
        "clipboard_allowed": bool(clipboard),
        "screenshots_allowed": False,
        "poll_interval_ms": int(poll_ms),
    }
    start_session(session_id, cfg)

    wal_path = WAL_DIR / f"session-{session_id}.jsonl"

    # Calculate poll interval in seconds
    interval_sec = poll_ms / 1000.0

    try:
        with WalWriter(wal_path) as writer:
            next_tick = time.time()
            while True:
                # Poll state now returns a list of JSON strings
                raw_events = poll_state(session_id)

                for raw_evt in raw_events:
                    evt = json.loads(raw_evt)
                    # Normalisieren & schreiben
                    evt["ts"] = now_iso()
                    evt["source"] = "os.context.state"
                    evt["session"] = session_id
                    writer.append(evt)

                    if embed:
                        eevt = _emit_embed(evt)
                        if eevt:
                            writer.append(eevt)

                # Drift-corrected sleep
                next_tick += interval_sec
                sleep_time = next_tick - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    # If we are behind, just update next_tick to now to avoid burst catch-up
                    next_tick = time.time()

    except KeyboardInterrupt:
        pass
    finally:
        stop_session(session_id)

# Für CLI import
__all__ = ["run_session", "SESSIONS_DIR"]
