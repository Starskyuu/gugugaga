"""现场参数集中放在这里，换 IP、阈值和场地尺寸时只改本文件。"""

# 树莓派和两个 ESP32 必须连接同一个 Mate 70 Pro 热点。
BOAT_IP = "192.168.43.14"
LIFT_IP = "192.168.43.21"
DEVICE_HTTP_PORT = 80

# 水位 ESP32 主动连接树莓派的这个 TCP 端口。
WATER_LISTEN_HOST = "0.0.0.0"
WATER_PORT = 5000
WATER_BASELINE_SAMPLES = 5
WATER_RISE_THRESHOLD = 6000
WATER_TRIGGER_COUNT = 3
WATER_ABSOLUTE_THRESHOLD = None  # 若已标定，可填写绝对 ADC 阈值，例如 35000

# 666.py 把检测结果发到这个 UDP 端口，并把最新画面写入 JPEG 文件。
VISION_HOST = "0.0.0.0"
VISION_PORT = 9101
VISION_TIMEOUT_S = 1.2
VISION_JPEG = "/tmp/rescue_latest.jpg"

# 现场坐标均为毫米；默认场地是 600 mm × 600 mm。
FIELD_WIDTH_MM = 600.0
FIELD_HEIGHT_MM = 600.0
GRID_RESOLUTION_MM = 20.0
SAFETY_MARGIN_MM = 12.0

# 不能航行区域（禁航区），轴对齐矩形 (x1, y1, x2, y2)，单位 mm。
# 1) ArUco 7/9/12 号标记为中心 30×30 的区域（中心坐标取自 666.py 的
#    REFERENCE_POINTS：7=(574,297)、9=(17,345)、12=(568,570)，均在场地内）。
# 2) 边角合围区：(70,190) 向左下、(70,440) 向左上、(535,180) 向右下、(420,75) 向左下。
# 3) 上边缘两段：(130,525)-(290,525)、(350,525)-(460,525) 连线与上边合围。
# 4) 中央矩形：以 (175,210)-(430,390) 连线为对角线，四边平行于边线。
# 规划器会在每个矩形外再扩 SAFETY_MARGIN_MM，重叠区域自动合并。
OBSTACLES_MM = [
    (559, 282, 589, 312),   # ArUco 7 号标记 30×30 中心禁航区
    (2, 330, 32, 360),      # ArUco 9 号标记 30×30 中心禁航区
    (553, 555, 583, 585),   # ArUco 12 号标记 30×30 中心禁航区
    (0, 0, 70, 190),        # (70,190) 向左侧、下侧垂线合围区域
    (0, 440, 70, 600),      # (70,440) 向左侧、上侧垂线合围区域
    (130, 525, 290, 600),   # (130,525)-(290,525) 连线与上侧合围区域
    (350, 525, 460, 600),   # (350,525)-(460,525) 连线与上侧合围区域
    (175, 210, 430, 390),   # 对角线 (175,210)-(430,390) 的中央矩形区域
    (535, 0, 600, 180),     # (535,180) 向右侧、下侧垂线合围区域
    (0, 0, 420, 75),        # (420,75) 向左侧、下侧垂线合围区域
]

# 小船控制参数。角度约定沿用 666.py：朝上为 0°，顺时针为正。
BOAT_ID = 0
WAYPOINT_RADIUS_MM = 28.0
ARRIVAL_RADIUS_MM = 55.0
TURN_THRESHOLD_DEG = 24.0
CONTROL_PERIOD_S = 0.20
REPLAN_PERIOD_S = 2.0
TARGET_LOST_TIMEOUT_S = 1.5
MISSION_TIMEOUT_S = 90.0
TURN_SIGN = 1  # 若左右转反了改成 -1

# ============================================================
# PID 双环导航（core/nav_control.py 双环 PID 连续油门）
# 航向换算：666.py 的"朝上 0°、顺时针为正" -> PID 的"+X 为 0°、逆时针为正"，
# 由 core/navigation.py 的 PidPilot 内部处理，现场无需手算。
# 参数先在 tests/sim_pid.py 里调，再下水实测。
# ============================================================

# 进入该半径（mm）视为到达；与 ARRIVAL_RADIUS_MM 保持一致。
PID_ACCEPT_RADIUS_MM = 55.0

# 到达后目标移开超过该距离（mm）才重新启动，防止目标点附近反复启停。
PID_ARRIVE_HYSTERESIS_MM = 15.0

# 动力限制（百分比）。固件 MAX_SPEED=55，超过会被截掉。
PID_MAX_SPEED = 55
PID_MAX_TURN = 55

# 远处最低巡航油门 / 慢速区最低爬行油门（克服电机死区与水阻）。
PID_MIN_CRUISE = 18
PID_MIN_APPROACH = 10

# 油门为零时的最小原地旋转差速（死区补偿兜底）。
PID_MIN_SPIN = 20

# 距目标小于该值（mm）后取消最低巡航，改用爬行油门。
PID_SLOW_ZONE_MM = 150.0

# 航向误差死区（度），抑制视觉抖动造成的蛇形。
PID_HEADING_DEADBAND_DEG = 8.0

# 船转向反了改成 -1（与 TURN_SIGN 同义；两套坐标系下符号一致，默认 1）。
PID_TURN_SIGN = 1

# 航向环：每度航向误差 -> 差速百分比。
PID_KP_H = 1.2
PID_KI_H = 0.0
PID_KD_H = 0.0

# 速度环：每毫米剩余距离 -> 油门百分比（PID 包默认 8.0 每米等比缩小为 0.008 每毫米）。
PID_KP_S = 0.008
PID_KI_S = 0.0
PID_KD_S = 0.002

# 积分限幅。
PID_I_MAX_H = 30.0
PID_I_MAX_S = 30.0

# 自动导航时连续下发油门失败（HTTP 不通）这么多次就停车报错。
THROTTLE_MAX_FAILS = 5

# 升降台没有位置反馈，发送上升命令后等待这个时间。
LIFT_RAISE_WAIT_S = 8.0
DEVICE_TIMEOUT_S = 0.7

# 网页服务。
WEB_HOST = "0.0.0.0"
WEB_PORT = 8080

