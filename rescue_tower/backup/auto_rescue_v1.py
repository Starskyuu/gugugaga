#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
城市方舟 / 智能救援塔
无人小船自动救人 V1 —— 独立联调版

用途：
    单独验证最后一段闭环：

    666.py 识别船 + 人
        ↓
    UDP 输出世界坐标
        ↓
    本程序计算目标方向
        ↓
    HTTP 控制 ESP32 小船
        ↓
    自动转向 / 前进 / 靠近 / 停车

默认控制：
    Boat 0 -> 192.168.43.14

运行：
    python3 auto_rescue_v1.py

指定船：
    python3 auto_rescue_v1.py --boat 1
    python3 auto_rescue_v1.py --boat 2

如果 666.py 已经在另一个终端以 --publish-state 运行：
    python3 auto_rescue_v1.py --no-start-vision

安全：
    - 启动先 STOP
    - 视觉状态超时立即 STOP
    - 坐标系不安全立即 STOP
    - 看不到船立即 STOP
    - 看不到人立即 STOP
    - Ctrl+C 立即 STOP
"""

import argparse
import json
import math
import os
import socket
import subprocess
import sys
import threading
import time


# ============================================================
# 1. 配置
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

VISION_FILE = os.path.join(BASE_DIR, "666.py")

# 666.py 已有的 UDP 状态输出接口
VISION_HOST = "127.0.0.1"
VISION_PORT = 9101
VISION_HZ = 10

# ArUco ID -> 小船 IP
BOAT_IPS = {
    0: "192.168.43.14",
    1: "192.168.43.18",
    2: "192.168.43.20",
}

DEFAULT_BOAT_ID = 0


# ============================================================
# 2. 自动控制参数
# ============================================================

# 距离人员多少 mm 时认为已经到达。
# 第一版保守一点，不让船直接撞人。
ARRIVE_DISTANCE_MM = 65.0

# 船头偏差大于这个角度：原地转向。
TURN_START_DEG = 20.0

# 偏差小于这个角度：允许前进。
FORWARD_ALLOW_DEG = 12.0

# 进入人员附近后，用 F/S 交替实现“软件减速”。
SLOW_APPROACH_DISTANCE_MM = 140.0

# 主控制周期。
# 原小船程序 700 ms 没指令会自动停车，
# 所以这里约每 0.20 s 重新发一次命令。
CONTROL_PERIOD_SEC = 0.20

# 视觉 UDP 超过多久没更新就停车。
VISION_STATE_TIMEOUT_SEC = 1.0

# HTTP 连接超时
HTTP_TIMEOUT_SEC = 0.45

# 连续看到几次有效状态，才允许正式起步。
# 避免刚启动视觉时数据抖一下，小船就突然动。
ARM_STABLE_COUNT = 5


# ============================================================
# 3. HTTP 控船
# ============================================================

def send_boat_command(boat_id, command):
    """
    小船原程序已有：
        /F 前进
        /B 后退
        /L 左转
        /R 右转
        /S 停止

    返回 True 表示 TCP/HTTP 请求至少成功发出。
    """
    ip = BOAT_IPS[boat_id]

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(HTTP_TIMEOUT_SEC)

    try:
        s.connect((ip, 80))

        request = (
            f"GET /{command} HTTP/1.1\r\n"
            f"Host: {ip}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("utf-8")

        s.sendall(request)

        # ESP32 回包不是控制所必需，只尝试读取一点。
        try:
            s.recv(128)
        except socket.timeout:
            pass

        return True

    except OSError as exc:
        print(f"[BOAT ERROR] {ip} /{command} -> {exc}")
        return False

    finally:
        try:
            s.close()
        except Exception:
            pass


def emergency_stop(boat_id):
    send_boat_command(boat_id, "S")


# ============================================================
# 4. 接收 666.py 状态
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

        sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        sock.bind(
            (VISION_HOST, VISION_PORT)
        )

        sock.settimeout(1.0)

        print(
            f"[VISION] Listening UDP "
            f"{VISION_HOST}:{VISION_PORT}"
        )

        try:
            while self.running:
                try:
                    data, _ = sock.recvfrom(65535)

                except socket.timeout:
                    continue

                except OSError:
                    break

                try:
                    state = json.loads(
                        data.decode("utf-8")
                    )

                    with self.lock:
                        self.latest_state = state
                        self.latest_time = time.monotonic()

                except Exception as exc:
                    print(
                        "[VISION] JSON ERROR:",
                        exc
                    )

        finally:
            try:
                sock.close()
            except Exception:
                pass


# ============================================================
# 5. 启动 666.py
# ============================================================

def start_vision():
    if not os.path.exists(VISION_FILE):
        raise FileNotFoundError(
            f"找不到 {VISION_FILE}\n"
            "请把 auto_rescue_v1.py 与 666.py 放在同一个文件夹。"
        )

    cmd = [
        sys.executable,
        VISION_FILE,
        "--publish-state",
        "--state-host",
        VISION_HOST,
        "--state-port",
        str(VISION_PORT),
        "--state-hz",
        str(VISION_HZ),
    ]

    print(
        "[VISION] Start:",
        " ".join(cmd)
    )

    return subprocess.Popen(cmd)


# ============================================================
# 6. 几何计算
# ============================================================

def normalize_error(angle_deg):
    """
    将角度误差限制到 [-180, 180)
    """
    return (
        angle_deg + 180.0
    ) % 360.0 - 180.0


def choose_nearest_person(
    persons,
    boat_x,
    boat_y
):
    """
    第一版只做最简单可靠策略：
    选择离当前船最近的人。

    后面接 jisuan / 多船任务分配时，
    替换这里即可。
    """
    valid = []

    for p in persons:
        if not p.get(
            "inside_field",
            True
        ):
            continue

        x = float(p["x"])
        y = float(p["y"])

        d = math.hypot(
            x - boat_x,
            y - boat_y
        )

        valid.append(
            (d, p)
        )

    if not valid:
        return None

    valid.sort(
        key=lambda item: item[0]
    )

    return valid[0][1]


def calculate_navigation(
    boat,
    person,
    previous_command
):
    """
    666.py 的角度约定：
        +Y = 0°
        +X = 90°

    因此目标方向：
        atan2(dx, dy)

    而不是常见的 atan2(dy, dx)。
    """

    bx = float(
        boat["x"]
    )

    by = float(
        boat["y"]
    )

    heading = boat.get(
        "angle_deg"
    )

    tx = float(
        person["x"]
    )

    ty = float(
        person["y"]
    )

    dx = tx - bx
    dy = ty - by

    distance = math.hypot(
        dx,
        dy
    )

    # ----------------------------------------
    # 1. 到达
    # ----------------------------------------

    if distance <= ARRIVE_DISTANCE_MM:
        return {
            "command": "S",
            "distance": distance,
            "desired": None,
            "error": None,
            "arrived": True,
        }

    # ----------------------------------------
    # 2. 没有可靠角度
    # ----------------------------------------

    if heading is None:
        return {
            "command": "S",
            "distance": distance,
            "desired": None,
            "error": None,
            "arrived": False,
        }

    heading = float(
        heading
    )

    desired = (
        math.degrees(
            math.atan2(
                dx,
                dy
            )
        )
        % 360.0
    )

    error = normalize_error(
        desired - heading
    )

    # ----------------------------------------
    # 3. 转向
    #
    # 带一点迟滞：
    # 大于 20° -> 一定转
    # 小于 12° -> 一定前进
    # 中间区域沿用前一动作，减少左右抖动
    # ----------------------------------------

    if error >= TURN_START_DEG:
        command = "R"

    elif error <= -TURN_START_DEG:
        command = "L"

    elif abs(error) <= FORWARD_ALLOW_DEG:
        command = "F"

    else:
        # 12° ~ 20°：
        # 如果刚才还在转，就继续同方向转；
        # 否则前进。
        if previous_command in (
            "L",
            "R"
        ):
            command = previous_command
        else:
            command = "F"

    return {
        "command": command,
        "distance": distance,
        "desired": desired,
        "error": error,
        "arrived": False,
    }


# ============================================================
# 7. 从视觉状态中取指定船
# ============================================================

def get_boat_from_state(
    state,
    boat_id
):
    boats = state.get(
        "boats",
        {}
    )

    # JSON 会把 int key 转成 str
    boat = boats.get(
        str(boat_id)
    )

    if boat is None:
        boat = boats.get(
            boat_id
        )

    return boat


def state_is_safe(
    state,
    age,
    boat_id
):
    """
    返回：
        safe, reason, boat, persons
    """

    if state is None:
        return (
            False,
            "NO VISION STATE",
            None,
            []
        )

    if (
        age is None
        or age
        > VISION_STATE_TIMEOUT_SEC
    ):
        return (
            False,
            "VISION TIMEOUT",
            None,
            []
        )

    if not state.get(
        "vision_ok_for_control",
        False
    ):
        return (
            False,
            "CONTROL HOLD",
            None,
            []
        )

    boat = get_boat_from_state(
        state,
        boat_id
    )

    if boat is None:
        return (
            False,
            f"BOAT {boat_id} LOST",
            None,
            []
        )

    if not boat.get(
        "inside_field",
        True
    ):
        return (
            False,
            "BOAT OUTSIDE FIELD",
            boat,
            []
        )

    persons = state.get(
        "persons",
        []
    )

    persons = [
        p for p in persons
        if p.get(
            "inside_field",
            True
        )
    ]

    if not persons:
        return (
            False,
            "NO PERSON",
            boat,
            []
        )

    return (
        True,
        "READY",
        boat,
        persons
    )


# ============================================================
# 8. 等待系统稳定
# ============================================================

def wait_until_ready(
    receiver,
    boat_id
):
    print()
    print(
        "[AUTO] 等待视觉、坐标、船和人员全部稳定..."
    )

    stable_count = 0
    last_reason = None

    while True:
        state, age = receiver.get()

        (
            safe,
            reason,
            boat,
            persons
        ) = state_is_safe(
            state,
            age,
            boat_id
        )

        if safe:
            stable_count += 1

            print(
                f"\r[AUTO] READY "
                f"{stable_count}/{ARM_STABLE_COUNT} "
                f"| Boat {boat_id} "
                f"| persons={len(persons)}      ",
                end="",
                flush=True
            )

            if (
                stable_count
                >= ARM_STABLE_COUNT
            ):
                print()
                return

        else:
            stable_count = 0

            if reason != last_reason:
                print(
                    f"\n[AUTO] WAIT: {reason}"
                )

                last_reason = reason

            emergency_stop(
                boat_id
            )

        time.sleep(
            CONTROL_PERIOD_SEC
        )


# ============================================================
# 9. 自动救援主循环
# ============================================================

def run_auto_rescue(
    receiver,
    boat_id
):
    previous_command = "S"
    slow_toggle = False
    last_print = 0.0

    print()
    print("=" * 70)
    print(
        f"AUTO RESCUE START | "
        f"Boat {boat_id} -> "
        f"{BOAT_IPS[boat_id]}"
    )
    print(
        "Ctrl+C = EMERGENCY STOP"
    )
    print("=" * 70)

    try:
        while True:
            loop_start = time.monotonic()

            state, age = receiver.get()

            (
                safe,
                reason,
                boat,
                persons
            ) = state_is_safe(
                state,
                age,
                boat_id
            )

            # --------------------------------------------
            # 任何视觉异常：立刻停
            # --------------------------------------------

            if not safe:
                if previous_command != "S":
                    print(
                        f"\n[SAFE STOP] {reason}"
                    )

                emergency_stop(
                    boat_id
                )

                previous_command = "S"

                time.sleep(
                    CONTROL_PERIOD_SEC
                )

                continue

            # --------------------------------------------
            # 选择离船最近的人
            # --------------------------------------------

            target = choose_nearest_person(
                persons,
                float(boat["x"]),
                float(boat["y"])
            )

            if target is None:
                emergency_stop(
                    boat_id
                )

                previous_command = "S"

                time.sleep(
                    CONTROL_PERIOD_SEC
                )

                continue

            # --------------------------------------------
            # 算控制动作
            # --------------------------------------------

            nav = calculate_navigation(
                boat,
                target,
                previous_command
            )

            command = nav[
                "command"
            ]

            distance = nav[
                "distance"
            ]

            # --------------------------------------------
            # 靠近人员时进行简单软件减速
            #
            # 只在“本来应该前进”的情况下 F/S 交替，
            # 转向仍然正常转。
            # --------------------------------------------

            actual_command = command

            if (
                command == "F"
                and distance
                < SLOW_APPROACH_DISTANCE_MM
            ):
                slow_toggle = (
                    not slow_toggle
                )

                actual_command = (
                    "F"
                    if slow_toggle
                    else "S"
                )

            else:
                slow_toggle = False

            # --------------------------------------------
            # 发命令
            # --------------------------------------------

            send_boat_command(
                boat_id,
                actual_command
            )

            previous_command = (
                command
            )

            # --------------------------------------------
            # 打印状态
            # --------------------------------------------

            now = time.monotonic()

            if (
                now - last_print
                >= 0.5
            ):
                heading = boat.get(
                    "angle_deg"
                )

                desired = nav[
                    "desired"
                ]

                error = nav[
                    "error"
                ]

                if (
                    desired is None
                    or error is None
                ):
                    print(
                        f"[AUTO] "
                        f"boat=({boat['x']:.1f},"
                        f"{boat['y']:.1f}) "
                        f"target=({target['x']:.1f},"
                        f"{target['y']:.1f}) "
                        f"dist={distance:.1f}mm "
                        f"-> {actual_command}"
                    )

                else:
                    print(
                        f"[AUTO] "
                        f"boat=({boat['x']:.1f},"
                        f"{boat['y']:.1f}) "
                        f"heading={float(heading):.1f}° | "
                        f"target=({target['x']:.1f},"
                        f"{target['y']:.1f}) "
                        f"dist={distance:.1f}mm | "
                        f"want={desired:.1f}° "
                        f"err={error:+.1f}° "
                        f"-> {actual_command}"
                    )

                last_print = now

            # --------------------------------------------
            # 到达人员
            # --------------------------------------------

            if nav[
                "arrived"
            ]:
                emergency_stop(
                    boat_id
                )

                print()
                print(
                    "=" * 70
                )

                print(
                    f"[ARRIVED] Boat {boat_id} "
                    f"距离人员 {distance:.1f} mm"
                )

                print(
                    "[ARRIVED] 小船已停止"
                )

                print(
                    "=" * 70
                )

                return

            # --------------------------------------------
            # 保持固定控制周期
            # --------------------------------------------

            elapsed = (
                time.monotonic()
                - loop_start
            )

            remaining = (
                CONTROL_PERIOD_SEC
                - elapsed
            )

            if remaining > 0:
                time.sleep(
                    remaining
                )

    finally:
        emergency_stop(
            boat_id
        )


# ============================================================
# 10. 参数
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--boat",
        type=int,
        default=DEFAULT_BOAT_ID,
        choices=sorted(
            BOAT_IPS.keys()
        ),
        help="控制哪艘船，默认 Boat 0"
    )

    parser.add_argument(
        "--no-start-vision",
        action="store_true",
        help=(
            "666.py 已经在另一个终端运行时使用"
        )
    )

    return parser.parse_args()


# ============================================================
# 11. Main
# ============================================================

def main():
    args = parse_args()

    boat_id = args.boat

    print()
    print("=" * 70)
    print(
        "城市方舟 - 无人小船自动救人 V1"
    )
    print("=" * 70)
    print(
        f"Boat ID : {boat_id}"
    )
    print(
        f"Boat IP : {BOAT_IPS[boat_id]}"
    )
    print(
        f"Vision  : UDP "
        f"{VISION_HOST}:{VISION_PORT}"
    )
    print(
        f"Arrival : {ARRIVE_DISTANCE_MM:.0f} mm"
    )
    print(
        f"Slow    : < "
        f"{SLOW_APPROACH_DISTANCE_MM:.0f} mm"
    )
    print("=" * 70)

    # ----------------------------------------
    # 启动先停车
    # ----------------------------------------

    emergency_stop(
        boat_id
    )

    receiver = VisionReceiver()
    receiver.start()

    vision_process = None

    try:
        # ------------------------------------
        # 启动视觉
        # ------------------------------------

        if not args.no_start_vision:
            vision_process = start_vision()

        else:
            print()
            print(
                "[VISION] 请确保另一个终端正在运行："
            )
            print(
                "python3 666.py --publish-state"
            )

        # ------------------------------------
        # 等待稳定
        # ------------------------------------

        wait_until_ready(
            receiver,
            boat_id
        )

        print()
        print(
            "[READY] 已稳定识别："
        )
        print(
            "- 场地坐标系正常"
        )
        print(
            f"- Boat {boat_id} 正常"
        )
        print(
            "- 至少 1 个 Person 正常"
        )
        print()

        input(
            "确认船已在水中、周围无人接触船体后，"
            "按 Enter 开始自动救人..."
        )

        # 启动前再取一次 STOP
        emergency_stop(
            boat_id
        )

        time.sleep(
            0.3
        )

        run_auto_rescue(
            receiver,
            boat_id
        )

    except KeyboardInterrupt:
        print()
        print(
            "[EMERGENCY] Ctrl+C -> STOP"
        )

    finally:
        emergency_stop(
            boat_id
        )

        receiver.stop()

        if vision_process is not None:
            try:
                vision_process.terminate()
                vision_process.wait(
                    timeout=2
                )

            except Exception:
                try:
                    vision_process.kill()
                except Exception:
                    pass

        print(
            "[SYSTEM] Boat STOP / Program exit"
        )


if __name__ == "__main__":
    main()
