# Contracts: OS Context (mitschreiber → leitstand/semantAH)

Dieses Dokument beschreibt die auf Datenschutz ausgelegten Contracts für kontextbezogene OS-Signale des mitschreiber-Dienstes.

- `os.context.text.embed` – persistierbare Embeddings mit Keyphrases
- `os.context.text.redacted` – flüchtige redigierte Snippets
- `os.context.state` – Metadaten zu aktiven Anwendungen

Alle Events enthalten ein `privacy`-Objekt mit `raw_retained: false`.
