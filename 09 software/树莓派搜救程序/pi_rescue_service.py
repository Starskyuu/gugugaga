"""Raspberry Pi rescue route service.

Input: UDP JSON VISION_FRAME packets containing relative boat/person positions.
Output: one UDP JSON ROUTE_PLAN packet per boat; a summary is saved to disk.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import socket
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from rescue_core import Boat, BoatPlan, GridMap, Point, RescuePlanner, Victim
from route_planners import Rectangle, RectangleVisibilityMap, balanced_greedy_plan


LOG = logging.getLogger("pi_rescue_service")


class PiRescueService:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.stop_event = threading.Event()
        self.plan_event = threading.Event()
        self.lock = threading.RLock()
        self.boats: dict[str, Boat] = {}
        self.victims: dict[str, Victim] = {}
        self.version = 0
        self.last_signature: tuple[Any, ...] | None = None
        self.last_plan: dict[str, Any] | None = None
        self.last_error: str | None = None
        self.unit_scale = {"m": 1.0, "cm": 0.01, "mm": 0.001}[config.get("coordinate_unit", "cm")]
        field = config["field"]
        self.grid = GridMap(
            float(field["width"]) * self.unit_scale,
            float(field["height"]) * self.unit_scale,
            float(field["grid_resolution"]) * self.unit_scale,
            obstacles=[self._scale_rect(rect) for rect in field.get("obstacles", [])],
            safety_margin_m=float(field.get("safety_margin", 0.0)) * self.unit_scale,
        )
        base = field["base_station"]
        margin = float(field.get("safety_margin", 0.0))
        self.base_safety = Rectangle(
            (float(base[0]) - margin) * self.unit_scale,
            (float(base[1]) - margin) * self.unit_scale,
            (float(base[2]) + margin) * self.unit_scale,
            (float(base[3]) + margin) * self.unit_scale,
        )
        self.visibility = RectangleVisibilityMap(self.base_safety)
        self.launch_points = {
            boat_id: Point(float(data["launch"][0]) * self.unit_scale, float(data["launch"][1]) * self.unit_scale)
            for boat_id, data in config["boats"].items()
        }

    def _scale_rect(self, rect: list[float]) -> list[float]:
        return [float(value) * self.unit_scale for value in rect]

    def run(self) -> None:
        planner_thread = threading.Thread(target=self._planning_loop, name="route-planner", daemon=True)
        planner_thread.start()
        network = self.config["vision_input"]
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind((str(network.get("bind_host", "0.0.0.0")), int(network["port"])))
            receiver.settimeout(1.0)
            LOG.info("Listening for vision coordinates on UDP %s:%s", network.get("bind_host", "0.0.0.0"), network["port"])
            while not self.stop_event.is_set():
                try:
                    payload, address = receiver.recvfrom(65507)
                    frame = json.loads(payload.decode("utf-8"))
                    self.accept_frame(frame)
                    LOG.debug("Accepted vision frame from %s:%s", *address)
                except socket.timeout:
                    continue
                except (UnicodeDecodeError, json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
                    self.last_error = str(exc)
                    LOG.warning("Rejected vision frame: %s", exc)

    def stop(self) -> None:
        self.stop_event.set()
        self.plan_event.set()

    def accept_frame(self, frame: dict[str, Any]) -> None:
        if frame.get("type") != "VISION_FRAME":
            raise ValueError("type must be VISION_FRAME")
        boat_items = frame.get("boats", [])
        victim_items = frame.get("people", frame.get("victims", []))
        allowed_boats = set(self.config["boats"])
        boats: dict[str, Boat] = {}
        for item in boat_items:
            boat_id = str(item["id"])
            if boat_id not in allowed_boats:
                continue
            point = self._read_point(item)
            speed = float(self.config["boats"][boat_id]["speed"]) * self.unit_scale
            boats[boat_id] = Boat(boat_id, point, speed)
        victims: dict[str, Victim] = {}
        for item in victim_items:
            victim_id = str(item["id"])
            point = self._read_point(item)
            if self.base_safety.contains(point):
                raise ValueError(f"Person {victim_id} is inside the base safety zone")
            victims[victim_id] = Victim(victim_id, point)
        if not boats:
            raise ValueError("No configured boats in frame")
        maximum = int(self.config["planning"].get("maximum_targets", 1000))
        if len(victims) > maximum:
            raise ValueError(f"Target count {len(victims)} exceeds configured maximum {maximum}")
        signature = (
            tuple((key, round(value.position.x, 3), round(value.position.y, 3)) for key, value in sorted(boats.items())),
            tuple((key, round(value.position.x, 3), round(value.position.y, 3)) for key, value in sorted(victims.items())),
        )
        with self.lock:
            self.boats, self.victims = boats, victims
            if signature != self.last_signature:
                self.last_signature = signature
                self.plan_event.set()

    def _read_point(self, item: dict[str, Any]) -> Point:
        x = item.get("x", item.get("x_cm"))
        y = item.get("y", item.get("y_cm"))
        if x is None or y is None:
            raise ValueError("Each detection requires x/y coordinates")
        point = Point(float(x) * self.unit_scale, float(y) * self.unit_scale)
        if not (0.0 <= point.x <= self.grid.width_m and 0.0 <= point.y <= self.grid.height_m):
            raise ValueError(f"Coordinate outside field: ({x}, {y})")
        return point

    def _planning_loop(self) -> None:
        while not self.stop_event.is_set():
            if not self.plan_event.wait(0.5):
                continue
            self.plan_event.clear()
            with self.lock:
                boats = [self.boats[key] for key in sorted(self.boats)]
                victims = [self.victims[key] for key in sorted(self.victims)]
            if not boats:
                continue
            started = time.perf_counter()
            try:
                plans, algorithm = self.compute_plans(boats, victims)
                self.version += 1
                elapsed_ms = (time.perf_counter() - started) * 1000
                packet = self._build_plan_packet(plans, algorithm, elapsed_ms)
                self._publish(packet)
                self.last_plan, self.last_error = packet, None
                LOG.info("Plan v%s: %s, %s targets, %.1f ms", self.version, algorithm, len(victims), elapsed_ms)
            except Exception as exc:
                self.last_error = str(exc)
                LOG.exception("Route planning failed")

    def compute_plans(self, boats: list[Boat], victims: list[Victim]) -> tuple[list[BoatPlan], str]:
        if not victims:
            return [BoatPlan(boat.boat_id, [], [boat.position], 0.0, 0.0) for boat in boats], "idle"
        safe_boats, launch_prefixes = [], {}
        for boat in boats:
            if self.base_safety.contains(boat.position):
                launch = self.launch_points[boat.boat_id]
                safe_boats.append(Boat(boat.boat_id, launch, boat.speed_mps))
                launch_prefixes[boat.boat_id] = [boat.position, launch]
            else:
                safe_boats.append(boat)
                launch_prefixes[boat.boat_id] = []
        planning = self.config["planning"]
        exact_limit = int(planning.get("exact_target_limit", 12))
        selected = planning.get("algorithm", "auto")
        use_exact = selected == "exact" or (selected == "auto" and len(victims) <= exact_limit)
        if use_exact:
            if len(victims) > exact_limit:
                raise ValueError(f"Exact algorithm supports at most {exact_limit} targets")
            plans = RescuePlanner(self.grid, float(planning.get("rescue_service_s", 3.0))).plan(safe_boats, victims)
            algorithm = "exact_dp_astar"
        else:
            plans = balanced_greedy_plan(
                safe_boats,
                victims,
                self.visibility,
                float(planning.get("rescue_service_s", 3.0)),
            )
            algorithm = "balanced_greedy_visibility"
        by_id = {boat.boat_id: boat for boat in boats}
        for plan in plans:
            prefix = launch_prefixes[plan.boat_id]
            if prefix:
                launch_distance = hypot_points(prefix[0], prefix[1])
                plan.waypoints = prefix + (plan.waypoints[1:] if plan.waypoints else [])
                plan.distance_m += launch_distance
                plan.estimated_time_s += launch_distance / by_id[plan.boat_id].speed_mps
        return plans, algorithm

    def _build_plan_packet(self, plans: list[BoatPlan], algorithm: str, elapsed_ms: float) -> dict[str, Any]:
        scale_back = 1.0 / self.unit_scale
        victim_lookup = self.victims
        return {
            "type": "RESCUE_PLAN_SUMMARY",
            "version": self.version,
            "algorithm": algorithm,
            "coordinate_unit": self.config.get("coordinate_unit", "cm"),
            "planning_time_ms": round(elapsed_ms, 2),
            "created_at": time.time(),
            "routes": [
                {
                    "boat_id": plan.boat_id,
                    "victim_ids": plan.victim_ids,
                    "targets": [
                        {
                            "id": victim_id,
                            "x": round(victim_lookup[victim_id].position.x * scale_back, 3),
                            "y": round(victim_lookup[victim_id].position.y * scale_back, 3),
                        }
                        for victim_id in plan.victim_ids
                        if victim_id in victim_lookup
                    ],
                    "waypoints": [
                        {"x": round(point.x * scale_back, 3), "y": round(point.y * scale_back, 3)}
                        for point in plan.waypoints
                    ],
                    "distance": round(plan.distance_m * scale_back, 3),
                    "estimated_time_s": round(plan.estimated_time_s, 2),
                }
                for plan in plans
            ],
        }

    def _publish(self, summary: dict[str, Any]) -> None:
        output = self.config["route_output"]
        address = str(output["host"]), int(output["port"])
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            for route in summary["routes"]:
                packet = {
                    "type": "ROUTE_PLAN",
                    "version": summary["version"],
                    "algorithm": summary["algorithm"],
                    "coordinate_unit": summary["coordinate_unit"],
                    **route,
                }
                payload = json.dumps(packet, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
                if len(payload) > 60000:
                    raise ValueError(f"Route packet for {route['boat_id']} exceeds safe UDP size")
                sender.sendto(payload, address)
        sender_path = Path(self.config.get("last_plan_file", "last_plan.json"))
        sender_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=sender_path.parent, suffix=".tmp") as stream:
            json.dump(summary, stream, ensure_ascii=False, indent=2)
            temporary = stream.name
        os.replace(temporary, sender_path)


def hypot_points(a: Point, b: Point) -> float:
    return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5


def load_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def main() -> None:
    parser = argparse.ArgumentParser(description="Raspberry Pi rescue route service")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper()), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    service = PiRescueService(load_config(args.config))
    signal.signal(signal.SIGINT, lambda *_: service.stop())
    signal.signal(signal.SIGTERM, lambda *_: service.stop())
    service.run()


if __name__ == "__main__":
    main()
