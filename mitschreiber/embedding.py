"""Deterministic, zero-dependency demo embeddings."""
from __future__ import annotations

import hashlib
import re
from typing import List

_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9_]{3,}")


def _hash32(text: str, dim: int = 32) -> List[float]:
    """Return a stable pseudo-embedding in [-0.5, 0.5)."""
    if dim > 64:
        raise ValueError("dim must be <= 64 for blake2b digest sizing")
    digest = hashlib.blake2b(text.encode("utf-8"), digest_size=dim).digest()
    return [byte / 255.0 - 0.5 for byte in digest]


def simple_keyphrases(text: str, top_n: int = 5) -> List[str]:
    """Extract stable first-occurrence tokens for demo records."""
    seen = set()
    phrases: List[str] = []
    for match in _WORD_RE.finditer(text.lower()):
        token = match.group(0)
        if token not in seen:
            seen.add(token)
            phrases.append(token)
        if len(phrases) >= top_n:
            break
    return phrases


def _schema_keyphrases(phrases: List[str]) -> List[str]:
    bounded = [phrase.strip()[:96] for phrase in phrases if phrase.strip()]
    return bounded[:64] or ["context"]


def build_embed_record(
    *,
    ts_iso: str,
    session: str,
    app: str,
    window: str,
    text: str,
    dim: int = 32,
) -> dict:
    """Construct a contract-valid ``os.context.text.embed`` record.

    ``session`` remains an input for API compatibility but is intentionally not
    persisted because the canonical embed contract is privacy-minimal.
    """
    _ = session
    app_value = str(app or "").strip()[:128] or "unknown"
    window_value = str(window or "").strip()[:512]
    record = {
        "ts": ts_iso,
        "source": "mitschreiber",
        "app": app_value,
        "keyphrases": _schema_keyphrases(simple_keyphrases(text)),
        "embedding": _hash32(text, dim=dim),
        "hash_id": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "privacy": {"raw_retained": False},
        "tags": ["model:hash32-demo"],
    }
    if window_value:
        record["window"] = window_value
    return record
