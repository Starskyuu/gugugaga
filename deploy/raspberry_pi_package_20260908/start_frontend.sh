#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_DIR/frontend"

if [[ ! -d node_modules ]]; then
  echo "未找到前端依赖，请先在frontend目录执行 npm ci"
  exit 1
fi

exec npm run dev -- --host 0.0.0.0
