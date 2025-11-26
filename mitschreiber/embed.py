from __future__ import annotations
import hashlib
import os
import re
from functools import lru_cache
from typing import List, Tuple, Dict, Any
from .util import now_iso

# Soft-Dependency: sentence-transformers
DEFAULT_MODEL = os.getenv("MITSCHREIBER_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

WORD_RE = re.compile(r"[A-Za-zÀ-ÿ0-9_]+", re.UNICODE)
STOPWORDS = {
    "the","and","or","a","an","of","for","to","in","on",
    "mit","und","oder","der","die","das","ein","eine","ist",
}


@lru_cache(maxsize=1)
def _load_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(DEFAULT_MODEL)

def _keyphrases(text: str, top_k: int = 5) -> List[str]:
    counts = {}
    for w in WORD_RE.findall(text.lower()):
        if len(w) <= 3 or w in STOPWORDS:
            continue
        counts[w] = counts.get(w, 0) + 1
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for (w, _) in items[:top_k]]

def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _embed(text: str) -> List[float]:
    model = _load_model()
    vec = model.encode(text, normalize_embeddings=True, convert_to_numpy=False)
    return [float(x) for x in vec]

def build_embed_event(text: str, session: str, app: str, window: str) -> Tuple[Dict[str, Any], str]:
    """
    Baut ein os.context.text.embed-Event und liefert (event, text_hash).
    """
    text_hash = _sha256_hex(text)
    kp = _keyphrases(text, top_k=5)
    embedding = _embed(text)

    evt = {
        "ts": now_iso(),
        "source": "os.context.text.embed",
        "session": session,
        "app": app,
        "window": window,
        "keyphrases": kp,
        "embedding": embedding,
        "hash_id": f"sha256:{text_hash}",
        "privacy": {"raw_retained": False},
        "meta": {"model": DEFAULT_MODEL},
    }
    return evt, text_hash
