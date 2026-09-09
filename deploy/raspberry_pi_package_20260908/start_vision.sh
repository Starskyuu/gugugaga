#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$PACKAGE_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "未找到虚拟环境，请先运行 ./install_pi.sh"
  exit 1
fi

ARGS=(
  "$PACKAGE_DIR/vision/6.py"
  --no-display
  --host 0.0.0.0
  --port 8080
)

if [[ -n "${ESP32_URL:-}" ]]; then
  ARGS+=(--esp32-url "$ESP32_URL")
fi

exec "$PYTHON_BIN" "${ARGS[@]}"
