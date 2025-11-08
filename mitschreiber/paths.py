from __future__ import annotations
from pathlib import Path

DATA_HOME = Path.home() / ".local" / "share" / "mitschreiber"
WAL_DIR = DATA_HOME / "wal"
SESS_DIR = DATA_HOME / "sessions"

def init_directories():
    DATA_HOME.mkdir(parents=True, exist_ok=True)
    SESS_DIR.mkdir(parents=True, exist_ok=True)
