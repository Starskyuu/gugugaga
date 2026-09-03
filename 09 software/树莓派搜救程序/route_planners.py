"""Scalable route planning helpers for Raspberry Pi deployment."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot, inf
from typing import Sequence

from rescue_core import Boat, BoatPlan, Point, Victim


@dataclass(frozen=True)
class Rectangle:
    x_min: float
    y_min: float
    x_max: float
    y_max: float

    def contains(self, point: Point) -> bool:
        return self.x_min < point.x < self.x_max and self.y_min < point.y < self.y_max


class RectangleVisibilityMap:
    """Shortest paths around one axis-aligned rectangular safety zone."""

    def __init__(self, rectangle: Rectangle) -> None:
        self.rectangle = rectangle

    def segment_crosses_interior(self, a: Point, b: Point) -> bool:
        low, high = 0.0, 1.0
        for origin, delta, minimum, maximum in (
            (a.x, b.x - a.x, self.rectangle.x_min, self.rectangle.x_max),
            (a.y, b.y - a.y, self.rectangle.y_min, self.rectangle.y_max),
        ):
            if abs(delta) < 1e-12:
                if origin <= minimum or origin >= maximum:
                    return False
                continue
            first, second = (minimum - origin) / delta, (maximum - origin) / delta
            if first > second:
                first, second = second, first
            low, high = max(low, first), min(high, second)
            if low >= high - 1e-12:
                return False
        return high > 0.0 and low < 1.0

    def path(self, start: Point, goal: Point) -> tuple[list[Point], float]:
        if self.rectangle.contains(start) or self.rectangle.contains(goal):
            raise ValueError("Path endpoint is inside the base-station safety zone")
        direct = hypot(goal.x - start.x, goal.y - start.y)
        if not self.segment_crosses_interior(start, goal):
            return [start, goal], direct
        r = self.rectangle
        nodes = [
            start,
            goal,
            Point(r.x_min, r.y_min),
            Point(r.x_max, r.y_min),
            Point(r.x_max, r.y_max),
            Point(r.x_min, r.y_max),
        ]
        distances = [inf] * len(nodes)
        previous = [-1] * len(nodes)
        used = [False] * len(nodes)
        distances[0] = 0.0
        for _ in nodes:
            current = min((i for i in range(len(nodes)) if not used[i]), key=distances.__getitem__, default=-1)
            if current < 0 or distances[current] == inf:
                break
            used[current] = True
            for neighbor in range(len(nodes)):
                if current == neighbor or self.segment_crosses_interior(nodes[current], nodes[neighbor]):
                    continue
                candidate = distances[current] + hypot(
                    nodes[neighbor].x - nodes[current].x,
                    nodes[neighbor].y - nodes[current].y,
                )
                if candidate < distances[neighbor]:
                    distances[neighbor] = candidate
                    previous[neighbor] = current
        if distances[1] == inf:
            raise ValueError("No path around base-station safety zone")
        indices, current = [], 1
        while current >= 0:
            indices.append(current)
            if current == 0:
                break
            current = previous[current]
        indices.reverse()
        return [nodes[i] for i in indices], distances[1]


def balanced_greedy_plan(
    boats: Sequence[Boat],
    victims: Sequence[Victim],
    visibility_map: RectangleVisibilityMap,
    rescue_service_s: float = 3.0,
) -> list[BoatPlan]:
    """Balance load while repeatedly selecting the cheapest next visit.

    Assignment uses cheap straight-line estimates and calculates an exact
    obstacle-avoiding leg only after a target has been selected. Runtime is
    O(number_of_victims^2), practical for roughly 1000 static targets on a Pi.
    """
    if not boats:
        raise ValueError("At least one boat is required")
    remaining = set(range(len(victims)))
    positions = [boat.position for boat in boats]
    distances = [0.0] * len(boats)
    durations = [0.0] * len(boats)
    orders: list[list[int]] = [[] for _ in boats]
    while remaining:
        best: tuple[float, float, int, int] | None = None
        # Extend the route that is currently expected to finish first. Using
        # Euclidean distance here makes large frames fast; the selected leg is
        # then replaced by its actual safe path around the base station.
        boat_index = min(range(len(boats)), key=lambda index: (durations[index], index))
        boat = boats[boat_index]
        for victim_index in remaining:
            target = victims[victim_index].position
            estimate = hypot(target.x - positions[boat_index].x, target.y - positions[boat_index].y)
            finish_time = durations[boat_index] + estimate / boat.speed_mps + rescue_service_s
            candidate = finish_time, estimate, boat_index, victim_index
            if best is None or candidate < best:
                best = candidate
        assert best is not None
        _, _, boat_index, victim_index = best
        _, leg_distance = visibility_map.path(positions[boat_index], victims[victim_index].position)
        orders[boat_index].append(victim_index)
        distances[boat_index] += leg_distance
        durations[boat_index] += leg_distance / boats[boat_index].speed_mps + rescue_service_s
        positions[boat_index] = victims[victim_index].position
        remaining.remove(victim_index)

    plans: list[BoatPlan] = []
    for boat_index, boat in enumerate(boats):
        waypoints: list[Point] = []
        current = boat.position
        for victim_index in orders[boat_index]:
            segment, _ = visibility_map.path(current, victims[victim_index].position)
            if waypoints:
                segment = segment[1:]
            waypoints.extend(segment)
            current = victims[victim_index].position
        plans.append(
            BoatPlan(
                boat_id=boat.boat_id,
                victim_ids=[victims[i].victim_id for i in orders[boat_index]],
                waypoints=waypoints,
                distance_m=distances[boat_index],
                estimated_time_s=durations[boat_index],
            )
        )
    return plans
