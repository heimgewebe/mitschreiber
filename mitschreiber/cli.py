# mitschreiber/cli.py
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from .session import SessionConfig, start as sess_start, run_loop, stop as sess_stop, STATUS_FILE

def cmd_start(ns: argparse.Namespace) -> int:
    cfg = SessionConfig(
        clipboard_allowed=ns.clipboard,
        screenshots_allowed=ns.screenshots,
        poll_interval_ms=ns.poll_interval,
        embeddings_enabled=ns.embed,
    )
    h = sess_start(cfg)
    print(f"Session {h.id} active "
          f"(clipboard={'on' if cfg.clipboard_allowed else 'off'}, "
          f"screenshots={'on' if cfg.screenshots_allowed else 'off'}, "
          f"embed={'on' if cfg.embeddings_enabled else 'off'})")
    print(f"WAL → {h.wal_path}")
    run_loop(h)
    return 0

def cmd_stop(_ns: argparse.Namespace) -> int:
    # Status lesen, falls aktiv
    if STATUS_FILE.exists():
        content = STATUS_FILE.read_text(encoding="utf-8")
        st = json.loads(content if content.strip() else "{}")
        sid = st.get("session") if st.get("active") else st.get("last_session")
        if sid:
            sess_stop(sid)
            print(f"Session {sid} stopped")
            return 0
    print("No active session found")
    return 1

def cmd_status(_ns: argparse.Namespace) -> int:
    if STATUS_FILE.exists():
        print(STATUS_FILE.read_text(encoding="utf-8"))
        return 0
    print(json.dumps({"active": False}, ensure_ascii=False))
    return 0

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser("mitschreiber")
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("start", help="Start a capture session")
    ps.add_argument("--clipboard", action="store_true", help="capture clipboard (opt-in)")
    ps.add_argument("--screenshots", action="store_true", help="allow screenshots (reserved)")
    ps.add_argument("--poll-interval", type=int, default=500, help="poll interval in ms (default: 500)")
    ps.add_argument("--embed", action="store_true", help="enable embeddings (hook, implemented in step 3)")
    ps.set_defaults(func=cmd_start)

    pt = sub.add_parser("stop", help="Stop the active or last session")
    pt.set_defaults(func=cmd_stop)

    pst = sub.add_parser("status", help="Show active/last session info")
    pst.set_defaults(func=cmd_status)

    return p

def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(argv)
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
