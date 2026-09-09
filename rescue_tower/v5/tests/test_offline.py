"""不连接硬件也能运行的基础测试。"""

import unittest
import threading

import config
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
        # 起点和两个目标都选在禁航区外（v5 起 (20,20) 已落在禁航区内）。
        route = PathPlanner().plan_first_target(
            {"id": 0, "x": 100, "y": 100},
            [{"id": 1, "x": 520, "y": 550}, {"id": 2, "x": 150, "y": 130}],
        )
        self.assertEqual(route.target_id, "2")
        self.assertGreater(route.distance_mm, 0)
        self.assertLess(distance(route.waypoints_mm[0], route.waypoints_mm[-1]), 200)

    def test_planner_rejects_start_inside_no_nav_zone(self):
        # 船一旦进入禁航区，规划直接报错；mission.py 会把异常转成 error 并停车。
        with self.assertRaises(ValueError):
            PathPlanner().plan_first_target(
                {"id": 0, "x": 20, "y": 20},
                [{"id": 1, "x": 520, "y": 550}],
            )

    def test_planner_detours_around_central_no_nav_zone(self):
        # (100,470)->(530,300) 的直线会穿过中央禁航区 (175,210)-(430,390)，
        # 规划路径必须绕行：总长严格大于直线距离，且航点不落入任何禁航区
        # （禁航区外扩 SAFETY_MARGIN_MM，与 GridMap 的膨胀规则一致）。
        route = PathPlanner().plan_first_target(
            {"id": 0, "x": 100, "y": 470},
            [{"id": 1, "x": 530, "y": 300}],
        )
        straight = distance((100, 470), (530, 300))
        self.assertGreater(route.distance_mm, straight)
        margin = config.SAFETY_MARGIN_MM
        for x, y in route.waypoints_mm:
            for x1, y1, x2, y2 in config.OBSTACLES_MM:
                if x1 - margin <= x <= x2 + margin and y1 - margin <= y <= y2 + margin:
                    self.fail(f"航点 ({x}, {y}) 落入禁航区 {(x1, y1, x2, y2)}")

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
