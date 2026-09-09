"""ESP32 网络通信及水位、视觉接收。"""

from __future__ import annotations

import json
import re
import socket
import statistics
import threading
import time
import urllib.request

import config
from core.state import SystemState


def http_command(ip: str, command: str, expect_body: str | None = None) -> tuple[bool, int | None, str | None]:
    """向 ESP32 发一个 HTTP 命令，返回成功、延迟和错误。

    expect_body: 期望的应答体。单字母命令（/F /B /L /R /S）回包是命令本身；
    自动导航 /M?A=..&B=.. 固定回 "M"，此时传 expect_body="M"。
    传 None 表示只检查 HTTP 成功（升降台返回整个网页）。
    """
    started = time.monotonic()
    path = command.lstrip("/")  # command 带不带斜杠都行，避免拼出 //M
    try:
        with urllib.request.urlopen(f"http://{ip}:{config.DEVICE_HTTP_PORT}/{path}", timeout=config.DEVICE_TIMEOUT_S) as response:
            body = response.read(32).decode("utf-8", "ignore").strip()
        latency = round((time.monotonic() - started) * 1000)
        if expect_body is not None and body != expect_body:
            return False, latency, f"ESP32 返回异常：{body}"
        return True, latency, None
    except Exception as exc:
        return False, None, str(exc)


class Boat:
    VALID = {"F", "B", "L", "R", "S"}

    def __init__(self, state: SystemState) -> None:
        self.state = state
        self.last_command = "S"

    def send(self, command: str) -> bool:
        if command not in self.VALID:
            raise ValueError(f"无效小船命令：{command}")
        ok, latency, error = http_command(config.BOAT_IP, command, expect_body=command)
        self.last_command = command
        self.state.update("control", command=command, ok=ok, latency_ms=latency, error=error)
        return ok

    def throttle(self, a: int, b: int) -> bool:
        """自动导航连续油门：GET /M?A=..&B=..（-100..100，正=前进）。固件回包固定为 M。"""
        ok, latency, error = http_command(config.BOAT_IP, f"M?A={int(a)}&B={int(b)}", expect_body="M")
        self.last_command = f"A={int(a)} B={int(b)}"
        self.state.update("control", command=self.last_command, ok=ok, latency_ms=latency, error=error)
        return ok

    def stop(self) -> bool:
        return self.send("S")


class Lift:
    def __init__(self, state: SystemState) -> None:
        self.state = state

    def send(self, command: str) -> bool:
        if command not in {"U", "D"}:
            raise ValueError(f"无效升降台命令：{command}")
        ok, latency, error = http_command(config.LIFT_IP, command)
        message = f"延迟 {latency}ms" if ok else (error or "无响应")
        self.state.update("lift", command=command, ok=ok, message=message)
        return ok


class VisionReceiver(threading.Thread):
    daemon = True

    def __init__(self, state: SystemState, stop_event: threading.Event) -> None:
        super().__init__(name="vision-udp")
        self.state, self.stop_event = state, stop_event
        self.person_tracks: dict[int, tuple[float, float, float]] = {}
        self.next_person_id = 1

    def normalize(self, data: dict) -> tuple[list[dict], list[dict], dict]:
        """兼容 666.py 的原始结构，并给没有 ID 的人员做简单位置跟踪。"""
        raw_boats = data.get("boats") or {}
        items = raw_boats.items() if isinstance(raw_boats, dict) else enumerate(raw_boats)
        boats = []
        for key, item in items:
            if not isinstance(item, dict) or item.get("inside_field", True) is False:
                continue
            if item.get("age_sec") is not None and item["age_sec"] > config.VISION_TIMEOUT_S:
                continue
            boats.append({
                "id": int(item.get("id", key)), "x": float(item["x"]), "y": float(item["y"]),
                "angle": item.get("angle", item.get("angle_deg")),
            })

        now = time.monotonic()
        available = set(self.person_tracks)
        persons = []
        for item in data.get("persons") or []:
            if not isinstance(item, dict) or item.get("inside_field", True) is False:
                continue
            if item.get("age_sec") is not None and item["age_sec"] > config.VISION_TIMEOUT_S:
                continue
            x, y = float(item["x"]), float(item["y"])
            if item.get("id") is not None:
                person_id = int(item["id"])
            else:
                candidates = [(pid, (px - x) ** 2 + (py - y) ** 2) for pid, (px, py, _) in self.person_tracks.items() if pid in available]
                person_id, square_distance = min(candidates, key=lambda pair: pair[1]) if candidates else (None, float("inf"))
                if person_id is None or square_distance > 80.0 ** 2:
                    person_id = self.next_person_id
                    self.next_person_id += 1
            available.discard(person_id)
            self.person_tracks[person_id] = (x, y, now)
            persons.append({"id": person_id, "x": x, "y": y, "confidence": float(item.get("confidence", item.get("conf", 0)))})
        self.person_tracks = {pid: value for pid, value in self.person_tracks.items() if now - value[2] <= 2.0}

        homography = data.get("homography") or {}
        active_ids = homography.get("active_reference_ids", [])
        references = data.get("references") or {
            "visible": len(active_ids), "inliers": homography.get("inliers", 0), "ids": active_ids,
        }
        return boats, persons, references

    def run(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((config.VISION_HOST, config.VISION_PORT))
        sock.settimeout(0.5)
        while not self.stop_event.is_set():
            try:
                payload, _ = sock.recvfrom(65535)
                data = json.loads(payload.decode("utf-8"))
                if data.get("type") not in (None, "vision"):
                    continue
                boats, persons, references = self.normalize(data)
                self.state.update(
                    "vision", received_at=time.monotonic(),
                    coordinate_ready=bool(data.get("vision_ok_for_control", data.get("coordinate_ready", False))),
                    boats=boats, persons=persons,
                    performance=data.get("performance", {}), references=references,
                )
            except socket.timeout:
                continue
            except Exception as exc:
                self.state.event(f"视觉数据格式错误：{exc}")
        sock.close()


class WaterReceiver(threading.Thread):
    """接收 Water:123 格式；可处理 TCP 粘包和拆包。"""
    daemon = True
    PATTERN = re.compile(r"Water\s*:\s*(-?\d+)", re.I)

    def __init__(self, state: SystemState, flood_event: threading.Event, stop_event: threading.Event) -> None:
        super().__init__(name="water-tcp")
        self.state, self.flood_event, self.stop_event = state, flood_event, stop_event
        self.samples: list[int] = []
        self.high_count = 0

    def _accept_value(self, value: int) -> None:
        if len(self.samples) < config.WATER_BASELINE_SAMPLES:
            self.samples.append(value)
        baseline = statistics.median(self.samples) if self.samples else value
        rise = value - baseline
        high = rise >= config.WATER_RISE_THRESHOLD
        if config.WATER_ABSOLUTE_THRESHOLD is not None:
            high = high or value >= config.WATER_ABSOLUTE_THRESHOLD
        self.high_count = self.high_count + 1 if high else 0
        triggered = self.high_count >= config.WATER_TRIGGER_COUNT
        self.state.update("water", value=value, baseline=baseline, rise=rise, triggered=triggered, online=True)
        if triggered:
            self.flood_event.set()

    def run(self) -> None:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((config.WATER_LISTEN_HOST, config.WATER_PORT))
        server.listen(2)
        server.settimeout(0.5)
        while not self.stop_event.is_set():
            try:
                client, address = server.accept()
                client.settimeout(1.5)
                self.state.event(f"水位传感器已连接：{address[0]}")
                buffer = ""
                with client:
                    while not self.stop_event.is_set():
                        try:
                            chunk = client.recv(1024)
                            if not chunk:
                                break
                            buffer += chunk.decode("utf-8", "ignore")
                            # v2 固件以换行分隔；同时兼容旧固件连续发送的 Water:1Water:2。
                            while "\n" in buffer:
                                line, buffer = buffer.split("\n", 1)
                                match = self.PATTERN.search(line)
                                if match:
                                    self._accept_value(int(match.group(1)))
                            starts = [match.start() for match in re.finditer(r"Water\s*:", buffer, re.I)]
                            while len(starts) >= 2:
                                message, buffer = buffer[:starts[1]], buffer[starts[1]:]
                                match = self.PATTERN.search(message)
                                if match:
                                    self._accept_value(int(match.group(1)))
                                starts = [match.start() for match in re.finditer(r"Water\s*:", buffer, re.I)]
                            buffer = buffer[-128:]
                        except socket.timeout:
                            continue
            except socket.timeout:
                continue
            except Exception as exc:
                self.state.event(f"水位接收错误：{exc}")
            finally:
                self.state.update("water", online=False)
        server.close()
