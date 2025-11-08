# mitschreiber/util.py
from __future__ import annotations
from datetime import datetime, timezone

ISO = "%Y-%m-%dT%H:%M:%S.%fZ"

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime(ISO)
