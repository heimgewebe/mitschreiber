### 📄 contracts/os.context.text.embed.schema.json

**Größe:** 2 KB | **md5:** `ef1055b39b46e8dac4d85d5811c7efb9`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.heimgewebe.org/os.context.text.embed.schema.json",
  "title": "OS Context Text Embed Event",
  "description": "Contract für persistierbare OS-Kontext-Events ohne Rohtext (JSONL: 1 Objekt pro Zeile).",
  "type": "object",
  "additionalProperties": false,
  "properties": {
    "ts": {
      "type": "string",
      "format": "date-time",
      "description": "Zeitstempel des Events im ISO-8601-Format."
    },
    "source": {
      "type": "string",
      "const": "os.context.text.embed",
      "description": "Event-Type Identifier."
    },
    "session": {
      "type": "string",
      "minLength": 1,
      "description": "Session- oder Conversation-Identifier des mitschreiber-Dienstes."
    },
    "app": {
      "type": "string",
      "pattern": "^[a-z0-9._-]{1,128}$",
      "description": "Name der aktiven Anwendung (lowercase, Ziffern, Punkt, Unterstrich, Bindestrich)."
    },
    "window": {
      "type": "string",
      "minLength": 1,
      "description": "Fenster- oder Dokumenttitel des Events."
    },
    "keyphrases": {
      "type": "array",
      "items": {
        "type": "string",
        "minLength": 1
      },
      "description": "Schlüsselbegriffe, extrahiert aus dem redigierten Kontext."
    },
    "embedding": {
      "type": "array",
      "items": {
        "type": "number"
      },
      "minItems": 1,
      "description": "Embedding-Vektor als Liste von Fließkommazahlen."
    },
    "hash_id": {
      "type": "string",
      "pattern": "^sha256:[a-f0-9]{64}$",
      "description": "Deterministischer SHA-256-Hash über die Snippet-Basisdaten."
    },
    "privacy": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "raw_retained": {
          "type": "boolean",
          "const": false,
          "description": "Flag, ob Rohtext gespeichert wurde (immer false)."
        }
      },
      "required": ["raw_retained"],
      "description": "Privacy-Garantie für dieses Event."
    },
    "meta": {
      "type": "object",
      "description": "Optionale Metadaten (z. B. Modellbezeichner)."
    }
  },
  "required": [
    "ts",
    "source",
    "session",
    "app",
    "window",
    "keyphrases",
    "embedding",
    "hash_id",
    "privacy"
  ]
}
```

