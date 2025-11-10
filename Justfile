set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

dev:
    uv run python -m mitschreiber

emit:fixtures:
    @mkdir -p fixtures/mitschreiber
    @cat <<'EOF' > fixtures/mitschreiber/embed.demo.jsonl
{"ts":"2025-01-01T12:00:00Z","source":"os.context.text.embed","session":"demo","app":"vscode","window":"README.md – mitschreiber","keyphrases":["mitschreiber","privacy","context"],"embedding":[0.012,-0.034,0.056,0.078,0.031,-0.045,0.022,0.007],"hash_id":"sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","privacy":{"raw_retained":false},"meta":{"model":"demo-embedding"}}
EOF
    @echo 'OK: fixtures/mitschreiber/embed.demo.jsonl angelegt'

validate:fixtures:
    @echo "→ Prüfe fixtures via reusable-validate-jsonl (GitHub CI). Lokal (ohne vendorte Schemas):"
    @echo "  ajv validate --spec=draft2020 -s contracts/os.context.text.embed.schema.json -d fixtures/mitschreiber/embed*.jsonl || true"
    @echo "  # Offline? Schema vendoren und Pfad im Befehl anpassen."
default: lint
lint:
    bash -n $(git ls-files *.sh *.bash)
    echo "lint ok"
