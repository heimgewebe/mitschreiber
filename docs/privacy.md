# Privacy & Opt-in-RAW-Erfassung

Dieser Leitfaden beschreibt, wie der **Mitschreiber** mit Inhalten umgeht – von der datensparsamen Standard-Pipeline bis hin zur **bewussten Opt-in-RAW-Erfassung**, bei der du gezielt Privacy gegen Funktionalität eintauschst.

> Kurzfassung: Standard ist *Redaction-First*. Auf Wunsch kannst du **RAW** aktivieren (Opt-in). Dann werden Inhalte nahezu unverändert erfasst, um Erkennen/Lernen/Feedback maximal zu ermöglichen.

---

## Betriebsmodi

| Modus | Zweck | Erfasste Inhalte | Default? |
|------|------|-------------------|---------|
| **Redaction-First** | Minimaler Datenabdruck, robuste Standards | Kontextsignale (App, Fenster-Titel), ggf. *redigierte* Snippets, Embeddings | ✅ |
| **RAW (Opt-in)** | Maximale Funktionalität/Analyse | Kontextsignale **plus** Clipboard/Inhalt (nahezu unverändert) | ❌ (manuell aktivieren) |

**Wichtig:** RAW ist **dein** explizites Opt-in. Ohne Opt-in bleibt Redaction-First aktiv.

---

## Aktivierung von RAW (Opt-in)

RAW lässt sich per CLI-Flag oder Umgebungsvariable einschalten.

### CLI

```bash
# Start im Vordergrund, Clipboard + RAW enabled, Embeddings an:
uv run mitschreiber start --clipboard --embed --raw
```

### Umgebungsvariable

```bash
export MITSCHREIBER_RAW=1
export MITSCHREIBER_EMBED=1
uv run mitschreiber start --clipboard
```

**Hinweis:** Falls `--raw` noch nicht im CLI verdrahtet ist, wird das in *Milestone 4 (UX)* finalisiert. Die ENV-Schalter können bereits für frühe Tests genutzt werden, sobald die Pipeline-Flags im Orchestrator anliegen.

---

## Was wird in RAW zusätzlich erfasst?

* **Clipboard-Inhalt** (wenn `--clipboard` gesetzt): Volltext, einschließlich formatierter Text-Varianten, soweit die Plattform-API das liefert.
* **Fenster-Kontext**: App-Name, Fenster-Titel, ggf. aktive Datei (z. B. Editor/IDE, soweit erkennbar).
* **Optional (später):** Screenshot-Surrogate/Thumbnails, Editor-Puffer via Plugin (nur mit zusätzlichem Opt-in).

> Kein Keylogging, keine Low-Level-Systemhooks. Fokus ist „was du **bewusst** in Fenstern bearbeitest/teilst“, nicht jede Taste.

---

## Speicherpfade & Lebensdauer

* **WAL (Write-Ahead-Log):**
  `~/.local/share/mitschreiber/wal/session-<UUID>.jsonl`
* **Audit/Status:**
  `~/.local/share/mitschreiber/sessions/<UUID>/audit.json` und `.../active.json`
* **TTL/Rotation (Empfehlung):**
  *Redaction-First:* kurze TTL (≤ 60 s) für flüchtige Snippets.
  *RAW:* kein automatischer Drop, stattdessen **explizites** Retention-Budget (z. B. max. 7 Tage oder 1 GB), konfigurierbar.

---

## Event-Formate (Beispiele)

### `os.context.state` (Kontextsignal)

```json
{
  "ts": "2025-01-01T12:00:00Z",
  "source": "os.context.state",
  "session": "uuid",
  "app": "vscode",
  "window": "README.md — mitschreiber",
  "privacy": { "raw_retained": true }
}
```

### `os.context.text.embed` (Embeddings)

```json
{
  "ts": "2025-01-01T12:00:05Z",
  "source": "os.context.text.embed",
  "session": "uuid",
  "app": "vscode",
  "window": "README.md — mitschreiber",
  "keyphrases": ["mitschreiber", "privacy", "context"],
  "embedding": [0.012, -0.034, 0.056, ...],
  "hash_id": "sha256:...",
  "privacy": { "raw_retained": true },
  "meta": { "model": "demo-embedding" }
}
```

> `privacy.raw_retained: true` kennzeichnet, dass die zugrunde liegenden Inhalte in dieser Session **ohne Redaction** gespeichert werden **dürfen** (Opt-in). In Redaction-First wäre es `false`.

---

## Sichtbarkeit & Kontrolle

* **Expliziter Start/Stop:**
  `uv run mitschreiber start …` / `uv run mitschreiber stop`
* **Status im Klartext:**
  `uv run mitschreiber status` zeigt Flags (`raw`, `clipboard`, `embed`) + WAL-Pfad.
* **Kill-Switch:**
  `stop` beendet die Session und räumt `active.json` auf. Zur Not: `pkill -f mitschreiber`.
* **Hotkeys (Pop!_OS / GNOME):**
  siehe Runbook – Start/Stop/Status als Shortcuts hinterlegen.

---

## Sicherheit & Risiken (bewusstes Opt-in)

* In RAW können **PII, Geheimnisse, Zugangsdaten** im Klartext landen (z. B. aus dem Clipboard).
  → Folge: Setze **Verschlüsselung auf Dateisystemebene** (z. B. LUKS), begrenze Retention (Zeit/Größe), und halte Backups bewusst getrennt.
* **Keine Cloud-Synchronisierung** im Standard. WAL bleibt lokal. Exporte sind explizit.
* **Prozess-Isolation:** Der Orchestrator läuft unter deinem Nutzerkonto, schreibt nur in `~/.local/share/mitschreiber/`.

---

## Konfiguration (Übersicht)

| Option | Typ | Wirkung |
|-------|-----|---------|
| `--raw` / `MITSCHREIBER_RAW=1` | Bool | Schaltet RAW-Modus ein (Opt-in). |
| `--clipboard` | Bool | Erfasst Clipboard-Inhalt (nur, wenn RAW sinnvoll ist). |
| `--embed` / `MITSCHREIBER_EMBED=1` | Bool | Erzeugt `os.context.text.embed`-Events. |
| `--poll-interval <ms>` | Zahl | Poll-Intervall (z. B. 250–1000 ms). |
| (später) `--retention-days` / `--retention-size-mb` | Zahl | WAL-Rotation/Limit für RAW. |

---

## Empfohlene Profile

### A) Redaction-First (Standard)

```bash
uv run mitschreiber start --poll-interval 500 --embed
```

*Ziel:* minimale Persistenz, schnelle Signal-Gewinnung.

### B) Volle Funktionalität (RAW)

```bash
uv run mitschreiber start --poll-interval 500 --embed --clipboard --raw
```

*Ziel:* maximale Lern-/Feedback-Qualität, bewusster Privacy-Trade-off.

---

## Compliance-Guardrails (leichtgewichtig)

* **Audit-Datei pro Session** mit Startzeit, Flags und Hash der CLI-Args.
* **Inline-Kennzeichnung** via `privacy.raw_retained`.
* **Explizite Doku** (dieses Dokument) als Teil des PRs.

---

## Roadmap-Hinweise

* **Milestone 4 (UX):** CLI-Flag `--raw` wird final verdrahtet (sofern noch offen), Statusausgabe zeigt „raw: on/off“.
* **Editor-Integrationen:** RAW-Puffer können *zusätzlich* opt-in an lokale Ports übergeben werden (separater PR, klarer Consent).

---

**Fazit:**
Mit RAW-Opt-in kannst du gezielt **möglichst wenig Privacy für möglichst viel Funktionalität** tauschen. Der Mitschreiber macht das sichtbar, lokal und kontrollierbar – Start/Stop im Klartext, eindeutiges Flagging in Events, keine stille Cloud-Sync.
