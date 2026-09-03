"""Start the base station, four dry-run boats and sample visual sender."""

from __future__ import annotations

import argparse
import subprocess
import socket
import sys
import time
from pathlib import Path


def find_free_port(socket_type: int, excluded: set[int]) -> int:
    """Ask Windows/Linux for an unused loopback port."""
    while True:
        with socket.socket(socket.AF_INET, socket_type) as probe:
            probe.bind(("127.0.0.1", 0))
            port = int(probe.getsockname()[1])
        if port not in excluded:
            return port


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the moving four-boat browser demo")
    parser.add_argument("--no-browser", action="store_true", help="do not open the browser automatically")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    selected: set[int] = set()
    boat_port = find_free_port(socket.SOCK_STREAM, selected)
    selected.add(boat_port)
    vision_port = find_free_port(socket.SOCK_DGRAM, selected)
    selected.add(vision_port)
    dashboard_port = find_free_port(socket.SOCK_STREAM, selected)
    base_command = [
            sys.executable, "base_station.py", "--config", "configs/base_station.json",
            "--visualize", "--demo",
            "--boat-port", str(boat_port),
            "--vision-port", str(vision_port),
            "--visualizer-port", str(dashboard_port),
        ]
    if not args.no_browser:
        base_command.append("--open-browser")
    commands = [base_command]
    processes: list[subprocess.Popen] = []
    try:
        for command in commands:
            processes.append(subprocess.Popen(command, cwd=root))
            time.sleep(0.25)
        print(
            f"\nDynamic demo is running at http://127.0.0.1:{dashboard_port}\n"
            f"Ports: dashboard={dashboard_port}, boats={boat_port}, vision={vision_port}\n"
            "Press Ctrl+C to stop.\n"
        )
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    main()
