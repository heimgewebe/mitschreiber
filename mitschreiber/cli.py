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
    active = _active_path()
    try:
        if not active.exists():
            print("No active session.")
            return

        # Defensive: file may disappear or be truncated between exists/read.
        content = active.read_text(encoding="utf-8")
        try:
            meta = json.loads(content)
        except json.JSONDecodeError:
            print("No active session (corrupt file).")
            active.unlink(missing_ok=True)
            return

        pid = meta.get("pid")
        if pid:
            try:
                p = psutil.Process(pid)
                if p.status() == psutil.STATUS_ZOMBIE:
                    raise psutil.NoSuchProcess(pid, "Zombie")

                # Verify it's a python process or related to us.
                # Stricter check "mitschreiber in cmdline" is too fragile (renames, wrappers).
                # If we can access the process and it is not a Zombie, we assume it is ours
                # because the PID file is inside our private data directory.
                pass
            except (psutil.NoSuchProcess, psutil.ZombieProcess, psutil.AccessDenied):
                print("No active session (stale file).")
                active.unlink(missing_ok=True)
                return

        print(content)

    except FileNotFoundError:
        print("No active session.")

def cmd_stop(_):
    active = _active_path()
    try:
        if not active.exists():
            print("No active session.")
            return
        meta = json.loads(active.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        print("No active session.")
        active.unlink(missing_ok=True)
        return

    pid = meta.get("pid")
    try:
        if not pid:
            print("No active session.")
            active.unlink(missing_ok=True)
            return
        try:
            p = psutil.Process(pid)
            if p.status() == psutil.STATUS_ZOMBIE:
                raise psutil.NoSuchProcess(pid, "Zombie")
        except psutil.NoSuchProcess:
            print(f"Process {pid} not found. Stale session file.")
            active.unlink(missing_ok=True)
            return

        # We trust the PID from our private active.json.
        # If the PID was reused by a root process, os.kill will raise PermissionError, which we handle.
        os.kill(pid, signal.SIGINT)
        print(f"Sent SIGINT to PID {pid}")
    except (psutil.AccessDenied, PermissionError):
        print(f"Stop failed: Permission denied when accessing PID {pid}.")
    except Exception as e:
        print(f"Stop hint: {e}")
        # In case of error (e.g. permission denied), we might want to cleanup if we are sure it's dead,
        # but safely we let the user retry or manually cleanup if force needed.
        # But if the process is genuinely gone, we should cleanup.
        if isinstance(e, ProcessLookupError) or (isinstance(e, OSError) and e.errno == 3): # ESRCH
            active.unlink(missing_ok=True)

    # Note: We do NOT unlink active.json here in the success case.
    # The running process (cmd_start) owns the file and will unlink it in its finally block
    # when it receives the SIGINT and shuts down.
    # This prevents the race condition where cmd_stop deletes the file, and cmd_start tries to delete it again
    # (which is harmless with missing_ok=True) or worse, cmd_start is still running and the file is gone,
    # confusing status checks.

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
