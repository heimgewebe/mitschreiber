# Privacy & Redaction

## Grundsätze

1. **Minimierung:** Es werden nur Metadaten, Keyphrases und Embeddings gespeichert.  
2. **Trennung:** Rohtext bleibt maximal im RAM.  
3. **Transparenz:** Jede Nachricht enthält ein `privacy`-Objekt.  
4. **Audit:** `privacy.raw_retained` ist immer `false`.

---

## Redaction-Pipeline

```text

Keyboard Stream
↓
Tokenizer
↓
PII-Detector (Regex + NER)
↓
Redactor → snippet.redacted (RAM/WAL, TTL ≤ 60 s)
↓
Embedder → embedding + keyphrases
↓
Leitstand-Sink (JSONL append)

```

---

## PII/Secret-Erkennung

- Regex-Patterns (IBAN, Mail, JWT, API-Keys)
- Named-Entity-Model (PERSON, ORG, LOCATION)
- Confidence-Threshold (`PII_MIN_CONFIDENCE`)
- Aktion (`PII_ACTION`):  
  `drop_and_shred` | `mask` | `allow`

---

## Opt-In-Modus

- Standard: `MITSCHREIBER_ENABLE_TEXT=false`
- Aktiviert nur durch bewusste Änderung in `.env`
- Hotkey `Ctrl + Alt + M` pausiert Erfassung sofort
