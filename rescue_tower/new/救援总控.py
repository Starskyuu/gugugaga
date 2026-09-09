#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能城市救援塔 —— 树莓派总控（一键网页版）
============================================================
整条流程：
    水位传感 -> 树莓派 -> 升降台升起 -> 人工放船 -> 找人 -> 无人船自动靠近并停船

日常用法（全部在 new/ 目录下执行）：
    树莓派一键启动：     bash start.sh
    或直接：             python3 救援总控.py --live --web
    电脑上离线演示：     python 救援总控.py --demo         （自动带网页，不连任何硬件）

单模块调试（不加 --live 只是模拟打印，加了才真动设备）：
    python 救援总控.py --check-water [--live]    持续看水位读数/基线/阈值
    python 救援总控.py --check-vision [--live]   持续看船/人坐标（666 需已启动）
    python 救援总控.py --lift U|D [--live]       升降台升降
    python 救援总控.py --boat F|B|L|R|S 秒数 [--live]   小船手动动作

网页（启动后浏览器打开 http://树莓派IP:8080）：
    - 一键开始：不等水位传感器，直接触发整条流程
    - 已放船确认：升台完成后人工把船放下去，点一下（或等摄像头自动看到船）
    - 急停：任何时刻点它，小船立刻停
    - 手动船/升降台按钮：现场调试用
    - 实时俯视图：场地上的船和人都画在图上

安全设计：
    - 小船固件 700ms 收不到命令自动停车；本程序每 0.2s 发一次命令续命
    - 视觉数据掉线/过期：立即发停车
    - 靠近目标自动降半速，防止撞上
    - 任何异常退出前，都会给小船发 /S 停车
    - 全程事件打印带时间，同时显示在网页上
"""

import argparse
import json
import math
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# 同目录的配置：所有 IP / 阈值 / 速度都在 config.py 里改
import config


# ============================================================================
# 一、小工具
# ============================================================================

def 事件(msg):
    """打印一条带时间的流程事件，同时收进网页事件列表。"""
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line)
    if 总控实例 is not None:
        总控实例.记事件(msg)


def wrap_deg(a):
    """角度归一到 [-180, 180)。"""
    a = a % 360.0
    return a - 360.0 if a > 180.0 else a


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# 全局单例，方便网页线程回调主控；模块级函数"事件()"也依赖它
总控实例 = None


def http_get(ip, path, timeout=config.HTTP_TIMEOUT_S):
    """给 ESP32 发一条 HTTP GET。

    旧固件只认路径（/F /B /L /R /S /U /D），不返回 JSON。
    只要 TCP 连上并成功发出请求，就算命令送达。返回 True/False。
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect((ip, config.HTTP_PORT))
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {ip}\r\n"
            "Connection: close\r\n"
            "\r\n"
        ).encode("utf-8")
        sock.sendall(request)
        try:
            sock.recv(256)   # 旧固件会回一段网页，读掉避免占着连接
        except socket.timeout:
            pass
        return True
    except OSError as exc:
        事件(f"[HTTP 失败] {ip}{path} -> {exc}")
        return False
    finally:
        try:
            sock.close()
        except OSError:
            pass


# ============================================================================
# 二、UDP 收件箱（接收 666.py 视觉状态）
# ============================================================================

class UDP收件箱:
    """后台线程只保留最新一包；坏包直接丢弃，不刷新心跳时间。"""

    def __init__(self, port, 校验):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", port))
        self.sock.settimeout(0.3)
        self.校验 = 校验
        self._lock = threading.Lock()
        self.packet = None      # 最新有效包
        self.at = 0.0           # 收到时间
        self._stop = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while not self._stop.is_set():
            try:
                raw, _ = self.sock.recvfrom(60000)
            except socket.timeout:
                continue
            except OSError:
                return
            try:
                data = json.loads(raw.decode("utf-8"))
                self.校验(data)
            except (ValueError, KeyError, TypeError):
                continue          # 坏包忽略，不算心跳
            with self._lock:
                self.packet, self.at = data, time.monotonic()

    def latest(self, max_age):
        """取最新包；没有或太旧抛 RuntimeError。"""
        with self._lock:
            if self.packet is None or time.monotonic() - self.at > max_age:
                raise RuntimeError("视觉数据过期或未收到")
            return self.packet

    def has_fresh(self, max_age):
        """探测用：有没有新鲜数据（不抛异常）。"""
        with self._lock:
            return self.packet is not None and time.monotonic() - self.at <= max_age

    def close(self):
        self._stop.set()
        try:
            self.sock.close()
        except OSError:
            pass


def 校验视觉(d):
    """666.py --publish-state 的 version=1 包格式检查。"""
    if d.get("type") != "vision" or d.get("version") != 1:
        raise ValueError("不是视觉状态包")
    f = d.get("field") or {}
    if f.get("unit") != "mm":
        raise ValueError("场地单位不是 mm")


def 解析视觉(d):
    """从视觉包里取船位和人的坐标。返回 (船, [人...])，缺失为 None。"""
    if not (d.get("coordinate_ready") and d.get("vision_ok_for_control")):
        return None, []          # 标定/Homography 未就绪，坐标不可信

    def fresh(age):
        # 注意：age_sec 是 666.py 自己算的"该目标最近一次被检测到距当前包的秒数"，
        # 已经在 666.py 进程里归一过（0 = 刚刚看到），直接和阈值比即可，
        # 不要和本进程 time.monotonic() 混算。
        return isinstance(age, (int, float)) and 0 <= age < 1.0

    boat = None
    for key, p in (d.get("boats") or {}).items():
        # JSON 的 key 一定是字符串，BOAT_ID 可能是 int
        if str(key) == str(config.BOAT_ID) and fresh(p.get("age_sec")) \
                and p.get("inside_field") and isinstance(p.get("angle_deg"), (int, float)):
            boat = {"x": float(p["x"]), "y": float(p["y"]),
                    "heading": float(p["angle_deg"]), "age": p["age_sec"]}
            break

    persons = []
    for p in d.get("persons") or []:
        if fresh(p.get("age_sec")) and p.get("inside_field") \
                and isinstance(p.get("x"), (int, float)) \
                and isinstance(p.get("y"), (int, float)):
            persons.append({"x": float(p["x"]), "y": float(p["y"]),
                            "age": p["age_sec"]})
    return boat, persons


# ============================================================================
# 三、水位 TCP 接收（水位 ESP32 主动连树莓派）
# ============================================================================

class 水位接收:
    """监听 TCP 端口，接收水位板发来的 "Water:12345"（无换行，按前缀切分）。

    触发逻辑：
      1. 先收集 WATER_BASELINE_SAMPLES 个值，取中位数当干燥基线
      2. 之后每个值 >= 基线+差值（或 >= 绝对值阈值）记一次高水位
      3. 连续 WATER_TRIGGER_COUNT 次高水位 -> flood_event 置位
    """

    def __init__(self, port):
        self.port = port
        self.flood_event = threading.Event()
        self.running = True

        self.latest_value = None     # 最近一次读数（网页显示）
        self.baseline = None         # 干燥基线
        self.baseline_values = []
        self.high_count = 0
        self.high_since = None       # 最近一次开始连续报警的时间
        self.connected = False       # 有没有水位板连着

        self._lock = threading.Lock()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="水位接收")
        self._thread.start()

    # ---- 数据入口 ----
    def _process_value(self, value):
        with self._lock:
            self.latest_value = value

        # 阶段一：还没凑够基线
        if self.baseline is None:
            self.baseline_values.append(value)
            事件(f"[水位] 基线收集中 {len(self.baseline_values)}"
                 f"/{config.WATER_BASELINE_SAMPLES} -> {value}")
            if len(self.baseline_values) >= config.WATER_BASELINE_SAMPLES:
                ordered = sorted(self.baseline_values)
                self.baseline = ordered[len(ordered) // 2]
                事件(f"[水位] 基线就绪 = {self.baseline}，"
                     f"触发阈值 = {self.触发阈值()}")
            return

        # 阶段二：判断高低
        high = value >= self.触发阈值()
        if high:
            self.high_count += 1
            self.high_since = self.high_since or time.monotonic()
            事件(f"[水位] 高水位 {value} >= {self.触发阈值()} "
                 f"({self.high_count}/{config.WATER_TRIGGER_COUNT})")
            if self.high_count >= config.WATER_TRIGGER_COUNT:
                self.flood_event.set()
        else:
            self.high_count = 0
            self.high_since = None

    def 触发阈值(self):
        thr = self.baseline + config.WATER_DELTA_TRIGGER
        if config.WATER_ABS_TRIGGER:
            thr = min(thr, config.WATER_ABS_TRIGGER)
        return thr

    # ---- TCP 服务 ----
    def _run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("0.0.0.0", self.port))
        server.listen(2)
        server.settimeout(1.0)
        事件(f"[水位] 监听 TCP 0.0.0.0:{self.port}，等水位板连接")

        try:
            while self.running:
                try:
                    conn, addr = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    return

                事件(f"[水位] 水位板已连接: {addr}")
                with self._lock:
                    self.connected = True
                self._handle_conn(conn)
                with self._lock:
                    self.connected = False
                事件("[水位] 水位板断开，继续等待重连")
        finally:
            server.close()

    def _handle_conn(self, conn):
        """处理一条 TCP 连接。固件发送 Water:数字 且没有换行，
        所以用 'Water:' 前缀切分：看到下一条前缀，上一条才算完整。"""
        conn.settimeout(1.0)
        buffer = ""
        try:
            while self.running:
                try:
                    data = conn.recv(1024)
                except socket.timeout:
                    continue
                if not data:
                    return
                buffer += data.decode("utf-8", "ignore")
                # 只保留最后一个可能不完整的记录
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
                    record, buffer = buffer[:second], buffer[second:]
                    m = re.fullmatch(r"Water:(\d+)", record)
                    if m:
                        self._process_value(int(m.group(1)))
        finally:
            # 断连时把最后一条完整记录也处理掉
            m = re.fullmatch(r"Water:(\d+)", buffer.strip())
            if m:
                self._process_value(int(m.group(1)))
            try:
                conn.close()
            except OSError:
                pass

    def stop(self):
        self.running = False


# ============================================================================
# 四、视觉子进程（666.py）管理
# ============================================================================

def 启动视觉(视觉箱):
    """先探测 UDP 里有没有数据：有 = 666.py 已在跑；没有 = 帮用户启动一个。

    返回 (子进程或 None, 日志文件句柄或 None)。
    """
    # 探测窗口内出现新鲜数据，说明外部已经启动了 666.py
    deadline = time.monotonic() + config.VISION_PROBE_SEC
    while time.monotonic() < deadline:
        if 视觉箱.has_fresh(2.0):
            事件("[视觉] 检测到 666.py 已在运行，采用外部模式")
            return None, None
        time.sleep(0.2)

    if not config.VISION_FILE.exists():
        事件(f"[视觉] 找不到 {config.VISION_FILE}，请手动启动 666.py")
        return None, None

    cmd = [
        sys.executable, str(config.VISION_FILE),
        "--publish-state",
        "--state-host", "127.0.0.1",
        "--state-port", str(config.VISION_PORT),
        "--state-hz", "10",
        "--model", str(config.MODEL_FILE),
        "--jpeg-path", str(config.SNAPSHOT_PATH),
    ]
    if not config.VISION_SHOW_WINDOW:
        cmd.append("--headless")
    if config.CALIB_FILE.exists():
        cmd += ["--calibration", str(config.CALIB_FILE)]
    else:
        事件(f"[视觉] 警告：标定文件不存在 {config.CALIB_FILE}")

    事件("[视觉] 启动 666.py 子进程 ...")

    log_handle = None
    if config.VISION_LOG_TO_FILE:
        config.LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_handle = open(config.LOG_DIR / "vision.log", "a",
                          encoding="utf-8", buffering=1)
        log_handle.write("\n\n========== 视觉启动 "
                         + time.strftime("%Y-%m-%d %H:%M:%S")
                         + " ==========\n")
        proc = subprocess.Popen(cmd, stdout=log_handle,
                                stderr=subprocess.STDOUT)
        事件(f"[视觉] 识别日志 -> {config.LOG_DIR / 'vision.log'}")
    else:
        proc = subprocess.Popen(cmd)

    return proc, log_handle


# ============================================================================
# 五、设备控制（小船 / 升降台）
# ============================================================================

class 设备:
    """封装三块板的 HTTP 控制。演示模式下只打印，不动任何硬件。"""

    def __init__(self, live, demo=None):
        self.live = live
        self.demo = demo
        self.boat_ip = config.BOAT_IP
        self.lift_ip = config.LIFT_IP

    def 船(self, cmd):
        """cmd ∈ F(前) B(后) L(左) R(右) S(停)。"""
        if not self.live:
            self.demo.接收命令(cmd)
            事件(f"[模拟] 小船 -> {cmd}")
            return True
        return http_get(self.boat_ip, "/" + cmd)

    def 升台(self):
        if not self.live:
            事件("[模拟] 升降台 -> /U 升起")
            return True
        return http_get(self.lift_ip, "/U")

    def 降台(self):
        if not self.live:
            事件("[模拟] 升降台 -> /D 降下")
            return True
        return http_get(self.lift_ip, "/D")

    def 全停(self):
        """任何异常兜底：给小船发停车。一块板失败不耽误流程记录。"""
        if not self.live:
            self.demo.接收命令("S")
            事件("[模拟] 全停：小船 /S")
            return
        if not http_get(self.boat_ip, "/S"):
            事件("[警告] 小船停车未确认（可能掉线）")


# ============================================================================
# 六、导航：选目标 -> 规划动作
# ============================================================================

def 最近的人(船, persons):
    if not persons:
        return None
    return min(persons,
               key=lambda p: math.hypot(p["x"] - 船["x"], p["y"] - 船["y"]))


def 规划(船, 目标):
    """根据船位、航向、目标，返回本控制周期要做的动作。

    返回 dict：cmd(F/L/R/S)、dist(目标距离 mm)、err(航向误差 度)。
    """
    dx, dy = 目标["x"] - 船["x"], 目标["y"] - 船["y"]
    dist = math.hypot(dx, dy)
    if dist <= config.ARRIVE_DIST_MM:
        return {"cmd": "S", "dist": dist, "err": 0.0}

    # 666.py 角度约定：+Y=0°，+X=90°（北=0，顺时针为正）
    desired = math.degrees(math.atan2(dx, dy)) % 360.0
    err = wrap_deg(desired - 船["heading"])
    err = err * config.TURN_SIGN       # 现场方向反了就在 config 改 TURN_SIGN

    if abs(err) >= config.TURN_THRESHOLD_DEG:
        return {"cmd": "R" if err > 0 else "L", "dist": dist, "err": err}
    return {"cmd": "F", "dist": dist, "err": err}


# ============================================================================
# 七、演示环境（--demo 模式：不连硬件，模拟整条流程）
# ============================================================================

class 演示环境:
    """模拟水位、666.py 视觉和一条会动的船，用来在电脑上验证闭环。

    关键：模拟船严格按收到的命令用差速模型实时推进（F 前进、L/R 原地转、
    S 停），绝不瞬移——否则控制律有没有写对根本测不出来。
    推进由后台线程每 0.02s 做一次，和真船"命令实时生效"的行为一致。
    """

    def __init__(self):
        self.t0 = time.monotonic()
        self.船 = {"x": 120.0, "y": 150.0, "heading": 90.0}
        self.人 = {"x": 420.0, "y": 300.0}
        self.flood_since = self.t0 + 2.5     # 2.5 秒后"水位报警"
        self.cmd = "S"                        # 最近一次收到的小船命令
        self._lock = threading.Lock()

        # 模拟物理参数
        self.SPEED_MM_PER_S = 80.0            # F 全速前进
        self.TURN_DEG_PER_S = 90.0            # L/R 原地转速

        threading.Thread(target=self._推进, daemon=True).start()

    def 接收命令(self, cmd):
        with self._lock:
            self.cmd = cmd

    def 读水位(self):
        flood = time.monotonic() >= self.flood_since
        return {"flood": flood, "adc": 38000 if flood else 31000}

    def _推进(self):
        """后台差速推进：命令实时生效，与真船一致。"""
        dt = 0.02
        while True:
            with self._lock:
                cmd = self.cmd
                b = dict(self.船)
            heading = b["heading"]
            rad = math.radians(heading)
            if cmd == "F":
                b["x"] = clamp(b["x"] + self.SPEED_MM_PER_S * dt * math.sin(rad),
                               0, config.FIELD_W)
                b["y"] = clamp(b["y"] + self.SPEED_MM_PER_S * dt * math.cos(rad),
                               0, config.FIELD_H)
            elif cmd == "B":
                b["x"] = clamp(b["x"] - self.SPEED_MM_PER_S * 0.6 * dt * math.sin(rad),
                               0, config.FIELD_W)
                b["y"] = clamp(b["y"] - self.SPEED_MM_PER_S * 0.6 * dt * math.cos(rad),
                               0, config.FIELD_H)
            elif cmd == "L":
                b["heading"] = wrap_deg(heading - self.TURN_DEG_PER_S * dt)
            elif cmd == "R":
                b["heading"] = wrap_deg(heading + self.TURN_DEG_PER_S * dt)
            with self._lock:
                self.船 = b
            time.sleep(dt)

    def 读视觉(self):
        """返回当前船状态和模拟的人（666.py 同款数据形状）。"""
        with self._lock:
            船 = dict(self.船)
        now = time.monotonic() - self.t0
        return 船, [dict(self.人, age=now)]


# ============================================================================
# 八、一键网页
# ============================================================================

网页页面 = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>智能城市救援塔 · 总控</title>
<style>
  :root { --bg:#0d1220; --card:#171e30; --line:#2a3550; --txt:#dde6f5;
          --dim:#7d8aa8; --acc:#7c5cff; --ok:#2ecc71; --warn:#f39c12;
          --bad:#e74c3c; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:var(--bg); color:var(--txt);
         font-family:"Microsoft YaHei",system-ui,sans-serif; padding:16px; }
  h1 { font-size:20px; margin-bottom:2px; }
  .sub { color:var(--dim); font-size:12px; margin-bottom:14px; }
  .grid { display:grid; grid-template-columns:minmax(300px,1.1fr) minmax(320px,1fr);
          gap:14px; }
  @media (max-width:760px){ .grid{grid-template-columns:1fr;} }
  .card { background:var(--card); border:1px solid var(--line);
          border-radius:12px; padding:14px; margin-bottom:14px; }
  .stage { display:inline-block; padding:6px 18px; border-radius:20px;
           font-size:17px; font-weight:bold; background:#222c48; }
  .stage.ok   { background:#123a24; color:var(--ok); }
  .stage.run  { background:#33240a; color:var(--warn); }
  .stage.bad  { background:#3a1216; color:var(--bad); }
  .row { display:flex; justify-content:space-between; padding:6px 0;
         border-bottom:1px dashed #232c44; font-size:14px; }
  .row b { color:var(--acc); font-variant-numeric:tabular-nums; }
  .hint { color:var(--dim); font-size:12px; margin-top:8px; line-height:1.6; }
  button { background:#233058; color:var(--txt); border:1px solid #35456f;
           border-radius:9px; padding:10px 14px; margin:4px 4px 4px 0;
           font-size:14px; cursor:pointer; }
  button:hover { background:#2c3d6e; }
  button.primary { background:var(--acc); border-color:var(--acc);
                   font-weight:bold; }
  button.estop { background:#8a2430; border-color:#b03242; font-weight:bold; }
  button:disabled { opacity:.35; cursor:not-allowed; }
  canvas { background:#0a0f1c; border:1px solid var(--line);
           border-radius:10px; width:100%; max-width:420px; display:block; }
  #log { height:170px; overflow-y:auto; font-size:12px; color:var(--dim);
         font-family:Consolas,monospace; line-height:1.7; }
  #snap { width:100%; max-width:420px; border-radius:10px;
          border:1px solid var(--line); display:block; margin-bottom:8px; }
  .tag { font-size:11px; color:var(--dim); }
</style>
</head>
<body>
<h1>智能城市救援塔 · 总控</h1>
<div class="sub">水位传感 → 升降台 → 人工放船 → 找人 → 无人船自动救人</div>

<div class="grid">
<div>
  <div class="card">
    <span class="stage" id="stage">—</span>
    <span class="tag" id="stage-note" style="margin-left:10px"></span>
    <div style="margin-top:12px">
      <button class="primary" id="btn-start" onclick="api('start')">▶ 一键开始</button>
      <button id="btn-confirm" onclick="api('confirm')" disabled>船已放好，开始找</button>
      <button class="estop" onclick="api('estop')">■ 急停</button>
      <button id="btn-reset" onclick="api('reset')" disabled>复位，再救一轮</button>
    </div>
    <div class="hint" id="tip"></div>
  </div>

  <div class="card">
    <div class="row"><span>水位读数</span><b id="w-adc">—</b></div>
    <div class="row"><span>干燥基线 / 阈值</span><b id="w-thr">—</b></div>
    <div class="row"><span>水位状态</span><b id="w-state">—</b></div>
    <div class="row"><span>视觉坐标</span><b id="v-ok">—</b></div>
    <div class="row"><span>船 (x, y) 航向</span><b id="boat">—</b></div>
    <div class="row"><span>目标人 (x, y)</span><b id="person">—</b></div>
    <div class="row"><span>船到目标距离</span><b id="dist">—</b></div>
  </div>

  <div class="card">
    <div class="tag" style="margin-bottom:6px">手动调试（现场确认硬件用）</div>
    <button onclick="api('boat?cmd=F')">小船前进</button>
    <button onclick="api('boat?cmd=B')">小船后退</button>
    <button onclick="api('boat?cmd=L')">小船左转</button>
    <button onclick="api('boat?cmd=R')">小船右转</button>
    <button onclick="api('boat?cmd=S')">小船停</button>
    <button onclick="api('lift?cmd=U')">升降台升</button>
    <button onclick="api('lift?cmd=D')">升降台降</button>
  </div>
</div>

<div>
  <div class="card">
    <img id="snap" alt="摄像头画面" style="display:none">
    <canvas id="map" width="420" height="420"></canvas>
    <div class="tag" style="margin-top:6px">俯视图：▲ 船（箭头=船头方向）· 红点=人 · 黄圈=当前目标</div>
  </div>
  <div class="card">
    <div class="tag" style="margin-bottom:6px">事件日志</div>
    <div id="log"></div>
  </div>
</div>
</div>

<script>
// ---------- 页面元素 ----------
const $ = id => document.getElementById(id);
let lastState = null;

// ---------- 发给总控的命令 ----------
async function api(path) {
  try {
    await fetch('/api/' + path, {method:'POST'});
  } catch (e) { /* 总控重启时忽略 */ }
  setTimeout(refresh, 200);
}

// ---------- 定时拉状态 ----------
async function refresh() {
  let s;
  try {
    const r = await fetch('/api/status');
    s = await r.json();
  } catch (e) {
    $('stage').textContent = '总控离线';
    $('stage').className = 'stage bad';
    return;
  }
  lastState = s;

  // 阶段徽章
  const stageEl = $('stage');
  stageEl.textContent = s.stage_cn;
  stageEl.className = 'stage ' +
    (s.stage === 'ARRIVED' ? 'ok' :
     s.stage === 'EMERGENCY' ? 'bad' :
     s.stage === 'WAIT_WATER' ? '' : 'run');
  $('stage-note').textContent = s.note || '';

  // 按钮可用性
  $('btn-start').disabled = s.stage !== 'WAIT_WATER';
  $('btn-confirm').disabled = s.stage !== 'WAIT_BOAT';
  $('btn-reset').disabled = !(s.stage === 'EMERGENCY' || s.stage === 'ARRIVED');
  $('tip').textContent = s.tip || '';

  // 水位
  const w = s.water || {};
  $('w-adc').textContent = (w.latest == null) ? '—（水位板未连接）' : w.latest;
  $('w-thr').textContent = (w.baseline == null)
    ? (w.threshold == null ? '—' : '绝对阈值 ' + w.threshold)
    : w.baseline + ' / ' + w.threshold;
  $('w-state').textContent = s.demo ? '演示模式' :
    (w.flood ? '⚠ 高水位' : (w.latest == null ? '等待数据' : '正常'));

  // 视觉与船/人
  $('v-ok').textContent = s.vision_ok ? '就绪' : '未就绪（标定/参考点问题）';
  const b = s.boat;
  $('boat').textContent = b ? `(${b.x.toFixed(0)}, ${b.y.toFixed(0)})  ${b.heading.toFixed(0)}°` : '未识别到';
  const p = s.target;
  $('person').textContent = p ? `(${p.x.toFixed(0)}, ${p.y.toFixed(0)})` : '—';
  $('dist').textContent = (s.dist_mm == null) ? '—' : s.dist_mm.toFixed(0) + ' mm';

  drawMap(s);
  renderLog(s.events);
  refreshSnap();
}

// ---------- 俯视图 ----------
function drawMap(s) {
  const cv = $('map'), ctx = cv.getContext('2d');
  const W = cv.width, H = cv.height, M = 600;   // 场地 600mm
  const k = (W - 30) / M;                        // mm -> px
  ctx.clearRect(0, 0, W, H);

  // 场地边框 + 100mm 网格
  ctx.strokeStyle = '#2a3550';
  for (let g = 0; g <= M; g += 100) {
    ctx.beginPath(); ctx.moveTo(15 + g*k, 15); ctx.lineTo(15 + g*k, 15 + M*k);
    ctx.stroke();
    ctx.beginPath(); ctx.moveTo(15, 15 + g*k); ctx.lineTo(15 + M*k, 15 + g*k);
    ctx.stroke();
  }
  ctx.strokeStyle = '#4a5a80'; ctx.lineWidth = 2;
  ctx.strokeRect(15, 15, M*k, M*k);
  ctx.lineWidth = 1;

  const sx = x => 15 + x * k;
  const sy = y => 15 + (M - y) * k;   // +Y=北=图上边

  // 人：红点，当前目标画黄圈
  const t = s.target;
  (s.persons || []).forEach(p => {
    const isTarget = t && Math.abs(p.x - t.x) < 1 && Math.abs(p.y - t.y) < 1;
    ctx.fillStyle = isTarget ? '#f39c12' : '#e74c3c';
    ctx.beginPath(); ctx.arc(sx(p.x), sy(p.y), 7, 0, 7); ctx.fill();
  });
  // 船：三角形，尖头=船头
  const b = s.boat;
  if (b) {
    ctx.save();
    ctx.translate(sx(b.x), sy(b.y));
    ctx.rotate(b.heading * Math.PI / 180);   // 北=0 顺时针
    ctx.fillStyle = '#7c5cff';
    ctx.beginPath();
    ctx.moveTo(0, -13); ctx.lineTo(-9, 10); ctx.lineTo(9, 10);
    ctx.closePath(); ctx.fill();
    ctx.restore();
  }
}

// ---------- 事件日志 ----------
function renderLog(events) {
  const el = $('log');
  if (!lastState || el._n === events.length) return;
  el._n = events.length;
  el.innerHTML = events.slice(-60).map(e =>
    `<div>[${e.t}] ${e.s === 'WARN' ? '⚠ ' : ''}${e.m}</div>`).join('');
  el.scrollTop = el.scrollHeight;
}

// ---------- 摄像头快照（666.py 每 1s 存一张，这里 2s 刷一次） ----------
let snapTimer = 0;
function refreshSnap() {
  snapTimer = (snapTimer + 1) % 4;
  if (snapTimer !== 0) return;
  const img = $('snap');
  img.onload = () => { img.style.display = 'block'; };
  img.onerror = () => { img.style.display = 'none'; };
  img.src = '/snapshot.jpg?t=' + Date.now();
}

setInterval(refresh, 500);
refresh();
</script>
</body>
</html>"""


class 网页服务器(ThreadingHTTPServer):
    """绑定总控实例的 HTTP 服务器。"""
    daemon_threads = True

    def __init__(self, addr, 总控):
        super().__init__(addr, 网页处理)
        self.总控 = 总控


class 网页处理(BaseHTTPRequestHandler):
    """极简路由：/ 页面、/api/status 状态、/api/* 命令、/snapshot.jpg 画面。"""

    def log_message(self, *args):
        pass   # 静音访问日志

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/" or path == "/index.html":
            body = 网页页面.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif path == "/api/status":
            self._json(self.server.总控.状态快照())
        elif path == "/snapshot.jpg":
            try:
                with open(config.SNAPSHOT_PATH, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except OSError:
                self._json({"ok": False}, code=404)
        else:
            self._json({"ok": False, "error": "unknown"}, code=404)

    def do_POST(self):
        path = urlparse(self.path).path
        q = parse_qs(urlparse(self.path).query)
        t = self.server.总控

        if path == "/api/start":
            t.网页开始()
        elif path == "/api/confirm":
            t.网页确认放船()
        elif path == "/api/estop":
            t.网页急停()
        elif path == "/api/reset":
            t.网页复位()
        elif path == "/api/boat":
            cmd = (q.get("cmd") or ["S"])[0].upper()
            if cmd in ("F", "B", "L", "R", "S"):
                t.dev.船(cmd)
        elif path == "/api/lift":
            cmd = (q.get("cmd") or [""])[0].upper()
            if cmd == "U":
                t.dev.升台()
            elif cmd == "D":
                t.dev.降台()
        else:
            self._json({"ok": False, "error": "unknown"}, code=404)
            return
        self._json({"ok": True})


# ============================================================================
# 九、总控状态机
# ============================================================================

class 救援总控:
    """顺序状态机，每个阶段只做一件事，任何一步异常都先停船再退出。"""

    # 阶段 -> (中文名, 网页提示)
    阶段名 = {
        "WAIT_WATER":  ("待命：等水位报警", "等水位触发，或点「一键开始」跳过等待直接演练"),
        "RAISING":     ("升降台上升中",     "升降台正在升起"),
        "WAIT_BOAT":   ("等人工放船",       "升降台已升起。把船放到水面，摄像头看到船后自动开始；也可点「船已放好」"),
        "SEARCHING":   ("找人中",           "视觉正在寻找最近的落水人员"),
        "NAVIGATING":  ("自动航行中",       "无人船自动靠近目标人员，任何时刻可点「急停」"),
        "ARRIVED":     ("救援完成",         "已到达目标并停船。点「复位」可再救一轮"),
        "EMERGENCY":   ("已急停",           "已停船。检查现场后点「复位」重新待命"),
    }

    def __init__(self, live, web=False):
        global 总控实例
        总控实例 = self

        self.live = live
        self.demo = None if live else 演示环境()
        self.dev = 设备(live, demo=self.demo)

        self.stage = "WAIT_WATER"
        self.note = ""
        self.stop_event = threading.Event()     # 网页急停 / 退出
        self._lock = threading.Lock()

        # 网页事件列表（最多留 200 条）
        self.事件们 = []

        # 最新状态缓存（网页轮询用）
        self.船缓存 = None
        self.人缓存 = []
        self.目标缓存 = None
        self.距离缓存 = None
        self.视觉ok = False
        self.视觉外部 = False

        # 流程控制
        self.手动开始 = threading.Event()        # 网页「一键开始」
        self.确认放船 = threading.Event()        # 网页「船已放好」
        self.复位事件 = threading.Event()        # 网页「复位」：从完成/急停回待命
        self.水位箱 = None
        self.视觉箱 = None

        if live:
            self.水位箱 = 水位接收(config.WATER_PORT)
            self.视觉箱 = UDP收件箱(config.VISION_PORT, 校验视觉)
        self.web = None
        if web:
            self.web = 网页服务器((config.WEB_HOST, config.WEB_PORT), self)
            threading.Thread(target=self.web.serve_forever, daemon=True).start()
            事件(f"[网页] 打开浏览器访问 http://<树莓派IP>:{config.WEB_PORT}")

    # ---------------- 事件/状态 ----------------
    def 记事件(self, msg):
        with self._lock:
            self.事件们.append({"t": time.strftime("%H:%M:%S"), "s": "INFO", "m": msg})
            if len(self.事件们) > 200:
                self.事件们 = self.事件们[-200:]

    def 置阶段(self, stage, note=""):
        with self._lock:
            self.stage = stage
            self.note = note

    def 状态快照(self):
        with self._lock:
            w = self.水位箱
            water = {
                "latest": w.latest_value if (w and self.live) else
                          (self.demo.读水位()["adc"] if self.demo else None),
                "baseline": w.baseline if w else None,
                "threshold": (w.触发阈值() if (w and w.baseline is not None) else
                              (config.WATER_ABS_TRIGGER if config.WATER_ABS_TRIGGER else None)),
                "flood": bool(w and w.flood_event.is_set()),
            }
            stage_cn, tip = self.阶段名.get(self.stage, (self.stage, ""))
            return {
                "stage": self.stage,
                "stage_cn": stage_cn,
                "note": self.note,
                "tip": tip,
                "demo": not self.live,
                "vision_ok": self.视觉ok,
                "vision_external": self.视觉外部,
                "boat": self.船缓存,
                "persons": self.人缓存,
                "target": self.目标缓存,
                "dist_mm": self.距离缓存,
                "water": water,
                "events": list(self.事件们[-80:]),
            }

    # ---------------- 网页按钮回调 ----------------
    def 网页开始(self):
        事件("[网页] 收到「一键开始」")
        self.手动开始.set()

    def 网页确认放船(self):
        事件("[网页] 收到「船已放好」确认")
        self.确认放船.set()

    def 网页急停(self):
        事件("[网页] 收到「急停」！")
        self.stop_event.set()
        self.dev.全停()
        # ARRIVED 阶段没有循环检查 stop_event，这里直接切 EMERGENCY
        if self.stage == "ARRIVED":
            self.置阶段("EMERGENCY", "已急停")

    def 网页复位(self):
        事件("[网页] 复位，重新待命")
        self.复位事件.set()

    # ---------------- 数据读取 ----------------
    def 读水位(self):
        if not self.live:
            return self.demo.读水位()
        if self.水位箱.latest_value is None:
            raise RuntimeError("还没收到水位数据")
        flood = self.水位箱.flood_event.is_set()
        return {"flood": flood, "adc": self.水位箱.latest_value}

    def 读视觉(self, 需要船=False):
        if not self.live:
            船, 人们 = self.demo.读视觉()
            self.视觉ok = True
        else:
            try:
                d = self.视觉箱.latest(config.VISION_TIMEOUT_S)
                船, 人们 = 解析视觉(d)
                self.视觉ok = True
            except RuntimeError:
                self.视觉ok = False
                raise
        # 更新网页缓存
        self.船缓存 = 船
        self.人缓存 = 人们
        if 需要船 and 船 is None:
            raise RuntimeError("没有可靠的船位置和航向")
        return 船, 人们

    # ---------------- 各阶段 ----------------
    def 阶段_等水位(self):
        self.置阶段("WAIT_WATER")
        事件("[流程] 待命：等水位持续报警（或网页一键开始）")
        while not self.stop_event.is_set():
            # 网页一键开始 or 真实水位触发
            if self.手动开始.is_set():
                self.手动开始.clear()
                事件("[流程] 手动触发，跳过水位等待")
                return
            try:
                w = self.读水位()
            except RuntimeError:
                time.sleep(0.2)
                continue
            # 顺便刷新网页上的船/人显示（失败不打断等待）
            try:
                self.读视觉()
            except RuntimeError:
                pass
            if w["flood"]:
                事件("[流程] 水位确认报警，进入升台")
                return
            time.sleep(0.2)
        raise RuntimeError("已停止")

    def 阶段_升台(self):
        self.置阶段("RAISING")
        事件("[流程] 给升降台发 /U")
        self.dev.升台()
        # 固件没有位置反馈，按时间等它升到位；拆成 0.2s 小步，
        # 保证「急停」随时能打断（升降台本身不危险，这里主要是流程可打断）
        deadline = time.monotonic() + config.LIFT_UP_TIME_SEC
        while time.monotonic() < deadline:
            if self.stop_event.is_set():
                raise RuntimeError("已停止")
            time.sleep(0.2)
        事件("[流程] 升降台上升完成（按时间估计）")

    def 阶段_等船(self):
        self.置阶段("WAIT_BOAT")
        事件("[流程] 等待人工放船，或摄像头看到船")
        self.确认放船.clear()
        seen_since = None
        last_hint = 0.0
        while not self.stop_event.is_set():
            if self.确认放船.is_set():
                事件("[流程] 已确认放船")
                return
            # 尝试看船：船稳定可见 3 秒就自动进入下一阶段
            try:
                船, _ = self.读视觉()
                self.视觉ok = True
            except RuntimeError:
                self.视觉ok = False
                船 = None
            if 船 is not None:
                seen_since = seen_since or time.monotonic()
                if time.monotonic() - seen_since >= 3.0:
                    事件("[流程] 摄像头持续看到船，自动开始")
                    return
            else:
                seen_since = None
                now = time.monotonic()
                if now - last_hint > 15.0:
                    last_hint = now
                    事件("[提示] 还没看到船：确认船已放水、ArUco 朝向摄像头")
            time.sleep(0.3)
        raise RuntimeError("已停止")

    def 阶段_找人(self):
        self.置阶段("SEARCHING")
        事件("[流程] 找最近的稳定人员目标")
        deadline = time.monotonic() + config.SEARCH_TIMEOUT_S
        last_target, stable = None, 0
        while time.monotonic() < deadline and not self.stop_event.is_set():
            船, 人们 = self.读视觉(需要船=True)
            人 = 最近的人(船, 人们)
            if 人 is None:
                last_target, stable = None, 0
            elif last_target and math.hypot(人["x"] - last_target["x"],
                                            人["y"] - last_target["y"]) < 50:
                stable += 1          # 同一位置连续出现 = 稳定目标
            else:
                last_target, stable = 人, 1
            if stable >= 3:
                事件(f"[流程] 锁定目标 ({人['x']:.0f}, {人['y']:.0f})")
                return 人
            time.sleep(config.CONTROL_INTERVAL_SEC)
        if self.stop_event.is_set():
            raise RuntimeError("已停止")
        raise RuntimeError("找人超时")

    def 阶段_导航(self, 目标):
        self.置阶段("NAVIGATING")
        事件("[流程] 开始自动航行，靠近目标")
        deadline = time.monotonic() + config.NAVIGATE_TIMEOUT_S
        arrived_since = lost_since = None
        fails = 0

        while time.monotonic() < deadline and not self.stop_event.is_set():
            try:
                船, 人们 = self.读视觉(需要船=True)
                self.视觉ok = True
            except RuntimeError as exc:
                # 视觉掉线：停船等恢复；连续失败过多就急停
                self.视觉ok = False
                self.dev.船("S")
                fails += 1
                事件(f"[警告] 视觉异常({exc})，停船等待")
                if fails >= config.NAV_MAX_FAILS:
                    raise RuntimeError("视觉连续掉线，触发急停")
                time.sleep(0.2)
                continue
            fails = 0

            # YOLO 每帧编号会变：取离原目标最近的人继续跟
            新目标 = 最近的人(船, 人们)
            if 新目标 is not None and math.hypot(新目标["x"] - 目标["x"],
                                                 新目标["y"] - 目标["y"]) < 60:
                目标, lost_since = 新目标, None
            elif 新目标 is None:
                lost_since = lost_since or time.monotonic()
                if time.monotonic() - lost_since > config.TARGET_LOST_TIMEOUT_S:
                    事件("[流程] 目标从视野消失，回到找人")
                    return "LOST"
            else:
                lost_since = None

            dist = math.hypot(船["x"] - 目标["x"], 船["y"] - 目标["y"])
            self.目标缓存, self.距离缓存 = dict(目标), dist

            if dist <= config.ARRIVE_DIST_MM:
                # 已在范围内：保持停车，稳住一会儿算到达
                self.dev.船("S")
                arrived_since = arrived_since or time.monotonic()
                if time.monotonic() - arrived_since >= config.ARRIVE_HOLD_S:
                    事件(f"[流程] 已到达目标并停船（距离 {dist:.0f} mm）")
                    return "ARRIVED"
                time.sleep(config.CONTROL_INTERVAL_SEC)
                continue
            arrived_since = None

            # 规划本周期动作
            plan = 规划(船, 目标)
            cmd, err = plan["cmd"], plan["err"]

            if cmd in ("L", "R"):
                # 航向差太多：整个周期原地转
                self.dev.船(cmd)
                time.sleep(config.CONTROL_INTERVAL_SEC)
            else:
                # 直行：误差小时先打一个小转向脉冲，再前进
                f_time = config.CONTROL_INTERVAL_SEC
                if dist <= config.SLOW_DIST_MM:
                    f_time *= 0.5          # 近处半速，防止冲过头
                if abs(err) > config.HEADING_DEADBAND_DEG:
                    pulse = min(0.10, 0.002 * abs(err))
                    转向 = "R" if err > 0 else "L"
                    self.dev.船(转向)
                    time.sleep(pulse)
                    f_time -= pulse
                self.dev.船("F")
                time.sleep(max(0.0, f_time))
                if f_time < config.CONTROL_INTERVAL_SEC:
                    self.dev.船("S")       # 剩余时间停着 = 占空比降速
                    time.sleep(max(0.0, config.CONTROL_INTERVAL_SEC - f_time))

        if self.stop_event.is_set():
            raise RuntimeError("已停止")
        raise RuntimeError("自动航行超时")

    # ---------------- 主循环 ----------------
    def 等复位(self):
        """停在当前阶段，直到网页点「复位」。"""
        while not self.复位事件.is_set():
            time.sleep(0.3)

    def run(self):
        """总流程状态机：每轮 = 等水位 -> 升台 -> 等船 -> 找人 -> 自动航行。

        任何异常/急停 -> 全停 -> EMERGENCY -> 等网页复位 -> 回到待命。
        """
        while True:
            # 回到待命状态，清空所有一次性事件
            self.stop_event.clear()
            self.复位事件.clear()
            self.手动开始.clear()
            self.确认放船.clear()
            self.置阶段("WAIT_WATER")

            try:
                self.阶段_等水位()
                self.阶段_升台()
                self.阶段_等船()
                目标 = self.阶段_找人()
                while True:
                    result = self.阶段_导航(目标)
                    if result == "ARRIVED":
                        self.置阶段("ARRIVED")
                        事件("[流程] 本轮救援完成，点「复位」可再救一轮")
                        break
                    if result == "LOST":
                        事件("[流程] 目标丢失，重新找人")
                        目标 = self.阶段_找人()
                        continue
                    break

            except RuntimeError as exc:
                事件(f"[停止] {exc}")
                self.dev.全停()
                note = str(exc) if str(exc) != "已停止" else "已急停"
                self.置阶段("EMERGENCY", note)

            # 无论正常完成还是急停/故障，都等网页「复位」再开始下一轮
            self.等复位()

    def stop(self):
        self.stop_event.set()
        self.复位事件.set()          # 让状态机线程退出等待
        self.dev.全停()
        if self.水位箱:
            self.水位箱.stop()
        if self.视觉箱:
            self.视觉箱.close()
        if self.web:
            self.web.shutdown()


# ============================================================================
# 十、单模块调试子命令
# ============================================================================

def 子命令_查水位(live):
    if not live:
        事件("[模拟] 检查水位（--live 才连接真水位板）")
        demo = 演示环境()
        for _ in range(10):
            w = demo.读水位()
            事件(f"[模拟] adc={w['adc']} flood={w['flood']}")
            time.sleep(0.5)
        return
    箱 = 水位接收(config.WATER_PORT)
    try:
        last = None
        while True:
            with 箱._lock:
                if 箱.latest_value != last:
                    last = 箱.latest_value
                    事件(f"[水位] 读数={last} 基线={箱.baseline} "
                         f"阈值={箱.触发阈值() if 箱.baseline is not None else '收集基线中'} "
                         f"高水位计数={箱.high_count}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        箱.stop()


def 子命令_查视觉(live):
    箱 = UDP收件箱(config.VISION_PORT, 校验视觉)
    if not live:
        事件("[模拟] 检查视觉通道（真机请先启动 666.py --publish-state）")
    last = None
    try:
        while True:
            try:
                d = 箱.latest(config.VISION_TIMEOUT_S)
            except RuntimeError:
                time.sleep(0.5)
                continue
            船, 人们 = 解析视觉(d)
            line = (f"[视觉] 坐标就绪={d.get('coordinate_ready')} "
                    f"可控制={d.get('vision_ok_for_control')} "
                    f"船={船} 人={人们}")
            if line != last:
                last = line
                事件(line)
            time.sleep(0.5)
    except KeyboardInterrupt:
        箱.close()


def 子命令_升降台(cmd, live):
    dev = 设备(live)
    if cmd == "U":
        事件("给升降台发 /U（升起）")
        dev.升台()
    elif cmd == "D":
        事件("给升降台发 /D（降下）")
        dev.降台()


def 子命令_小船(cmd, 秒数, live):
    dev = 设备(live)
    事件(f"小船 -> /{cmd} 持续 {秒数}s")
    dev.船(cmd)
    time.sleep(秒数)
    dev.船("S")
    事件("小船 -> /S 已停")


# ============================================================================
# 十一、入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="智能城市救援塔总控")
    parser.add_argument("--demo", action="store_true",
                        help="离线演示：模拟水位/视觉/船，不连任何硬件")
    parser.add_argument("--live", action="store_true",
                        help="连接真实 ESP32 和 666.py（默认不连）")
    parser.add_argument("--web", action="store_true",
                        help="开启一键网页（--demo 默认自带网页）")
    parser.add_argument("--no-web", action="store_true", help="关闭网页")
    parser.add_argument("--no-start-vision", action="store_true",
                        help="666.py 已单独运行时使用")
    # 单模块调试
    parser.add_argument("--check-water", action="store_true", help="持续看水位")
    parser.add_argument("--check-vision", action="store_true", help="持续看船/人坐标")
    parser.add_argument("--lift", choices=["U", "D"], help="升降台：U 升 D 降")
    parser.add_argument("--boat", choices=["F", "B", "L", "R", "S"],
                        help="小船：F前 B后 L左 R右 S停")
    parser.add_argument("--seconds", type=float, default=1.0, help="--boat 持续时间")
    # 现场临时覆盖（一般不用，测试/换网段时用）
    parser.add_argument("--boat-ip", help="覆盖 config.BOAT_IP")
    parser.add_argument("--lift-ip", help="覆盖 config.LIFT_IP")
    parser.add_argument("--http-port", type=int, help="覆盖 config.HTTP_PORT")
    parser.add_argument("--water-port", type=int, help="覆盖 config.WATER_PORT")
    parser.add_argument("--vision-port", type=int, help="覆盖 config.VISION_PORT")
    parser.add_argument("--web-port", type=int, help="覆盖 config.WEB_PORT")
    parser.add_argument("--lift-wait", type=float, help="覆盖 config.LIFT_UP_TIME_SEC")
    parser.add_argument("--arrive", type=float, help="覆盖 config.ARRIVE_DIST_MM")
    args = parser.parse_args()

    # 命令行覆盖配置
    if args.boat_ip:
        config.BOAT_IP = args.boat_ip
    if args.lift_ip:
        config.LIFT_IP = args.lift_ip
    if args.http_port:
        config.HTTP_PORT = args.http_port
    if args.water_port:
        config.WATER_PORT = args.water_port
    if args.vision_port:
        config.VISION_PORT = args.vision_port
    if args.web_port:
        config.WEB_PORT = args.web_port
    if args.lift_wait:
        config.LIFT_UP_TIME_SEC = args.lift_wait
    if args.arrive:
        config.ARRIVE_DIST_MM = args.arrive

    # ---- 单模块调试 ----
    if args.check_water:
        子命令_查水位(args.live)
        return
    if args.check_vision:
        子命令_查视觉(args.live)
        return
    if args.lift:
        子命令_升降台(args.lift, args.live)
        return
    if args.boat:
        子命令_小船(args.boat, args.seconds, args.live)
        return

    # ---- 完整流程 ----
    live = args.live
    web = (args.web or args.demo) and not args.no_web

    print()
    print("=" * 64)
    print("智能城市救援塔 · 总控（一键网页版）")
    print("=" * 64)
    print(f"模式         : {'连接真机' if live else '离线演示（模拟）'}")
    print(f"小船         : {config.BOAT_IP}  (ArUco ID {config.BOAT_ID})")
    print(f"升降台       : {config.LIFT_IP}")
    if live:
        print(f"水位 TCP     : 0.0.0.0:{config.WATER_PORT}")
        print(f"视觉 UDP     : 127.0.0.1:{config.VISION_PORT}")
    if web:
        print(f"一键网页     : http://<本机IP>:{config.WEB_PORT}")
    print("=" * 64)
    print()

    总控 = 救援总控(live, web=web)

    vision_proc = None
    vision_log = None

    try:
        if live and not args.no_start_vision:
            vision_proc, vision_log = 启动视觉(总控.视觉箱)
            if vision_proc is None and vision_log is None:
                总控.视觉外部 = True
        elif live:
            事件("[视觉] 外部模式：请确认 666.py 已带 --publish-state 启动")
            总控.视觉外部 = True

        总控.run()
    except KeyboardInterrupt:
        事件("\n[退出] Ctrl+C -> 全停")
    finally:
        if vision_proc is not None:
            try:
                vision_proc.terminate()
                vision_proc.wait(timeout=3.0)
            except Exception:
                try:
                    vision_proc.kill()
                except Exception:
                    pass
        if vision_log is not None:
            try:
                vision_log.close()
            except Exception:
                pass
        总控.stop()
        事件("[退出] 小船已发 /S，总控关闭")


if __name__ == "__main__":
    main()
