set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

dev:
    uv run python -m mitschreiber

emit:fixtures:
    @mkdir -p fixtures/mitschreiber
    @echo '{"ts":"2025-01-01T12:00:00Z","source":"os.context.state","session":"demo","app":"vscode","window":"README.md – mitschreiber","privacy":{"raw_retained":false}}' > fixtures/mitschreiber/state.demo.jsonl
    @echo 'OK: fixtures/mitschreiber/* angelegt'

validate:fixtures:
    @echo "→ Prüfe fixtures via reusable-validate-jsonl (GitHub CI). Lokal kannst du ajv-cli nutzen:"
    @echo "  ajv validate --spec=draft2020 -s contracts/os.context.text.embed.schema.json -d fixtures/mitschreiber/*.jsonl || true"
