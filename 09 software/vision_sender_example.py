"""Example adapter that sends calibrated visual detections to the base station.

Replace the sample-data section with the output of YOLO + homography.  The UDP
wire format remains unchanged.
"""

from __future__ import annotations

import argparse
import json
import socket
import time


SAMPLE_BOATS = [
    {"id": "boat_1", "x": 0.4, "y": 0.4, "heading": 0.0, "confidence": 0.99},
    {"id": "boat_2", "x": 0.4, "y": 3.6, "heading": 0.0, "confidence": 0.99},
    {"id": "boat_3", "x": 5.6, "y": 0.4, "heading": 3.14, "confidence": 0.99},
    {"id": "boat_4", "x": 5.6, "y": 3.6, "heading": 3.14, "confidence": 0.99},
]

SAMPLE_VICTIMS = [
    {"id": f"person_{index + 1}", "x": x, "y": y, "confidence": 0.99}
    for index, (x, y) in enumerate(
        [(1.1, 0.9), (2.0, 0.7), (3.1, 1.0), (4.8, 0.8), (1.2, 2.0),
         (2.6, 2.1), (4.6, 2.0), (1.0, 3.2), (3.2, 3.3), (5.0, 3.1)]
    )
]


def send_frame(host: str, port: int, boats: list[dict], victims: list[dict]) -> None:
    frame = {"type": "VISION_FRAME", "timestamp": time.time(), "boats": boats, "victims": victims}
    payload = json.dumps(frame, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(payload, (host, port))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9100)
    parser.add_argument("--repeat", action="store_true", help="send at 10 Hz until Ctrl+C")
    args = parser.parse_args()
    while True:
        send_frame(args.host, args.port, SAMPLE_BOATS, SAMPLE_VICTIMS)
        if not args.repeat:
            break
        time.sleep(0.1)


if __name__ == "__main__":
    main()

