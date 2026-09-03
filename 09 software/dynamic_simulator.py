"""Dynamic four-boat world used by the local browser demonstration.

Each simulated boat is a real TCP protocol client.  It follows PATH_CMD
waypoints with simple point-mass kinematics while the world publishes changing
VISION_FRAME coordinates at 10 Hz.  No physical motor code is used.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import socket
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from protocol import JsonLineConnection
from vision_sender_example import SAMPLE_BOATS, SAMPLE_VICTIMS, send_frame


LOG = logging.getLogger("dynamic_simulator")


@dataclass
class SimBoat:
    boat_id: str
    x: float
    y: float
    heading: float
    speed_mps: float
    connection: JsonLineConnection | None = None
    waypoints: list[dict[str, float]] = field(default_factory=list)
    targets: list[dict[str, Any]] = field(default_factory=list)
    path_version: int = -1
    reported: set[str] = field(default_factory=set)
    lock: threading.RLock = field(default_factory=threading.RLock)

    def connect(self, host: str, port: int) -> None:
        sock = socket.create_connection((host, port), timeout=5.0)
        sock.settimeout(None)
        connection = JsonLineConnection(sock)
        connection.send({"type": "HELLO", "boat_id": self.boat_id, "software_version": "sim-1.0"})
        reply = connection.receive()
        if not reply or reply.get("type") != "HELLO_ACK":
            connection.close()
            raise RuntimeError(f"Base station rejected {self.boat_id}")
        self.connection = connection
        threading.Thread(target=self._reader, name=f"{self.boat_id}-reader", daemon=True).start()
        LOG.info("%s connected", self.boat_id)

    def _reader(self) -> None:
        assert self.connection is not None
        try:
            while True:
                message = self.connection.receive()
                if message is None:
                    return
                kind = message.get("type")
                if kind == "PATH_CMD":
                    version = int(message["path_version"])
                    with self.lock:
                        if version > self.path_version:
                            self.path_version = version
                            self.waypoints = [
                                {"x": float(p["x"]), "y": float(p["y"])}
                                for p in message.get("waypoints", [])
                            ]
                            self.targets = [
                                {"id": str(p["id"]), "x": float(p["x"]), "y": float(p["y"])}
                                for p in message.get("targets", [])
                            ]
                            self.reported.difference_update(p["id"] for p in self.targets)
                    self.send({"type": "ACK", "path_version": version, "result": "ACCEPTED"})
                    LOG.info("%s accepted v%s -> %s", self.boat_id, version, message.get("victim_ids", []))
                elif kind == "E_STOP":
                    with self.lock:
                        self.waypoints.clear()
                    self.send({"type": "ACK", "command": "E_STOP", "result": "STOPPED"})
                    LOG.warning("%s stopped: %s", self.boat_id, message.get("reason"))
                # POSE_UPDATE is intentionally ignored: the simulated world is
                # the source of truth for its own pose.
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            LOG.warning("%s reader ended: %s", self.boat_id, exc)

    def step(self, dt: float, rescue_radius_m: float) -> None:
        reports: list[str] = []
        with self.lock:
            remaining = self.speed_mps * dt
            while remaining > 0 and self.waypoints:
                waypoint = self.waypoints[0]
                dx, dy = waypoint["x"] - self.x, waypoint["y"] - self.y
                distance = math.hypot(dx, dy)
                if distance < 0.02:
                    self.x, self.y = waypoint["x"], waypoint["y"]
                    self.waypoints.pop(0)
                    continue
                self.heading = math.atan2(dy, dx)
                if remaining >= distance:
                    self.x, self.y = waypoint["x"], waypoint["y"]
                    self.waypoints.pop(0)
                    remaining -= distance
                else:
                    self.x += dx / distance * remaining
                    self.y += dy / distance * remaining
                    remaining = 0
            while self.targets:
                target = self.targets[0]
                if math.hypot(target["x"] - self.x, target["y"] - self.y) > rescue_radius_m:
                    break
                self.targets.pop(0)
                if target["id"] not in self.reported:
                    self.reported.add(target["id"])
                    reports.append(target["id"])
        for victim_id in reports:
            self.send({"type": "RESCUED", "victim_id": victim_id, "timestamp": time.time()})
            LOG.info("%s rescued %s", self.boat_id, victim_id)

    def send(self, message: dict[str, Any]) -> None:
        if not self.connection:
            return
        message.setdefault("boat_id", self.boat_id)
        try:
            self.connection.send(message)
        except OSError:
            pass

    def vision_record(self) -> dict[str, Any]:
        with self.lock:
            return {
                "id": self.boat_id,
                "x": round(self.x, 4),
                "y": round(self.y, 4),
                "heading": round(self.heading, 5),
                "confidence": 0.99,
            }

    def close(self) -> None:
        if self.connection:
            self.connection.close()


def run_simulation(
    host: str = "127.0.0.1",
    boat_port: int = 9000,
    vision_port: int = 9100,
    speed: float = 0.28,
    stop_event: threading.Event | None = None,
) -> None:
    stop_event = stop_event or threading.Event()
    boats = [
        SimBoat(str(item["id"]), float(item["x"]), float(item["y"]), float(item["heading"]), speed)
        for item in SAMPLE_BOATS
    ]
    try:
        deadline = time.monotonic() + 10.0
        for boat in boats:
            while not stop_event.is_set():
                try:
                    boat.connect(host, boat_port)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise
                    stop_event.wait(0.25)
            if stop_event.is_set():
                return
        LOG.info("Dynamic simulation started; all four boats are online")
        last = time.monotonic()
        last_heartbeat = 0.0
        while not stop_event.is_set():
            now = time.monotonic()
            dt, last = min(now - last, 0.25), now
            for boat in boats:
                boat.step(dt, rescue_radius_m=0.14)
            if now - last_heartbeat >= 0.5:
                last_heartbeat = now
                for boat in boats:
                    boat.send({"type": "HEARTBEAT", "mode": "SIMULATION", "timestamp": time.time()})
            send_frame(host, vision_port, [boat.vision_record() for boat in boats], SAMPLE_VICTIMS)
            stop_event.wait(0.1)
    finally:
        for boat in boats:
            boat.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Dynamic four-boat visual simulation")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--boat-port", type=int, default=9000)
    parser.add_argument("--vision-port", type=int, default=9100)
    parser.add_argument("--speed", type=float, default=0.28, help="visual simulation speed in metres/second")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stop_event = threading.Event()
    try:
        run_simulation(args.host, args.boat_port, args.vision_port, args.speed, stop_event)
    except KeyboardInterrupt:
        stop_event.set()


if __name__ == "__main__":
    main()
