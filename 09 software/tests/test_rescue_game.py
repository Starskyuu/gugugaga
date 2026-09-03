from __future__ import annotations

import socket
import unittest

from rescue_game import choose_port
from rescue_game_ui import GAME_HTML


class RescueGameTests(unittest.TestCase):
    def test_game_contains_required_dimensions_and_controls(self) -> None:
        self.assertIn("const FIELD=60", GAME_HTML)
        self.assertIn("BASE={x:19,y:22.5,w:22,h:15}", GAME_HTML)
        self.assertIn('max="1000"', GAME_HTML)
        self.assertIn("开始搜救", GAME_HTML)
        self.assertIn("点击添加", GAME_HTML)
        self.assertIn("均衡最近邻", GAME_HTML)
        self.assertIn("分区最近邻", GAME_HTML)
        self.assertIn("精确四船动态规划", GAME_HTML)

    def test_auto_port_is_bindable(self) -> None:
        port = choose_port(0)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.bind(("127.0.0.1", port))


if __name__ == "__main__":
    unittest.main()
