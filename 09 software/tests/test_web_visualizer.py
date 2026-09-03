from __future__ import annotations

import json
import unittest
from urllib.request import Request, urlopen

from web_visualizer import start_visualizer


class FakeStation:
    def __init__(self) -> None:
        self.actions: list[str] = []

    def visualization_snapshot(self) -> dict:
        return {
            "map": {"width_m": 6, "height_m": 4, "resolution_m": 0.1, "obstacles": []},
            "boats": [], "victims": [], "plans": [], "path_version": 0, "stopping": False,
        }

    def request_replan(self) -> None:
        self.actions.append("replan")

    def reset_mission(self) -> None:
        self.actions.append("reset")

    def emergency_stop(self, _reason: str) -> None:
        self.actions.append("stop")

    def start_demo(self) -> bool:
        self.actions.append("demo")
        return True


class WebVisualizerTests(unittest.TestCase):
    def test_dashboard_and_api(self) -> None:
        station = FakeStation()
        server = start_visualizer(station, "127.0.0.1", 0)
        port = server.server_address[1]
        try:
            with urlopen(f"http://127.0.0.1:{port}/", timeout=2) as response:
                html = response.read().decode("utf-8")
            self.assertIn("四船协同搜救实时态势", html)
            with urlopen(f"http://127.0.0.1:{port}/api/state", timeout=2) as response:
                state = json.loads(response.read())
            self.assertEqual(state["path_version"], 0)
            request = Request(f"http://127.0.0.1:{port}/api/replan", method="POST")
            with urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 200)
            self.assertEqual(station.actions, ["replan"])
            request = Request(f"http://127.0.0.1:{port}/api/start-demo", method="POST")
            with urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 200)
            self.assertEqual(station.actions, ["replan", "demo"])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
