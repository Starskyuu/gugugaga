# -*- coding: utf-8 -*-
# ============================================================
# nav_control.py —— 纯控制算法（无任何硬件依赖）
#
# 树莓派端和电脑仿真共用：
#   - pi_pid_nav.py  船上运行时 import 本文件
#   - sim_test.py    电脑上调参时 import 本文件
#
# 双环 PID：
#   外环 速度PID：根据到目标的剩余距离计算总油门
#   内环 航向PID：根据航向误差计算差速转向
#   动力混合：左电机 = 油门 + 转向
#             右电机 = 油门 - 转向
#
# 坐标约定（重要）：
#   位置 (x, y) 和航向 heading 必须使用同一个坐标系：
#   0° 指向 +x 方向，向 +y 方向为正（与 atan2 一致）。
#   直接用图像像素坐标也可以——只要 heading 也在图像系里定义，
#   例如用两帧位移 atan2(dy, dx) 或船头-船尾连线算出，就天然满足约定。
# ============================================================

import math


# ------------------------------------------------------------
# 角度与数值工具
# ------------------------------------------------------------

def wrap180(deg):
    """把角度折叠到 [-180, 180]"""
    while deg > 180.0:
        deg -= 360.0
    while deg < -180.0:
        deg += 360.0
    return deg


def clamp(v, lo, hi):
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


# ------------------------------------------------------------
# PID
# ------------------------------------------------------------

class PID:
    """位置式 PID，带积分限幅和输出限幅"""

    def __init__(self, kp, ki, kd, out_min=-100.0, out_max=100.0, i_max=50.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.out_min = out_min
        self.out_max = out_max
        self.i_max = i_max
        self.reset()

    def reset(self):
        self.i = 0.0
        self.prev_error = 0.0
        self.has_prev = False

    def update_error(self, error, dt):
        """直接用误差更新（航向环用它，因为角度误差需要先 wrap）"""
        if dt <= 0:
            dt = 0.05

        # 微分用误差差分；如果抖动大，先调小 kd 或置 0
        d = 0.0
        if self.has_prev:
            d = (error - self.prev_error) / dt

        self.i = clamp(self.i + self.ki * error * dt, -self.i_max, self.i_max)

        out = self.kp * error + self.i + self.kd * d

        self.prev_error = error
        self.has_prev = True

        return clamp(out, self.out_min, self.out_max)

    def update(self, setpoint, measurement, dt):
        """标准用法：error = setpoint - measurement"""
        return self.update_error(setpoint - measurement, dt)


# ------------------------------------------------------------
# 导航参数
# ------------------------------------------------------------

class NavConfig:
    def __init__(self):
        # ---- 到达判定（单位与视觉坐标一致：像素就是像素，米就是米）----
        self.accept_radius = 0.3        # 进入该半径视为到达
        self.arrive_hysteresis = 0.5    # 到达后目标移开超过该距离才重新启动

        # ---- 动力限制（百分比）----
        # 注意：esp32_main.py 里 MAX_SPEED = 55，超过会被截掉
        self.max_speed = 55             # 最大油门
        self.max_turn = 55              # 最大差速转向量
        self.min_cruise = 18            # 克服阻力/死区的最小前进油门
        self.min_spin = 20              # 原地旋转的最小差速（死区补偿兜底）
        self.slow_zone = 1.0            # 距目标小于该值后取消 min_cruise，改用 min_approach
        self.min_approach = 10          # 慢速区内的最小前进油门（爬行接近，防止原地转圈到不了）

        # ---- 航向 ----
        self.heading_deadband = 5.0     # 航向误差死区（度），抑制视觉抖动
        self.turn_sign = 1              # 船转向反了就改成 -1

        # ---- PID 参数（先在 sim_test.py 里调，再下水）----
        self.kp_h = 1.2     # 每度航向误差 → 差速百分比
        self.ki_h = 0.0     # 一般保持 0；有恒定水流/风向偏移时再加
        self.kd_h = 0.0
        self.kp_s = 8.0     # 每单位距离 → 油门百分比
        self.ki_s = 0.0     # 速度环用 P（+D）就够；I 会让冲刺更猛，慎用
        self.kd_s = 2.0     # 接近目标时自动减速
        self.i_max_h = 30.0
        self.i_max_s = 30.0


# ------------------------------------------------------------
# 导航器：双环 PID
# ------------------------------------------------------------

class Navigator:
    """
    输入船位 / 航向 / 目标点，输出左右电机油门（-100..100，正=前进）。

    差速约定（与 esp32_main.py 的手动逻辑一致）：
      turn > 0  → A 快 B 慢 → 船向右转
      turn < 0  → A 慢 B 快 → 船向左转
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.hpid = PID(cfg.kp_h, cfg.ki_h, cfg.kd_h,
                        out_min=-float(cfg.max_turn),
                        out_max=float(cfg.max_turn),
                        i_max=cfg.i_max_h)
        self.spid = PID(cfg.kp_s, cfg.ki_s, cfg.kd_s,
                        out_min=0.0,
                        out_max=float(cfg.max_speed),
                        i_max=cfg.i_max_s)
        self.arrived = False

    def reset(self):
        self.hpid.reset()
        self.spid.reset()
        self.arrived = False

    def update(self, bx, by, heading, tx, ty, dt):
        """
        输入：
            bx, by   船当前位置（视觉坐标）
            heading  船当前航向（度，与位置同一坐标系，任意 ± 范围）
            tx, ty   目标位置
            dt       距上次调用的实际时间（秒）
        返回：
            (motor_a, motor_b, status)
            status: "run" / "arrived"
        """
        cfg = self.cfg

        dx = tx - bx
        dy = ty - by
        dist = math.hypot(dx, dy)

        # ---- 到达判定（带迟滞，防止在目标点附近反复启停）----
        if dist <= cfg.accept_radius:
            self.arrived = True
            self.hpid.reset()
            self.spid.reset()
            return 0.0, 0.0, "arrived"
        if self.arrived and dist <= cfg.arrive_hysteresis:
            return 0.0, 0.0, "arrived"
        self.arrived = False

        # ---- 内环：航向 ----
        # 目标方位角与航向同一坐标系，误差折叠到 ±180（永远走最短转向）
        bearing = math.degrees(math.atan2(dy, dx))
        err_h = wrap180(bearing - heading)
        if abs(err_h) <= cfg.heading_deadband:
            err_h = 0.0
        # err_h > 0 表示目标在逆时针方向 → 需要左转 → 差速为负
        turn = -self.hpid.update_error(err_h, dt) * cfg.turn_sign

        # ---- 外环：速度（剩余距离 → 油门）----
        # 速度环的设定值恒为 0（“到达”），直接拿剩余距离当误差：
        # 距离大 → 油门大；接近时 P 项自动减小，D 项起减速作用
        throttle = self.spid.update_error(dist, dt)
        throttle = clamp(throttle, 0.0, float(cfg.max_speed))

        # 远处保持最低油门（电机死区/水阻补偿）；近处降到 min_approach 爬行
        if dist > cfg.slow_zone:
            if 0.0 < throttle < cfg.min_cruise:
                throttle = float(cfg.min_cruise)
        else:
            # 不能直接切断油门——没有惯性的船会停在目标外围原地转圈，
            # 永远进不了 accept_radius
            if throttle < cfg.min_approach:
                throttle = float(cfg.min_approach)

        # ---- 航向没对准时按 cos 降速；误差超 90° 原地转向 ----
        align = math.cos(math.radians(err_h))
        base = throttle * max(0.0, align)

        a = base + turn
        b = base - turn

        # 油门为零且差速太小 → 船转不动，补一个最小差速兜底
        if base <= 0.0 and abs(turn) < cfg.min_spin:
            spin = cfg.min_spin if turn >= 0.0 else -cfg.min_spin
            a, b = spin, -spin

        a = clamp(a, -float(cfg.max_speed), float(cfg.max_speed))
        b = clamp(b, -float(cfg.max_speed), float(cfg.max_speed))

        return a, b, "run"
