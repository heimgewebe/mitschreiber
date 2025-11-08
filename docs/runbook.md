## Lokale Entwicklung

```bash
uv sync
cp .env.example .env
just dev
```

## Fixtures erzeugen

```bash
just fixtures
```

legt ein Beispiel-Embedding-Event unter `fixtures/mitschreiber/embed.demo.jsonl` an.

---

## Validierung

```bash
just validate
```

nutzt den metarepo-Workflow `.github/workflows/reusable-validate-jsonl.yml`.

---

## Status, Stop & Hotkeys (Pop!_OS)

### Status & Stop

```bash
# Status der aktiven Session anzeigen
uv run mitschreiber status

# Aktive Session sauber beenden (SIGTERM)
uv run mitschreiber stop
```

Während der Aufnahme existiert eine Statusdatei:

- `~/.local/share/mitschreiber/active.json`
- Pro Session ein Audit: `~/.local/share/mitschreiber/sessions/<UUID>/audit.json`

### Pop!_OS (GNOME) – Tastaturkürzel für Start/Stop

1. **Einstellungen → Tastatur → Tastaturkürzel → Benutzerdefiniert → “+”**
2. **Start-Kürzel**
   - Name: `mitschreiber start (embed+clipboard)`
   - Befehl: `bash -lc 'uv run mitschreiber start --embed --clipboard --poll-interval 500'`
   - Shortcut z. B. `Ctrl+Alt+M`
3. **Stop-Kürzel**
   - Name: `mitschreiber stop`
   - Befehl: `bash -lc 'uv run mitschreiber stop'`
   - Shortcut z. B. `Ctrl+Alt+L`

> Tipp: Falls `uv` nicht in PATH der GNOME-Shell verfügbar ist, den vollen Pfad verwenden (`/home/<user>/.local/bin/uv`).

---

## Logs & Troubleshooting

* Laufzeitlogs: `.runtime/logs/*.log`
* WAL-Einträge: `.runtime/wal/`
* Fehlerdiagnose: `just doctor` (geplant)
