# mitschreiber/paths.py
from pathlib import Path

APP_DIR = Path.home() / ".local" / "share" / "mitschreiber"
WAL_DIR = APP_DIR / "wal"
SESS_DIR = APP_DIR / "sessions"
RUNTIME_DIR = Path.cwd() / ".runtime"  # falls gewünscht

def init_directories():
    for d in (APP_DIR, WAL_DIR, SESS_DIR, RUNTIME_DIR):
        d.mkdir(parents=True, exist_ok=True)
