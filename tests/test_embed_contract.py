from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from mitschreiber import embed, embedding, session

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts/os.context.text.embed.schema.json").read_text(encoding="utf-8")
)


def assert_contract_shape(event: dict[str, Any]) -> None:
    properties = SCHEMA["properties"]
    assert set(event) <= set(properties)
    assert set(SCHEMA["required"]) <= set(event)
    assert isinstance(event["app"], str) and 1 <= len(event["app"]) <= 128
    if "window" in event:
        assert isinstance(event["window"], str) and len(event["window"]) <= 512
    assert 1 <= len(event["keyphrases"]) <= 64
    assert all(isinstance(item, str) and 1 <= len(item) <= 96 for item in event["keyphrases"])
    assert 8 <= len(event["embedding"]) <= 4096
    assert all(isinstance(item, (int, float)) for item in event["embedding"])
    assert re.fullmatch(properties["hash_id"]["pattern"], event["hash_id"])
    assert event["privacy"]["raw_retained"] is False
    assert set(event["privacy"]) <= set(properties["privacy"]["properties"])
    if "source" in event:
        assert len(event["source"]) <= 64
    if "tags" in event:
        assert len(event["tags"]) <= 32
        assert all(isinstance(tag, str) and len(tag) <= 64 for tag in event["tags"])
    assert "session" not in event
    assert "meta" not in event


def test_demo_fixture_matches_contract() -> None:
    path = ROOT / "fixtures/mitschreiber/embed.demo.jsonl"
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert records
    for record in records:
        assert_contract_shape(record)


def test_hash_demo_producer_matches_contract() -> None:
    record = embedding.build_embed_record(
        ts_iso="2026-08-01T00:00:00Z",
        session="must-not-leak",
        app="   ",
        window="",
        text="a",
        dim=8,
    )
    assert_contract_shape(record)
    assert record["app"] == "unknown"
    assert record["keyphrases"] == ["context"]
    assert "window" not in record


def test_model_producer_matches_contract(monkeypatch) -> None:
    monkeypatch.setattr(embed, "now_iso", lambda: "2026-08-01T00:00:00Z")
    monkeypatch.setattr(embed, "_embed", lambda _text: [0.0] * 8)
    event, text_hash = embed.build_embed_event(
        "the and", "must-not-leak", "Firefox", ""
    )
    assert_contract_shape(event)
    assert event["hash_id"] == text_hash
    assert event["keyphrases"] == ["context"]
    assert "window" not in event


def test_inline_session_producer_matches_contract(monkeypatch) -> None:
    monkeypatch.setattr(session, "now_iso", lambda: "2026-08-01T00:00:00Z")
    event = session._emit_embed(
        {"session": "must-not-leak", "app": None, "window": None}
    )
    assert event is not None
    assert_contract_shape(event)
    assert event["app"] == "unknown"
