import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pi_rescue_service import PiRescueService


class PiRescueServiceTests(unittest.TestCase):
    def setUp(self):
        config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
        self.service = PiRescueService(config)

    @staticmethod
    def frame(count):
        boats = [
            {"id": "boat_1", "x": 24, "y": 27},
            {"id": "boat_2", "x": 24, "y": 33},
            {"id": "boat_3", "x": 36, "y": 27},
            {"id": "boat_4", "x": 36, "y": 33},
        ]
        people = []
        candidates = [
            (5 + (i * 7) % 50, 5 + (i * 11) % 50)
            for i in range(count * 2 + 4)
        ]
        for x, y in candidates:
            if 16.5 <= x <= 43.5 and 20 <= y <= 40:
                continue
            people.append({"id": f"person_{len(people) + 1}", "x": x, "y": y})
            if len(people) == count:
                break
        return {"type": "VISION_FRAME", "frame_id": 1, "boats": boats, "people": people}

    def plan_frame(self, count):
        self.service.accept_frame(self.frame(count))
        boats = list(self.service.boats.values())
        victims = list(self.service.victims.values())
        plans, algorithm = self.service.compute_plans(boats, victims)
        assigned = [victim for plan in plans for victim in plan.victim_ids]
        return plans, algorithm, assigned

    def test_exact_mode_assigns_every_target_once(self):
        plans, algorithm, assigned = self.plan_frame(6)
        self.assertEqual(algorithm, "exact_dp_astar")
        self.assertEqual(len(assigned), 6)
        self.assertEqual(len(set(assigned)), 6)
        self.assertTrue(all(plan.waypoints for plan in plans))

    def test_large_input_uses_scalable_mode(self):
        _, algorithm, assigned = self.plan_frame(20)
        self.assertEqual(algorithm, "balanced_greedy_visibility")
        self.assertEqual(len(assigned), 20)
        self.assertEqual(len(set(assigned)), 20)

    def test_empty_target_frame_produces_idle_routes(self):
        self.service.accept_frame(self.frame(0))
        plans, algorithm = self.service.compute_plans(list(self.service.boats.values()), [])
        self.assertEqual(algorithm, "idle")
        self.assertTrue(all(not plan.victim_ids and plan.distance_m == 0 for plan in plans))

    def test_output_contains_target_coordinates(self):
        plans, algorithm, _ = self.plan_frame(4)
        summary = self.service._build_plan_packet(plans, algorithm, 1.25)
        targets = [target for route in summary["routes"] for target in route["targets"]]
        self.assertEqual(len(targets), 4)
        self.assertTrue(all({"id", "x", "y"} <= set(target) for target in targets))

    def test_target_just_outside_safety_zone_survives_grid_rounding(self):
        frame = self.frame(0)
        frame["people"] = [{"id": "edge_person", "x": 30.0, "y": 40.2}]
        self.service.accept_frame(frame)
        plans, algorithm = self.service.compute_plans(
            list(self.service.boats.values()), list(self.service.victims.values())
        )
        assigned = [victim for plan in plans for victim in plan.victim_ids]
        self.assertEqual(algorithm, "exact_dp_astar")
        self.assertEqual(assigned, ["edge_person"])


if __name__ == "__main__":
    unittest.main()
