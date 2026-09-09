# -*- coding: utf-8 -*-
"""把 v4 + 视觉程序打成可直接发给朋友的部署包。

树莓派上的目标结构：
    rescue_tower/
    ├── raspberry_pi/vision/666.py + best.pt + camera_calibration_usb.json
    └── v4/ ...

666.py 期望模型和标定文件与它同目录，所以打包时按这个结构摆好。
"""

import os
import zipfile

ROOT = r"F:\gugugaga\rescue_tower"
OUT = os.path.join(ROOT, "v4_树莓派部署包.zip")
SKIP = {"__pycache__", ".next", "node_modules"}

DEPLOY_NOTE = """智能救援塔 V4 部署包 —— 先看这个

包里有两部分：
  1. v4/           —— 总控程序（必需）
  2. raspberry_pi/ —— 视觉程序 666.py + 模型 best.pt + 摄像头标定文件

============================================================
一、如果朋友的树莓派已经在跑旧系统（旧版已在 rescue_tower/ 里）
============================================================
只做两件事：
  1. 把 v4/ 整个文件夹放到 ~/rescue_tower/ 下面（与 raspberry_pi/ 平级）：
     rescue_tower/
     ├── raspberry_pi/   （树莓派上原有的，不动）
     └── v4/
  2. 把小船 ESP32 固件换成新的：用 Thonny 打开 v4/firmware/boat_main.py，
     烧进小船（旧固件没有 /M 接口，自动航行必须换）。
     （升降台、水位固件如果已经在跑就不用动。）

============================================================
二、如果朋友的树莓派是全新的（什么都没有）
============================================================
  1. 把 v4/ 和 raspberry_pi/ 都放到 ~/rescue_tower/ 下面（结构如上）。
  2. 装视觉依赖（在 raspberry_pi/vision/ 下）：
        pip install ultralytics opencv-python numpy
     并在 666.py 提示时按需执行 yolo export 转换 NCNN（不转也能用 best.pt 跑）。
  3. 烧固件（小船必须烧 v4/firmware/boat_main.py）：
        boat_main.py -> 小船
        lift_main.py  -> 升降台
        water_main.py -> 水位传感器
  4. 确认摄像头标定：包里带的是开发机的标定文件，
     如果朋友的摄像头不同，需要跑一次 666.py 的标定流程（python3 666.py --calibrate）。

============================================================
三、启动（两种场景都一样）
============================================================
  cd ~/rescue_tower/v4
  chmod +x start.sh
  ./start.sh
  浏览器打开 http://树莓派IP:8080

先跑一遍自检（不连硬件也能过）：
  cd ~/rescue_tower/v4
  python3 tests/sim_pid.py
  python3 -m unittest discover -s tests -v

============================================================
四、下水前必改 config.py
============================================================
  BOAT_IP / LIFT_IP      —— 改成现场设备的实际 IP
  PID_*                   —— 先跑 tests/sim_pid.py 调好再抄进来
  船转向反了：PID_TURN_SIGN 改成 -1
"""


def add_tree(zf: zipfile.ZipFile, src: str, arc: str) -> None:
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in SKIP]
        for name in filenames:
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, src)
            zf.write(path, os.path.join(arc, rel))


def main() -> None:
    note = os.path.join(ROOT, "_部署包说明.txt")
    with open(note, "w", encoding="utf-8") as fh:
        fh.write(DEPLOY_NOTE)
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(note, "部署说明-先看这个.txt")
        add_tree(zf, os.path.join(ROOT, "v4"), "v4")
        # 视觉程序按树莓派实际目录结构摆放（模型、标定与 666.py 同目录）
        zf.write(os.path.join(ROOT, "raspberry_pi", "vision", "666.py"),
                 "raspberry_pi/vision/666.py")
        zf.write(os.path.join(ROOT, "raspberry_pi", "models", "best.pt"),
                 "raspberry_pi/vision/best.pt")
        zf.write(os.path.join(ROOT, "raspberry_pi", "calibration", "camera_calibration_usb.json"),
                 "raspberry_pi/vision/camera_calibration_usb.json")
    os.remove(note)
    size = os.path.getsize(OUT) / 1024 / 1024
    print(f"已生成：{OUT}（{size:.2f} MB）")
    with zipfile.ZipFile(OUT) as zf:
        print(f"共 {len(zf.namelist())} 个文件")


if __name__ == "__main__":
    main()
