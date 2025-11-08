from __future__ import annotations
import hashlib
import re
from typing import List

_WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9_]{3,}")

def _hash32(text: str, dim: int = 32) -> List[float]:
    """
    Deterministic, zero-dep pseudo-embedding in [-0.5, 0.5).
    Using BLAKE2b so it's stable across machines and Python versions.
    """
    if dim > 64:
        raise ValueError("dim must be <= 64 for blake2b digest sizing")
    h = hashlib.blake2b(text.encode("utf-8"), digest_size=dim).digest()
    # Map each byte (0..255) -> float in [-0.5, 0.5)
    return [b / 255.0 - 0.5 for b in h]

def simple_keyphrases(text: str, top_n: int = 5) -> List[str]:
    """
    Crude keyphrase extractor: lowercase tokens >=3 chars, keep first occurrences.
    Stable and fast; replace with a real extractor later.
    """
    seen = set()
    phrases: List[str] = []
    for m in _WORD_RE.finditer(text.lower()):
        tok = m.group(0)
        if tok not in seen:
            seen.add(tok)
            phrases.append(tok)
        if len(phrases) >= top_n:
            break
    return phrases

def build_embed_record(
    *,
    ts_iso: str,
    session: str,
    app: str,
    window: str,
    text: str,
    dim: int = 32,
) -> dict:
    """
    Construct a schema-shaped os.context.text.embed record.
    """
    # Hash of the *content* we embed (helps dedup downstream)
    sha_hex = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "ts": ts_iso,
        "source": "os.context.text.embed",
        "session": session,
        "app": app,
        "window": window,
        "keyphrases": simple_keyphrases(text),
        "embedding": _hash32(text, dim=dim),
        "hash_id": f"sha256:{sha_hex}",
        "privacy": {"raw_retained": False},
        "meta": {"model": "hash32-demo"},
    }
