#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
智能救援塔视觉主程序（Raspberry Pi 5 高流畅版）

运行方式：

1) 第一次换 USB 摄像头后，先标定：
       python3 gogogo.py --calibrate

   标定窗口中：
       SPACE = 采集一组标定数据
       C     = 计算并保存标定参数（建议采集 >= 12~15 组）
       Q/ESC = 退出

   标定时要改变摄像头/场地的相对姿态：
       - 不同俯仰角
       - 不同距离
       - 让参考点分布到画面四周
   不能把固定摄像头对着完全不动的场地连续拍 15 张，那些样本几乎是重复的。

2) 正常运行：
       python3 gogogo.py

系统功能：
- USB 摄像头后台线程持续取最新帧，避免 VideoCapture 队列造成“越看越卡”
- MJPG + buffer=1，尽量提高 USB 摄像头取流帧率
- ArUco ID 0~5：船
- ArUco ID 6~13：场地基准点
- 用基准点建立像素 -> 场地 Homography
- YOLO 独立线程检测人员，主显示线程不再等待推理
- 自动优先加载 best_ncnn_model；不存在时回退 best.pt
- ArUco 默认 30Hz（摄像头 60Hz 时每2帧检测一次），兼顾流畅与定位刷新率
- 实时显示 Camera FPS / Display FPS / YOLO 推理 FPS
- USB相机标定结果用于镜头畸变矫正
- ArUco 船头角度先经畸变矫正 + Homography 再计算，不直接使用图像斜率
- 支持每艘船的 ArUco 安装偏角修正
- 对船角度做圆周 EMA 平滑，避免 359°/0°附近跳变
"""

import argparse
import json
import math
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np
from ultralytics import YOLO


# ============================================================
# 1. 用户配置区 —— 建议先审核这一段
# ============================================================

# ---------------- USB 摄像头 ----------------
CAMERA_ID = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 60

# 很多 USB 摄像头在 Linux 下用 MJPG 能明显提高 720p 帧率。
USE_MJPG = True

# OpenCV 内部缓存设小，避免显示的是“几秒前的旧帧”。
CAMERA_BUFFER_SIZE = 1

# ---------------- 项目路径 ----------------
# 以脚本自身目录为基准，这样从任意终端目录启动都能找到模型/标定文件。
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------- YOLO ----------------
# Raspberry Pi 5 优先使用 NCNN；如果尚未转换，就自动回退 best.pt。
# 在电脑上可执行：yolo export model=best.pt format=ncnn imgsz=416
NCNN_MODEL_PATH = os.path.join(BASE_DIR, "best_ncnn_model")
PT_MODEL_PATH = os.path.join(BASE_DIR, "best.pt")
MODEL_PATH = NCNN_MODEL_PATH if os.path.isdir(NCNN_MODEL_PATH) else PT_MODEL_PATH
CONF_THRESH = 0.50

# Pi 5 上先用 416，速度和小目标识别之间比较均衡。
YOLO_IMGSZ = 416

# YOLO 已改为独立线程。主线程按这个最短时间间隔投递最新帧；
# 推理来不及时不会排队，而是自动覆盖成“最新帧”。
# 0.05 = 最多约 20 次/秒投递；实际 YOLO FPS 由模型速度决定。
YOLO_SUBMIT_INTERVAL_SEC = 0.05

# Pi 5 是 4 核 CPU。PT/PyTorch 推理时限制为 3 线程，
# 给摄像头、ArUco、GUI 留出余量，减少“YOLO一跑画面就顿”的情况。
YOLO_CPU_THREADS = 3

PERSON_CLASS_IDS = {0}

# "bottom_center"：检测框底边中心，更适合地面/水面映射
# "center"：检测框中心
PERSON_POINT_MODE = "bottom_center"

# ---------------- ArUco ----------------
# 必须与实体打印码一致。
ARUCO_DICT_TYPE = cv2.aruco.DICT_4X4_50

BOAT_IDS = set(range(0, 6))
FIELD_IDS = set(range(6, 14))

# 是否进行亚像素角点优化。
# True：角度/坐标更稳，耗时略增；一般建议保留。
ARUCO_SUBPIX = True

# 摄像头是 1280x720@60fps。ArUco 每2帧检测一次 => 最高约30Hz，
# 对船控制已经足够，同时明显降低 CPU 压力。要追求更高刷新率可改为 1。
ARUCO_EVERY_N_FRAMES = 2

# ---------------- 已知场地基准点 ----------------
# 每个坐标表示该参考 ArUco 的“中心”在场地平面中的真实位置。
REFERENCE_POINTS = {
    6: (0.0, 0.0),
    7: (100.0, 0.0),
    8: (200.0, 0.0),
    9: (0.0, 100.0),
    10: (100.0, 100.0),
    11: (200.0, 100.0),
    12: (0.0, 200.0),
    13: (200.0, 200.0),
}

COORD_UNIT = "mm"
MIN_REFERENCE_MARKERS = 4
HOMOGRAPHY_RANSAC_THRESHOLD = 5.0

# ---------------- 相机标定 ----------------
CALIB_FILE = os.path.join(BASE_DIR, "camera_calibration_usb.json")

# 正常运行时，如果找到当前 USB 摄像头的标定文件，就自动去畸变。
USE_UNDISTORT_IF_AVAILABLE = True

# 标定模式每张图至少检测到多少个参考点才允许采样。
# 参考点越多，标定通常越稳。
CALIB_MIN_REF_POINTS = 6
CALIB_RECOMMENDED_SAMPLES = 15

# ============================================================
# 新增标定板物理参数（与 aruco_gen.py 保持一致）
# ============================================================
CALIB_BOARD_MARKERS_X = 6          # 列数
CALIB_BOARD_MARKERS_Y = 4          # 行数
CALIB_BOARD_WIDTH_MM = 120.0       # 板宽 (mm)
CALIB_BOARD_HEIGHT_MM = 80.0       # 板高 (mm)
CALIB_MARKER_RATIO = 0.7           # 标记占格子比例 (与生成代码相同)

# 计算单个标记尺寸和间距 (单位 mm)
_cell_x = CALIB_BOARD_WIDTH_MM / CALIB_BOARD_MARKERS_X
_cell_y = CALIB_BOARD_HEIGHT_MM / CALIB_BOARD_MARKERS_Y
_cell_size = min(_cell_x, _cell_y)
CALIB_MARKER_LENGTH_MM = _cell_size * CALIB_MARKER_RATIO
CALIB_MARKER_SEPARATION_MM = _cell_size * (1.0 - CALIB_MARKER_RATIO)

# ---------------- ArUco 角度定义 / 安装偏角 ----------------
# 船头定义：ArUco 中心 -> ArUco 的上边中点(corner0/corner1中点)
# 角度约定沿用你的 aruco_position.py：
#   +Y = 0°
#   +X = 90°
#   范围 0~360°
#
# 如果某个 ArUco 实际贴在船上时旋转了几度，可在这里单独补偿。
# 例如 ID0 的码相对真正船头顺时针歪了 5°，实测后可填 -5 或 +5 校正。
BOAT_HEADING_OFFSETS_DEG = {
    0: 0.0,
    1: 0.0,
    2: 0.0,
    3: 0.0,
    4: 0.0,
    5: 0.0,
}

# 角度圆周 EMA：越大越跟手，越小越稳。
ANGLE_EMA_ALPHA = 0.35

# 参考点像素中心 EMA，降低 Homography 轻微抖动。
REFERENCE_EMA_ALPHA = 0.35

# Homography 不必每帧重算；它很便宜，但降低频率可进一步稳定坐标。
H_UPDATE_EVERY_N_FRAMES = 2

# 控制台打印太频繁也会拖慢树莓派。
PRINT_INTERVAL_SEC = 0.5


# ============================================================
# 2. 参数解析
# ============================================================

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--calibrate",
        action="store_true",
        help="进入 USB 摄像头标定模式"
    )
    parser.add_argument(
        "--camera",
        type=int,
        default=CAMERA_ID,
        help="USB 摄像头编号，默认 0"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="网页接口监听地址，默认 0.0.0.0"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="网页接口端口，默认 8080"
    )
    parser.add_argument(
        "--esp32-url",
        default=os.environ.get("ESP32_URL", ""),
        help="ESP32 地址，例如 http://192.168.43.120；也可使用 ESP32_URL 环境变量"
    )
    parser.add_argument(
        "--no-display",
        action="store_true",
        help="不打开本地 OpenCV 窗口，适合无显示器运行"
    )
    return parser.parse_args()


# ============================================================
# 3. 高帧率 USB 摄像头：后台只保留最新一帧
# ============================================================

class LatestFrameCamera:
    """
    单独线程不断调用 cap.read()。

    主线程做 YOLO 的时候，摄像头线程仍在继续读帧；
    主线程下一次取图时直接拿“最新帧”，而不是排队处理旧帧。

    这对解决树莓派 OpenCV 画面“卡一下、追旧帧”的问题很有效。
    """

    def __init__(self, camera_id):
        # Raspberry Pi OS / Linux 优先用 V4L2，Windows 优先用 DirectShow。
        preferred_backend = (
            cv2.CAP_DSHOW
            if os.name == "nt"
            else cv2.CAP_V4L2
        )
        try:
            self.cap = cv2.VideoCapture(camera_id, preferred_backend)
        except Exception:
            self.cap = cv2.VideoCapture(camera_id)

        if not self.cap.isOpened():
            # 某些环境显式 V4L2 反而失败，回退普通方式。
            self.cap.release()
            self.cap = cv2.VideoCapture(camera_id)

        if not self.cap.isOpened():
            raise RuntimeError("无法打开 USB 摄像头")

        if USE_MJPG:
            self.cap.set(
                cv2.CAP_PROP_FOURCC,
                cv2.VideoWriter_fourcc(*"MJPG")
            )

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, CAMERA_BUFFER_SIZE)

        self.lock = threading.Lock()
        self.frame_ready = threading.Condition(self.lock)
        self.frame = None
        self.frame_sequence = 0
        self.running = True

        # 实测采集 FPS，不只相信 CAP_PROP_FPS 的“标称值”。
        self.capture_fps = 0.0
        self._fps_count = 0
        self._fps_window_start = time.perf_counter()

        self.thread = threading.Thread(
            target=self._reader,
            daemon=True
        )
        self.thread.start()

    def _reader(self):
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.005)
                continue

            now = time.perf_counter()

            with self.frame_ready:
                # 只覆盖旧帧，不形成队列。
                self.frame = frame
                self.frame_sequence += 1
                self.frame_ready.notify_all()

                self._fps_count += 1
                elapsed = now - self._fps_window_start
                if elapsed >= 1.0:
                    self.capture_fps = self._fps_count / elapsed
                    self._fps_count = 0
                    self._fps_window_start = now

    def read(self):
        with self.lock:
            if self.frame is None:
                return False, None
            return True, self.frame.copy()

    def read_latest(self, previous_sequence, timeout=0.1):
        """等待一张新帧，避免无显示模式重复处理同一张图而空耗 CPU。"""
        with self.frame_ready:
            if self.frame_sequence == previous_sequence and self.running:
                self.frame_ready.wait(timeout=timeout)
            if self.frame is None or self.frame_sequence == previous_sequence:
                return False, None, previous_sequence
            return True, self.frame.copy(), self.frame_sequence

    def get_actual_settings(self):
        fourcc_value = int(self.cap.get(cv2.CAP_PROP_FOURCC))
        fourcc_text = "".join(
            chr((fourcc_value >> (8 * i)) & 0xFF)
            for i in range(4)
        )
        return {
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": float(self.cap.get(cv2.CAP_PROP_FPS)),
            "fourcc": fourcc_text,
        }

    def get_capture_fps(self):
        with self.lock:
            return float(self.capture_fps)

    def stop(self):
        self.running = False
        with self.frame_ready:
            self.frame_ready.notify_all()
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.cap.release()


# ============================================================
# 4. ArUco 检测器
# ============================================================

def create_aruco_detector():
    dictionary = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_TYPE)
    parameters = cv2.aruco.DetectorParameters()

    if ARUCO_SUBPIX:
        parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
        parameters.cornerRefinementWinSize = 5
        parameters.cornerRefinementMaxIterations = 20
        parameters.cornerRefinementMinAccuracy = 0.05

    try:
        detector = cv2.aruco.ArucoDetector(dictionary, parameters)
        return dictionary, parameters, detector, True
    except AttributeError:
        return dictionary, parameters, None, False


def detect_aruco(frame, dictionary, parameters, detector, use_new_api):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    if use_new_api:
        corners, ids, rejected = detector.detectMarkers(gray)
    else:
        corners, ids, rejected = cv2.aruco.detectMarkers(
            gray,
            dictionary,
            parameters=parameters
        )

    return corners, ids, rejected


def get_marker_center(corners_4x2):
    return np.mean(corners_4x2, axis=0).astype(np.float32)


def marker_data_from_detection(corners, ids):
    marker_data = {}

    if ids is None:
        return marker_data

    for i, marker_id_raw in enumerate(ids.flatten()):
        marker_id = int(marker_id_raw)
        marker_corners = corners[i].reshape(4, 2).astype(np.float32)

        marker_data[marker_id] = {
            "corners": marker_corners,
            "center": get_marker_center(marker_corners),
        }

    return marker_data


# ============================================================
# 5. USB 摄像头标定
# ============================================================

def save_calibration(path, camera_matrix, dist_coeffs, rms, image_size, sample_count):
    data = {
        "camera_matrix": camera_matrix.tolist(),
        "dist_coeffs": dist_coeffs.tolist(),
        "rms": float(rms),
        "image_width": int(image_size[0]),
        "image_height": int(image_size[1]),
        "sample_count": int(sample_count),
        "reference_points": {
            str(k): [float(v[0]), float(v[1])]
            for k, v in REFERENCE_POINTS.items()
        },
    }

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def load_calibration(path, runtime_size=None):
    """
    加载 USB 摄像头内参。

    如果运行分辨率与标定分辨率不同，会按比例缩放 fx/fy/cx/cy。
    最稳妥的方案仍然是：标定和运行使用相同分辨率。
    """
    if not os.path.exists(path):
        return None, None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    camera_matrix = np.array(data["camera_matrix"], dtype=np.float64)
    dist_coeffs = np.array(data["dist_coeffs"], dtype=np.float64)

    calib_w = int(data.get("image_width", CAMERA_WIDTH))
    calib_h = int(data.get("image_height", CAMERA_HEIGHT))

    if runtime_size is not None:
        run_w, run_h = runtime_size

        if calib_w != run_w or calib_h != run_h:
            sx = run_w / calib_w
            sy = run_h / calib_h

            camera_matrix[0, 0] *= sx  # fx
            camera_matrix[0, 2] *= sx  # cx
            camera_matrix[1, 1] *= sy  # fy
            camera_matrix[1, 2] *= sy  # cy

            print(
                f"标定分辨率 {calib_w}x{calib_h} -> "
                f"运行分辨率 {run_w}x{run_h}，已缩放相机内参。"
            )

    return camera_matrix, dist_coeffs


def build_undistort_maps(camera_matrix, dist_coeffs, image_size):
    """
    只在程序启动时计算一次去畸变查找表。

    后续每帧使用 cv2.remap，
    比每帧 cv2.undistort 重算映射快很多。
    """
    w, h = image_size

    new_camera_matrix, _ = cv2.getOptimalNewCameraMatrix(
        camera_matrix,
        dist_coeffs,
        (w, h),
        alpha=0.0,
        newImgSize=(w, h)
    )

    map1, map2 = cv2.initUndistortRectifyMap(
        camera_matrix,
        dist_coeffs,
        None,
        new_camera_matrix,
        (w, h),
        cv2.CV_16SC2
    )

    return map1, map2


def run_camera_calibration(camera_id):
    """
    使用 6×4 标准 ArUco 标定板进行相机内参标定。

    交互：
        SPACE : 采集当前帧（需看到足够多的标记）
        C     : 计算并保存标定结果
        Q/ESC : 退出
    """
    # 使用与标定板相同的字典
    dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_250)
    parameters = cv2.aruco.DetectorParameters()
    # 为获得更准的角点，开启亚像素
    parameters.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    parameters.cornerRefinementWinSize = 5
    parameters.cornerRefinementMaxIterations = 20
    parameters.cornerRefinementMinAccuracy = 0.05
    detector = cv2.aruco.ArucoDetector(dictionary, parameters)

    cam = LatestFrameCamera(camera_id)

    object_points_all = []   # 世界坐标系中的 3D 点 (mm)
    image_points_all = []    # 对应的图像像素坐标
    image_size = None

    print("\n========== 使用 6×4 标定板进行相机标定 ==========")
    print("标定板物理参数：")
    print(f"  板尺寸 : {CALIB_BOARD_WIDTH_MM}×{CALIB_BOARD_HEIGHT_MM} mm")
    print(f"  标记网格 : {CALIB_BOARD_MARKERS_X}×{CALIB_BOARD_MARKERS_Y}")
    print(f"  标记边长 : {CALIB_MARKER_LENGTH_MM:.2f} mm")
    print(f"  标记间距 : {CALIB_MARKER_SEPARATION_MM:.2f} mm")
    print("\n操作说明：")
    print("  SPACE : 采集当前姿态（建议改变角度/距离）")
    print("  C     : 计算并保存标定结果")
    print("  Q/ESC : 退出")
    print(f"建议采集 >= 15 组不同姿态，且标定板应充满画面大部分区域。")

    while True:
        ret, frame = cam.read()
        if not ret:
            time.sleep(0.01)
            continue

        h, w = frame.shape[:2]
        image_size = (w, h)

        # 检测所有 ArUco 标记（ID 0~23）
        corners, ids, _ = detector.detectMarkers(frame)
        display = frame.copy()

        if ids is not None:
            cv2.aruco.drawDetectedMarkers(display, corners, ids)

        # 计算当前帧可见标记的数量
        visible_count = len(ids) if ids is not None else 0

        cv2.putText(
            display,
            f"Samples: {len(object_points_all)}  Visible markers: {visible_count}",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2
        )
        cv2.imshow("Camera Calibration (GridBoard)", display)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord('q'), 27):
            break

        # ---- 采集 ----
        if key == 32:  # SPACE
            if ids is None or len(ids) < 8:
                print("检测到的标记太少（<8），请调整角度或距离，使标定板尽量完整可见。")
                continue

            # 准备这一帧的 object_points 和 image_points
            obj_pts = []
            img_pts = []

            # 遍历每个检测到的标记
            for i, marker_id in enumerate(ids.flatten()):
                # 计算该标记在标定板网格中的行列
                row = marker_id // CALIB_BOARD_MARKERS_X
                col = marker_id % CALIB_BOARD_MARKERS_X
                # 标记左上角的世界坐标 (mm)
                x0 = col * (CALIB_MARKER_LENGTH_MM + CALIB_MARKER_SEPARATION_MM)
                y0 = row * (CALIB_MARKER_LENGTH_MM + CALIB_MARKER_SEPARATION_MM)

                # 四个角点的世界坐标 (顺序：左上、右上、右下、左下)
                # 与 detectMarkers 返回的角点顺序一致
                world_corners = np.array([
                    [x0, y0, 0],
                    [x0 + CALIB_MARKER_LENGTH_MM, y0, 0],
                    [x0 + CALIB_MARKER_LENGTH_MM, y0 + CALIB_MARKER_LENGTH_MM, 0],
                    [x0, y0 + CALIB_MARKER_LENGTH_MM, 0]
                ], dtype=np.float32)

                # 图像中的四个角点
                img_corners = corners[i].reshape(4, 2).astype(np.float32)

                # 将四个角点加入列表
                obj_pts.extend(world_corners)
                img_pts.extend(img_corners)

            object_points_all.append(np.array(obj_pts, dtype=np.float32))
            image_points_all.append(np.array(img_pts, dtype=np.float32))

            print(f"已采集第 {len(object_points_all)} 组，使用了 {len(obj_pts)//4} 个标记的角点。")

        # ---- 计算标定 ----
        if key in (ord('c'), ord('C')):
            if len(object_points_all) < 8:
                print("样本数不足，至少需要 8 组不同姿态，建议 ≥15 组。")
                continue

            print(f"开始标定，共 {len(object_points_all)} 组样本...")
            rms, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
                object_points_all,
                image_points_all,
                image_size,
                None,
                None
            )

            print(f"RMS 重投影误差: {rms:.6f}")
            print("Camera matrix:\n", camera_matrix)
            print("Distortion coefficients:\n", dist_coeffs.ravel())

            save_calibration(
                CALIB_FILE,
                camera_matrix,
                dist_coeffs,
                rms,
                image_size,
                len(object_points_all)
            )
            print(f"标定结果已保存至 {CALIB_FILE}")
            print("标定完成，可以退出并正常运行主程序。")

    cam.stop()
    cv2.destroyAllWindows()


# ============================================================
# 6. 参考点平滑 + Homography
# ============================================================

def ema_point(old_point, new_point, alpha):
    if old_point is None:
        return np.asarray(new_point, dtype=np.float32)

    return (
        (1.0 - alpha) * np.asarray(old_point, dtype=np.float32)
        + alpha * np.asarray(new_point, dtype=np.float32)
    )


def update_smoothed_reference_centers(marker_data, state):
    """
    state: {ref_id: smoothed_pixel_center}
    """
    for ref_id in REFERENCE_POINTS:
        if ref_id not in marker_data:
            continue

        new_center = marker_data[ref_id]["center"]
        state[ref_id] = ema_point(
            state.get(ref_id),
            new_center,
            REFERENCE_EMA_ALPHA
        )

    return state


def build_homography_from_reference_state(ref_state):
    src = []
    dst = []
    used_ids = []

    for ref_id, world_xy in REFERENCE_POINTS.items():
        if ref_id not in ref_state:
            continue

        src.append(ref_state[ref_id])
        dst.append(world_xy)
        used_ids.append(ref_id)

    if len(src) < MIN_REFERENCE_MARKERS:
        return None, used_ids, 0

    src = np.asarray(src, dtype=np.float32)
    dst = np.asarray(dst, dtype=np.float32)

    H, mask = cv2.findHomography(
        src,
        dst,
        cv2.RANSAC,
        HOMOGRAPHY_RANSAC_THRESHOLD
    )

    if H is None:
        return None, used_ids, 0

    inliers = int(mask.sum()) if mask is not None else len(used_ids)

    if inliers < 4:
        return None, used_ids, inliers

    # 归一化，便于数值稳定。
    if abs(H[2, 2]) > 1e-12:
        H = H / H[2, 2]

    return H, used_ids, inliers


# ============================================================
# 7. 像素坐标 <-> 场地坐标
# ============================================================

def pixels_to_world(points_xy, H):
    if H is None:
        return None

    pts = np.asarray(points_xy, dtype=np.float32).reshape(-1, 1, 2)
    out = cv2.perspectiveTransform(pts, H)
    return out.reshape(-1, 2)


def pixel_to_world(point_xy, H):
    out = pixels_to_world([point_xy], H)
    if out is None:
        return None
    return float(out[0, 0]), float(out[0, 1])


def world_to_pixel(point_xy, H):
    if H is None:
        return None

    try:
        H_inv = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        return None

    pts = np.asarray([[point_xy]], dtype=np.float32)
    out = cv2.perspectiveTransform(pts, H_inv)
    return int(round(out[0, 0, 0])), int(round(out[0, 0, 1]))


# ============================================================
# 8. ArUco 船角度：透视矫正 + 安装偏角 + 圆周平滑
# ============================================================

def normalize_angle(angle_deg):
    return angle_deg % 360.0


def circular_ema(previous_deg, current_deg, alpha):
    """
    普通角度平均会把 359° 和 1° 平均成 180°，这是错的。
    这里把角度转成单位圆向量后进行 EMA。
    """
    if previous_deg is None:
        return normalize_angle(current_deg)

    p = math.radians(previous_deg)
    c = math.radians(current_deg)

    x = (1.0 - alpha) * math.cos(p) + alpha * math.cos(c)
    y = (1.0 - alpha) * math.sin(p) + alpha * math.sin(c)

    if abs(x) < 1e-12 and abs(y) < 1e-12:
        return normalize_angle(current_deg)

    return normalize_angle(math.degrees(math.atan2(y, x)))


def compute_boat_pose(boat_id, marker_info, H, angle_state):
    """
    角度矫正链路：

    原始 ArUco 像素四角
        -> （主循环已完成镜头去畸变）
        -> Homography 映射到真实场地平面
        -> 在真实场地平面计算中心 -> 上边中点方向
        -> 加上每艘船的安装偏角
        -> 圆周 EMA 平滑

    因此摄像头斜着俯拍时，图像中的“视觉角度”不会直接当作船角度。
    """
    pixel_corners = marker_info["corners"]
    pixel_center = marker_info["center"]

    world_corners = pixels_to_world(pixel_corners, H)
    center_world = pixel_to_world(pixel_center, H)

    if world_corners is None or center_world is None:
        return None

    cx, cy = center_world

    # OpenCV ArUco 四角通常为：
    # 0 左上、1 右上、2 右下、3 左下（相对于码自身的定义）
    top_mid = (world_corners[0] + world_corners[1]) / 2.0

    dx = float(top_mid[0] - cx)
    dy = float(top_mid[1] - cy)

    if math.hypot(dx, dy) < 1e-6:
        raw_angle = None
        corrected_angle = None
        smooth_angle = None
    else:
        # 保留你原先的定义：+Y 为 0°，+X 为 90°。
        raw_angle = normalize_angle(
            math.degrees(math.atan2(dx, dy))
        )

        # 修正 ArUco 在船体上的实际安装偏角。
        corrected_angle = normalize_angle(
            raw_angle + BOAT_HEADING_OFFSETS_DEG.get(boat_id, 0.0)
        )

        smooth_angle = circular_ema(
            angle_state.get(boat_id),
            corrected_angle,
            ANGLE_EMA_ALPHA
        )

        angle_state[boat_id] = smooth_angle

    return {
        "id": boat_id,
        "x": cx,
        "y": cy,
        "raw_angle_deg": raw_angle,
        "angle_deg": smooth_angle,
        "world_corners": world_corners,
        "pixel_center": pixel_center,
        "pixel_corners": pixel_corners,
    }


# ============================================================
# 9. YOLO 相关
# ============================================================

def get_person_pixel_point(x1, y1, x2, y2):
    if PERSON_POINT_MODE == "center":
        return (x1 + x2) / 2.0, (y1 + y2) / 2.0

    return (x1 + x2) / 2.0, y2


def run_yolo_once(model, frame):
    """
    返回缓存友好的简单结构；非 YOLO 帧直接复用上次结果进行显示。
    """
    detections = []

    predict_kwargs = {
        "source": frame,
        "conf": CONF_THRESH,
        "imgsz": YOLO_IMGSZ,
        "verbose": False,
    }

    # .pt 使用 CPU；NCNN 本身就是 ARM/CPU 后端，不额外传 device。
    if str(MODEL_PATH).lower().endswith(".pt"):
        predict_kwargs["device"] = "cpu"

    results = model.predict(**predict_kwargs)

    result = results[0]

    if result.boxes is None:
        return detections

    for box in result.boxes:
        cls_id = int(box.cls[0])
        if cls_id not in PERSON_CLASS_IDS:
            continue

        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()

        detections.append({
            "cls_id": cls_id,
            "conf": conf,
            "bbox": (x1, y1, x2, y2),
        })

    return detections


class AsyncYOLO:
    """
    Pi 5 流畅版核心：YOLO 独立线程。

    主线程只负责把“最新帧”交给这里，不等待推理完成。
    如果 YOLO 还在忙，后来的帧会覆盖旧待处理帧，因此不会形成积压队列。
    显示线程始终读取最近一次已经完成的检测结果。
    """

    def __init__(self, model_path):
        self.model_path = model_path

        # 仅在 PyTorch 模型时限制 CPU 线程数，避免 4 个核心被 YOLO 吃满。
        if str(model_path).lower().endswith(".pt"):
            try:
                import torch
                torch.set_num_threads(YOLO_CPU_THREADS)
                try:
                    torch.set_num_interop_threads(1)
                except RuntimeError:
                    pass
                print(f"PyTorch CPU threads: {YOLO_CPU_THREADS}")
            except Exception as e:
                print("无法设置 PyTorch CPU 线程数，将使用默认值：", e)

        print(f"Loading YOLO model: {model_path}")
        self.model = YOLO(model_path)
        print("YOLO model loaded.")
        print("YOLO classes:", self.model.names)

        self.lock = threading.Lock()
        self.event = threading.Event()
        self.running = True

        self.pending_frame = None
        self.latest_detections = []
        self.inference_ms = 0.0
        self.inference_fps = 0.0
        self.last_result_time = 0.0
        self.total_inferences = 0

        self.thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="YOLOWorker"
        )
        self.thread.start()

    def submit(self, frame):
        # 单槽“最新帧邮箱”：永远只保留最新待推理帧。
        with self.lock:
            self.pending_frame = frame.copy()
        self.event.set()

    def _worker(self):
        while self.running:
            self.event.wait(timeout=0.1)
            if not self.running:
                break

            with self.lock:
                frame = self.pending_frame
                self.pending_frame = None
                self.event.clear()

            if frame is None:
                continue

            t0 = time.perf_counter()
            try:
                detections = run_yolo_once(self.model, frame)
            except Exception as e:
                print("YOLO error:", e)
                detections = []

            elapsed = time.perf_counter() - t0
            ms = elapsed * 1000.0
            fps = (1.0 / elapsed) if elapsed > 1e-9 else 0.0

            with self.lock:
                self.latest_detections = detections
                self.inference_ms = ms
                self.inference_fps = fps
                self.last_result_time = time.perf_counter()
                self.total_inferences += 1

            # 如果推理期间主线程已经投递了更新帧，立即继续，不等待下一次唤醒。
            with self.lock:
                has_pending = self.pending_frame is not None
            if has_pending:
                self.event.set()

    def get_latest(self):
        with self.lock:
            detections = [dict(d) for d in self.latest_detections]
            result_time = self.last_result_time
            return {
                "detections": detections,
                "inference_ms": float(self.inference_ms),
                "inference_fps": float(self.inference_fps),
                "result_age_sec": (
                    time.perf_counter() - result_time
                    if result_time > 0 else None
                ),
                "total_inferences": int(self.total_inferences),
            }

    def stop(self):
        self.running = False
        self.event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)


# ============================================================
# 10. 实时网页数据与控制桥接
# ============================================================

class RescueWebState:
    """视觉线程与 HTTP 线程之间的线程安全状态缓存。"""

    def __init__(self, esp32_url=""):
        self.lock = threading.Lock()
        self.frame_ready = threading.Condition(self.lock)
        self.started_at = time.time()
        self.updated_at = 0.0
        self.frame_seq = 0
        self.jpeg_frame = None
        self.stream_clients = 0
        self.last_jpeg_time = 0.0
        self.esp32_url = esp32_url.rstrip("/")
        self.last_command = "S"
        self.control_ok = None
        self.control_latency_ms = None
        self.control_error = None
        self.snapshot = {
            "coordinate_ready": False,
            "boats": [],
            "persons": [],
            "performance": {},
            "references": {"visible": 0, "inliers": 0, "ids": []},
            "camera": {"undistort": False},
        }

    def publish(self, frame, boats, persons, performance, references, undistort):
        public_boats = []
        for boat_id, boat in sorted(boats.items()):
            public_boats.append({
                "id": int(boat_id),
                "x": round(float(boat["x"]), 3),
                "y": round(float(boat["y"]), 3),
                "angle": (
                    round(float(boat["angle_deg"]), 3)
                    if boat["angle_deg"] is not None else None
                ),
            })

        public_persons = []
        for index, person in enumerate(persons):
            public_persons.append({
                "id": index,
                "x": round(float(person["x"]), 3),
                "y": round(float(person["y"]), 3),
                "confidence": round(float(person["conf"]), 4),
            })

        now = time.time()
        with self.lock:
            self.updated_at = now
            self.snapshot = {
                "coordinate_ready": bool(references["coordinate_ready"]),
                "boats": public_boats,
                "persons": public_persons,
                "performance": performance,
                "references": {
                    "visible": int(references["visible"]),
                    "inliers": int(references["inliers"]),
                    "ids": [int(value) for value in references["ids"]],
                },
                "camera": {"undistort": bool(undistort)},
            }
            should_encode = (
                self.stream_clients > 0
                and now - self.last_jpeg_time >= 1.0 / 15.0
            )

        # JPEG 编码放在锁外，避免状态查询被较慢的编码阻塞。
        if should_encode:
            ok, encoded = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 78]
            )
            if ok:
                with self.frame_ready:
                    self.jpeg_frame = encoded.tobytes()
                    self.last_jpeg_time = now
                    self.frame_seq += 1
                    self.frame_ready.notify_all()

    def get_snapshot(self):
        with self.lock:
            result = dict(self.snapshot)
            result["timestamp"] = self.updated_at
            result["age_ms"] = (
                round((time.time() - self.updated_at) * 1000)
                if self.updated_at > 0 else None
            )
            result["service"] = {
                "online": True,
                "uptime_sec": round(time.time() - self.started_at, 1),
            }
            result["control"] = {
                "esp32_configured": bool(self.esp32_url),
                "last_command": self.last_command,
                "ok": self.control_ok,
                "latency_ms": self.control_latency_ms,
                "error": self.control_error,
            }
            return result

    def set_control_result(self, command, ok, latency_ms=None, error=None):
        with self.lock:
            self.last_command = command
            self.control_ok = bool(ok)
            self.control_latency_ms = latency_ms
            self.control_error = error

    def add_stream_client(self):
        with self.lock:
            self.stream_clients += 1

    def remove_stream_client(self):
        with self.lock:
            self.stream_clients = max(0, self.stream_clients - 1)

    def wait_for_frame(self, previous_seq, timeout=2.0):
        with self.frame_ready:
            if self.frame_seq == previous_seq:
                self.frame_ready.wait(timeout=timeout)
            return self.frame_seq, self.jpeg_frame


class RescueRequestHandler(BaseHTTPRequestHandler):
    web_state = None

    def log_message(self, fmt, *args):
        print("WEB:", fmt % args)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-store")

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text, status=200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _read_control_command(self, parsed):
        if parsed.path in ("/F", "/B", "/L", "/R", "/S"):
            return parsed.path[1:]

        query = urllib.parse.parse_qs(parsed.query)
        command = query.get("command", [""])[0].upper()

        if self.command == "POST" and not command:
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                command = str(payload.get("command", "")).upper()
            except (ValueError, json.JSONDecodeError):
                command = ""

        return command if command in ("F", "B", "L", "R", "S") else None

    def _forward_control(self, command):
        state = self.web_state
        if not state.esp32_url:
            state.set_control_result(command, False, error="ESP32 URL 未配置")
            self._send_json({"ok": False, "command": command, "error": "ESP32 URL 未配置"}, 503)
            return

        target = f"{state.esp32_url}/{command}?t={int(time.time() * 1000)}"
        started = time.perf_counter()
        try:
            request = urllib.request.Request(target, method="GET")
            with urllib.request.urlopen(request, timeout=0.6) as response:
                acknowledgement = response.read(16).decode("utf-8", "ignore").strip()
            latency_ms = round((time.perf_counter() - started) * 1000)
            if acknowledgement != command:
                raise RuntimeError("ESP32 返回了无效确认")
            state.set_control_result(command, True, latency_ms=latency_ms)
            # 兼容原 ESP32 前端：/F 等接口仍直接返回单字符确认。
            if self.path.startswith(f"/{command}"):
                self._send_text(command)
            else:
                self._send_json({"ok": True, "command": command, "latency_ms": latency_ms})
        except Exception as exc:
            error = str(exc)
            state.set_control_result(command, False, error=error)
            self._send_json({"ok": False, "command": command, "error": error}, 503)

    def _stream_video(self):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self._cors_headers()
        self.end_headers()
        sequence = -1
        self.web_state.add_stream_client()
        try:
            while True:
                sequence, jpeg = self.web_state.wait_for_frame(sequence)
                if jpeg is None:
                    continue
                self.wfile.write(b"--frame\r\n")
                self.wfile.write(b"Content-Type: image/jpeg\r\n")
                self.wfile.write(f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii"))
                self.wfile.write(jpeg)
                self.wfile.write(b"\r\n")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        finally:
            self.web_state.remove_stream_client()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in ("/api/status", "/api/vision"):
            self._send_json(self.web_state.get_snapshot())
            return
        if parsed.path in ("/video", "/video.mjpg"):
            self._stream_video()
            return

        command = self._read_control_command(parsed)
        if command:
            self._forward_control(command)
            return

        self._send_json({
            "name": "城市方舟视觉服务",
            "status": "/api/status",
            "vision": "/api/vision",
            "video": "/video",
            "control": "/api/control?command=F",
        })

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/control":
            self._send_json({"ok": False, "error": "Not found"}, 404)
            return
        command = self._read_control_command(parsed)
        if not command:
            self._send_json({"ok": False, "error": "command 必须是 F/B/L/R/S"}, 400)
            return
        self._forward_control(command)


def start_web_server(state, host, port):
    RescueRequestHandler.web_state = state
    server = ThreadingHTTPServer((host, port), RescueRequestHandler)
    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True,
        name="RescueWebServer"
    )
    thread.start()
    print(f"Web API: http://{host}:{port}")
    print(f"Video : http://{host}:{port}/video")
    return server


# ============================================================
# 11. 可视化
# ============================================================

def draw_world_axes(frame, H):
    origin = world_to_pixel((0.0, 0.0), H)
    x_end = world_to_pixel((100.0, 0.0), H)
    y_end = world_to_pixel((0.0, 100.0), H)

    if origin is None or x_end is None or y_end is None:
        return

    cv2.circle(frame, origin, 5, (255, 255, 255), -1)
    cv2.arrowedLine(frame, origin, x_end, (0, 0, 255), 2)
    cv2.arrowedLine(frame, origin, y_end, (255, 0, 0), 2)

    cv2.putText(
        frame, "O", (origin[0] + 6, origin[1] - 6),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1
    )
    cv2.putText(
        frame, "+X", x_end,
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1
    )
    cv2.putText(
        frame, "+Y", y_end,
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 1
    )


def draw_boat_heading(frame, boat):
    """把已经矫正后的真实世界角度画回图像。"""
    angle = boat["angle_deg"]
    if angle is None:
        return

    x = boat["x"]
    y = boat["y"]

    # 因为角度定义 +Y=0°, +X=90°：
    # dx = sin(theta), dy = cos(theta)
    theta = math.radians(angle)
    length_world = 30.0

    end_world = (
        x + length_world * math.sin(theta),
        y + length_world * math.cos(theta)
    )

    start_px = world_to_pixel((x, y), boat["H"])
    end_px = world_to_pixel(end_world, boat["H"])

    if start_px is not None and end_px is not None:
        cv2.arrowedLine(frame, start_px, end_px, (0, 165, 255), 3)


# ============================================================
# 11. 正常主程序
# ============================================================

def run_main(camera_id, host="0.0.0.0", port=8080, esp32_url="", no_display=False):
    print("=" * 72)
    print("Raspberry Pi 5 Rescue Tower Vision - gogogo.py")
    print(f"Model path: {MODEL_PATH}")

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"找不到模型：{MODEL_PATH}\n"
            "请把 best.pt 放到当前目录；或者把 best_ncnn_model 文件夹放到当前目录。"
        )

    # OpenCV 不要与 PyTorch/NCNN 无限制抢线程。
    try:
        cv2.setNumThreads(2)
    except Exception:
        pass

    dictionary, parameters, detector, use_new_api = create_aruco_detector()

    cam = LatestFrameCamera(camera_id)
    settings = cam.get_actual_settings()
    print("Camera requested:", {
        "width": CAMERA_WIDTH,
        "height": CAMERA_HEIGHT,
        "fps": CAMERA_FPS,
        "fourcc": "MJPG" if USE_MJPG else "default",
    })
    print("Camera actual settings:", settings)

    if (
        settings["width"] != CAMERA_WIDTH
        or settings["height"] != CAMERA_HEIGHT
        or abs(settings["fps"] - CAMERA_FPS) > 1.0
    ):
        print("WARNING: 摄像头没有完全接受请求参数，请检查 V4L2 模式。")

    # 等第一帧，获取真正图像尺寸。
    first_frame = None
    while first_frame is None:
        ret, first_frame = cam.read()
        if not ret:
            first_frame = None
            time.sleep(0.01)

    h, w = first_frame.shape[:2]

    # --------------------------------------------------------
    # 加载 USB 摄像头标定，并预计算去畸变 remap 表。
    # --------------------------------------------------------
    map1 = None
    map2 = None

    if USE_UNDISTORT_IF_AVAILABLE and os.path.exists(CALIB_FILE):
        try:
            camera_matrix, dist_coeffs = load_calibration(
                CALIB_FILE,
                runtime_size=(w, h)
            )

            map1, map2 = build_undistort_maps(
                camera_matrix,
                dist_coeffs,
                (w, h)
            )

            print(f"USB 标定文件已加载：{CALIB_FILE}")
            print("镜头畸变矫正：ON（预计算 remap）")
        except Exception as e:
            print("标定文件加载失败，将不做镜头畸变矫正：", e)
            map1 = map2 = None
    else:
        print("未找到 USB 摄像头标定文件，镜头畸变矫正：OFF")
        print("建议先运行：python3 gogogo.py --calibrate")

    # YOLO 独立线程：模型加载完成后才进入主循环。
    yolo_worker = AsyncYOLO(MODEL_PATH)
    web_state = RescueWebState(esp32_url=esp32_url)
    web_server = start_web_server(web_state, host, port)

    if esp32_url:
        print(f"ESP32 control target: {esp32_url}")
    else:
        print("ESP32 control target: NOT CONFIGURED")
        print("提示：使用 --esp32-url http://设备IP 启用控制转发。")

    # --------------------------------------------------------
    # 状态缓存
    # --------------------------------------------------------
    frame_index = 0
    ref_center_state = {}
    H = None
    used_ref_ids = []
    inlier_count = 0
    angle_state = {}

    # ArUco 只在指定帧更新；中间帧复用最近一次结果。
    last_aruco_corners = []
    last_aruco_ids = None
    last_marker_data = {}
    last_boats = {}

    # YOLO 投递控制。
    last_yolo_submit_time = 0.0

    # Display FPS 统计。
    display_fps_ema = 0.0
    last_loop_time = time.perf_counter()
    last_print_time = 0.0
    camera_sequence = -1

    print("Press Q to quit.")
    print("=" * 72)

    try:
        while True:
            ret, raw_frame, camera_sequence = cam.read_latest(camera_sequence)
            if not ret:
                time.sleep(0.002)
                continue

            frame_index += 1

            # ------------------------------------------------
            # A. 镜头畸变矫正
            # ------------------------------------------------
            if map1 is not None:
                frame = cv2.remap(
                    raw_frame,
                    map1,
                    map2,
                    interpolation=cv2.INTER_LINEAR
                )
            else:
                frame = raw_frame

            display = frame.copy()

            # ------------------------------------------------
            # B. ArUco：默认每2帧一次 => 720p60 时最高约30Hz
            # ------------------------------------------------
            aruco_updated = (
                frame_index == 1
                or frame_index % ARUCO_EVERY_N_FRAMES == 0
            )

            if aruco_updated:
                corners, ids, _ = detect_aruco(
                    frame,
                    dictionary,
                    parameters,
                    detector,
                    use_new_api
                )

                last_aruco_corners = corners
                last_aruco_ids = ids
                last_marker_data = marker_data_from_detection(corners, ids)

                # 仅在真正获得新 ArUco 数据时更新参考点 EMA。
                update_smoothed_reference_centers(
                    last_marker_data,
                    ref_center_state
                )

                if (
                    H is None
                    or frame_index % H_UPDATE_EVERY_N_FRAMES == 0
                ):
                    new_H, new_used_ids, new_inliers = (
                        build_homography_from_reference_state(ref_center_state)
                    )

                    if new_H is not None:
                        H = new_H
                        used_ref_ids = new_used_ids
                        inlier_count = new_inliers

            marker_data = last_marker_data
            corners = last_aruco_corners
            ids = last_aruco_ids

            if ids is not None and len(corners) > 0:
                cv2.aruco.drawDetectedMarkers(display, corners, ids)

            coordinate_ready = H is not None

            # 显示参考点坐标。
            for ref_id in FIELD_IDS:
                if ref_id not in marker_data:
                    continue

                center = marker_data[ref_id]["center"]
                cx, cy = map(int, center)
                wx, wy = REFERENCE_POINTS[ref_id]

                cv2.putText(
                    display,
                    f"R{ref_id}({wx:.0f},{wy:.0f})",
                    (cx + 4, cy + 16),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.42,
                    (255, 0, 255),
                    1
                )

            if coordinate_ready:
                draw_world_axes(display, H)

            # ------------------------------------------------
            # C. 船位置与角度：只在新 ArUco 帧计算，避免重复 EMA
            # ------------------------------------------------
            if aruco_updated:
                boats = {}

                if coordinate_ready:
                    for boat_id in sorted(BOAT_IDS):
                        if boat_id not in marker_data:
                            continue

                        boat = compute_boat_pose(
                            boat_id,
                            marker_data[boat_id],
                            H,
                            angle_state
                        )

                        if boat is None:
                            continue

                        boat["H"] = H
                        boats[boat_id] = boat

                last_boats = boats

            boats = last_boats

            for boat_id, boat in boats.items():
                px = int(boat["pixel_center"][0])
                py = int(boat["pixel_center"][1])

                for idx, p in enumerate(boat["pixel_corners"]):
                    cpx, cpy = int(p[0]), int(p[1])
                    cv2.circle(display, (cpx, cpy), 3, (255, 255, 0), -1)
                    cv2.putText(
                        display,
                        str(idx),
                        (cpx + 3, cpy - 3),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.38,
                        (255, 255, 0),
                        1
                    )

                angle = boat["angle_deg"]
                angle_text = "?" if angle is None else f"{angle:.1f}deg"

                cv2.putText(
                    display,
                    f"Boat{boat_id} ({boat['x']:.1f},{boat['y']:.1f}) {angle_text}",
                    (px + 8, py + 22),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.48,
                    (0, 255, 255),
                    2
                )

                draw_boat_heading(display, boat)

            # ------------------------------------------------
            # D. YOLO 独立线程
            # ------------------------------------------------
            now_perf = time.perf_counter()
            if now_perf - last_yolo_submit_time >= YOLO_SUBMIT_INTERVAL_SEC:
                yolo_worker.submit(frame)
                last_yolo_submit_time = now_perf

            yolo_state = yolo_worker.get_latest()
            last_yolo_detections = yolo_state["detections"]

            persons = []

            # 主线程只画最近一次已完成的 YOLO 结果，不等待推理。
            for det in last_yolo_detections:
                conf = det["conf"]
                x1, y1, x2, y2 = det["bbox"]

                person_pixel = get_person_pixel_point(x1, y1, x2, y2)
                person_px = int(person_pixel[0])
                person_py = int(person_pixel[1])

                cv2.rectangle(
                    display,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    (0, 255, 0),
                    2
                )
                cv2.circle(
                    display,
                    (person_px, person_py),
                    5,
                    (0, 0, 255),
                    -1
                )

                world = pixel_to_world(person_pixel, H) if coordinate_ready else None

                if world is not None:
                    person_x, person_y = world
                    persons.append({
                        "x": person_x,
                        "y": person_y,
                        "conf": conf,
                        "pixel": person_pixel,
                    })
                    label = (
                        f"Person {conf:.2f} "
                        f"({person_x:.1f},{person_y:.1f})"
                    )
                else:
                    label = f"Person {conf:.2f}"

                cv2.putText(
                    display,
                    label,
                    (int(x1), max(18, int(y1) - 7)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.45,
                    (0, 255, 0),
                    1
                )

            # ------------------------------------------------
            # E. FPS 统计
            # ------------------------------------------------
            now = time.perf_counter()
            dt = now - last_loop_time
            last_loop_time = now

            if dt > 1e-6:
                instant_fps = 1.0 / dt
                if display_fps_ema <= 0:
                    display_fps_ema = instant_fps
                else:
                    display_fps_ema = (
                        0.90 * display_fps_ema + 0.10 * instant_fps
                    )

            camera_fps = cam.get_capture_fps()
            yolo_fps = yolo_state["inference_fps"]
            yolo_ms = yolo_state["inference_ms"]
            yolo_age = yolo_state["result_age_sec"]

            visible_reference_ids = sorted(
                int(marker_id)
                for marker_id in marker_data
                if marker_id in FIELD_IDS
            )

            web_state.publish(
                frame=display,
                boats=boats,
                persons=persons,
                performance={
                    "camera_fps": round(float(camera_fps), 2),
                    "display_fps": round(float(display_fps_ema), 2),
                    "yolo_fps": round(float(yolo_fps), 2),
                    "yolo_ms": round(float(yolo_ms), 2),
                    "yolo_age_sec": (
                        round(float(yolo_age), 3)
                        if yolo_age is not None else None
                    ),
                    "total_inferences": int(yolo_state["total_inferences"]),
                },
                references={
                    "coordinate_ready": coordinate_ready,
                    "visible": len(visible_reference_ids),
                    "inliers": inlier_count,
                    "ids": visible_reference_ids,
                },
                undistort=map1 is not None,
            )

            status1 = (
                f"CAM {camera_fps:.1f} | DISP {display_fps_ema:.1f} | "
                f"YOLO {yolo_fps:.1f}fps {yolo_ms:.0f}ms"
            )
            status2 = (
                f"ArUco 1/{ARUCO_EVERY_N_FRAMES} | refs {len(used_ref_ids)} "
                f"inliers {inlier_count} | model {os.path.basename(MODEL_PATH)}"
            )

            if yolo_age is not None:
                status2 += f" | yolo age {yolo_age:.2f}s"

            cv2.putText(
                display,
                status1,
                (15, 26),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.56,
                (255, 255, 255),
                2
            )
            cv2.putText(
                display,
                status2,
                (15, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (255, 255, 255),
                1
            )

            if map1 is not None:
                cv2.putText(
                    display,
                    "UNDISTORT ON",
                    (15, 72),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.46,
                    (0, 255, 0),
                    1
                )

            # ------------------------------------------------
            # F. 限频打印
            # ------------------------------------------------
            wall_now = time.time()
            if wall_now - last_print_time >= PRINT_INTERVAL_SEC:
                last_print_time = wall_now

                print(
                    f"PERF | cam={camera_fps:.1f}fps "
                    f"display={display_fps_ema:.1f}fps "
                    f"yolo={yolo_fps:.1f}fps/{yolo_ms:.0f}ms "
                    f"refs={len(used_ref_ids)} inliers={inlier_count}"
                )

                for boat_id, boat in boats.items():
                    a = boat["angle_deg"]
                    raw = boat["raw_angle_deg"]
                    print(
                        f"BOAT {boat_id} | "
                        f"({boat['x']:.2f},{boat['y']:.2f}) {COORD_UNIT} | "
                        f"angle={a:.1f}deg raw={raw:.1f}deg"
                        if a is not None and raw is not None
                        else
                        f"BOAT {boat_id} | "
                        f"({boat['x']:.2f},{boat['y']:.2f}) {COORD_UNIT} | angle=?"
                    )

                for person in persons:
                    print(
                        f"PERSON | ({person['x']:.2f},{person['y']:.2f}) "
                        f"{COORD_UNIT} | conf={person['conf']:.2f}"
                    )

            # ------------------------------------------------
            # G. 显示
            # ------------------------------------------------
            if not no_display:
                cv2.imshow(
                    "Rescue Tower Pi5 - gogogo",
                    display
                )

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

    finally:
        web_server.shutdown()
        web_server.server_close()
        yolo_worker.stop()
        cam.stop()
        if not no_display:
            cv2.destroyAllWindows()
        print("Program stopped.")


# ============================================================
# 12. 程序入口
# ============================================================

if __name__ == "__main__":
    args = parse_args()

    if args.calibrate:
        run_camera_calibration(args.camera)
    else:
        run_main(
            args.camera,
            host=args.host,
            port=args.port,
            esp32_url=args.esp32_url,
            no_display=args.no_display,
        )
