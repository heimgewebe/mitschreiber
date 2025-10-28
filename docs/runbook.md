# Runbook – Betrieb & Entwicklung

## Lokale Entwicklung

```bash
uv sync
cp .env.example .env
just dev

```

**Hotkeys**

| Tastenkombination | Aktion                            |
| ----------------- | --------------------------------- |
| Ctrl + Alt + M    | Mitschreiber pausieren/fortsetzen |
| Ctrl + Alt + L    | Letzten Status loggen             |

---

## Fixtures erzeugen

```bash
just emit:fixtures
```

legt ein Beispiel-Embedding-Event unter `fixtures/mitschreiber/embed.demo.jsonl` an.

---

## Validierung

```bash
just validate:fixtures
```

nutzt den metarepo-Workflow `.github/workflows/reusable-validate-jsonl.yml`.

---

## Logs & Troubleshooting

* Laufzeitlogs: `.runtime/logs/*.log`
* WAL-Einträge: `.runtime/wal/`
* Fehlerdiagnose: `just doctor` (geplant)

---

## Deployment (autonom)

1. systemd-Service anlegen:

   ```
   [Unit]
   Description=Mitschreiber Sensor
   After=network.target

   [Service]
   ExecStart=/usr/bin/env uv run python -m mitschreiber
   WorkingDirectory=/home/user/mitschreiber
   Restart=on-failure
   ```

2. Aktivieren:

```bash
sudo systemctl enable --now mitschreiber
```
