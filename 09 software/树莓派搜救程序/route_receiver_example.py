"""Print route packets produced by the Raspberry Pi planner."""

from __future__ import annotations

import argparse
import json
import socket


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9300)
    args = parser.parse_args()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
        receiver.bind((args.host, args.port))
        print(f"Listening on UDP {args.host}:{args.port}")
        while True:
            payload, address = receiver.recvfrom(65507)
            packet = json.loads(payload.decode("utf-8"))
            print(f"\nFrom {address[0]}:{address[1]}")
            print(json.dumps(packet, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

