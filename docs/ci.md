# CI / Validierung

Dieses Repo nutzt die Reusable-Workflows aus dem **metarepo**.

## JSONL-Validierung

```yaml
name: validate
on:
  push:
    branches: [main]
  pull_request:

jobs:
  validate:
    uses: heimgewebe/metarepo/.github/workflows/reusable-validate-jsonl.yml@contracts-v1
    with:
      jsonl_paths_list: |
        fixtures/mitschreiber/*.jsonl
      schema_url: https://raw.githubusercontent.com/heimgewebe/metarepo/contracts-v1/contracts/os.context.state.schema.json
```

Analog für `os.context.text.embed` und `os.context.text.redacted`.

---

## Lint / Tests

```yaml
jobs:
  ci:
    uses: heimgewebe/metarepo/.github/workflows/reusable-ci.yml@main
    with:
      run_lint: true
      run_tests: true
```

---

## Badge (README)

```md
![JSONL Validation](https://github.com/heimgewebe/mitschreiber/actions/workflows/validate.yml/badge.svg)
```
