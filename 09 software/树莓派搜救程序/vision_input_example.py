"""Send one sample coordinate frame to the Raspberry Pi planner."""

from __future__ import annotations

import argparse
import json
import socket
import time


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9200)
    args = parser.parse_args()
    frame = {
        "type": "VISION_FRAME",
        "timestamp": time.time(),
        "boats": [
            {"id": "boat_1", "x": 22.5, "y": 27.0},
            {"id": "boat_2", "x": 22.5, "y": 33.0},
            {"id": "boat_3", "x": 37.5, "y": 27.0},
            {"id": "boat_4", "x": 37.5, "y": 33.0}
        ],
        "people": [
            {"id": "person_1", "x": 7.0, "y": 8.0},
            {"id": "person_2", "x": 13.0, "y": 48.0},
            {"id": "person_3", "x": 51.0, "y": 9.0},
            {"id": "person_4", "x": 52.0, "y": 49.0},
            {"id": "person_5", "x": 29.0, "y": 54.0}
        ]
    }
    payload = json.dumps(frame, ensure_ascii=False).encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        sender.sendto(payload, (args.host, args.port))
    print(f"Sent {len(frame['people'])} targets to {args.host}:{args.port}")


if __name__ == "__main__":
    main()

