# -*- coding: utf-8 -*-
# ============================================================
# sim_pid.py —— 600mm 场地运动学仿真（下水前先在这里调 PID 参数）
#
# 运行（在 v4 目录下）：python tests/sim_pid.py
#   装了 matplotlib 会弹出轨迹图；没装只看文字结果。
#
# 与 PID 包原版 sim_test.py 的差别：
#   - 单位换成毫米，参数直接读 config.py 的 PID 块（调好即用）；
#   - 航向用 666.py 约定（+Y 为 0°，顺时针为正）跟踪，
#     并让测量值经过 PidPilot 的换算，完整验证换算正确性。
# ============================================================

import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
from core.navigation import PidPilot, build_nav_config  # noqa: E402


# ============================================================
# 船模动力学参数（按你的船实测改）
# ============================================================

V_MAX_MM_S = 120.0   # 100% 油门时的航速 (mm/s)，现场实测后修改
W_MAX_DEG_S = 90.0   # 100% 差速时的原地旋转角速度 (度/s)，现场实测后修改
DRAG = 0.05          # 水阻系数（速度衰减，模拟阻力+惯性）
HEADING_NOISE = 5.0  # 航向测量噪声标准差（度，666 约定），0 表示无噪声


# ============================================================
# 场景（600 x 600 mm 场地）
# ============================================================

START_X, START_Y, START_H = 80.0, 520.0, 0.0   # 起点（航向 0° = 朝 +Y）
TARGET_X, TARGET_Y = 520.0, 80.0               # 目标（待救人员）

DT = 0.05    # 仿真步长（秒）
T_MAX = 90.0  # 最长仿真时间（秒），与 MISSION_TIMEOUT_S 一致


def simulate(noise: float = HEADING_NOISE):
    pilot = PidPilot()

    x, y, h = START_X, START_Y, START_H   # h 为 666 约定：+Y 为 0°，顺时针为正
    trail = [(x, y)]
    t = 0.0
    status = "run"

    while t < T_MAX:
        # 视觉测量（航向带噪声，与现场一致）
        h_meas = h + random.gauss(0.0, noise)

        a, b, status = pilot.update(x, y, h_meas, TARGET_X, TARGET_Y, DT)
        if status == "arrived":
            break

        # 差速油门 -> 速度/角速度（666 约定：顺时针为正）
        #   a > b（左快右慢）-> 右转 -> h 增大
        v = (a + b) / 2.0 / 100.0 * V_MAX_MM_S
        w = (a - b) / 2.0 / 100.0 * W_MAX_DEG_S

        v *= (1.0 - DRAG * DT)   # 水阻

        h += w * DT
        x += v * math.sin(math.radians(h)) * DT
        y += v * math.cos(math.radians(h)) * DT

        t += DT
        trail.append((x, y))

    return trail, t, status


def main():
    for noise in (0.0, HEADING_NOISE):
        trail, t, status = simulate(noise)
        fx, fy = trail[-1]
        err = math.hypot(TARGET_X - fx, TARGET_Y - fy)
        print("噪声 %4.1f° 结果：%-8s 用时 %5.1f 秒  终点 (%.1f, %.1f)  距目标 %.1f mm" % (
            noise, status, t, fx, fy, err))

    try:
        import matplotlib.pyplot as plt
        trail, t, status = simulate()
        xs = [p[0] for p in trail]
        ys = [p[1] for p in trail]
        cfg = build_nav_config()
        plt.figure(figsize=(6, 6))
        plt.plot(xs, ys, "-o", markersize=3, label="轨迹")
        plt.plot([START_X], [START_Y], "g^", markersize=12, label="起点")
        plt.plot([TARGET_X], [TARGET_Y], "r*", markersize=16, label="目标")
        plt.gca().add_patch(plt.Circle(
            (TARGET_X, TARGET_Y), cfg.accept_radius, fill=False, ls="--", color="r"))
        plt.xlim(0, config.FIELD_WIDTH_MM)
        plt.ylim(0, config.FIELD_HEIGHT_MM)
        plt.axis("equal")
        plt.grid(True)
        plt.legend()
        plt.title("PID 导航仿真（600mm 场地）")
        plt.show()
    except ImportError:
        print("（没装 matplotlib，跳过绘图。pip install matplotlib 可看图）")


if __name__ == "__main__":
    main()
