from __future__ import annotations

import unittest

from dynamic_simulator import SimBoat


class FakeConnection:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    def send(self, message: dict) -> None:
        self.messages.append(message)


class DynamicSimulatorTests(unittest.TestCase):
    def test_boat_moves_and_reports_rescue(self) -> None:
        boat = SimBoat("boat_1", 0.0, 0.0, 0.0, 1.0)
        connection = FakeConnection()
        boat.connection = connection  # type: ignore[assignment]
        boat.waypoints = [{"x": 1.0, "y": 0.0}]
        boat.targets = [{"id": "person_1", "x": 1.0, "y": 0.0}]
        boat.step(0.5, rescue_radius_m=0.1)
        self.assertAlmostEqual(boat.x, 0.5)
        boat.step(0.5, rescue_radius_m=0.1)
        self.assertAlmostEqual(boat.x, 1.0)
        self.assertTrue(any(m.get("type") == "RESCUED" for m in connection.messages))


if __name__ == "__main__":
    unittest.main()

