#!/bin/bash
set -e
cd "$(dirname "$0")"

# 只启动视觉和 Python 总控，不需要 Node.js/npm。
python3 ../raspberry_pi/vision/666.py \
  --publish-state --state-host 127.0.0.1 --state-port 9101 \
  --jpeg-path /tmp/rescue_latest.jpg --headless &
VISION_PID=$!
trap 'kill "$VISION_PID" 2>/dev/null || true' EXIT
python3 main.py run
