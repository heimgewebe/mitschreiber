# Runbook

## Lokale Entwicklung

```bash
uv sync
cp .env.example .env
just dev
```

## Hotkeys

| Tastenkombination | Aktion |
|---|---|
| `Ctrl` + `Alt` + `M` | Mitschreiber pausieren/fortsetzen |
| `Ctrl` + `Alt` + `L` | Letzten Status loggen |


⸻

## CLI: Start / Status / Stop (Opt-in)

Der Mitschreiber lässt sich sichtbar starten und stoppen. Standard-WAL-Pfad:
`~/.local/share/mitschreiber/wal/`

### Start (blocking im Vordergrund)

```bash
# Embeddings optional einschalten (--embed) und Clipboard opt-in:
uv run mitschreiber start --clipboard --poll-interval 500 --embed
```

Anzeige beim Start:
- Session-UUID
- Flags (clipboard/screenshots/embed)
- WAL-Pfad

Die Session läuft im Vordergrund bis `Ctrl` + `C` oder `mitschreiber stop`.

### Status

```bash
uv run mitschreiber status
```

Zeigt aktive Session (PID, WAL-Pfad, Flags). Datenbasis ist `~/.local/share/mitschreiber/sessions/active.json`.

### Stop (aus zweitem Terminal)

```bash
uv run mitschreiber stop
```

Sendet `SIGTERM` (und bei Bedarf `SIGKILL`) an die aktive Session und räumt `active.json` auf.

### ENV-Schalter

Statt `--embed` kann per ENV aktiviert werden:

```bash
export MITSCHREIBER_EMBED=1
uv run mitschreiber start --clipboard
```

---


## Fixtures erzeugen

```bash
just emit:fixtures
```

legt ein Beispiel-Embedding-Event unter `fixtures/mitschreiber/embed.demo.jsonl` an.

⸻

## Validierung

```bash
just validate:fixtures
```

nutzt den metarepo-Workflow `.github/workflows/reusable-validate-jsonl.yml`.

⸻

## Hotkey (Pop!_OS / GNOME)

Optional kann über `Systemeinstellungen` → `Tastatur` → `Tastenkombinationen` ein Hotkey
für Start/Stop angelegt werden:

| Aktion     | Befehl                                                    |
|------------|-----------------------------------------------------------|
| Start      | `bash -lc 'uv run mitschreiber start --clipboard --embed'`  |
| Stop       | `bash -lc 'uv run mitschreiber stop'`                     |
| Status     | `bash -lc 'uv run mitschreiber status'`                   |

Tipp: Für den Start-Hotkey ein separates Terminalprofil nutzen, damit die Session sichtbar ist.

---


## Logs & Troubleshooting
• Laufzeitlogs: `.runtime/logs/*.log`
• WAL-Einträge: `.runtime/wal/`
• Fehlerdiagnose: `just doctor` (geplant)

•

## Typische Stolpersteine

1. **`ModuleNotFoundError` (Sampler)**
   • Lösung: `uv sync` neu ausführen. Sicherstellen, dass das `pyo3`-Modul (Rust) korrekt gebaut ist (z. B. via `maturin develop --release` falls separat).
2. **Keine Events im WAL**
   • Prüfen: `uv run mitschreiber status` → `wal:`-Pfad öffnen und `tail -f` darauf.
   • Fenstertitel/Clipboard ändern; Poll-Intervall ggf. auf 250 ms senken.
3. **Wayland/X11**
   • Erste Version priorisiert X11. Auf Wayland ggf. reduzierte Signale; Feature-Flag im Sampler beachten.
4. **Embeddings langsam**
   • Kleines lokales Modell nutzen; Intervall über `embed_min_interval_s` (Code-Config) erhöhen.

⸻

## Deployment (autonom)
1. `systemd`-Service anlegen:
