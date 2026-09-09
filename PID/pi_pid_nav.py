# -*- coding: utf-8 -*-
# ============================================================
# pi_pid_nav.py —— 树莓派端视觉导航主程序
#
# 数据流：
#   视觉识别 → 船位/航向/目标 → 双环PID（nav_control.py）
#   → HTTP 下发 /M?A=..&B=.. → ESP32-C3 → DRV8833 → 双电机差速
#
# 使用前：
#   1. 树莓派连接船载热点（SSID: Mate 70 Pro / 密码 87654321）
#   2. 填 ESP32_IP（或留 None 让它启动时自动扫描）
#   3. 实现 VisionInterface.get_state()（唯一必须自己写的部分）
#
# 安全链（任何一环失效船都会停）：
#   - 视觉拿不到新数据   → 本程序主动发停车
#   - 本程序死掉 / 断网  → ESP32 一秒收不到 /M 自动停车
#   - ESP32 失联         → 打印 SEND FAIL，船靠上一条兜底自动停
# ============================================================

import math
import socket
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from nav_control import NavConfig, Navigator


# ============================================================
# 配置
# ============================================================

ESP32_IP = None    # 例："192.168.43.10"；None = 启动时自动扫描
CONTROL_DT = 0.1   # 期望控制周期（秒）。视觉慢也没关系，程序按实际耗时走
SEND_TIMEOUT = 0.4  # 单次 HTTP 超时（秒）


# ============================================================
# 视觉接口（唯一必须自己实现的部分）
# ============================================================

class VisionInterface:
    """
    视觉识别接口。

    重要约定：
    1. get_state() 必须“非阻塞”：建议你在另一个线程里跑视觉识别、
       持续更新最新结果，get_state() 只负责把最新值交出来。
    2. 没有新结果时返回 None —— 本程序会停车，绝不带着旧数据瞎开。
    3. 坐标系约定：位置 (x, y) 与航向 heading 必须用同一个坐标系，
       0° 指向 +x 方向、向 +y 方向为正（与 atan2 一致）。
       直接用图像像素坐标也可以，例如：
         heading = degrees(atan2(船头y - 船尾y, 船头x - 船尾x))
       或用两帧位移：
         heading = degrees(atan2(y2 - y1, x2 - x1))   （船停着时算不出，返回 None）
    4. 单位自定（像素或米），但 NavConfig 里的 accept_radius、
       slow_zone、kp_s 都要用同一个单位。
    """

    def get_state(self):
        """
        返回 (boat_x, boat_y, heading, target_x, target_y)：
          前三个是船的位置与航向；后两个是目标点坐标（None = 暂无目标）。
        整组返回 None → 视为“看不到船”，程序停车。
        """
        # TODO: 接入你的视觉识别结果。示例：
        # bx, by = latest_boat_pos()
        # heading = latest_boat_heading()
        # tx, ty = latest_target_pos()
        # return bx, by, heading, tx, ty
        return None


# ============================================================
# ESP32 通信
# ============================================================

def send_motors(ip, a, b):
    """把左右电机油门（-100..100）发给 ESP32，成功返回 True"""
    url = "http://%s/M?A=%d&B=%d" % (ip, int(round(a)), int(round(b)))
    try:
        with urllib.request.urlopen(url, timeout=SEND_TIMEOUT) as resp:
            return resp.read() == b"M"
    except Exception:
        return False


def find_esp32():
    """
    按本机所在网段扫描 1~254 的 80 端口，返回第一个响应的 IP。
    只在启动时执行（此时船应停在岸边）。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))   # UDP 不真正发包，只是取本机局域网 IP
        local_ip = s.getsockname()[0]
    finally:
        s.close()

    prefix = local_ip.rsplit(".", 1)[0]

    def probe(i):
        ip = "%s.%d" % (prefix, i)
        if ip == local_ip:
            return None
        try:
            c = socket.create_connection((ip, 80), timeout=0.25)
            c.close()
            return ip
        except OSError:
            return None

    print("正在扫描 ESP32 (%s.*)..." % prefix)
    with ThreadPoolExecutor(max_workers=64) as ex:
        for ip in ex.map(probe, range(1, 255)):
            if ip:
                return ip
    return None


# ============================================================
# 主程序
# ============================================================

def main():
    cfg = NavConfig()
    nav = Navigator(cfg)
    vision = VisionInterface()

    ip = ESP32_IP
    if not ip:
        ip = find_esp32()
    if not ip:
        print("找不到 ESP32，请把 IP 填到 ESP32_IP 后重试")
        return

    print("ESP32: http://%s" % ip)
    print("视觉导航启动。Ctrl+C 停车退出。")

    last_status = None
    last_print = 0.0
    t_last = time.monotonic()

    try:
        while True:
            t_now = time.monotonic()
            dt = min(t_now - t_last, 0.5)   # 上限防止长时间停摆后积分突跳
            t_last = t_now

            # ---- 读取视觉结果 ----
            try:
                st = vision.get_state()
            except Exception as e:
                print("VISION ERROR:", e)
                st = None

            # ---- 看不到船 → 停车 ----
            if not st or len(st) < 5 or st[0] is None or st[1] is None or st[2] is None:
                send_motors(ip, 0, 0)
                nav.reset()
                last_status = None
            else:
                bx, by, heading, tx, ty = st

                # ---- 没有目标 → 停车等待 ----
                if tx is None or ty is None:
                    send_motors(ip, 0, 0)
                    nav.reset()
                    if last_status != "wait":
                        print("WAIT: 没有目标")
                        last_status = "wait"
                else:
                    a, b, status = nav.update(bx, by, heading, tx, ty, dt)
                    ok = send_motors(ip, a, b)

                    if status != last_status:
                        print("%s  A=%+3d  B=%+3d  %s" % (
                            status.upper(), a, b, "OK" if ok else "SEND FAIL"))
                        last_status = status
                    elif time.monotonic() - last_print > 2.0:
                        last_print = time.monotonic()
                        dist = math.hypot(tx - bx, ty - by)
                        print("RUN  A=%+3d  B=%+3d  距离=%.2f  %s" % (
                            a, b, dist, "OK" if ok else "SEND FAIL"))

            # ---- 固定周期 ----
            next_t = t_last + CONTROL_DT
            delay = next_t - time.monotonic()
            if delay > 0:
                time.sleep(delay)

    except KeyboardInterrupt:
        print("\nCTRL+C")
    finally:
        send_motors(ip, 0, 0)
        print("MOTOR STOPPED")


if __name__ == "__main__":
    main()
