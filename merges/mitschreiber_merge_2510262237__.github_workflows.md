### 📄 .github/workflows/ci.yml

**Größe:** 440 B | **md5:** `f25f21901603a9b90af6e52e7ad71339`

```yaml
name: CI
on:
  push:
    branches: [ main ]
  pull_request:
permissions:
  contents: read
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  ci:
    # Keep the pinned SHA in sync with documentation and CONTRACTS_REF in validate.yml.
    uses: heimgewebe/metarepo/.github/workflows/reusable-ci.yml@78674c7159fb4c623cf3d65e978e4e5d6ca699bb
    with:
      run_lint: true
      run_tests: false
```

### 📄 .github/workflows/validate.yml

**Größe:** 2 KB | **md5:** `b73fff258353c0ccb6022cfa44154828`

```yaml
name: Validate JSONL
on:
  push:
    branches: [ main ]
  pull_request:
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

env:
  CONTRACTS_REF: 78674c7159fb4c623cf3d65e978e4e5d6ca699bb

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

  validate-state:
    needs: contract-sanity
    timeout-minutes: 10
    # Keep the pinned SHA in sync with CONTRACTS_REF above.
    uses: heimgewebe/metarepo/.github/workflows/reusable-validate-jsonl.yml@78674c7159fb4c623cf3d65e978e4e5d6ca699bb
    with:
      jsonl_paths_list: |
        fixtures/mitschreiber/*.jsonl
      schema_url: https://raw.githubusercontent.com/heimgewebe/metarepo/${{ env.CONTRACTS_REF }}/contracts/os.context.state.schema.json

  # Beispiel für weitere Streams (später aktivieren):
  # validate-embed:
  #   # Keep the pinned SHA in sync with CONTRACTS_REF above.
  #   uses: heimgewebe/metarepo/.github/workflows/reusable-validate-jsonl.yml@78674c7159fb4c623cf3d65e978e4e5d6ca699bb
  #   with:
  #     jsonl_paths_list: fixtures/mitschreiber/embed*.jsonl
  #     schema_url: https://raw.githubusercontent.com/heimgewebe/metarepo/${{ env.CONTRACTS_REF }}/contracts/os.context.text.embed.schema.json
```

