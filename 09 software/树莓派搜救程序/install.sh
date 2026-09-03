#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_USER="${SUDO_USER:-$(id -un)}"

sudo install -d -m 0755 /opt/rescue-planner /etc/rescue-planner
sudo install -m 0644 "$SCRIPT_DIR/pi_rescue_service.py" /opt/rescue-planner/
sudo install -m 0644 "$SCRIPT_DIR/rescue_core.py" /opt/rescue-planner/
sudo install -m 0644 "$SCRIPT_DIR/route_planners.py" /opt/rescue-planner/
sudo install -m 0644 "$SCRIPT_DIR/vision_input_example.py" /opt/rescue-planner/
sudo install -m 0644 "$SCRIPT_DIR/route_receiver_example.py" /opt/rescue-planner/

if [[ ! -f /etc/rescue-planner/config.json ]]; then
  sudo install -m 0644 "$SCRIPT_DIR/config.json" /etc/rescue-planner/config.json
fi

sed "s/__RUN_USER__/$RUN_USER/g" "$SCRIPT_DIR/rescue-planner.service" | sudo tee /etc/systemd/system/rescue-planner.service >/dev/null
sudo install -d -o "$RUN_USER" -g "$RUN_USER" -m 0755 /opt/rescue-planner/runtime
sudo systemctl daemon-reload
sudo systemctl enable rescue-planner.service

echo "Installed. Edit /etc/rescue-planner/config.json, then run:"
echo "  sudo systemctl start rescue-planner"
echo "  journalctl -u rescue-planner -f"
