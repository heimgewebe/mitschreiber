# mitschreiber/cli.py
from __future__ import annotations
import argparse, json, os, signal, sys, uuid
import psutil
from pathlib import Path
from .session import run_session, SESSIONS_DIR

def _active_path() -> Path:
    return SESSIONS_DIR / "active.json"

def cmd_start(args):
    sid = str(uuid.uuid4())
    active = {
        "session_id": sid,
        "pid": os.getpid(),
        "flags": {
            "embed": bool(args.embed),
            "clipboard": bool(args.clipboard),
            "poll_interval_ms": int(args.poll_interval),
        }
    }
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    _active_path().write_text(json.dumps(active, indent=2), encoding="utf-8")
    print(f"Session {sid} active (embed={args.embed}, clipboard={args.clipboard}, poll={args.poll_interval}ms)")
    try:
        # Übergibt in den Event-Loop (blockiert bis Ctrl+C)
        run_session(session_id=sid,
                    embed=args.embed,
                    clipboard=args.clipboard,
                    poll_ms=int(args.poll_interval))
    finally:
        # Nach Beendigung (sauber oder via Crash)
        _active_path().unlink(missing_ok=True)
        print("Session stopped.")

def cmd_status(_):
    if not _active_path().exists():
        print("No active session.")
        return
    print(_active_path().read_text(encoding="utf-8"))

def cmd_stop(_):
    if not _active_path().exists():
        print("No active session.")
        return
    meta = json.loads(_active_path().read_text(encoding="utf-8"))
    pid = meta.get("pid")
    try:
        if not pid:
            return
        try:
            p = psutil.Process(pid)
            # Check if the process name or command line contains "mitschreiber"
            cmdline = " ".join(p.cmdline())
            if "mitschreiber" not in cmdline:
                print(f"PID {pid} is not a mitschreiber process. Stale session file.")
                return
        except psutil.NoSuchProcess:
            print(f"Process {pid} not found. Stale session file.")
            return

        os.kill(pid, signal.SIGINT)
        print(f"Sent SIGINT to PID {pid}")
    except Exception as e:
        print(f"Stop hint: {e}")
    finally:
        _active_path().unlink(missing_ok=True)
        print("Session stopped.")

def main(argv=None):
    p = argparse.ArgumentParser("mitschreiber")
    sub = p.add_subparsers(dest="cmd", required=True)

    s_start = sub.add_parser("start")
    s_start.add_argument("--embed", action="store_true")
    s_start.add_argument("--clipboard", action="store_true")
    s_start.add_argument("--poll-interval", type=int, default=500)
    s_start.set_defaults(fn=cmd_start)

    s_status = sub.add_parser("status")
    s_status.set_defaults(fn=cmd_status)

    s_stop = sub.add_parser("stop")
    s_stop.set_defaults(fn=cmd_stop)

    args = p.parse_args(argv)
    return args.fn(args)

if __name__ == "__main__":
    sys.exit(main())
