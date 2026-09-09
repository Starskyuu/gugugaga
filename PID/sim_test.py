# -*- coding: utf-8 -*-
# ============================================================
# sim_test.py —— 电脑上跑的运动学仿真（先在这里调 PID 参数）
#
# 运行：python sim_test.py
#   装了 matplotlib 会弹出轨迹图；没装只看文字结果。
#
# 目的：先把参数调到“能到点、不绕圈、不震荡”，
#       再抄到 pi_pid_nav.py 的 NavConfig 里下水实测。
# ============================================================

import math
import random

from nav_control import NavConfig, Navigator


# ============================================================
# 船模动力学参数（按你的船实测改）
# ============================================================

V_MAX = 1.0          # 100% 油门时的航速 (m/s)
W_MAX = 2.5          # 100% 差速时的原地旋转角速度 (rad/s)
DRAG = 0.05          # 水阻系数（速度衰减，模拟阻力+惯性）
HEADING_NOISE = 0.0  # 航向测量噪声标准差（度），模拟视觉抖动（试试 3~8）


# ============================================================
# 场景
# ============================================================

START_X, START_Y, START_H = 0.0, 0.0, 180.0   # 起点（初始航向故意背对目标）
TARGET_X, TARGET_Y = 10.0, 5.0

DT = 0.05        # 仿真步长（秒）
T_MAX = 120.0    # 最长仿真时间（秒）


def simulate():
    cfg = NavConfig()
    nav = Navigator(cfg)

    x, y, h = START_X, START_Y, START_H
    trail = [(x, y)]
    t = 0.0
    status = "run"

    while t < T_MAX:
        # 视觉测量（带噪声）
        h_meas = h + random.gauss(0.0, HEADING_NOISE)

        a, b, status = nav.update(x, y, h_meas, TARGET_X, TARGET_Y, DT)
        if status == "arrived":
            break

        # 差速油门 → 速度/角速度
        # 约定与实物一致：a<b（左慢右快）→ 左转 → 航向（逆时针为正）增大
        v = (a + b) / 2.0 / 100.0 * V_MAX
        w = (b - a) / 2.0 / 100.0 * W_MAX

        v *= (1.0 - DRAG * DT)   # 水阻

        h += math.degrees(w * DT)
        x += v * math.cos(math.radians(h)) * DT
        y += v * math.sin(math.radians(h)) * DT

        t += DT
        trail.append((x, y))

    return trail, t, status


def main():
    trail, t, status = simulate()
    fx, fy = trail[-1]
    err = math.hypot(TARGET_X - fx, TARGET_Y - fy)

    print("结果：%-8s 用时 %6.1f 秒  终点 (%.2f, %.2f)  距目标 %.2f m" % (
        status, t, fx, fy, err))

    try:
        import matplotlib.pyplot as plt
        cfg = NavConfig()
        xs = [p[0] for p in trail]
        ys = [p[1] for p in trail]
        plt.figure(figsize=(6, 6))
        plt.plot(xs, ys, "-o", markersize=3, label="轨迹")
        plt.plot([START_X], [START_Y], "g^", markersize=12, label="起点")
        plt.plot([TARGET_X], [TARGET_Y], "r*", markersize=16, label="目标")
        plt.gca().add_patch(plt.Circle(
            (TARGET_X, TARGET_Y), cfg.accept_radius,
            fill=False, ls="--", color="r"))
        plt.axis("equal")
        plt.grid(True)
        plt.legend()
        plt.title("PID 导航仿真")
        plt.show()
    except ImportError:
        print("（没装 matplotlib，跳过绘图。pip install matplotlib 可看图）")


if __name__ == "__main__":
    main()
