#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[*] Creating Python virtual environment if needed..."
python3 -m venv "$ROOT_DIR/.venv" || true

echo "[*] Installing Python package in editable mode..."
"$ROOT_DIR/.venv/bin/pip" install --upgrade pip
"$ROOT_DIR/.venv/bin/pip" install -e "$ROOT_DIR[dev]"

echo "[*] Starting host bridge setup..."
"$ROOT_DIR/scripts/setup-host.sh" || true

echo "[*] Installation complete."