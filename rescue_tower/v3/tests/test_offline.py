"""不连接硬件也能运行的基础测试。"""

import unittest
import threading

from core.devices import VisionReceiver
from core.navigation import choose_command, desired_heading, distance
from core.planner import PathPlanner
from core.state import SystemState


class OfflineTest(unittest.TestCase):
    def test_heading_and_command(self):
        self.assertAlmostEqual(desired_heading((100, 100), (100, 200)), 0)
        self.assertEqual(choose_command((100, 100), 0, (100, 200))[0], "F")
        self.assertEqual(choose_command((100, 100), 0, (200, 100))[0], "R")

    def test_real_666_payload_is_normalized(self):
        receiver = VisionReceiver(SystemState(), threading.Event())
        payload = {
            "boats": {"0": {"x": 40, "y": 50, "angle_deg": 90, "inside_field": True, "age_sec": 0.1}},
            "persons": [{"x": 200, "y": 300, "confidence": 0.9, "inside_field": True, "age_sec": 0.1}],
            "homography": {"active_reference_ids": [10, 11, 12, 13], "inliers": 4},
        }
        boats, persons, references = receiver.normalize(payload)
        self.assertEqual(boats[0]["angle"], 90)
        self.assertEqual(persons[0]["id"], 1)
        self.assertEqual(references["visible"], 4)

    def test_planner_selects_near_target(self):
        route = PathPlanner().plan_first_target(
            {"id": 0, "x": 20, "y": 20},
            [{"id": 1, "x": 550, "y": 550}, {"id": 2, "x": 100, "y": 100}],
        )
        self.assertEqual(route.target_id, "2")
        self.assertGreater(route.distance_mm, 0)
        self.assertLess(distance(route.waypoints_mm[0], route.waypoints_mm[-1]), 200)


if __name__ == "__main__":
    unittest.main()
