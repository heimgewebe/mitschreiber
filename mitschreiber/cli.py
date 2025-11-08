from __future__ import annotations
import argparse
import json
import os
import signal
import time
from typing import Optional

from .paths import WAL_DIR, SESS_DIR
from .session import SessionConfig, start_interactive_session, ACTIVE_FILE, STATE_ROOT

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
    # Start interactive (blocking) loop; this function schreibt audit + active.json
    start_interactive_session(cfg)
    return 0

def cmd_stop(_args: argparse.Namespace) -> int:
    try:
        active = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print("No active session.")
        return 1
    pid = active.get("pid")
    if not isinstance(pid, int):
        print("Active session file is corrupt (missing pid).")
        return 1

    if not _is_mitschreiber_proc(pid):
        print(f"PID {pid} does not appear to be a mitschreiber process. Stale session file?")
        return 1

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM to session pid={pid}.")
    except ProcessLookupError:
        print("No running process for recorded session; clearing active status.")
        try:
            ACTIVE_FILE.unlink()
        except FileNotFoundError:
            pass
    return 0

def cmd_status(_args: argparse.Namespace) -> int:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    if not ACTIVE_FILE.exists():
        print("No active session.")
        return 0
    try:
        active = json.loads(ACTIVE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Failed to read active status: {e}")
        return 1
    pid = active.get("pid")
    running = False
    if isinstance(pid, int):
        try:
            os.kill(pid, 0)
            running = True
        except ProcessLookupError:
            running = False
    flags = active.get("flags", {})
    print(f"Session: {active.get('session')}")
    print(f"PID: {pid}  running={running}")
    print(f"Started: {active.get('started_at')}")
    print(f"Embed: {flags.get('embed')}  Clipboard: {flags.get('clipboard')}  Screenshots: {flags.get('screenshots')}")
    print(f"WAL: {active.get('wal_path')}")
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
