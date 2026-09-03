from __future__ import annotations

import unittest

from rescue_core import Boat, GridMap, Point, RescuePlanner, Victim


class GridMapTests(unittest.TestCase):
    def test_astar_avoids_obstacle(self) -> None:
        grid = GridMap(4, 3, 0.1, obstacles=[[1.8, 0.0, 2.2, 2.2]], safety_margin_m=0.0)
        path, distance = grid.astar(Point(0.5, 0.5), Point(3.5, 0.5))
        self.assertGreater(distance, 3.0)
        self.assertTrue(all(not (1.8 <= p.x <= 2.2 and 0.0 <= p.y <= 2.2) for p in path))

    def test_unreachable_path_raises(self) -> None:
        grid = GridMap(2, 2, 0.1, obstacles=[[0.9, 0.0, 1.1, 2.0]])
        with self.assertRaises(ValueError):
            grid.astar(Point(0.2, 1.0), Point(1.8, 1.0))


class PlannerTests(unittest.TestCase):
    def test_assigns_each_victim_exactly_once(self) -> None:
        grid = GridMap(6, 4, 0.1)
        boats = [
            Boat("boat_1", Point(0.2, 0.2), 0.4),
            Boat("boat_2", Point(5.8, 3.8), 0.4),
        ]
        victims = [
            Victim("p1", Point(0.8, 0.8)),
            Victim("p2", Point(1.2, 1.0)),
            Victim("p3", Point(5.0, 3.0)),
            Victim("p4", Point(4.6, 3.2)),
        ]
        plans = RescuePlanner(grid).plan(boats, victims)
        assigned = [victim_id for plan in plans for victim_id in plan.victim_ids]
        self.assertEqual(sorted(assigned), ["p1", "p2", "p3", "p4"])
        self.assertEqual(len(assigned), len(set(assigned)))

    def test_ten_victims_four_boats(self) -> None:
        grid = GridMap(6, 4, 0.2, obstacles=[[2.8, 1.4, 3.2, 2.6]], safety_margin_m=0.1)
        boats = [
            Boat("boat_1", Point(0.4, 0.4)), Boat("boat_2", Point(0.4, 3.6)),
            Boat("boat_3", Point(5.6, 0.4)), Boat("boat_4", Point(5.6, 3.6)),
        ]
        coords = [(1.1, 0.9), (2.0, 0.7), (3.1, 1.0), (4.8, 0.8), (1.2, 2.0),
                  (2.6, 2.1), (4.6, 2.0), (1.0, 3.2), (3.2, 3.3), (5.0, 3.1)]
        victims = [Victim(f"person_{i+1}", Point(*xy)) for i, xy in enumerate(coords)]
        plans = RescuePlanner(grid).plan(boats, victims)
        self.assertEqual(sum(len(plan.victim_ids) for plan in plans), 10)
        self.assertTrue(all(plan.estimated_time_s >= 0 for plan in plans))


if __name__ == "__main__":
    unittest.main()

