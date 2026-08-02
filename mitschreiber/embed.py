"""Production sentence-transformer embeddings."""
from __future__ import annotations

import hashlib
import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Tuple

from .util import now_iso

DEFAULT_MODEL = os.getenv(
    "MITSCHREIBER_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)

WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9_]+", re.UNICODE)
STOPWORDS = {
    "the",
    "and",
    "or",
    "a",
    "an",
    "of",
    "for",
    "to",
    "in",
    "on",
    "mit",
    "und",
    "oder",
    "der",
    "die",
    "das",
    "ein",
    "eine",
    "ist",
}


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(DEFAULT_MODEL)


def _keyphrases(text: str, top_k: int = 5) -> List[str]:
    counts: Dict[str, int] = {}
    for word in WORD_RE.findall(text.lower()):
        if len(word) <= 3 or word in STOPWORDS:
            continue
        counts[word] = counts.get(word, 0) + 1
    items = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [word for word, _ in items[:top_k]]


def _schema_keyphrases(phrases: List[str]) -> List[str]:
    bounded = [phrase.strip()[:96] for phrase in phrases if phrase.strip()]
    return bounded[:64] or ["context"]


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _embed(text: str) -> List[float]:
    model = _load_model()
    vector = model.encode(text, normalize_embeddings=True, convert_to_numpy=False)
    return [float(value) for value in vector]


def build_embed_event(
    text: str, session: str, app: str, window: str
) -> Tuple[Dict[str, Any], str]:
    """Build one contract-valid event and return ``(event, text_hash)``.

    ``session`` remains accepted for caller compatibility but is deliberately
    excluded from the privacy-minimal canonical event.
    """
    _ = session
    text_hash = _sha256_hex(text)
    app_value = str(app or "").strip()[:128] or "unknown"
    window_value = str(window or "").strip()[:512]
    event: Dict[str, Any] = {
        "ts": now_iso(),
        "source": "mitschreiber",
        "app": app_value,
        "keyphrases": _schema_keyphrases(_keyphrases(text, top_k=5)),
        "embedding": _embed(text),
        "hash_id": text_hash,
        "privacy": {"raw_retained": False},
        "tags": [f"model:{DEFAULT_MODEL}"[:64]],
    }
    if window_value:
        event["window"] = window_value
    return event, text_hash
