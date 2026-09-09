#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线闭环测试：用假硬件验证 救援总控.py 的整条控制链路
============================================================
假小船 + 假升降台 + 假水位板 + 假 666.py 视觉，全部走真实网络协议
（HTTP / TCP / UDP，和树莓派上一模一样），然后以 --live 模式启动总控，
断言它在没有任何真机的情况下能完成：

    水位触发 -> 升台 /U -> 摄像头看到船 -> 找到人 -> 自动航行 -> 停船到达

关键点：假船严格按收到的命令用差速模型推进（F 前进、L/R 原地转、S 停），
绝不瞬移到目标——否则总控的导航控制律根本测不出来。

用法：
    python 测试/mock_hardware.py

退出码：0 = 通过；1 = 失败（说明总控逻辑有问题，先别上真机）
"""

import json
import math
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# ============================================================
# 一、测试用端口（全部是回环地址，不影响任何真机）
# ============================================================

# 假 ESP32 的 HTTP 端口：先试 80（与真固件一致），被占用就换 18001
try:
    _s = socket.socket()
    _s.bind(("127.0.0.1", 80))
    _s.close()
    HTTP_PORT = 80
except OSError:
    HTTP_PORT = 18001

BOAT_IP = "127.0.0.1"       # 假小船（回环地址 A）
LIFT_IP = "127.0.0.2"       # 假升降台（回环地址 B，与船同端口不冲突）
WATER_PORT = 15000          # 总控的水位 TCP 监听口（--water-port 覆盖）
VISION_PORT = 19101         # 总控的视觉 UDP 口（--vision-port 覆盖）
WEB_PORT = 18080            # 总控网页口（--web-port 覆盖）

PERSON_X, PERSON_Y = 420.0, 300.0    # 假人位置（假视觉一直报告这里有人）

# ============================================================
# 二、共享的假船状态
# ============================================================

船 = {"x": 120.0, "y": 150.0, "heading": 90.0}
命令锁 = threading.Lock()
船命令 = "S"
记录 = {"boat": [], "lift": []}       # 收过的命令，供断言

SPEED_MM_PER_S = 80.0     # F 全速
TURN_DEG_PER_S = 90.0     # L/R 原地转速


# ============================================================
# 三、假小船 HTTP 服务（与 ESP32 固件同款路径）
# ============================================================

class 假船处理器(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        global 船命令
        cmd = urlparse(self.path).path.lstrip("/")
        if cmd in ("F", "B", "L", "R", "S"):
            with 命令锁:
                船命令 = cmd
                记录["boat"].append(cmd)
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()


class 假台处理器(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/U", "/D"):
            记录["lift"].append(path)
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()


# ============================================================
# 四、假船物理推进（差速模型，绝不瞬移）
# ============================================================

def 物理推进():
    while True:
        with 命令锁:
            cmd = 船命令
        dt = 0.05
        h = 船["heading"]
        r = math.radians(h)
        if cmd == "F":
            船["x"] = min(600, max(0, 船["x"] + SPEED_MM_PER_S * dt * math.sin(r)))
            船["y"] = min(600, max(0, 船["y"] + SPEED_MM_PER_S * dt * math.cos(r)))
        elif cmd == "B":
            船["x"] = min(600, max(0, 船["x"] - SPEED_MM_PER_S * 0.6 * dt * math.sin(r)))
            船["y"] = min(600, max(0, 船["y"] - SPEED_MM_PER_S * 0.6 * dt * math.cos(r)))
        elif cmd == "L":
            船["heading"] = (h - TURN_DEG_PER_S * dt) % 360
        elif cmd == "R":
            船["heading"] = (h + TURN_DEG_PER_S * dt) % 360
        time.sleep(dt)


# ============================================================
# 五、假 666.py 视觉（UDP，10Hz，666.py 的真实 JSON 格式）
# ============================================================

def 假视觉发送():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        with 命令锁:
            b = dict(船)
        pkg = {
            "type": "vision",
            "version": 1,
            "field": {"width_mm": 600, "height_mm": 600, "unit": "mm"},
            "coordinate_ready": True,
            "vision_ok_for_control": True,
            "boats": {"0": {"x": b["x"], "y": b["y"], "angle_deg": b["heading"],
                            "inside_field": True, "age_sec": 0.02}},
            "persons": [{"x": PERSON_X, "y": PERSON_Y, "confidence": 0.9,
                         "inside_field": True, "age_sec": 0.02}],
        }
        sock.sendto(json.dumps(pkg).encode("utf-8"), ("127.0.0.1", VISION_PORT))
        time.sleep(0.1)


# ============================================================
# 六、假水位板（TCP 客户端，4 秒后水位拉高）
# ============================================================

def 假水位发送():
    t0 = time.monotonic()
    while True:
        try:
            conn = socket.create_connection(("127.0.0.1", WATER_PORT), timeout=2)
            while True:
                adc = 38000 if time.monotonic() - t0 >= 4 else 31000
                conn.sendall(f"Water:{adc}".encode("utf-8"))
                time.sleep(0.3)
        except OSError:
            time.sleep(0.5)      # 总控还没起来，重试


# ============================================================
# 七、主流程
# ============================================================

def 总控路径():
    import pathlib
    return pathlib.Path(__file__).resolve().parent.parent / "救援总控.py"


def 查状态():
    """问总控网页要 JSON 状态。"""
    try:
        sock = socket.create_connection(("127.0.0.1", WEB_PORT), timeout=1.5)
        sock.sendall(b"GET /api/status HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n")
        data = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
        sock.close()
        body = data.split(b"\r\n\r\n", 1)[1]
        return json.loads(body.decode("utf-8"))
    except OSError:
        return None


def main():
    print("=" * 64)
    print("救援塔总控 · 离线闭环测试（假硬件，真协议）")
    print("=" * 64)
    print(f"假船 HTTP   {BOAT_IP}:{HTTP_PORT}")
    print(f"假台 HTTP   {LIFT_IP}:{HTTP_PORT}")
    print(f"假水位 TCP  127.0.0.1:{WATER_PORT}")
    print(f"假视觉 UDP  127.0.0.1:{VISION_PORT}")
    print(f"总控网页    127.0.0.1:{WEB_PORT}")
    print("=" * 64)

    # 1. 起假硬件
    server_boat = ThreadingHTTPServer((BOAT_IP, HTTP_PORT), 假船处理器)
    server_lift = ThreadingHTTPServer((LIFT_IP, HTTP_PORT), 假台处理器)
    for s in (server_boat, server_lift):
        threading.Thread(target=s.serve_forever, daemon=True).start()
    threading.Thread(target=物理推进, daemon=True).start()
    threading.Thread(target=假视觉发送, daemon=True).start()
    threading.Thread(target=假水位发送, daemon=True).start()
    print("[测试] 假硬件已启动")

    # 2. 起总控（--live：连这些假硬件）
    cmd = [
        sys.executable, str(总控路径()),
        "--live", "--web", "--no-start-vision",
        "--boat-ip", BOAT_IP,
        "--lift-ip", LIFT_IP,
        "--http-port", str(HTTP_PORT),
        "--water-port", str(WATER_PORT),
        "--vision-port", str(VISION_PORT),
        "--web-port", str(WEB_PORT),
        "--lift-wait", "1",
    ]
    print("[测试] 启动总控:", " ".join(cmd[1:]))
    import pathlib
    总控日志 = pathlib.Path(__file__).resolve().parent / "总控输出.log"
    log_file = open(总控日志, "w", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        cmd,
        stdout=log_file, stderr=subprocess.STDOUT,
    )

    # 3. 轮询总控网页，等 ARRIVED / EMERGENCY
    deadline = time.monotonic() + 90
    last_stage = None
    stage = None
    try:
        while time.monotonic() < deadline:
            st = 查状态()
            if st:
                stage = st.get("stage")
                if stage != last_stage:
                    print(f"[测试] 总控阶段 -> {stage} ({st.get('stage_cn')})")
                    last_stage = stage
            if stage in ("ARRIVED", "EMERGENCY"):
                break
            time.sleep(0.5)
    finally:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except Exception:
            pass
        log_file.close()
        try:
            总控输出 = 总控日志.read_text(encoding="utf-8", errors="replace")
        except Exception:
            总控输出 = ""

    # 4. 断言
    print()
    print("=" * 64)
    print("测试结果")
    print("=" * 64)
    errors = []
    if stage != "ARRIVED":
        errors.append(f"最终阶段是 {stage}，期望 ARRIVED")
    if "/U" not in 记录["lift"]:
        errors.append("升降台从未收到 /U（升台指令）")
    if "F" not in 记录["boat"]:
        errors.append("小船从未收到 /F（前进指令）")
    if 记录["boat"] and 记录["boat"][-1] != "S":
        errors.append(f"小船最后一条命令是 {记录['boat'][-1]}，期望 S（停车）")
    if not 记录["boat"]:
        errors.append("小船没收到任何命令")

    print(f"船收到命令序列: {记录['boat']}")
    print(f"升降台收到命令: {记录['lift']}")
    print(f"最终船位置    : ({船['x']:.1f}, {船['y']:.1f}) 目标 ({PERSON_X}, {PERSON_Y}) "
          f"距离 {math.hypot(船['x']-PERSON_X, 船['y']-PERSON_Y):.1f} mm")

    if errors:
        print("\n[失败]")
        for e in errors:
            print("  -", e)
        print(f"\n----- 总控输出（完整，见 {总控日志}）-----")
        lines = (总控输出 or "").splitlines()
        print("\n".join(lines[-60:]))
        sys.exit(1)
    print("\n[通过] 整条链路闭环成功：水位触发 -> 升台 -> 找船 -> 找人 -> 自动航行 -> 停船到达")
    sys.exit(0)


if __name__ == "__main__":
    main()
