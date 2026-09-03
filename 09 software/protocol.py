"""Newline-delimited JSON protocol shared by base station and boats."""

from __future__ import annotations

import json
import socket
import threading
from typing import Any


class JsonLineConnection:
    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.file = sock.makefile("r", encoding="utf-8", newline="\n")
        self._send_lock = threading.Lock()

    def send(self, message: dict[str, Any]) -> None:
        payload = (json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
        with self._send_lock:
            self.sock.sendall(payload)

    def receive(self) -> dict[str, Any] | None:
        line = self.file.readline()
        if not line:
            return None
        data = json.loads(line)
        if not isinstance(data, dict) or "type" not in data:
            raise ValueError("Message must be a JSON object containing 'type'")
        return data

    def close(self) -> None:
        try:
            self.file.close()
        finally:
            self.sock.close()

