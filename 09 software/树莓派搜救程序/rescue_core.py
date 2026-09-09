"""Core planning code for the four-boat rescue prototype.

Only the Python standard library is used so the same code can run on a
Windows laptop, Raspberry Pi or an offline field computer.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from heapq import heappop, heappush
from math import hypot, inf
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Boat:
    boat_id: str
    position: Point
    speed_mps: float = 0.4


@dataclass(frozen=True)
class Victim:
    victim_id: str
    position: Point


@dataclass
class BoatPlan:
    boat_id: str
    victim_ids: list[str]
    waypoints: list[Point]
    distance_m: float
    estimated_time_s: float


class GridMap:
    """Occupancy grid used by A*.

    Rectangles are expressed in calibrated water coordinates in metres as
    [x_min, y_min, x_max, y_max].  Obstacles are inflated by safety_margin_m.
    """

    def __init__(
        self,
        width_m: float,
        height_m: float,
        resolution_m: float,
        obstacles: Iterable[Sequence[float]] = (),
        safety_margin_m: float = 0.0,
    ) -> None:
        if min(width_m, height_m, resolution_m) <= 0:
            raise ValueError("Map dimensions and resolution must be positive")
        self.width_m = width_m
        self.height_m = height_m
        self.resolution_m = resolution_m
        self.cols = max(1, round(width_m / resolution_m) + 1)
        self.rows = max(1, round(height_m / resolution_m) + 1)
        self.blocked: set[tuple[int, int]] = set()
        for rectangle in obstacles:
            if len(rectangle) != 4:
                raise ValueError(f"Invalid obstacle rectangle: {rectangle!r}")
            x1, y1, x2, y2 = map(float, rectangle)
            x1, x2 = sorted((x1 - safety_margin_m, x2 + safety_margin_m))
            y1, y2 = sorted((y1 - safety_margin_m, y2 + safety_margin_m))
            for row in range(self.rows):
                for col in range(self.cols):
                    p = self.to_point((col, row))
                    if x1 <= p.x <= x2 and y1 <= p.y <= y2:
                        self.blocked.add((col, row))

    def to_cell(self, point: Point) -> tuple[int, int]:
        col = round(point.x / self.resolution_m)
        row = round(point.y / self.resolution_m)
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            raise ValueError(f"Point outside map: ({point.x:.3f}, {point.y:.3f})")
        return col, row

    def to_point(self, cell: tuple[int, int]) -> Point:
        return Point(cell[0] * self.resolution_m, cell[1] * self.resolution_m)

    def is_free(self, cell: tuple[int, int]) -> bool:
        col, row = cell
        return 0 <= col < self.cols and 0 <= row < self.rows and cell not in self.blocked

    def nearest_free_cell(self, cell: tuple[int, int]) -> tuple[int, int]:
        """Return the closest traversable grid cell to a rounded endpoint."""
        if self.is_free(cell):
            return cell
        for radius in range(1, max(self.cols, self.rows)):
            candidates: list[tuple[int, int]] = []
            for col in range(cell[0] - radius, cell[0] + radius + 1):
                candidates.append((col, cell[1] - radius))
                candidates.append((col, cell[1] + radius))
            for row in range(cell[1] - radius + 1, cell[1] + radius):
                candidates.append((cell[0] - radius, row))
                candidates.append((cell[0] + radius, row))
            free = [candidate for candidate in candidates if self.is_free(candidate)]
            if free:
                return min(
                    free,
                    key=lambda candidate: (
                        (candidate[0] - cell[0]) ** 2 + (candidate[1] - cell[1]) ** 2,
                        candidate[1],
                        candidate[0],
                    ),
                )
        raise ValueError("No free grid cell exists near the route endpoint")

    def astar(self, start: Point, goal: Point) -> tuple[list[Point], float]:
        # A geometrically valid point just outside an obstacle can round into the
        # obstacle's outermost 1 cm grid cell. Snap only that discrete endpoint
        # to its nearest free cell; the returned path still starts/ends at the
        # original measured coordinates.
        start_cell = self.nearest_free_cell(self.to_cell(start))
        goal_cell = self.nearest_free_cell(self.to_cell(goal))
        if start_cell == goal_cell:
            return [start, goal], hypot(goal.x - start.x, goal.y - start.y)

        def heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
            dx, dy = abs(a[0] - b[0]), abs(a[1] - b[1])
            # Octile distance is admissible for an 8-connected grid.
            return (max(dx, dy) + (2**0.5 - 1) * min(dx, dy)) * self.resolution_m

        open_heap: list[tuple[float, int, tuple[int, int]]] = []
        counter = 0
        heappush(open_heap, (heuristic(start_cell, goal_cell), counter, start_cell))
        came_from: dict[tuple[int, int], tuple[int, int]] = {}
        g_score = {start_cell: 0.0}
        closed: set[tuple[int, int]] = set()
        moves = (
            (-1, -1, 2**0.5), (0, -1, 1), (1, -1, 2**0.5),
            (-1, 0, 1),                         (1, 0, 1),
            (-1, 1, 2**0.5),  (0, 1, 1),  (1, 1, 2**0.5),
        )

        while open_heap:
            _, _, current = heappop(open_heap)
            if current in closed:
                continue
            if current == goal_cell:
                cells = [current]
                while cells[-1] in came_from:
                    cells.append(came_from[cells[-1]])
                cells.reverse()
                points = [self.to_point(c) for c in cells]
                points[0], points[-1] = start, goal
                points = simplify_path(points)
                distance = sum(
                    hypot(b.x - a.x, b.y - a.y) for a, b in zip(points, points[1:])
                )
                return points, distance
            closed.add(current)
            for dx, dy, factor in moves:
                neighbor = current[0] + dx, current[1] + dy
                if not self.is_free(neighbor) or neighbor in closed:
                    continue
                # Prevent diagonal corner cutting.
                if dx and dy:
                    if not self.is_free((current[0] + dx, current[1])):
                        continue
                    if not self.is_free((current[0], current[1] + dy)):
                        continue
                tentative = g_score[current] + factor * self.resolution_m
                if tentative < g_score.get(neighbor, inf):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative
                    counter += 1
                    heappush(
                        open_heap,
                        (tentative + heuristic(neighbor, goal_cell), counter, neighbor),
                    )
        raise ValueError("No safe A* path exists between the two points")


def simplify_path(points: Sequence[Point]) -> list[Point]:
    if len(points) <= 2:
        return list(points)
    result = [points[0]]
    previous_direction: tuple[int, int] | None = None
    for index in range(1, len(points)):
        dx = round(points[index].x - points[index - 1].x, 9)
        dy = round(points[index].y - points[index - 1].y, 9)
        direction = (0 if dx == 0 else (1 if dx > 0 else -1), 0 if dy == 0 else (1 if dy > 0 else -1))
        if previous_direction is not None and direction != previous_direction:
            result.append(points[index - 1])
        previous_direction = direction
    result.append(points[-1])
    return result


class RescuePlanner:
    """Exact open-route assignment for up to roughly 12 static victims.

    For every boat and every victim subset, Held-Karp dynamic programming finds
    the shortest open route.  A second dynamic program partitions all victims
    between the boats.  The primary objective is the earliest possible time at
    which the last boat finishes; total boat time is the tie breaker.
    """

    def __init__(self, grid: GridMap, rescue_service_s: float = 3.0) -> None:
        self.grid = grid
        self.rescue_service_s = rescue_service_s

    def plan(self, boats: Sequence[Boat], victims: Sequence[Victim]) -> list[BoatPlan]:
        if not boats:
            raise ValueError("At least one boat is required")
        if len(victims) > 14:
            raise ValueError("Exact planner supports at most 14 victims; split the task or use a heuristic")
        if not victims:
            return [BoatPlan(b.boat_id, [], [], 0.0, 0.0) for b in boats]

        n = len(victims)
        all_mask = (1 << n) - 1
        pair_paths: dict[tuple[int, int], list[Point]] = {}
        pair_distance = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i + 1, n):
                path, distance = self.grid.astar(victims[i].position, victims[j].position)
                pair_paths[i, j] = path
                pair_paths[j, i] = list(reversed(path))
                pair_distance[i][j] = pair_distance[j][i] = distance

        boat_start_paths: list[list[list[Point]]] = []
        boat_start_distance: list[list[float]] = []
        for boat in boats:
            paths, distances = [], []
            for victim in victims:
                path, distance = self.grid.astar(boat.position, victim.position)
                paths.append(path)
                distances.append(distance)
            boat_start_paths.append(paths)
            boat_start_distance.append(distances)

        subset_routes: list[dict[int, tuple[float, tuple[int, ...]]]] = []
        for boat_index, _boat in enumerate(boats):
            dp: dict[tuple[int, int], tuple[float, tuple[int, ...]]] = {}
            for end in range(n):
                dp[1 << end, end] = (boat_start_distance[boat_index][end], (end,))
            for mask in range(1, all_mask + 1):
                for end in range(n):
                    if not mask & (1 << end) or (mask, end) not in dp:
                        continue
                    cost, order = dp[mask, end]
                    remaining = all_mask ^ mask
                    next_index = 0
                    while remaining:
                        if remaining & 1:
                            new_mask = mask | (1 << next_index)
                            candidate = (cost + pair_distance[end][next_index], order + (next_index,))
                            if candidate[0] < dp.get((new_mask, next_index), (inf, ()))[0]:
                                dp[new_mask, next_index] = candidate
                        remaining >>= 1
                        next_index += 1
            routes: dict[int, tuple[float, tuple[int, ...]]] = {0: (0.0, ())}
            for mask in range(1, all_mask + 1):
                best = min((dp[mask, end] for end in range(n) if (mask, end) in dp), key=lambda x: x[0])
                routes[mask] = best
            subset_routes.append(routes)

        @lru_cache(maxsize=None)
        def assign(boat_index: int, remaining: int) -> tuple[float, float, tuple[int, ...]]:
            if boat_index == len(boats):
                return (0.0, 0.0, ()) if remaining == 0 else (inf, inf, ())
            best = (inf, inf, ())
            subset = remaining
            while True:
                distance, _ = subset_routes[boat_index][subset]
                duration = distance / boats[boat_index].speed_mps + self.rescue_service_s * subset.bit_count()
                downstream_max, downstream_total, downstream_masks = assign(boat_index + 1, remaining ^ subset)
                candidate = (max(duration, downstream_max), duration + downstream_total, (subset,) + downstream_masks)
                if candidate[:2] < best[:2]:
                    best = candidate
                if subset == 0:
                    break
                subset = (subset - 1) & remaining
            return best

        _, _, masks = assign(0, all_mask)
        plans: list[BoatPlan] = []
        for boat_index, (boat, mask) in enumerate(zip(boats, masks)):
            distance, order = subset_routes[boat_index][mask]
            waypoints: list[Point] = []
            previous: int | None = None
            for victim_index in order:
                segment = (
                    boat_start_paths[boat_index][victim_index]
                    if previous is None
                    else pair_paths[previous, victim_index]
                )
                if waypoints and segment:
                    segment = segment[1:]
                waypoints.extend(segment)
                previous = victim_index
            plans.append(
                BoatPlan(
                    boat_id=boat.boat_id,
                    victim_ids=[victims[i].victim_id for i in order],
                    waypoints=waypoints,
                    distance_m=distance,
                    estimated_time_s=distance / boat.speed_mps + self.rescue_service_s * len(order),
                )
            )
        return plans


def point_to_dict(point: Point) -> dict[str, float]:
    return {"x": round(point.x, 4), "y": round(point.y, 4)}
