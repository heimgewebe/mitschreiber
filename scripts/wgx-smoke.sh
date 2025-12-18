#!/usr/bin/env bash
set -euo pipefail

echo "[wgx.smoke] mitschreiber – schneller Grundcheck"

# Ensure jq is present (required for metrics snapshot)
if ! command -v jq >/dev/null 2>&1; then
  echo "[wgx.smoke] jq fehlt – bitte installieren." >&2
  exit 1
fi

# Ensure basic POSIX tools
for cmd in date hostname; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[wgx.smoke] $cmd fehlt – bitte installieren." >&2
    exit 1
  fi
done

if command -v cargo >/dev/null 2>&1; then
  cargo build --workspace --quiet
else
  echo "[wgx.smoke] cargo nicht vorhanden – Rust-Build übersprungen."
fi

if command -v uv >/dev/null 2>&1; then
  # Build & install das Python-Extension-Modul in die uv-Umgebung,
  # damit der Import-Test wirklich das ausgelieferte Artefakt prüft.
  uv run --group dev maturin develop --quiet
  uv run python - <<'PY'
try:
    import mitschreiber  # noqa: F401
    print("mitschreiber import ok")
except Exception as e:
    print(f"mitschreiber import failed: {e}")
    exit(1)
PY
else
  echo "[wgx.smoke] uv nicht vorhanden – Python-Smoke übersprungen."
fi
