### 📄 .env.example

**Größe:** 413 B | **md5:** `3232b8b39e8a23994aadb95cbf562edb`

```plaintext
# Mitschreiber – Beispielkonfiguration
# Kopiere diese Datei zu ".env" und passe Werte an.

# Ziel für persistente Events (leitstand)
LEITSTAND_INGEST_URL=http://localhost:8080/ingest
LEITSTAND_TOKEN=
# optional mTLS (Base64, einzeilig)
LEITSTAND_MTLS_CERT=
LEITSTAND_MTLS_KEY=

# Text-Mitschnitt bewusst aktivieren (Opt-in)
MITSCHREIBER_ENABLE_TEXT=false

# Embeddings (lokal/optional extern)
OPENAI_API_KEY=
```

### 📄 .gitignore

**Größe:** 163 B | **md5:** `6ce5f83db28838f8355b7052763cef55`

```plaintext
# Python / uv
__pycache__/
.venv/
.uv/
*.pyc

# Runtime
.runtime/

# Env
.env

# Editors
.DS_Store
.idea/
.vscode/

# Fixtures generated
fixtures/**/*.generated.*
```

### 📄 Justfile

**Größe:** 665 B | **md5:** `1ded87217ca56f68ae0a697895dce654`

```plaintext
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
```

### 📄 README.md

**Größe:** 2 KB | **md5:** `9f486fe036f195ac63807891525de13c`

```markdown
# mitschreiber

![CI](https://github.com/heimgewebe/mitschreiber/actions/workflows/ci.yml/badge.svg)
![JSONL Validation](https://github.com/heimgewebe/mitschreiber/actions/workflows/validate.yml/badge.svg)

Reusable-Workflows und Schemas sind auf Commit `78674c7159fb4c623cf3d65e978e4e5d6ca699bb` gepinnt.

On-device Kontext-Schreiber des **Heimgewebe-Ökosystems**.
Erfasst aktive Anwendungen, Fenster-Titel, Tipp-Intensität und – bei explizitem Opt-in – redigierte Text-Kontexte.  
Keine Cloud, kein Rohtext, kein Tracking.

---

### Kernrollen

| Rolle | Beschreibung |
|-------|---------------|
| **Producer** | mitschreiber (Erfassung, Redaction, Embedding) |
| **Consumer** | leitstand (Ingest), semantAH (Suche/Graph), heimlern (Policy-Feedback) |
| **Contracts** | aus metarepo (gepinnt auf `78674c7159fb4c623cf3d65e978e4e5d6ca699bb`) – `os.context.*` |

---

## Features

- **Offline-First, Privacy-First**
- **App-Kontext-Signale:** aktive Anwendung, Fenster-Titel, Aktivitäts-Intensität
- **Redigierte Text-Snippets (Opt-in):** flüchtig im RAM/WAL
- **Embeddings + Keyphrases:** persistierbar, ohne Rohtext
- **PII-/Secret-Gate:** erkennt und maskiert sensible Daten
- **Leitstand-Anbindung:** JSONL-Event-Streams (`feed.jsonl`-kompatibel)

---

## Datenflüsse

```text
mitschreiber
├─ emits os.context.state          → leitstand ingest
├─ emits os.context.text.redacted  → RAM/WAL (flüchtig)
└─ emits os.context.text.embed     → leitstand ingest → semantAH
```

---

## Quickstart

```bash
# Abhängigkeiten
uv sync --frozen
cp .env.example .env

# Start
uv run python -m mitschreiber
```

oder via Just:

```bash
just dev
```

---

## Privacy-Prinzipien

1. **Keine Speicherung von Rohtext**
2. **Redaction & Dropping vor Persistenz**
3. **TTL ≤ 60 s für flüchtige Daten**
4. **Opt-in-Erfassung mit Hotkey-Pause**
5. **Auditierbarer Privacy-Status** (`privacy.raw_retained=false`)

Details siehe [`docs/privacy.md`](docs/privacy.md)

---

## Architektur & Verträge

* Technische Übersicht: [`docs/architecture.md`](docs/architecture.md)
* Contracts-Übersicht: [`docs/contracts.md`](docs/contracts.md)

---

## Entwicklung & CI

* [`docs/runbook.md`](docs/runbook.md) – Alltagsablauf
* [`docs/devcontainer.md`](docs/devcontainer.md) – Setup-Anleitung
* [`docs/ci.md`](docs/ci.md) – Validierung & Reusable-Workflows

---

## Lizenz

MIT
```

### 📄 renovate.json

**Größe:** 7 KB | **md5:** `4e60b964da571d28f65f8f295f942a9d`

```json
{
  "$schema": "https://docs.renovatebot.com/renovate-schema.json",
  "extends": [
    "config:recommended"
  ],
  "dependencyDashboard": true,
  "prConcurrentLimit": 2,
  "labels": [
    "deps",
    "contracts-pin"
  ],
  "packageRules": [
    {
      "matchManagers": ["regex"],
      "matchPackageNames": ["heimgewebe/metarepo contracts"],
      "automerge": true,
      "automergeType": "branch"
    }
  ],
  "enabledManagers": [
    "regex"
  ],
  "regexManagers": [
    {
      "description": "Pin metarepo contracts ref across workflows and docs",
      "fileMatch": [
        "^[.]github/workflows/validate[.]yml$",
        "^docs/ci[.]md$",
        "^docs/contracts[.]md$"
      ],
      "matchStrings": [
        "  CONTRACTS_REF: (?<currentDigest>[0-9a-f]{40})"
      ],
      "depNameTemplate": "heimgewebe/metarepo contracts",
      "datasourceTemplate": "github-tags",
      "lookupNameTemplate": "heimgewebe/metarepo",
      "extractVersionTemplate": "contracts-v(?<version>[0-9]+[.][0-9]+[.][0-9]+)",
      "versioningTemplate": "semver",
      "replaceStringTemplate": "  CONTRACTS_REF: {{lookupResult.sha}}"
    },
    {
      "description": "Pinned reusable JSONL validator reference",
      "fileMatch": [
        "^[.]github/workflows/validate[.]yml$",
        "^docs/ci[.]md$",
        "^docs/contracts[.]md$"
      ],
      "matchStrings": [
        "    uses: heimgewebe/metarepo/[.]github/workflows/reusable-validate-jsonl[.]yml@(?<currentDigest>[0-9a-f]{40})"
      ],
      "depNameTemplate": "heimgewebe/metarepo contracts",
      "datasourceTemplate": "github-tags",
      "lookupNameTemplate": "heimgewebe/metarepo",
      "extractVersionTemplate": "contracts-v(?<version>[0-9]+[.][0-9]+[.][0-9]+)",
      "versioningTemplate": "semver",
      "replaceStringTemplate": "    uses: heimgewebe/metarepo/.github/workflows/reusable-validate-jsonl.yml@{{lookupResult.sha}}"
    },
    {
      "description": "Pinned reusable CI workflow reference",
      "fileMatch": [
        "^[.]github/workflows/ci[.]yml$",
        "^docs/ci[.]md$"
      ],
      "matchStrings": [
        "    uses: heimgewebe/metarepo/[.]github/workflows/reusable-ci[.]yml@(?<currentDigest>[0-9a-f]{40})"
      ],
      "depNameTemplate": "heimgewebe/metarepo contracts",
      "datasourceTemplate": "github-tags",
      "lookupNameTemplate": "heimgewebe/metarepo",
      "extractVersionTemplate": "contracts-v(?<version>[0-9]+[.][0-9]+[.][0-9]+)",
      "versioningTemplate": "semver",
      "replaceStringTemplate": "    uses: heimgewebe/metarepo/.github/workflows/reusable-ci.yml@{{lookupResult.sha}}"
    },
    {
      "description": "README commit note",
      "fileMatch": [
        "^README[.]md$"
      ],
      "matchStrings": [
        "Reusable-Workflows und Schemas sind auf Commit `(?<currentDigest>[0-9a-f]{40})` gepinnt[.]"
      ],
      "depNameTemplate": "heimgewebe/metarepo contracts",
      "datasourceTemplate": "github-tags",
      "lookupNameTemplate": "heimgewebe/metarepo",
      "extractVersionTemplate": "contracts-v(?<version>[0-9]+[.][0-9]+[.][0-9]+)",
      "versioningTemplate": "semver",
      "replaceStringTemplate": "Reusable-Workflows und Schemas sind auf Commit `{{lookupResult.sha}}` gepinnt."
    },
    {
      "description": "CI documentation intro pin note",
      "fileMatch": [
        "^docs/ci[.]md$"
      ],
      "matchStrings": [
        "Dieses Repo nutzt die Reusable-Workflows aus dem [*][*]metarepo[*][*] [(]gepinnt auf Commit `(?<currentDigest>[0-9a-f]{40})`[)]."
      ],
      "depNameTemplate": "heimgewebe/metarepo contracts",
      "datasourceTemplate": "github-tags",
      "lookupNameTemplate": "heimgewebe/metarepo",
      "extractVersionTemplate": "contracts-v(?<version>[0-9]+[.][0-9]+[.][0-9]+)",
      "versioningTemplate": "semver",
      "replaceStringTemplate": "Dieses Repo nutzt die Reusable-Workflows aus dem **metarepo** (gepinnt auf Commit `{{lookupResult.sha}}`)."
    },
    {
      "description": "Contracts documentation intro pin note",
      "fileMatch": [
        "^docs/contracts[.]md$"
      ],
      "matchStrings": [
        "Die Schemas liegen zentral im [*][*]metarepo[*][*] [(]gepinnt auf Commit `(?<currentDigest>[0-9a-f]{40})`[)]:"
      ],
      "depNameTemplate": "heimgewebe/metarepo contracts",
      "datasourceTemplate": "github-tags",
      "lookupNameTemplate": "heimgewebe/metarepo",
      "extractVersionTemplate": "contracts-v(?<version>[0-9]+[.][0-9]+[.][0-9]+)",
      "versioningTemplate": "semver",
      "replaceStringTemplate": "Die Schemas liegen zentral im **metarepo** (gepinnt auf Commit `{{lookupResult.sha}}`):"
    },
    {
      "description": "Contracts table (state schema)",
      "fileMatch": [
        "^docs/contracts[.]md$"
      ],
      "matchStrings": [
        "https://github[.]com/heimgewebe/metarepo/blob/(?<currentDigest>[0-9a-f]{40})/contracts/os[.]context[.]state[.]schema[.]json"
      ],
      "depNameTemplate": "heimgewebe/metarepo contracts",
      "datasourceTemplate": "github-tags",
      "lookupNameTemplate": "heimgewebe/metarepo",
      "extractVersionTemplate": "contracts-v(?<version>[0-9]+[.][0-9]+[.][0-9]+)",
      "versioningTemplate": "semver",
      "replaceStringTemplate": "https://github.com/heimgewebe/metarepo/blob/{{lookupResult.sha}}/contracts/os.context.state.schema.json"
    },
    {
      "description": "Contracts table (embed schema)",
      "fileMatch": [
        "^docs/contracts[.]md$"
      ],
      "matchStrings": [
        "https://github[.]com/heimgewebe/metarepo/blob/(?<currentDigest>[0-9a-f]{40})/contracts/os[.]context[.]text[.]embed[.]schema[.]json"
      ],
      "depNameTemplate": "heimgewebe/metarepo contracts",
      "datasourceTemplate": "github-tags",
      "lookupNameTemplate": "heimgewebe/metarepo",
      "extractVersionTemplate": "contracts-v(?<version>[0-9]+[.][0-9]+[.][0-9]+)",
      "versioningTemplate": "semver",
      "replaceStringTemplate": "https://github.com/heimgewebe/metarepo/blob/{{lookupResult.sha}}/contracts/os.context.text.embed.schema.json"
    },
    {
      "description": "Contracts table (redacted schema)",
      "fileMatch": [
        "^docs/contracts[.]md$"
      ],
      "matchStrings": [
        "https://github[.]com/heimgewebe/metarepo/blob/(?<currentDigest>[0-9a-f]{40})/contracts/os[.]context[.]text[.]redacted[.]schema[.]json"
      ],
      "depNameTemplate": "heimgewebe/metarepo contracts",
      "datasourceTemplate": "github-tags",
      "lookupNameTemplate": "heimgewebe/metarepo",
        "extractVersionTemplate": "contracts-v(?<version>[0-9]+[.][0-9]+[.][0-9]+)",
      "versioningTemplate": "semver",
      "replaceStringTemplate": "https://github.com/heimgewebe/metarepo/blob/{{lookupResult.sha}}/contracts/os.context.text.redacted.schema.json"
    }
  ]
}
```

