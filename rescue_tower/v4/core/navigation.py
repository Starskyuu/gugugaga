"""导航：把路径点换算成小船运动指令。

v4 起自动航行使用双环 PID 连续油门（core/nav_control.py），
通过 /M?A=..&B=.. 下发；开关式 F/L/R/S 指令保留给手动遥控和调试。
"""

from __future__ import annotations

import math

import config
from core.nav_control import NavConfig, Navigator


def normalize_angle(angle: float) -> float:
    return (angle + 180.0) % 360.0 - 180.0


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(b[0] - a[0], b[1] - a[1])


def desired_heading(start: tuple[float, float], target: tuple[float, float]) -> float:
    # 严格沿用 666.py 的世界坐标约定：+Y 为 0°，+X 为 90°。
    return math.degrees(math.atan2(target[0] - start[0], target[1] - start[1])) % 360.0


def choose_command(position: tuple[float, float], angle: float, target: tuple[float, float]) -> tuple[str, float]:
    """开关式转向（手动遥控/备用），v3 逻辑原样保留。"""
    error = normalize_angle(desired_heading(position, target) - angle)
    if abs(error) <= config.TURN_THRESHOLD_DEG:
        return "F", error
    right = error > 0
    if config.TURN_SIGN < 0:
        right = not right
    return ("R" if right else "L"), error


# ============================================================
# PID 双环导航（v4 新增）
# ============================================================

def build_nav_config() -> NavConfig:
    """用 config.py 的参数组装 PID 配置；v4 全程使用毫米。"""
    cfg = NavConfig()
    cfg.accept_radius = config.PID_ACCEPT_RADIUS_MM
    cfg.arrive_hysteresis = config.PID_ARRIVE_HYSTERESIS_MM
    cfg.max_speed = config.PID_MAX_SPEED
    cfg.max_turn = config.PID_MAX_TURN
    cfg.min_cruise = config.PID_MIN_CRUISE
    cfg.min_spin = config.PID_MIN_SPIN
    cfg.slow_zone = config.PID_SLOW_ZONE_MM
    cfg.min_approach = config.PID_MIN_APPROACH
    cfg.heading_deadband = config.PID_HEADING_DEADBAND_DEG
    cfg.turn_sign = config.PID_TURN_SIGN
    cfg.kp_h = config.PID_KP_H
    cfg.ki_h = config.PID_KI_H
    cfg.kd_h = config.PID_KD_H
    cfg.kp_s = config.PID_KP_S
    cfg.ki_s = config.PID_KI_S
    cfg.kd_s = config.PID_KD_S
    cfg.i_max_h = config.PID_I_MAX_H
    cfg.i_max_s = config.PID_I_MAX_S
    return cfg


class PidPilot:
    """双环 PID 驾驶员：外环距离->油门，内环航向->差速。

    世界坐标沿用 666.py（+Y 为 0°，顺时针为正，毫米）。
    nav_control.py 要求 0° 指向 +X、逆时针为正（atan2 约定），
    所以喂给 Navigator 之前先换算：heading_pid = 90 - heading_666。
    位置坐标两套约定一致，直接透传。
    """

    def __init__(self, cfg: NavConfig | None = None) -> None:
        self.nav = Navigator(cfg or build_nav_config())

    @staticmethod
    def to_pid_heading(angle_666: float) -> float:
        """666.py 航向（+Y 为 0°，顺时针为正）-> PID 航向（+X 为 0°，逆时针为正）。"""
        return normalize_angle(90.0 - angle_666)

    def update(self, x: float, y: float, angle_666: float, tx: float, ty: float, dt: float):
        """返回 (motor_a, motor_b, status)，status 为 "run" / "arrived"。"""
        return self.nav.update(x, y, self.to_pid_heading(angle_666), tx, ty, dt)

    def reset(self) -> None:
        self.nav.reset()
