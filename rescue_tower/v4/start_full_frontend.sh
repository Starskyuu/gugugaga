#!/bin/bash
set -e
cd "$(dirname "$0")"

if ! command -v npm >/dev/null 2>&1; then
  echo "未安装 Node.js/npm，请先安装，或者直接运行 ./start.sh 使用轻量前端。"
  exit 1
fi

if [ ! -d frontend_full/node_modules ]; then
  echo "首次运行完整前端，正在安装依赖……"
  (cd frontend_full && npm ci)
fi

python3 ../raspberry_pi/vision/666.py \
  --publish-state --state-host 127.0.0.1 --state-port 9101 \
  --jpeg-path /tmp/rescue_latest.jpg --headless &
VISION_PID=$!
(cd frontend_full && npm run dev -- --host 0.0.0.0) &
UI_PID=$!
trap 'kill "$VISION_PID" "$UI_PID" 2>/dev/null || true' EXIT
python3 main.py run
