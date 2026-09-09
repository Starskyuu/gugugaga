"""将路径点转换为旧版小船 ESP32 的 F/L/R/S 指令。"""

from __future__ import annotations

import math

import config


def normalize_angle(angle: float) -> float:
    return (angle + 180.0) % 360.0 - 180.0


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def desired_heading(start: tuple[float, float], target: tuple[float, float]) -> float:
    # 严格沿用 666.py 的世界坐标约定：+Y 为 0°，+X 为 90°。
    return math.degrees(math.atan2(target[0] - start[0], target[1] - start[1])) % 360.0


def choose_command(position: tuple[float, float], angle: float, target: tuple[float, float]) -> tuple[str, float]:
    error = normalize_angle(desired_heading(position, target) - angle)
    if abs(error) <= config.TURN_THRESHOLD_DEG:
        return "F", error
    right = error > 0
    if config.TURN_SIGN < 0:
        right = not right
    return ("R" if right else "L"), error
