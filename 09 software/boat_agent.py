"""Boat-side agent.

The default console driver never energises a motor.  The serial driver sends
normalised left/right commands to an ESP32 running the supplied firmware.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import socket
import threading
import time
from pathlib import Path
from typing import Any, Protocol

from protocol import JsonLineConnection


LOG = logging.getLogger("boat_agent")


class MotorDriver(Protocol):
    def drive(self, left: float, right: float) -> None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...


class ConsoleMotorDriver:
    def __init__(self) -> None:
        self.last = (None, None)

    def drive(self, left: float, right: float) -> None:
        command = (round(left, 2), round(right, 2))
        if command != self.last:
            LOG.info("DRY-RUN motors left=%+.2f right=%+.2f", *command)
            self.last = command

    def stop(self) -> None:
        self.drive(0.0, 0.0)

    def close(self) -> None:
        self.stop()


class SerialMotorDriver:
    def __init__(self, port: str, baudrate: int) -> None:
        try:
            import serial  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Serial mode requires: python -m pip install pyserial") from exc
        self.serial = serial.Serial(port, baudrate=baudrate, timeout=0.2)
        time.sleep(2.0)

    def drive(self, left: float, right: float) -> None:
        payload = {"left": clamp(left), "right": clamp(right)}
        self.serial.write((json.dumps(payload, separators=(",", ":")) + "\n").encode("ascii"))

    def stop(self) -> None:
        self.drive(0.0, 0.0)

    def close(self) -> None:
        try:
            self.stop()
        finally:
            self.serial.close()


class BoatAgent:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.boat_id = str(config["boat_id"])
        driver_cfg = config.get("motor_driver", {"type": "console"})
        if driver_cfg.get("type") == "serial":
            self.driver: MotorDriver = SerialMotorDriver(str(driver_cfg["port"]), int(driver_cfg.get("baudrate", 115200)))
        else:
            self.driver = ConsoleMotorDriver()
        self._stop = threading.Event()
        self._connection: JsonLineConnection | None = None
        self._last_server_message = time.monotonic()
        self._active_version = -1
        self._waypoints: list[dict[str, float]] = []
        self._victim_ids: list[str] = []
        self._targets: list[dict[str, Any]] = []
        self._pose: dict[str, float] | None = None
        self._state_lock = threading.RLock()

    def run(self) -> None:
        retry = float(self.config.get("reconnect_interval_s", 2.0))
        while not self._stop.is_set():
            try:
                self._run_connection()
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                LOG.warning("Connection lost: %s", exc)
            finally:
                self.driver.stop()
                if self._connection:
                    self._connection.close()
                    self._connection = None
            self._stop.wait(retry)
        self.driver.close()

    def stop(self) -> None:
        self._stop.set()
        self.driver.stop()

    def _run_connection(self) -> None:
        host, port = str(self.config["base_station_host"]), int(self.config["base_station_port"])
        LOG.info("Connecting to %s:%s as %s", host, port, self.boat_id)
        sock = socket.create_connection((host, port), timeout=5.0)
        sock.settimeout(None)
        connection = JsonLineConnection(sock)
        self._connection = connection
        connection.send({"type": "HELLO", "boat_id": self.boat_id, "software_version": "1.0"})
        hello_ack = connection.receive()
        if not hello_ack or hello_ack.get("type") != "HELLO_ACK":
            raise ValueError("Base station did not accept HELLO")
        self._last_server_message = time.monotonic()
        threads = [
            threading.Thread(target=self._heartbeat_loop, daemon=True),
            threading.Thread(target=self._control_loop, daemon=True),
            threading.Thread(target=self._watchdog_loop, daemon=True),
        ]
        for thread in threads:
            thread.start()
        while not self._stop.is_set():
            message = connection.receive()
            if message is None:
                break
            self._last_server_message = time.monotonic()
            self._handle_message(message)

    def _handle_message(self, message: dict[str, Any]) -> None:
        kind = message["type"]
        if kind == "PATH_CMD":
            if str(message["boat_id"]) != self.boat_id:
                return
            version = int(message["path_version"])
            if version <= self._active_version:
                self._send({"type": "ACK", "path_version": version, "result": "IGNORED_OLD"})
                return
            waypoints = message.get("waypoints", [])
            with self._state_lock:
                self._active_version = version
                self._waypoints = [{"x": float(p["x"]), "y": float(p["y"])} for p in waypoints]
                self._victim_ids = list(map(str, message.get("victim_ids", [])))
                self._targets = [
                    {"id": str(p["id"]), "x": float(p["x"]), "y": float(p["y"])}
                    for p in message.get("targets", [])
                ]
            self._send({"type": "ACK", "path_version": version, "result": "ACCEPTED"})
            LOG.info("Accepted path v%s: victims=%s, waypoints=%s", version, self._victim_ids, len(waypoints))
        elif kind == "POSE_UPDATE":
            with self._state_lock:
                self._pose = {
                    "x": float(message["x"]), "y": float(message["y"]),
                    "heading": float(message["heading"]), "timestamp": float(message["timestamp"]),
                }
        elif kind == "E_STOP":
            with self._state_lock:
                self._waypoints.clear()
            self.driver.stop()
            self._send({"type": "ACK", "command": "E_STOP", "result": "STOPPED"})
            LOG.error("Emergency stop: %s", message.get("reason", "unspecified"))
        else:
            LOG.warning("Unknown base-station message: %s", message)

    def _heartbeat_loop(self) -> None:
        interval = float(self.config.get("heartbeat_interval_s", 0.5))
        while not self._stop.wait(interval) and self._connection:
            try:
                self._send({"type": "HEARTBEAT", "mode": "AUTO", "timestamp": time.time()})
            except OSError:
                return

    def _watchdog_loop(self) -> None:
        timeout = float(self.config.get("server_timeout_s", 3.0))
        while not self._stop.wait(0.1) and self._connection:
            if time.monotonic() - self._last_server_message > timeout:
                LOG.error("Server timeout; motors stopped")
                self.driver.stop()
                try:
                    self._connection.close()
                except OSError:
                    pass
                return

    def _control_loop(self) -> None:
        """Waypoint follower used when POSE_UPDATE messages are available.

        Without pose updates it intentionally remains stopped.  The central
        visual adapter or another local navigation source must provide pose.
        """
        hz = float(self.config.get("control_hz", 10.0))
        arrival = float(self.config.get("waypoint_tolerance_m", 0.12))
        rescue_radius = float(self.config.get("rescue_radius_m", 0.18))
        heading_gain = float(self.config.get("heading_gain", 1.2))
        cruise = float(self.config.get("cruise_output", 0.45))
        pose_max_age = float(self.config.get("pose_max_age_s", 0.5))
        while not self._stop.wait(1.0 / hz) and self._connection:
            with self._state_lock:
                pose = dict(self._pose) if self._pose else None
                waypoint = dict(self._waypoints[0]) if self._waypoints else None
                target = dict(self._targets[0]) if self._targets else None
            if not pose or not waypoint or time.time() - pose["timestamp"] > pose_max_age:
                self.driver.stop()
                continue
            if target and math.hypot(target["x"] - pose["x"], target["y"] - pose["y"]) <= rescue_radius:
                with self._state_lock:
                    if self._targets and self._targets[0]["id"] == target["id"]:
                        self._targets.pop(0)
                    if self._victim_ids and self._victim_ids[0] == target["id"]:
                        self._victim_ids.pop(0)
                self._send({"type": "RESCUED", "victim_id": target["id"], "timestamp": time.time()})
            dx, dy = waypoint["x"] - pose["x"], waypoint["y"] - pose["y"]
            distance = math.hypot(dx, dy)
            if distance <= arrival:
                with self._state_lock:
                    if self._waypoints:
                        self._waypoints.pop(0)
                    finished = not self._waypoints
                self.driver.stop()
                continue
            desired = math.atan2(dy, dx)
            error = wrap_angle(desired - pose["heading"])
            turn = clamp(heading_gain * error)
            forward = cruise * max(0.0, 1.0 - abs(error) / math.pi)
            self.driver.drive(clamp(forward - turn), clamp(forward + turn))

    def _send(self, message: dict[str, Any]) -> None:
        if not self._connection:
            raise OSError("Not connected")
        message.setdefault("boat_id", self.boat_id)
        self._connection.send(message)


def clamp(value: float, lower: float = -1.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def wrap_angle(angle: float) -> float:
    return (angle + math.pi) % (2 * math.pi) - math.pi


def main() -> None:
    parser = argparse.ArgumentParser(description="Rescue boat agent")
    parser.add_argument("--config", required=True)
    parser.add_argument("--host", help="override base_station_host (use 127.0.0.1 for local demo)")
    parser.add_argument("--dry-run", action="store_true", help="force console motor driver")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    with open(args.config, "r", encoding="utf-8") as stream:
        config = json.load(stream)
    if args.host:
        config["base_station_host"] = args.host
    if args.dry_run:
        config["motor_driver"] = {"type": "console"}
    agent = BoatAgent(config)
    try:
        agent.run()
    except KeyboardInterrupt:
        agent.stop()


if __name__ == "__main__":
    main()
