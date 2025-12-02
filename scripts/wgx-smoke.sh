#!/usr/bin/env bash
set -euo pipefail

echo "[wgx.smoke] mitschreiber – schneller Grundcheck"

if command -v cargo >/dev/null 2>&1; then
  cargo build --workspace --quiet
else
  echo "[wgx.smoke] cargo nicht vorhanden – Rust-Build übersprungen."
fi

if command -v uv >/dev/null 2>&1; then
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
