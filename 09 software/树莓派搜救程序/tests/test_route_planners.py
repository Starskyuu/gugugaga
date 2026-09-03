import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rescue_core import Boat, Point, Victim
from route_planners import Rectangle, RectangleVisibilityMap, balanced_greedy_plan


class RoutePlannerTests(unittest.TestCase):
    def test_visibility_path_avoids_base_interior(self):
        visibility = RectangleVisibilityMap(Rectangle(0.2, 0.2, 0.4, 0.4))
        path, distance = visibility.path(Point(0.1, 0.3), Point(0.5, 0.3))
        self.assertGreater(len(path), 2)
        self.assertGreater(distance, 0.4)
        for start, goal in zip(path, path[1:]):
            self.assertFalse(visibility.segment_crosses_interior(start, goal))

    def test_balanced_plan_assigns_each_target_once(self):
        visibility = RectangleVisibilityMap(Rectangle(0.2, 0.2, 0.4, 0.4))
        boats = [Boat("a", Point(0.1, 0.1), 0.1), Boat("b", Point(0.5, 0.5), 0.1)]
        victims = [Victim(str(i), Point(0.05 + i * 0.05, 0.55)) for i in range(8)]
        plans = balanced_greedy_plan(boats, victims, visibility)
        assigned = [victim for plan in plans for victim in plan.victim_ids]
        self.assertCountEqual(assigned, [str(i) for i in range(8)])


if __name__ == "__main__":
    unittest.main()
