# mitschreiber

![CI](https://github.com/heimgewebe/mitschreiber/actions/workflows/ci.yml/badge.svg)
![JSONL Validation](https://github.com/heimgewebe/mitschreiber/actions/workflows/validate.yml/badge.svg)
[![Status: Prototype](https://img.shields.io/badge/status-prototype-yellow.svg)](./docs/runbook.md)
[![Platform: Pop!_OS](https://img.shields.io/badge/platform-Pop!__OS%20%2F%20Linux-blue)](./docs/runbook.md)

Reusable-Workflows und Schemas sind auf Commit `78674c7159fb4c623cf3d65e978e4e5d6ca699bb` gepinnt.

On-device Kontext-Schreiber des **Heimgewebe-Ökosystems**.
Erfasst aktive Anwendungen, Fenster-Titel, Tipp-Intensität und – bei explizitem Opt-in – redigierte Text-Kontexte.  
Keine Cloud, kein Rohtext, kein Tracking.

---

### Kernrollen

| Rolle | Beschreibung |
|-------|---------------|
| **Producer** | mitschreiber (Erfassung, Redaction, Embedding) |
| **Consumer** | chronik (Ingest), semantAH (Suche/Graph), heimlern (Policy-Feedback) |
| **Contracts** | aus metarepo (gepinnt auf `78674c7159fb4c623cf3d65e978e4e5d6ca699bb`) – `os.context.*` |

---

## Features

- **Offline-First, Privacy-First**
- **App-Kontext-Signale:** aktive Anwendung, Fenster-Titel, Aktivitäts-Intensität
- **Redigierte Text-Snippets (Opt-in):** flüchtig im RAM/WAL
- **Embeddings + Keyphrases:** persistierbar, ohne Rohtext
- **PII-/Secret-Gate:** erkennt und maskiert sensible Daten
- **Chronik-Anbindung:** JSONL-Event-Streams (`feed.jsonl`-kompatibel)

---

## Datenflüsse

```text
mitschreiber
├─ emits os.context.state          → chronik ingest
├─ emits os.context.text.redacted  → RAM/WAL (flüchtig)
└─ emits os.context.text.embed     → chronik ingest → semantAH
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

(Opt-in/RAW möglich; siehe [`docs/privacy.md`](docs/privacy.md) und Runbook → CLI Start/Stop)
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

* [`docs/runbook.md`](docs/runbook.md) – Alltagsablauf (CLI Start/Stop/Status, Hotkey, Pfade, Fixtures)
* [`docs/devcontainer.md`](docs/devcontainer.md) – Setup-Anleitung
* [`docs/ci.md`](docs/ci.md) – Validierung & Reusable-Workflows
* Beispiel-Event: `fixtures/mitschreiber/embed.demo.jsonl`

---

## Lizenz

MIT

## Organismus-Kontext

Dieses Repository ist Teil des **Heimgewebe-Organismus**.

Die übergeordnete Architektur, Achsen, Rollen und Contracts sind zentral beschrieben im
👉 [`metarepo/docs/heimgewebe-organismus.md`](https://github.com/heimgewebe/metarepo/blob/main/docs/heimgewebe-organismus.md)
sowie im Zielbild
👉 [`metarepo/docs/heimgewebe-zielbild.md`](https://github.com/heimgewebe/metarepo/blob/main/docs/heimgewebe-zielbild.md).

Alle Rollen-Definitionen, Datenflüsse und Contract-Zuordnungen dieses Repos
sind dort verankert.
