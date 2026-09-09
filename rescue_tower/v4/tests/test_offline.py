"""不连接硬件也能运行的基础测试。"""

import unittest
import threading

from core.devices import VisionReceiver
from core.navigation import PidPilot, build_nav_config, choose_command, desired_heading, distance
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

    def test_pid_heading_conversion(self):
        # 666.py 约定（+Y 为 0°，顺时针为正）-> PID 约定（+X 为 0°，逆时针为正）。
        cases = {0.0: 90.0, 90.0: 0.0, 180.0: -90.0, 270.0: -180.0, 45.0: 45.0, -45.0: 135.0}
        for angle_666, expected in cases.items():
            self.assertAlmostEqual(PidPilot.to_pid_heading(angle_666), expected)

    def test_pilot_goes_straight_then_turns_right(self):
        pilot = PidPilot()
        # 船在原点，航向 666 的 0°（朝 +Y），目标在正前方 300mm：无差速、前进。
        a, b, status = pilot.update(0.0, 0.0, 0.0, 0.0, 300.0, 0.2)
        self.assertEqual(status, "run")
        self.assertAlmostEqual(a, b)
        self.assertGreater(a, 10.0)
        # 目标在正右方（+X）：a > b（右电机慢）-> 右转。
        a, b, status = pilot.update(0.0, 0.0, 0.0, 300.0, 0.0, 0.2)
        self.assertEqual(status, "run")
        self.assertGreater(a, b)

    def test_pilot_arrives_and_stops(self):
        pilot = PidPilot()
        a, b, status = pilot.update(0.0, 0.0, 0.0, 20.0, 20.0, 0.2)
        self.assertEqual(status, "arrived")
        self.assertEqual((a, b), (0.0, 0.0))

    def test_pid_config_units_are_millimeters(self):
        cfg = build_nav_config()
        self.assertLess(cfg.accept_radius, 100.0)  # 毫米级，不可能是默认的 0.3 米
        self.assertLess(cfg.slow_zone, 1000.0)
        self.assertLess(cfg.kp_s, 0.1)             # 每毫米，而不是每米


if __name__ == "__main__":
    unittest.main()
