# mitschreiber

![CI](https://github.com/heimgewebe/mitschreiber/actions/workflows/ci.yml/badge.svg)
![JSONL Validation](https://github.com/heimgewebe/mitschreiber/actions/workflows/validate.yml/badge.svg)

On-device Kontext-Schreiber des **Heimgewebe-Ökosystems**.  
Erfasst aktive Anwendungen, Fenster-Titel, Tipp-Intensität und – bei explizitem Opt-in – redigierte Text-Kontexte.  
Keine Cloud, kein Rohtext, kein Tracking.

---

### Kernrollen

| Rolle | Beschreibung |
|-------|---------------|
| **Producer** | mitschreiber (Erfassung, Redaction, Embedding) |
| **Consumer** | leitstand (Ingest), semantAH (Suche/Graph), heimlern (Policy-Feedback) |
| **Contracts** | aus metarepo (`contracts-v1`) – `os.context.*` |

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
