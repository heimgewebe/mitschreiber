# Contracts

Die Schemas liegen zentral im **metarepo** (gepinnt auf Commit `f3524f9b040be957cfead5b80f7a683d0ea6df72`):

| Event | Schema-Datei | Persistenz |
|--------|---------------|------------|
| `os.context.state` | [metarepo/contracts/os.context.state.schema.json](https://github.com/heimgewebe/metarepo/blob/f3524f9b040be957cfead5b80f7a683d0ea6df72/contracts/os.context.state.schema.json) | dauerhaft |
| `os.context.text.redacted` | [metarepo/contracts/os.context.text.redacted.schema.json](https://github.com/heimgewebe/metarepo/blob/f3524f9b040be957cfead5b80f7a683d0ea6df72/contracts/os.context.text.redacted.schema.json) | flüchtig |
| `os.context.text.embed` | [metarepo/contracts/os.context.text.embed.schema.json](https://github.com/heimgewebe/metarepo/blob/f3524f9b040be957cfead5b80f7a683d0ea6df72/contracts/os.context.text.embed.schema.json) | dauerhaft |

Validierung per Reusable-Workflow:

```yaml
env:
  CONTRACTS_REF: f3524f9b040be957cfead5b80f7a683d0ea6df72

jobs:
  contract-sanity:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    permissions:
      contents: read
    strategy:
      fail-fast: false
      matrix:
        include:
          - stream: state
            schema_file: os.context.state.schema.json
          - stream: embed
            schema_file: os.context.text.embed.schema.json
          - stream: redacted
            schema_file: os.context.text.redacted.schema.json
    steps:
      - name: Check schema availability (${{ matrix.stream }})
        env:
          SCHEMA_URL: https://raw.githubusercontent.com/heimgewebe/metarepo/${{ env.CONTRACTS_REF }}/contracts/${{ matrix.schema_file }}
        run: curl -fsSL --retry 3 --retry-delay 2 --max-time 10 "$SCHEMA_URL" >/dev/null

  validate:
    needs: contract-sanity
    timeout-minutes: 10
    # Keep the pinned SHA in sync with CONTRACTS_REF above.
    uses: heimgewebe/metarepo/.github/workflows/reusable-validate-jsonl.yml@f3524f9b040be957cfead5b80f7a683d0ea6df72
    with:
      jsonl_paths_list: |
        fixtures/mitschreiber/*.jsonl
      schema_url: https://raw.githubusercontent.com/heimgewebe/metarepo/${{ env.CONTRACTS_REF }}/contracts/os.context.text.embed.schema.json
```
