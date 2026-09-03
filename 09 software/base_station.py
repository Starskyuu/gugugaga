"""Central base-station process for visual input, planning and boat dispatch."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import socket
import threading
import time
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from protocol import JsonLineConnection
from rescue_core import Boat, GridMap, Point, RescuePlanner, Victim, point_to_dict


LOG = logging.getLogger("base_station")


@dataclass
class BoatSession:
    boat_id: str
    connection: JsonLineConnection
    address: tuple[str, int]
    last_seen: float = field(default_factory=time.monotonic)
    last_state: dict[str, Any] = field(default_factory=dict)


class BaseStation:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        map_cfg = config["map"]
        self.grid = GridMap(
            width_m=float(map_cfg["width_m"]),
            height_m=float(map_cfg["height_m"]),
            resolution_m=float(map_cfg["resolution_m"]),
            obstacles=map_cfg.get("obstacles", []),
            safety_margin_m=float(map_cfg.get("safety_margin_m", 0.0)),
        )
        self.planner = RescuePlanner(self.grid, float(config.get("rescue_service_s", 3.0)))
        self.sessions: dict[str, BoatSession] = {}
        self.boat_positions: dict[str, Point] = {}
        self.boat_headings: dict[str, float] = {}
        self.victims: dict[str, Victim] = {}
        self.completed_victims: set[str] = set()
        self.last_plans: list[dict[str, Any]] = []
        self.path_version = 0
        self._state_lock = threading.RLock()
        self._stop = threading.Event()
        self._dirty = threading.Event()
        self._tcp_socket: socket.socket | None = None
        self._udp_socket: socket.socket | None = None
        self._boat_server_ready = threading.Event()
        self._vision_receiver_ready = threading.Event()
        self._fatal_error: str | None = None
        self._demo_stop = threading.Event()
        self._demo_thread: threading.Thread | None = None

    def run(self) -> None:
        net = self.config["network"]
        threads = [
            threading.Thread(target=self._boat_server, name="boat-server", daemon=True),
            threading.Thread(target=self._vision_receiver, name="vision-receiver", daemon=True),
            threading.Thread(target=self._planning_loop, name="planner", daemon=True),
            threading.Thread(target=self._watchdog_loop, name="watchdog", daemon=True),
        ]
        for thread in threads:
            thread.start()
        if not self._boat_server_ready.wait(2.0) or not self._vision_receiver_ready.wait(2.0):
            if not self._fatal_error:
                self._fatal_error = "Network services did not start within 2 seconds"
                LOG.critical(self._fatal_error)
            self._stop.set()
            return
        LOG.info(
            "Base station ready: boats TCP %s:%s; vision UDP %s:%s",
            net.get("bind_host", "0.0.0.0"), net["boat_tcp_port"],
            net.get("bind_host", "0.0.0.0"), net["vision_udp_port"],
        )
        while not self._stop.wait(0.5):
            pass
        self.emergency_stop("base_station_shutdown")
        for sock in (self._tcp_socket, self._udp_socket):
            if sock:
                try:
                    sock.close()
                except OSError:
                    pass

    def stop(self) -> None:
        self._demo_stop.set()
        self._stop.set()

    def _boat_server(self) -> None:
        net = self.config["network"]
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
            self._tcp_socket = server
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                server.bind((net.get("bind_host", "0.0.0.0"), int(net["boat_tcp_port"])))
            except OSError as exc:
                self._fatal_error = f"Boat TCP port {net['boat_tcp_port']} is unavailable: {exc}"
                LOG.critical(self._fatal_error)
                self._stop.set()
                return
            server.listen(8)
            self._boat_server_ready.set()
            server.settimeout(1.0)
            while not self._stop.is_set():
                try:
                    sock, address = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                threading.Thread(target=self._handle_boat, args=(sock, address), daemon=True).start()

    def _handle_boat(self, sock: socket.socket, address: tuple[str, int]) -> None:
        connection = JsonLineConnection(sock)
        boat_id = "unknown"
        try:
            hello = connection.receive()
            if not hello or hello.get("type") != "HELLO":
                raise ValueError("First message must be HELLO")
            boat_id = str(hello["boat_id"])
            allowed = set(self.config["boats"])
            if boat_id not in allowed:
                raise ValueError(f"Unconfigured boat_id {boat_id!r}")
            with self._state_lock:
                old = self.sessions.pop(boat_id, None)
                if old:
                    old.connection.close()
                self.sessions[boat_id] = BoatSession(boat_id, connection, address)
            connection.send({"type": "HELLO_ACK", "boat_id": boat_id, "server_time": time.time()})
            LOG.info("%s connected from %s:%s", boat_id, *address)
            self._dirty.set()
            while not self._stop.is_set():
                message = connection.receive()
                if message is None:
                    break
                with self._state_lock:
                    session = self.sessions.get(boat_id)
                    if session:
                        session.last_seen = time.monotonic()
                        session.last_state = message
                kind = message.get("type")
                if kind == "RESCUED":
                    victim_id = str(message["victim_id"])
                    with self._state_lock:
                        self.completed_victims.add(victim_id)
                    LOG.info("%s reports %s rescued", boat_id, victim_id)
                    self._dirty.set()
                elif kind in {"ACK", "TELEMETRY", "HEARTBEAT"}:
                    LOG.debug("%s: %s", boat_id, message)
                else:
                    LOG.warning("Unhandled message from %s: %s", boat_id, message)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            LOG.warning("Boat connection %s ended: %s", boat_id, exc)
        finally:
            with self._state_lock:
                if self.sessions.get(boat_id, None) and self.sessions[boat_id].connection is connection:
                    self.sessions.pop(boat_id, None)
            connection.close()

    def _vision_receiver(self) -> None:
        net = self.config["network"]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            self._udp_socket = receiver
            try:
                receiver.bind((net.get("bind_host", "0.0.0.0"), int(net["vision_udp_port"])))
            except OSError as exc:
                self._fatal_error = f"Vision UDP port {net['vision_udp_port']} is unavailable: {exc}"
                LOG.critical(self._fatal_error)
                self._stop.set()
                return
            self._vision_receiver_ready.set()
            receiver.settimeout(1.0)
            while not self._stop.is_set():
                try:
                    payload, address = receiver.recvfrom(65507)
                    frame = json.loads(payload.decode("utf-8"))
                    self._apply_vision_frame(frame)
                    LOG.debug("Vision frame from %s:%s", *address)
                except socket.timeout:
                    continue
                except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError) as exc:
                    if not self._stop.is_set():
                        LOG.warning("Rejected vision frame: %s", exc)

    def _apply_vision_frame(self, frame: dict[str, Any]) -> None:
        if frame.get("type") != "VISION_FRAME":
            raise ValueError("UDP message type must be VISION_FRAME")
        max_age = float(self.config.get("vision_max_age_s", 1.0))
        timestamp = float(frame["timestamp"])
        if abs(time.time() - timestamp) > max_age:
            raise ValueError("Vision frame timestamp is stale")
        minimum_confidence = float(self.config.get("vision_min_confidence", 0.6))
        positions: dict[str, Point] = {}
        for item in frame.get("boats", []):
            if float(item.get("confidence", 1.0)) >= minimum_confidence:
                positions[str(item["id"])] = Point(float(item["x"]), float(item["y"]))
        detected_victims: dict[str, Victim] = {}
        for item in frame.get("victims", []):
            if float(item.get("confidence", 1.0)) >= minimum_confidence:
                victim_id = str(item["id"])
                detected_victims[victim_id] = Victim(victim_id, Point(float(item["x"]), float(item["y"])))
        with self._state_lock:
            previous_positions = self.boat_positions
            self.boat_positions = positions
            self.boat_headings = {
                str(item["id"]): float(item.get("heading", 0.0))
                for item in frame.get("boats", [])
                if str(item["id"]) in positions
            }
            # Victims are fixed: first valid observation locks their coordinates.
            previous_victim_ids = set(self.victims)
            for victim_id, victim in detected_victims.items():
                self.victims.setdefault(victim_id, victim)
            has_new_victim = set(self.victims) != previous_victim_ids
            threshold = float(self.config.get("replan_position_change_m", 0.15))
            changed = positions.keys() != previous_positions.keys() or any(
                hypot_point(positions[k], previous_positions[k]) > threshold
                for k in positions.keys() & previous_positions.keys()
            )
            sessions = {boat_id: self.sessions.get(boat_id) for boat_id in positions}
        # Forward calibrated visual pose to the corresponding boat. Heading is
        # optional in early simulations and defaults to zero.
        headings = dict(self.boat_headings)
        for boat_id, point in positions.items():
            session = sessions.get(boat_id)
            if session:
                try:
                    session.connection.send({
                        "type": "POSE_UPDATE", "boat_id": boat_id,
                        "x": point.x, "y": point.y, "heading": headings.get(boat_id, 0.0),
                        "timestamp": timestamp,
                    })
                except OSError:
                    pass
        if changed or has_new_victim:
            self._dirty.set()

    def _planning_loop(self) -> None:
        minimum_interval = float(self.config.get("minimum_replan_interval_s", 1.0))
        last_plan = 0.0
        while not self._stop.is_set():
            if not self._dirty.wait(0.5):
                continue
            remaining_wait = minimum_interval - (time.monotonic() - last_plan)
            if remaining_wait > 0 and self._stop.wait(remaining_wait):
                return
            self._dirty.clear()
            try:
                if self.plan_and_dispatch():
                    last_plan = time.monotonic()
            except Exception:
                LOG.exception("Planning failed; sending E_STOP")
                self.emergency_stop("planning_failed")

    def plan_and_dispatch(self) -> bool:
        with self._state_lock:
            ready_ids = [boat_id for boat_id in self.config["boats"] if boat_id in self.sessions and boat_id in self.boat_positions]
            victims = [v for key, v in sorted(self.victims.items()) if key not in self.completed_victims]
            victim_lookup = {victim.victim_id: victim for victim in victims}
            if not ready_ids or not victims:
                if not victims:
                    self.last_plans = []
                return False
            boats = [
                Boat(boat_id, self.boat_positions[boat_id], float(self.config["boats"][boat_id]["speed_mps"]))
                for boat_id in ready_ids
            ]
        plans = self.planner.plan(boats, victims)
        self.path_version += 1
        with self._state_lock:
            self.last_plans = [
                {
                    "boat_id": plan.boat_id,
                    "victim_ids": list(plan.victim_ids),
                    "waypoints": [point_to_dict(p) for p in plan.waypoints],
                    "distance_m": plan.distance_m,
                    "estimated_time_s": plan.estimated_time_s,
                }
                for plan in plans
            ]
        for plan in plans:
            with self._state_lock:
                session = self.sessions.get(plan.boat_id)
            if not session:
                continue
            session.connection.send(
                {
                    "type": "PATH_CMD",
                    "boat_id": plan.boat_id,
                    "path_version": self.path_version,
                    "victim_ids": plan.victim_ids,
                    "targets": [
                        {"id": victim_id, **point_to_dict(victim_lookup[victim_id].position)}
                        for victim_id in plan.victim_ids
                    ],
                    "waypoints": [point_to_dict(p) for p in plan.waypoints],
                    "speed_limit_mps": float(self.config["boats"][plan.boat_id]["speed_mps"]),
                    "estimated_time_s": round(plan.estimated_time_s, 2),
                    "timestamp": time.time(),
                }
            )
            LOG.info(
                "v%s %s -> %s, %.2f m / %.1f s",
                self.path_version, plan.boat_id, plan.victim_ids, plan.distance_m, plan.estimated_time_s,
            )
        return True

    def emergency_stop(self, reason: str) -> None:
        message = {"type": "E_STOP", "reason": reason, "timestamp": time.time()}
        with self._state_lock:
            sessions = list(self.sessions.values())
        for session in sessions:
            try:
                session.connection.send(message)
            except OSError:
                pass

    def request_replan(self) -> None:
        self._dirty.set()

    def start_demo(self) -> bool:
        """Start the built-in moving four-boat simulation once."""
        with self._state_lock:
            if self._demo_thread and self._demo_thread.is_alive():
                return False
            self._demo_stop = threading.Event()

            def run() -> None:
                try:
                    from dynamic_simulator import run_simulation

                    net = self.config["network"]
                    run_simulation(
                        host="127.0.0.1",
                        boat_port=int(net["boat_tcp_port"]),
                        vision_port=int(net["vision_udp_port"]),
                        speed=0.28,
                        stop_event=self._demo_stop,
                    )
                except Exception:
                    LOG.exception("Built-in dynamic demo failed")

            self._demo_thread = threading.Thread(target=run, name="dynamic-demo", daemon=True)
            self._demo_thread.start()
            return True

    def reset_mission(self) -> None:
        """Forget fixed victims and completion flags; the next frame relocks them."""
        with self._state_lock:
            self.victims.clear()
            self.completed_victims.clear()
            self.last_plans.clear()
        self._dirty.set()

    def visualization_snapshot(self) -> dict[str, Any]:
        """Return an immutable, JSON-like state snapshot for the GUI."""
        now = time.monotonic()
        with self._state_lock:
            boats = []
            for boat_id in self.config["boats"]:
                position = self.boat_positions.get(boat_id)
                session = self.sessions.get(boat_id)
                boats.append(
                    {
                        "id": boat_id,
                        "x": position.x if position else None,
                        "y": position.y if position else None,
                        "heading": self.boat_headings.get(boat_id, 0.0),
                        "online": session is not None,
                        "last_seen_age_s": now - session.last_seen if session else None,
                    }
                )
            victims = [
                {
                    "id": victim_id,
                    "x": victim.position.x,
                    "y": victim.position.y,
                    "completed": victim_id in self.completed_victims,
                }
                for victim_id, victim in sorted(self.victims.items())
            ]
            plans = [
                {
                    **plan,
                    "victim_ids": list(plan["victim_ids"]),
                    "waypoints": [dict(point) for point in plan["waypoints"]],
                }
                for plan in self.last_plans
            ]
        return {
            "map": dict(self.config["map"]),
            "boats": boats,
            "victims": victims,
            "plans": plans,
            "path_version": self.path_version,
            "demo_running": bool(self._demo_thread and self._demo_thread.is_alive()),
            "fatal_error": self._fatal_error,
            "stopping": self._stop.is_set(),
        }

    def _watchdog_loop(self) -> None:
        timeout = float(self.config.get("boat_heartbeat_timeout_s", 3.0))
        while not self._stop.wait(0.5):
            now = time.monotonic()
            with self._state_lock:
                stale = [s for s in self.sessions.values() if now - s.last_seen > timeout]
            for session in stale:
                LOG.error("%s heartbeat timeout", session.boat_id)
                try:
                    session.connection.close()
                except OSError:
                    pass


def hypot_point(a: Point, b: Point) -> float:
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def load_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def main() -> None:
    parser = argparse.ArgumentParser(description="Four-boat rescue base station")
    parser.add_argument("--config", default="configs/base_station.json")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--visualize", action="store_true", help="open the real-time 2D map")
    parser.add_argument("--visualizer-host", default="0.0.0.0")
    parser.add_argument("--visualizer-port", type=int, default=8080)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--demo", action="store_true", help="start the built-in moving four-boat simulation")
    parser.add_argument("--boat-port", type=int, help="override configured boat TCP port")
    parser.add_argument("--vision-port", type=int, help="override configured vision UDP port")
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config(args.config)
    if args.boat_port is not None:
        config["network"]["boat_tcp_port"] = args.boat_port
    if args.vision_port is not None:
        config["network"]["vision_udp_port"] = args.vision_port
    station = BaseStation(config)
    signal.signal(signal.SIGINT, lambda *_: station.stop())
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, lambda *_: station.stop())
    web_server = None
    if args.visualize:
        from web_visualizer import start_visualizer

        web_server = start_visualizer(station, args.visualizer_host, args.visualizer_port)
        local_url = f"http://127.0.0.1:{args.visualizer_port}"
        LOG.info("2D dashboard: %s (LAN: http://<base-station-IP>:%s)", local_url, args.visualizer_port)
        if args.open_browser:
            webbrowser.open(local_url)
    if args.demo:
        station.start_demo()
    try:
        station.run()
    finally:
        if web_server:
            web_server.shutdown()
            web_server.server_close()


if __name__ == "__main__":
    main()
