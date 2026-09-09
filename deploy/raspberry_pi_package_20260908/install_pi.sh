#!/usr/bin/env bash
set -euo pipefail

PACKAGE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PACKAGE_DIR"

sudo apt update
sudo apt install -y python3-venv python3-pip libgl1 libglib2.0-0

python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

echo "Python环境安装完成。"
echo "下一步运行：./start_vision.sh"
