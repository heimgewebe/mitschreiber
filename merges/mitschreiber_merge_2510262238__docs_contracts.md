### 📄 docs/contracts/index.md

**Größe:** 415 B | **md5:** `f3195ee8ee8fdbe69af2de3a2769e6ac`

```markdown
# Contracts Index

| Schema | Beschreibung | Producer | Consumer |
| ------ | ------------- | -------- | -------- |
| [`contracts/os.context.text.embed.schema.json`](../../contracts/os.context.text.embed.schema.json) | Kontext-Embeddings ohne Rohtext | `mitschreiber` | `leitstand`, `semantAH` |

Weitere Dokumentation:

- [OS Context Contracts](./os-context.md) – Details zu mitschreiber → leitstand/semantAH.
```

### 📄 docs/contracts/os-context.md

**Größe:** 456 B | **md5:** `bf701e006e6e150286efa4b5787e6085`

```markdown
# Contracts: OS Context (mitschreiber → leitstand/semantAH)

Dieses Dokument beschreibt die auf Datenschutz ausgelegten Contracts für kontextbezogene OS-Signale des mitschreiber-Dienstes.

- `os.context.text.embed` – persistierbare Embeddings mit Keyphrases
- `os.context.text.redacted` – flüchtige redigierte Snippets
- `os.context.state` – Metadaten zu aktiven Anwendungen

Alle Events enthalten ein `privacy`-Objekt mit `raw_retained: false`.
```

