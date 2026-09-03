from __future__ import annotations

import socket
import unittest

from start_local_demo import find_free_port


class LocalDemoTests(unittest.TestCase):
    def test_selects_distinct_bindable_ports(self) -> None:
        selected: set[int] = set()
        tcp_port = find_free_port(socket.SOCK_STREAM, selected)
        selected.add(tcp_port)
        udp_port = find_free_port(socket.SOCK_DGRAM, selected)
        self.assertNotEqual(tcp_port, udp_port)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp:
            tcp.bind(("127.0.0.1", tcp_port))
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
            udp.bind(("127.0.0.1", udp_port))


if __name__ == "__main__":
    unittest.main()

