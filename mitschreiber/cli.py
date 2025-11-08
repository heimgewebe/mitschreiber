from __future__ import annotations
import argparse
import json
import os
import signal
import time
from typing import Optional

from .paths import WAL_DIR, SESS_DIR
from .session import SessionConfig, start_interactive_session

ACTIVE_FILE = SESS_DIR / "active.json"

def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but different owner/session; treat as alive.
        return True

def _is_mitschreiber_proc(pid: int) -> bool:
    """
    Checks if the process is likely a mitschreiber instance.
    This is a safeguard against killing random processes.
    """
    if not _pid_alive(pid):
        return False
    try:
        with open(f"/proc/{pid}/cmdline", "r", encoding="utf-8") as f:
            cmdline = f.read()
            return "mitschreiber" in cmdline
    except FileNotFoundError:
        # Process vanished or not on a procfs system.
        return False
    except Exception:
        # Broad catch-all for permission errors or other issues.
        return False

def cmd_start(args: argparse.Namespace) -> int:
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    WAL_DIR.mkdir(parents=True, exist_ok=True)

    cfg = SessionConfig(
        clipboard_allowed=bool(args.clipboard),
        screenshots_allowed=bool(args.screenshots),
        poll_interval_ms=int(args.poll_interval),
        embeddings_enabled=bool(args.embed),
    )

    print("mitschreiber: starting session …")
    print(f"  flags: clipboard={cfg.clipboard_allowed} screenshots={cfg.screenshots_allowed} embed={cfg.embeddings_enabled}")
    print(f"  poll interval: {cfg.poll_interval_ms} ms")
    print(f"  wal dir: {WAL_DIR}")

    # Start interactive (blocking) loop; this function schreibt audit + active.json
    start_interactive_session(cfg)
    return 0

def cmd_stop(_args: argparse.Namespace) -> int:
    if not ACTIVE_FILE.exists():
        print("mitschreiber: no active session")
        return 0
    try:
        data = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
    except Exception:
        print("mitschreiber: active state unreadable – remove file and stop manually if needed:", ACTIVE_FILE)
        return 2

    pid = int(data.get("pid", 0))
    sid = data.get("session")
    if pid <= 0:
        print("mitschreiber: invalid pid in active.json")
        return 2

    if not _pid_alive(pid):
        print(f"mitschreiber: session {sid} is not running (stale active.json) – cleaning up")
        try:
            ACTIVE_FILE.unlink(missing_ok=True)  # py>=3.8
        except Exception:
            pass
        return 0

    if not _is_mitschreiber_proc(pid):
        print(f"mitschreiber: process with pid {pid} is not a mitschreiber instance – not stopping")
        return 1

    print(f"mitschreiber: stopping session {sid} (pid={pid}) …")
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        # Process already exited
        pass
    # wait a bit
    for _ in range(20):
        if not _pid_alive(pid):
            break
        time.sleep(0.1)
    if _pid_alive(pid):
        print("  process did not exit in time, sending SIGKILL")
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        ACTIVE_FILE.unlink(missing_ok=True)
    except Exception as e:
        print(f"mitschreiber: warning – could not remove active file {ACTIVE_FILE}: {e!r}")
    print("mitschreiber: stopped.")
    return 0

def cmd_status(_args: argparse.Namespace) -> int:
    if not ACTIVE_FILE.exists():
        print("mitschreiber: no active session")
        return 0
    try:
        data = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
    except Exception:
        print("mitschreiber: active state unreadable:", ACTIVE_FILE)
        return 2
    pid = int(data.get("pid", 0))
    sid = data.get("session")
    wal = data.get("wal_path")
    cfg = data.get("config", {})

    alive = _pid_alive(pid)
    print(f"Session: {sid}")
    print(f"  pid: {pid}  alive={alive}")
    print(f"  wal: {wal}")
    print(f"  flags: clipboard={cfg.get('clipboard_allowed')} screenshots={cfg.get('screenshots_allowed')} embed={cfg.get('embeddings_enabled')}")
    print(f"  poll_interval_ms: {cfg.get('poll_interval_ms')}")
    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="mitschreiber", description="On-device context sampler & embedder")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("start", help="start a visible session (blocking until Ctrl+C)")
    ps.add_argument("--clipboard", action="store_true", help="allow clipboard capture (opt-in)")
    ps.add_argument("--screenshots", action="store_true", help="allow screenshots capture (opt-in)")
    ps.add_argument("--poll-interval", type=int, default=500, help="poll interval in ms (default: 500)")
    ps.add_argument("--embed", action="store_true", help="enable embeddings pipeline (opt-in)")
    ps.set_defaults(func=cmd_start)

    pk = sub.add_parser("stop", help="stop the active session")
    pk.set_defaults(func=cmd_stop)

    pst = sub.add_parser("status", help="show active/last session status")
    pst.set_defaults(func=cmd_status)

    return p

def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    rc = args.func(args)
    raise SystemExit(rc)
