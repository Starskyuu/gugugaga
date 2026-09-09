#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能城市救援塔 - Raspberry Pi 正式总控 V1.1

当前闭环：
水位 ESP32
    -> 树莓派
    -> 升降台升起
    -> 人工放船
    -> 666.py 找船/找人
    -> 树莓派自动控制一艘船靠近最近人员
    -> 到达后停车

当前暂时不接：
- jisuan 最优路径
- frontend 前端
- 多船任务分配

运行：
    python3 tower_master.py --test

正式接水位：
    python3 tower_master.py

若 666.py 已在另一个终端运行：
    python3 tower_master.py --no-start-vision

选择其他船：
    python3 tower_master.py --test --boat 1
"""

import argparse
import json
import math
import re
import socket
import subprocess
import sys
import threading
import time

import config


# ============================================================
# 1. 通用 HTTP 控制
# ============================================================

def http_get(ip, path, timeout=None):
    if timeout is None:
        timeout = config.HTTP_TIMEOUT_SEC

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)

    try:
        sock.connect((ip, 80))

        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {ip}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("utf-8")

        sock.sendall(request)

        try:
            sock.recv(128)
        except socket.timeout:
            pass

        return True

    except OSError as exc:
        print(f"[HTTP ERROR] {ip}{path} -> {exc}")
        return False

    finally:
        try:
            sock.close()
        except Exception:
            pass


# ============================================================
# 2. 升降台
# ============================================================

def lift_up():
    print("[LIFT] UP")
    return http_get(config.LIFT_IP, "/U", timeout=0.8)


def lift_down():
    print("[LIFT] DOWN")
    return http_get(config.LIFT_IP, "/D", timeout=0.8)


# ============================================================
# 3. 小船
# ============================================================

def boat_command(boat_id, command):
    ip = config.BOAT_IPS[boat_id]
    return http_get(ip, "/" + command)


def stop_boat(boat_id):
    boat_command(boat_id, "S")


# ============================================================
# 4. 水位无线 TCP 接收
# ============================================================

class WaterReceiver:
    def __init__(self):
        self.flood_event = threading.Event()
        self.running = True

        self.baseline_values = []
        self.baseline = None
        self.high_count = 0

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
        # 先建立干燥基线
        if self.baseline is None:
            self.baseline_values.append(value)

            print(
                f"[WATER] baseline "
                f"{len(self.baseline_values)}/"
                f"{config.WATER_BASELINE_SAMPLES}: {value}"
            )

            if len(self.baseline_values) >= config.WATER_BASELINE_SAMPLES:
                ordered = sorted(self.baseline_values)
                self.baseline = ordered[len(ordered) // 2]

                print(
                    "[WATER] baseline ready =",
                    self.baseline
                )
                print(
                    "[WATER] flood threshold =",
                    self.baseline + config.WATER_DELTA_TRIGGER
                )

            return

        threshold = self.baseline + config.WATER_DELTA_TRIGGER

        if value >= threshold:
            self.high_count += 1

            print(
                f"[WATER] HIGH {value} >= {threshold} "
                f"({self.high_count}/{config.WATER_TRIGGER_COUNT})"
            )

            if self.high_count >= config.WATER_TRIGGER_COUNT:
                self.flood_event.set()

        else:
            self.high_count = 0
            print(f"[WATER] normal {value} < {threshold}")

    def _run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        server.bind((config.WATER_HOST, config.WATER_PORT))
        server.listen(2)
        server.settimeout(1.0)

        print(
            f"[WATER] listening TCP "
            f"{config.PI_IP}:{config.WATER_PORT}"
        )

        try:
            while self.running:
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue

                print("[WATER] ESP32 connected:", addr)

                conn.settimeout(1.0)
                buffer = ""

                try:
                    while self.running:
                        try:
                            data = conn.recv(1024)
                        except socket.timeout:
                            continue

                        if not data:
                            print("[WATER] ESP32 disconnected")
                            break

                        buffer += data.decode("utf-8", "ignore")

                        # ESP32 原程序发送 Water:12345，但没有换行。
                        # 只有看到下一条 Water: 时，上一条才视为完整，
                        # 避免 TCP 恰好把一个数字拆成两包时误读。
                        while True:
                            first = buffer.find("Water:")
                            if first < 0:
                                buffer = buffer[-32:]
                                break

                            if first > 0:
                                buffer = buffer[first:]

                            second = buffer.find("Water:", 6)

                            if second < 0:
                                break

                            record = buffer[:second]
                            buffer = buffer[second:]

                            match = re.fullmatch(r"Water:(\d+)", record)

                            if match:
                                self._process_value(
                                    int(match.group(1))
                                )

                finally:
                    # 连接断开时尝试处理最后一个完整记录
                    match = re.fullmatch(
                        r"Water:(\d+)",
                        buffer.strip()
                    )

                    if match:
                        self._process_value(
                            int(match.group(1))
                        )

                    try:
                        conn.close()
                    except Exception:
                        pass

        finally:
            server.close()


# ============================================================
# 5. 666.py 视觉状态接收
# ============================================================

class VisionReceiver:
    def __init__(self):
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

            age = time.monotonic() - self.latest_time
            return self.latest_state, age

    def _run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        sock.bind(
            (
                config.VISION_STATE_HOST,
                config.VISION_STATE_PORT
            )
        )

        sock.settimeout(1.0)

        print(
            f"[VISION] listening UDP "
            f"{config.VISION_STATE_HOST}:"
            f"{config.VISION_STATE_PORT}"
        )

        try:
            while self.running:
                try:
                    data, _ = sock.recvfrom(65535)
                except socket.timeout:
                    continue

                try:
                    state = json.loads(
                        data.decode("utf-8")
                    )

                    with self.lock:
                        self.latest_state = state
                        self.latest_time = time.monotonic()

                except Exception as exc:
                    print("[VISION] bad state:", exc)

        finally:
            sock.close()


# ============================================================
# 6. 启动现有视觉程序
# ============================================================

def validate_project_files():
    required = [
        config.VISION_FILE,
        config.MODEL_FILE,
    ]

    missing = [
        str(path)
        for path in required
        if not path.exists()
    ]

    if missing:
        print("[ERROR] missing project files:")
        for path in missing:
            print("   ", path)
        raise FileNotFoundError("project files missing")

    if not config.CALIB_FILE.exists():
        print(
            "[WARNING] calibration file not found:",
            config.CALIB_FILE
        )


def start_vision():
    validate_project_files()

    cmd = [
        sys.executable,
        str(config.VISION_FILE),

        "--model",
        str(config.MODEL_FILE),

        "--publish-state",
        "--state-host",
        config.VISION_STATE_HOST,

        "--state-port",
        str(config.VISION_STATE_PORT),

        "--state-hz",
        str(config.VISION_STATE_HZ),
    ]

    if config.CALIB_FILE.exists():
        cmd += [
            "--calibration",
            str(config.CALIB_FILE)
        ]

    print("[VISION] 启动视觉系统")

    # 默认不让 666.py 的 YOLO / ArUco / FPS 信息刷满总控终端。
    # 详细信息全部保存到 logs/vision.log。
    if config.VISION_OUTPUT_TO_TERMINAL:
        process = subprocess.Popen(cmd)
        return process, None

    config.LOG_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    vision_log_path = (
        config.LOG_DIR / "vision.log"
    )

    log_handle = open(
        vision_log_path,
        "a",
        encoding="utf-8",
        buffering=1
    )

    log_handle.write(
        "\n\n========== VISION START "
        + time.strftime("%Y-%m-%d %H:%M:%S")
        + " ==========\n"
    )

    process = subprocess.Popen(
        cmd,
        stdout=log_handle,
        stderr=subprocess.STDOUT
    )

    print(
        "[VISION] 详细识别日志 ->",
        vision_log_path
    )

    return process, log_handle


# ============================================================
# 7. 自动导航
# ============================================================

def wrap_angle(angle):
    return (angle + 180.0) % 360.0 - 180.0


def choose_nearest_person(persons, boat):
    candidates = [
        person
        for person in persons
        if person.get("inside_field", True)
    ]

    if not candidates:
        return None

    bx = float(boat["x"])
    by = float(boat["y"])

    return min(
        candidates,
        key=lambda person: math.hypot(
            float(person["x"]) - bx,
            float(person["y"]) - by
        )
    )


def decide_command(boat, person):
    bx = float(boat["x"])
    by = float(boat["y"])

    tx = float(person["x"])
    ty = float(person["y"])

    heading = boat.get("angle_deg")

    dx = tx - bx
    dy = ty - by

    distance = math.hypot(dx, dy)

    if distance <= config.ARRIVE_DISTANCE_MM:
        return "S", distance, None, None

    if heading is None:
        return "S", distance, None, None

    # 与 666.py 保持一致：
    # +Y = 0°, +X = 90°
    desired = math.degrees(
        math.atan2(dx, dy)
    ) % 360.0

    error = wrap_angle(
        desired - float(heading)
    )

    if error > config.TURN_THRESHOLD_DEG:
        return "R", distance, desired, error

    if error < -config.TURN_THRESHOLD_DEG:
        return "L", distance, desired, error

    return "F", distance, desired, error


def autonomous_rescue(vision_receiver, boat_id):
    print()
    print("=" * 64)
    print(f"[AUTO] rescue started | Boat {boat_id}")
    print("=" * 64)

    last_print = 0.0

    try:
        while True:
            started = time.monotonic()

            state, age = vision_receiver.get()

            # 视觉断流直接停车
            if (
                state is None
                or age is None
                or age > config.VISION_TIMEOUT_SEC
            ):
                stop_boat(boat_id)

                if time.monotonic() - last_print > 1.0:
                    print("[AUTO] waiting for vision...")
                    last_print = time.monotonic()

                time.sleep(config.CONTROL_INTERVAL_SEC)
                continue

            # 666.py 自己判断坐标是否安全
            if not state.get("vision_ok_for_control", False):
                stop_boat(boat_id)

                if time.monotonic() - last_print > 1.0:
                    print("[AUTO] CONTROL HOLD")
                    last_print = time.monotonic()

                time.sleep(config.CONTROL_INTERVAL_SEC)
                continue

            boats = state.get("boats", {})
            persons = state.get("persons", [])

            # JSON key 会变成字符串
            boat = boats.get(str(boat_id))
            if boat is None:
                boat = boats.get(boat_id)

            if boat is None:
                stop_boat(boat_id)

                if time.monotonic() - last_print > 1.0:
                    print(f"[AUTO] Boat {boat_id} not found")
                    last_print = time.monotonic()

                time.sleep(config.CONTROL_INTERVAL_SEC)
                continue

            if not persons:
                stop_boat(boat_id)

                if time.monotonic() - last_print > 1.0:
                    print("[AUTO] no person detected")
                    last_print = time.monotonic()

                time.sleep(config.CONTROL_INTERVAL_SEC)
                continue

            target = choose_nearest_person(
                persons,
                boat
            )

            if target is None:
                stop_boat(boat_id)
                time.sleep(config.CONTROL_INTERVAL_SEC)
                continue

            command, distance, desired, error = (
                decide_command(boat, target)
            )

            boat_command(
                boat_id,
                command
            )

            if (
                time.monotonic() - last_print
                > config.MASTER_STATUS_INTERVAL_SEC
            ):
                if desired is None:
                    print(
                        f"[AUTO] distance={distance:.1f} mm "
                        f"-> {command}"
                    )
                else:
                    print(
                        f"[AUTO] boat=({boat['x']:.1f},"
                        f"{boat['y']:.1f}) "
                        f"heading={float(boat['angle_deg']):.1f}° | "
                        f"target=({target['x']:.1f},"
                        f"{target['y']:.1f}) "
                        f"distance={distance:.1f} mm | "
                        f"error={error:+.1f}° -> {command}"
                    )

                last_print = time.monotonic()

            if (
                command == "S"
                and distance <= config.ARRIVE_DISTANCE_MM
            ):
                stop_boat(boat_id)

                print()
                print(
                    f"[AUTO] target reached "
                    f"({distance:.1f} mm)"
                )
                return

            elapsed = time.monotonic() - started
            delay = config.CONTROL_INTERVAL_SEC - elapsed

            if delay > 0:
                time.sleep(delay)

    finally:
        stop_boat(boat_id)


# ============================================================
# 8. 参数
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--test",
        action="store_true",
        help="按 Enter 模拟洪水，不等待水位 ESP32"
    )

    parser.add_argument(
        "--no-start-vision",
        action="store_true",
        help="666.py 已经单独运行时使用"
    )

    parser.add_argument(
        "--boat",
        type=int,
        default=config.DEFAULT_BOAT_ID,
        choices=sorted(config.BOAT_IPS),
        help="选择自动控制哪艘船"
    )

    return parser.parse_args()


# ============================================================
# 9. 主流程
# ============================================================

def main():
    args = parse_args()

    print()
    print("=" * 68)
    print("智能城市救援塔 - Raspberry Pi Master V1.1")
    print("=" * 68)
    print("Pi       :", config.PI_IP)
    print("Lift     :", config.LIFT_IP)
    print(
        "Boat     :",
        args.boat,
        "->",
        config.BOAT_IPS[args.boat]
    )
    print(
        "Water    : TCP",
        config.WATER_PORT
    )
    print(
        "Vision   : UDP",
        f"{config.VISION_STATE_HOST}:"
        f"{config.VISION_STATE_PORT}"
    )
    print("=" * 68)
    print()

    vision_receiver = VisionReceiver()
    vision_receiver.start()

    water_receiver = None
    vision_process = None
    vision_log_handle = None

    # 启动时先尝试停车。
    # 如果船没开机，出现 HTTP timeout 不影响总控继续启动。
    stop_boat(args.boat)

    try:
        if not args.no_start_vision:
            vision_process, vision_log_handle = start_vision()

        else:
            print(
                "[VISION] external mode: "
                "please start 666.py with --publish-state"
            )

        # ----------------------------------------------------
        # A. 等待洪水
        # ----------------------------------------------------
        if args.test:
            input(
                "\n[TEST] 按 Enter 模拟洪水来临..."
            )

        else:
            water_receiver = WaterReceiver()
            water_receiver.start()

            print(
                "\n[SYSTEM] waiting for wireless water sensor..."
            )

            water_receiver.flood_event.wait()

        # ----------------------------------------------------
        # B. 洪水触发
        # ----------------------------------------------------
        print()
        print("!" * 68)
        print("[FLOOD] FLOOD DETECTED")
        print("!" * 68)

        if lift_up():
            print("[SYSTEM] lift command sent")
        else:
            print("[SYSTEM] lift command failed")

        time.sleep(config.LIFT_WAIT_SEC)

        # ----------------------------------------------------
        # C. 目前仍人工出船
        # ----------------------------------------------------
        input(
            "\n[MANUAL] 人工把船放到水面，"
            "确认 ArUco 已被摄像头看到后按 Enter..."
        )

        # ----------------------------------------------------
        # D. 自动救人
        # ----------------------------------------------------
        autonomous_rescue(
            vision_receiver,
            args.boat
        )

        print("\n[SYSTEM] rescue round finished")

    except KeyboardInterrupt:
        print("\n[EMERGENCY] Ctrl+C -> STOP")

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
                vision_process.wait(timeout=2.0)
            except Exception:
                try:
                    vision_process.kill()
                except Exception:
                    pass

        if vision_log_handle is not None:
            try:
                vision_log_handle.close()
            except Exception:
                pass

        print("[SYSTEM] boat STOP sent, master closed")


if __name__ == "__main__":
    main()
