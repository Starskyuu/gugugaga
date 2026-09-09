#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
城市方舟 / 智能救援塔 - 树莓派最小总控版

目标：
水位传感器 -> 树莓派 -> 升降台升起 -> 人工放船 -> 视觉找人 -> 小船自动靠近人员

尽量不修改现有程序：
1. 666.py 继续负责 YOLO + ArUco + 坐标，使用它已有的 --publish-state UDP 输出
2. 升降台继续使用原网页接口 /U /D
3. 小船继续使用原网页接口 /F /B /L /R /S
4. 水位 ESP32 继续 TCP 连接树莓派 5000 端口

第一次测试建议：
    python3 tower_master_simple.py --test

正式接水位：
    python3 tower_master_simple.py

如果你已经单独启动了 666.py：
    python3 tower_master_simple.py --no-start-vision

Ctrl+C：立刻给小船发送 STOP 并退出。
"""

import argparse
import json
import math
import os
import re
import socket
import subprocess
import sys
import threading
import time


# ============================================================
# 1. 配置区
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 现有视觉程序
VISION_FILE = os.path.join(BASE_DIR, "666.py")

# 设备 IP
PI_IP = "192.168.43.12"
LIFT_IP = "192.168.43.21"

# ArUco 船 ID -> 小船 IP
BOAT_IPS = {
    0: "192.168.43.14",
    1: "192.168.43.18",
    2: "192.168.43.20",
}

# 第一版先只自动控制 0 号船，最容易调通
ACTIVE_BOAT_ID = 0

# 水位 ESP32 -> 树莓派
WATER_PORT = 5000

# 666.py -> 总控 UDP
VISION_HOST = "127.0.0.1"
VISION_PORT = 9101

# ---------------- 水位触发 ----------------
# 如果 WATER_ABSOLUTE_THRESHOLD = None：
# 程序启动后前 5 个水位值作为“干燥基线”，
# 连续 3 次超过 基线 + WATER_DELTA_TRIGGER 就认为洪水来临。
#
# 展示时请让传感器在程序启动阶段保持“未进水”。
WATER_ABSOLUTE_THRESHOLD = None
WATER_BASELINE_SAMPLES = 5
WATER_DELTA_TRIGGER = 6000
WATER_TRIGGER_COUNT = 3

# ---------------- 自动导航 ----------------
# 距离人小于该值后停车，单位 mm
ARRIVE_DISTANCE_MM = 55.0

# 船头方向误差大于该值时先原地转向
TURN_THRESHOLD_DEG = 18.0

# 为避免左右反复抖动，低于这个角度直接前进
FORWARD_ANGLE_DEG = 10.0

# 视觉状态超过该时间没更新，强制停车
VISION_TIMEOUT_SEC = 1.2

# 每隔约 0.20s 发一次命令。
# 原船控有 700ms 安全停车，所以必须持续发。
CONTROL_INTERVAL_SEC = 0.20

# HTTP 单次连接超时
HTTP_TIMEOUT_SEC = 0.25


# ============================================================
# 2. HTTP 控制
# ============================================================

def http_get(ip, path, timeout=HTTP_TIMEOUT_SEC):
    """
    用最原始的 socket 发 HTTP GET。
    不依赖 requests，树莓派标准 Python 就能运行。
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)

    try:
        s.connect((ip, 80))

        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {ip}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("utf-8")

        s.sendall(request)

        # 只需要确认设备有回应，不需要完整读取网页
        try:
            s.recv(128)
        except socket.timeout:
            pass

        return True

    except OSError as e:
        print(f"[HTTP ERROR] {ip}{path} -> {e}")
        return False

    finally:
        try:
            s.close()
        except Exception:
            pass


def lift_up():
    print("[LIFT] 升降台 -> UP")
    return http_get(LIFT_IP, "/U", timeout=0.8)


def lift_down():
    print("[LIFT] 升降台 -> DOWN")
    return http_get(LIFT_IP, "/D", timeout=0.8)


def boat_command(boat_id, command):
    """
    command: F / B / L / R / S
    """
    ip = BOAT_IPS[boat_id]
    return http_get(ip, "/" + command)


def stop_boat(boat_id=ACTIVE_BOAT_ID):
    boat_command(boat_id, "S")


# ============================================================
# 3. 水位 TCP 接收
# ============================================================

class WaterReceiver:
    def __init__(self, host="0.0.0.0", port=WATER_PORT):
        self.host = host
        self.port = port

        self.latest_value = None
        self.latest_time = 0.0

        self.baseline_values = []
        self.baseline = None
        self.high_count = 0
        self.flood_event = threading.Event()

        self.running = True
        self.thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="WaterReceiver"
        )

    def start(self):
        self.thread.start()

    def stop(self):
        self.running = False

    def _process_value(self, value):
        self.latest_value = value
        self.latest_time = time.monotonic()

        # -------- 使用绝对阈值 --------
        if WATER_ABSOLUTE_THRESHOLD is not None:
            threshold = WATER_ABSOLUTE_THRESHOLD

        # -------- 自动建立干燥基线 --------
        else:
            if self.baseline is None:
                self.baseline_values.append(value)
                print(
                    f"[WATER] 基线采样 "
                    f"{len(self.baseline_values)}/{WATER_BASELINE_SAMPLES}: {value}"
                )

                if len(self.baseline_values) >= WATER_BASELINE_SAMPLES:
                    ordered = sorted(self.baseline_values)
                    self.baseline = ordered[len(ordered) // 2]
                    threshold = self.baseline + WATER_DELTA_TRIGGER
                    print(
                        f"[WATER] 干燥基线 = {self.baseline}, "
                        f"自动洪水阈值 = {threshold}"
                    )
                return

            threshold = self.baseline + WATER_DELTA_TRIGGER

        # -------- 连续多次超过阈值才触发 --------
        if value >= threshold:
            self.high_count += 1
            print(
                f"[WATER] {value} >= {threshold} "
                f"({self.high_count}/{WATER_TRIGGER_COUNT})"
            )

            if self.high_count >= WATER_TRIGGER_COUNT:
                self.flood_event.set()

        else:
            self.high_count = 0
            print(f"[WATER] {value} < {threshold}")

    def _run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.host, self.port))
        server.listen(2)
        server.settimeout(1.0)

        print(f"[WATER] 树莓派监听 TCP {PI_IP}:{self.port}")

        try:
            while self.running:
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break

                print(f"[WATER] ESP32 已连接: {addr}")

                conn.settimeout(1.0)
                buffer = ""

                try:
                    while self.running:
                        try:
                            data = conn.recv(1024)
                        except socket.timeout:
                            continue

                        if not data:
                            print("[WATER] ESP32 断开，等待重连")
                            break

                        buffer += data.decode("utf-8", "ignore")

                        # ESP32 当前没有换行符，所以可能出现：
                        # Water:12345Water:12360Water:12400
                        # 用正则一次提取全部完整数值。
                        matches = list(
                            re.finditer(r"Water:(\d+)(?=Water:|$)", buffer)
                        )

                        if matches:
                            for match in matches:
                                self._process_value(int(match.group(1)))

                            # 已处理到最后一个完整值，清空即可。
                            buffer = ""

                        # 防止异常数据无限增长
                        if len(buffer) > 4096:
                            buffer = buffer[-256:]

                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass

        finally:
            try:
                server.close()
            except Exception:
                pass


# ============================================================
# 4. 接收 666.py 的视觉状态
# ============================================================

class VisionReceiver:
    def __init__(self, host=VISION_HOST, port=VISION_PORT):
        self.host = host
        self.port = port

        self.latest_state = None
        self.latest_time = 0.0

        self.lock = threading.Lock()
        self.running = True

        self.thread = threading.Thread(
            target=self._run,
            daemon=True,
            name="VisionReceiver"
        )

    def start(self):
        self.thread.start()

    def stop(self):
        self.running = False

    def get(self):
        with self.lock:
            if self.latest_state is None:
                return None, None

            return self.latest_state, time.monotonic() - self.latest_time

    def _run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.port))
        sock.settimeout(1.0)

        print(f"[VISION] 监听 UDP {self.host}:{self.port}")

        try:
            while self.running:
                try:
                    data, _ = sock.recvfrom(65535)
                except socket.timeout:
                    continue
                except OSError:
                    break

                try:
                    state = json.loads(data.decode("utf-8"))

                    with self.lock:
                        self.latest_state = state
                        self.latest_time = time.monotonic()

                except Exception as e:
                    print("[VISION] 状态解析失败:", e)

        finally:
            sock.close()


# ============================================================
# 5. 启动现有 666.py
# ============================================================

def start_vision_process():
    if not os.path.exists(VISION_FILE):
        raise FileNotFoundError(
            f"找不到 {VISION_FILE}\n"
            "请把本脚本和 666.py 放在同一个文件夹。"
        )

    cmd = [
        sys.executable,
        VISION_FILE,
        "--publish-state",
        "--state-host", VISION_HOST,
        "--state-port", str(VISION_PORT),
        "--state-hz", "10",
    ]

    print("[VISION] 启动:", " ".join(cmd))

    # 不加 --headless：
    # 保留你原来 666.py 的 OpenCV 画面，方便现场观察。
    return subprocess.Popen(cmd)


# ============================================================
# 6. 自动导航
# ============================================================

def wrap_angle(error_deg):
    """
    把角度误差变成 [-180, 180)
    """
    return (error_deg + 180.0) % 360.0 - 180.0


def choose_target(persons, boat_x, boat_y):
    """
    第一版：选离当前船最近的人。
    """
    valid = [
        p for p in persons
        if p.get("inside_field", True)
    ]

    if not valid:
        return None

    return min(
        valid,
        key=lambda p: math.hypot(
            float(p["x"]) - boat_x,
            float(p["y"]) - boat_y
        )
    )


def decide_command(boat, person):
    """
    666.py 的角度约定：
        +Y = 0°
        +X = 90°
    所以目标角度同样使用 atan2(dx, dy)。
    """
    bx = float(boat["x"])
    by = float(boat["y"])
    heading = boat.get("angle_deg")

    tx = float(person["x"])
    ty = float(person["y"])

    dx = tx - bx
    dy = ty - by

    distance = math.hypot(dx, dy)

    if distance <= ARRIVE_DISTANCE_MM:
        return "S", distance, None, None

    if heading is None:
        return "S", distance, None, None

    desired = math.degrees(math.atan2(dx, dy)) % 360.0
    error = wrap_angle(desired - float(heading))

    # 偏差较大：原地转向
    if error > TURN_THRESHOLD_DEG:
        return "R", distance, desired, error

    if error < -TURN_THRESHOLD_DEG:
        return "L", distance, desired, error

    # 偏差已经较小：向前走
    return "F", distance, desired, error


def autonomous_rescue(vision_receiver, boat_id=ACTIVE_BOAT_ID):
    """
    最小自动救人逻辑：
    1. 等视觉系统坐标准备好
    2. 找到指定船
    3. 找最近的人
    4. 转向 -> 前进 -> 到达阈值 -> STOP
    """
    print()
    print("=" * 60)
    print(f"[AUTO] 开始自动救援：Boat {boat_id}")
    print("[AUTO] Ctrl+C 可随时紧急停车")
    print("=" * 60)

    last_print = 0.0

    try:
        while True:
            loop_start = time.monotonic()

            state, state_age = vision_receiver.get()

            # ---------- 没视觉 / 视觉超时 ----------
            if state is None or state_age is None or state_age > VISION_TIMEOUT_SEC:
                stop_boat(boat_id)

                if time.monotonic() - last_print > 1.0:
                    print("[AUTO] 等待 666.py 视觉状态...")
                    last_print = time.monotonic()

                time.sleep(CONTROL_INTERVAL_SEC)
                continue

            # ---------- 坐标系不安全 ----------
            if not state.get("vision_ok_for_control", False):
                stop_boat(boat_id)

                if time.monotonic() - last_print > 1.0:
                    print("[AUTO] 坐标系未就绪 / CONTROL HOLD")
                    last_print = time.monotonic()

                time.sleep(CONTROL_INTERVAL_SEC)
                continue

            boats = state.get("boats", {})
            persons = state.get("persons", [])

            # JSON 里的字典 key 会变成字符串
            boat = boats.get(str(boat_id))
            if boat is None:
                boat = boats.get(boat_id)

            if boat is None:
                stop_boat(boat_id)

                if time.monotonic() - last_print > 1.0:
                    print(f"[AUTO] 暂未看到 Boat {boat_id}")
                    last_print = time.monotonic()

                time.sleep(CONTROL_INTERVAL_SEC)
                continue

            if not persons:
                stop_boat(boat_id)

                if time.monotonic() - last_print > 1.0:
                    print("[AUTO] 暂未检测到人员，原地等待")
                    last_print = time.monotonic()

                time.sleep(CONTROL_INTERVAL_SEC)
                continue

            target = choose_target(
                persons,
                float(boat["x"]),
                float(boat["y"])
            )

            if target is None:
                stop_boat(boat_id)
                time.sleep(CONTROL_INTERVAL_SEC)
                continue

            command, distance, desired, error = decide_command(
                boat,
                target
            )

            boat_command(boat_id, command)

            if time.monotonic() - last_print > 0.5:
                heading = boat.get("angle_deg")

                if desired is None:
                    print(
                        f"[AUTO] boat=({boat['x']:.1f},{boat['y']:.1f}) "
                        f"target=({target['x']:.1f},{target['y']:.1f}) "
                        f"distance={distance:.1f}mm -> {command}"
                    )
                else:
                    print(
                        f"[AUTO] boat=({boat['x']:.1f},{boat['y']:.1f}) "
                        f"heading={heading:.1f}° | "
                        f"target=({target['x']:.1f},{target['y']:.1f}) "
                        f"distance={distance:.1f}mm | "
                        f"desired={desired:.1f}° error={error:+.1f}° "
                        f"-> {command}"
                    )

                last_print = time.monotonic()

            # 到达后先停车并结束第一轮
            if command == "S" and distance <= ARRIVE_DISTANCE_MM:
                print()
                print(
                    f"[AUTO] 已到达人员附近：{distance:.1f} mm，"
                    "小船停车。"
                )
                stop_boat(boat_id)
                return

            elapsed = time.monotonic() - loop_start
            sleep_time = CONTROL_INTERVAL_SEC - elapsed

            if sleep_time > 0:
                time.sleep(sleep_time)

    finally:
        stop_boat(boat_id)


# ============================================================
# 7. 主流程
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--test",
        action="store_true",
        help="测试模式：按 Enter 手动模拟洪水，不等待水位传感器"
    )

    parser.add_argument(
        "--no-start-vision",
        action="store_true",
        help="不自动启动 666.py；适合你已经单独运行 666.py 的情况"
    )

    parser.add_argument(
        "--boat",
        type=int,
        default=ACTIVE_BOAT_ID,
        choices=sorted(BOAT_IPS.keys()),
        help="本次自动控制哪艘船，默认 0"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    print()
    print("=" * 66)
    print("城市方舟 / 智能救援塔 - Raspberry Pi 最小总控")
    print("=" * 66)
    print(f"树莓派      : {PI_IP}")
    print(f"升降台      : {LIFT_IP}")
    print(f"本次小船    : Boat {args.boat} -> {BOAT_IPS[args.boat]}")
    print(f"水位端口    : TCP {WATER_PORT}")
    print(f"视觉状态    : UDP {VISION_HOST}:{VISION_PORT}")
    print("=" * 66)
    print()

    # 先停车，避免小船上电后处在未知状态
    stop_boat(args.boat)

    vision_receiver = VisionReceiver()
    vision_receiver.start()

    vision_process = None
    water_receiver = None

    try:
        # -------- 启动视觉 --------
        if not args.no_start_vision:
            vision_process = start_vision_process()
        else:
            print(
                "[VISION] 请确保你另一个终端正在运行：\n"
                "python3 666.py --publish-state"
            )

        # -------- 洪水触发 --------
        if args.test:
            print()
            input(
                "[TEST] 这是测试模式。\n"
                "确认设备安全后，按 Enter 模拟“洪水来临”..."
            )

        else:
            water_receiver = WaterReceiver()
            water_receiver.start()

            print()
            print("[SYSTEM] 等待水位 ESP32 触发洪水...")
            print(
                "[SYSTEM] 注意：ESP32-S3.py 中 "
                'RASPBERRY_PI_IP 必须是 "192.168.43.12"'
            )

            water_receiver.flood_event.wait()

        # -------- 洪水来了 --------
        print()
        print("!" * 66)
        print("[FLOOD] 检测到洪水")
        print("!" * 66)

        # 1. 升起平台
        if lift_up():
            print("[SYSTEM] 已发送升降台升起命令")
        else:
            print("[SYSTEM] 升降台命令发送失败，请检查 192.168.43.21")

        # 给升降台一点动作时间
        time.sleep(1.0)

        # 2. 人工出船
        print()
        input(
            "[MANUAL] 现在请人工把小船放到水面。\n"
            "确认 Boat ArUco 已在摄像头画面中后，按 Enter 开始无人救援..."
        )

        # 3. 自动救人
        autonomous_rescue(
            vision_receiver=vision_receiver,
            boat_id=args.boat
        )

        print()
        print("[SYSTEM] 本轮最小自动救援流程结束。")

    except KeyboardInterrupt:
        print()
        print("[EMERGENCY] Ctrl+C -> 紧急停车")

    finally:
        try:
            stop_boat(args.boat)
        except Exception:
            pass

        if water_receiver is not None:
            water_receiver.stop()

        vision_receiver.stop()

        if vision_process is not None:
            try:
                vision_process.terminate()
                vision_process.wait(timeout=2)
            except Exception:
                try:
                    vision_process.kill()
                except Exception:
                    pass

        print("[SYSTEM] 小船已发送 STOP，总控退出。")


if __name__ == "__main__":
    main()
