"""把 666.py 的毫米坐标接到 jisuan 的 A* 路径规划器。"""

from __future__ import annotations

from dataclasses import dataclass

import config
from planning.rescue_core import Boat, GridMap, Point, RescuePlanner, Victim


@dataclass
class PlannedRoute:
    target_id: str
    target_x_mm: float
    target_y_mm: float
    waypoints_mm: list[tuple[float, float]]
    distance_mm: float


class PathPlanner:
    def __init__(self) -> None:
        obstacles_m = [[v / 1000.0 for v in item] for item in config.OBSTACLES_MM]
        self.grid = GridMap(
            config.FIELD_WIDTH_MM / 1000.0,
            config.FIELD_HEIGHT_MM / 1000.0,
            config.GRID_RESOLUTION_MM / 1000.0,
            obstacles_m,
            config.SAFETY_MARGIN_MM / 1000.0,
        )

    @staticmethod
    def _point(item: dict) -> Point:
        return Point(float(item["x"]) / 1000.0, float(item["y"]) / 1000.0)

    def plan_first_target(self, boat_data: dict, persons: list[dict]) -> PlannedRoute:
        """先用 RescuePlanner 求最优访问顺序，再为第一个目标生成 A* 路径。"""
        if not persons:
            raise ValueError("当前没有检测到待救人员")
        boat = Boat(str(boat_data.get("id", 0)), self._point(boat_data))
        victims = [Victim(str(p.get("id", i)), self._point(p)) for i, p in enumerate(persons)]
        order = RescuePlanner(self.grid, rescue_service_s=0).plan([boat], victims)[0].victim_ids
        target_id = order[0]
        target_index = next(i for i, victim in enumerate(victims) if victim.victim_id == target_id)
        target = persons[target_index]
        path, distance_m = self.grid.astar(boat.position, victims[target_index].position)
        return PlannedRoute(
            target_id=target_id,
            target_x_mm=float(target["x"]), target_y_mm=float(target["y"]),
            waypoints_mm=[(round(p.x * 1000, 1), round(p.y * 1000, 1)) for p in path],
            distance_mm=round(distance_m * 1000, 1),
        )
