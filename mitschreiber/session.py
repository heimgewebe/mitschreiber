# mitschreiber/session.py
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import json, fcntl, time, os
from typing import Dict, Any, Optional

from mitschreiber._mitschreiber import start_session, stop_session, poll_state

HOME = Path.home()
DATA_DIR = HOME / ".local" / "share" / "mitschreiber"
WAL_DIR = DATA_DIR / "wal"
SESSIONS_DIR = DATA_DIR / "sessions"

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        fcntl.flock(f, fcntl.LOCK_UN)

def _emit_embed(state_evt: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Minimaler Stub: bildet ein deterministisches kleines „Embedding“
    # aus app+window Hash – genügt für Pipe-Integration & Schema-Form.
    import hashlib
    text = f"{state_evt.get('app','')}|{state_evt.get('window','')}"
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    # Achtung: Demo-Embedding mit 8 Werten
    vec = [((ord(c) % 17) - 8) / 100.0 for c in h[:8]]
    return {
        "ts": _now_iso(),
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

    wal = WAL_DIR / f"session-{session_id}.jsonl"
    try:
        while True:
            raw_evt = poll_state(session_id)  # -> dict oder None
            if raw_evt:
                evt = json.loads(raw_evt)
                # Normalisieren & schreiben
                evt["ts"] = _now_iso()
                evt["source"] = "os.context.state"
                evt["session"] = session_id
                _append_jsonl(wal, evt)

                if embed:
                    eevt = _emit_embed(evt)
                    if eevt:
                        _append_jsonl(wal, eevt)

            time.sleep(poll_ms / 1000.0)
    except KeyboardInterrupt:
        pass
    finally:
        stop_session(session_id)

# Für CLI import
__all__ = ["run_session", "SESSIONS_DIR"]
