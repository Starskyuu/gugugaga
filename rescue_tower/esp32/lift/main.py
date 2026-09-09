# ============================================================
# 城市方舟 - ESP32 手机控制升降平台 V2 LOW-START
# ============================================================
#
# 这版严格基于“真正能用”的第一版修改：
#
# 底层控制范围：
#   0 ~ 360
#
# 底层 PWM 映射：
#   0   -> 300 us
#   180 -> 1500 us
#   360 -> 2700 us
#
# 平台实际安全范围：
#   40  -> 最低
#   175 -> 最高（实测最合适）
#
# 网页允许调节范围：
#   40 ~ 180
#
# 注意：
#   这版的“40”和原来正确第一版的“40”完全一致。
#
# ============================================================

import network
import socket
import time
import gc

from machine import Pin, PWM


# ============================================================
# 1. Wi-Fi 参数
# ============================================================

WIFI_SSID = "Mate 70 Pro"
WIFI_PASSWORD = "87654321"

WIFI_TX_POWER = 2


# ============================================================
# 2. 舵机底层参数
# ============================================================

SERVO_PIN = 18

# 底层完整控制范围
MIN_ANGLE = 0
MAX_ANGLE = 360

# PWM 范围
SERVO_MIN_US = 300
SERVO_MAX_US = 2700


# ============================================================
# 3. 升降平台机械标定
#
# 以后主要改这里
# ============================================================

# 实测最低
PLATFORM_MIN = 40

# 网页允许的最大调节值
PLATFORM_MAX = 160

# 三个主要位置
DOWN_VALUE = 40
MID_VALUE = 110
UP_VALUE = 160

# 调节步长
BIG_STEP = 5
SMALL_STEP = 1

# 开机默认位置：完全收缩到最低位置
START_VALUE = DOWN_VALUE

current_value = START_VALUE


# ============================================================
# 4. 初始化舵机
# ============================================================

servo = PWM(
    Pin(SERVO_PIN),
    freq=50,
    duty_u16=0
)


# ============================================================
# 5. 控制值 -> PWM
#
# 完全沿用你真正能用的第一版
# ============================================================

def angle_to_us(angle):

    return int(
        SERVO_MIN_US
        +
        angle
        * (SERVO_MAX_US - SERVO_MIN_US)
        / 360
    )


# ============================================================
# 6. 底层设置舵机
#
# 仍允许 0 ~ 360
# ============================================================

def set_angle(angle):

    global current_value

    angle = int(angle)

    if angle < MIN_ANGLE:
        angle = MIN_ANGLE

    if angle > MAX_ANGLE:
        angle = MAX_ANGLE

    pulse_us = angle_to_us(
        angle
    )

    duty = int(
        pulse_us
        * 65535
        / 20000
    )

    servo.duty_u16(
        duty
    )

    current_value = angle

    print(
        "SERVO ->",
        current_value,
        "/360",
        "| PWM:",
        pulse_us,
        "us",
        "| duty:",
        duty
    )


# ============================================================
# 7. 平台安全控制层
#
# 网页只能进入 40 ~ 180
# ============================================================

def set_platform(value):

    value = int(value)

    if value < PLATFORM_MIN:
        value = PLATFORM_MIN

    if value > PLATFORM_MAX:
        value = PLATFORM_MAX

    set_angle(
        value
    )


# ============================================================
# 8. 平台动作
# ============================================================

def platform_up():

    print()
    print("COMMAND -> UP")

    set_platform(
        UP_VALUE
    )


def platform_down():

    print()
    print("COMMAND -> DOWN")

    set_platform(
        DOWN_VALUE
    )


def platform_middle():

    print()
    print("COMMAND -> MIDDLE")

    set_platform(
        MID_VALUE
    )


def value_plus(step):

    print()
    print(
        "COMMAND -> +",
        step
    )

    set_platform(
        current_value + step
    )


def value_minus(step):

    print()
    print(
        "COMMAND -> -",
        step
    )

    set_platform(
        current_value - step
    )


# ============================================================
# 9. Wi-Fi
# ============================================================

def connect_wifi():

    try:

        sta = network.WLAN(
            network.WLAN.IF_STA
        )

    except AttributeError:

        sta = network.WLAN(
            network.STA_IF
        )

    sta.active(False)
    time.sleep(1)

    sta.active(True)
    time.sleep(1)

    sta.config(
        txpower=WIFI_TX_POWER
    )

    print(
        "Wi-Fi TX Power =",
        sta.config("txpower"),
        "dBm"
    )

    try:
        sta.disconnect()
    except Exception:
        pass

    time.sleep_ms(
        300
    )

    print()
    print(
        "================================"
    )
    print(
        "Connecting Wi-Fi"
    )
    print(
        "================================"
    )
    print(
        "SSID:",
        WIFI_SSID
    )
    print()

    sta.connect(
        WIFI_SSID,
        WIFI_PASSWORD
    )

    for i in range(30):

        if sta.isconnected():

            info = sta.ifconfig()

            print()
            print(
                "★★★★★ Wi-Fi CONNECTED ★★★★★"
            )
            print(
                "IP:",
                info[0]
            )
            print(
                "Gateway:",
                info[2]
            )
            print(
                "TX Power:",
                sta.config("txpower"),
                "dBm"
            )
            print()

            return sta

        print(
            "Wi-Fi...",
            i + 1,
            "/30",
            "status:",
            sta.status()
        )

        time.sleep(
            1
        )

    return None


# ============================================================
# 10. 网页
# ============================================================

def make_html():

    pulse_us = angle_to_us(
        current_value
    )

    return """<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
name="viewport"
content="width=device-width,
initial-scale=1.0,
maximum-scale=1.0">

<title>城市方舟</title>

<style>

body {
    margin: 0;
    background: #17191e;
    color: white;
    font-family: Arial, sans-serif;
    text-align: center;
}

.container {
    width: 90%;
    max-width: 430px;
    margin: auto;
    padding-top: 35px;
}

h1 {
    margin-bottom: 5px;
}

.subtitle {
    color: #999;
    margin-bottom: 25px;
}

.status {
    background: #30333b;
    padding: 25px;
    border-radius: 20px;
    margin-bottom: 25px;
}

.value {
    font-size: 56px;
    font-weight: bold;
    margin-top: 8px;
}

.pwm {
    margin-top: 8px;
    color: #999;
}

.range {
    margin-top: 8px;
    color: #999;
}

a {
    display: flex;
    box-sizing: border-box;
    width: 100%;
    height: 70px;
    margin: 12px 0;
    border-radius: 18px;
    align-items: center;
    justify-content: center;
    text-decoration: none;
    font-size: 22px;
    font-weight: bold;
}

.up {
    background: #68efb0;
    color: #111;
}

.middle {
    background: white;
    color: #111;
}

.down {
    background: #ff7777;
    color: white;
}

.row {
    display: flex;
    gap: 10px;
}

.adjust {
    width: 50%;
    background: #414650;
    color: white;
}

.small {
    background: #343840;
}

a:active {
    transform: scale(0.96);
}

.footer {
    color: #777;
    margin-top: 25px;
    font-size: 14px;
    line-height: 1.6;
}

</style>

</head>

<body>

<div class="container">

<h1>
城市方舟
</h1>

<div class="subtitle">
智能救援塔 · 升降平台 V2
</div>

<div class="status">

当前控制值

<div class="value">
""" + str(current_value) + """
</div>

<div class="pwm">
PWM = """ + str(pulse_us) + """ us
</div>

<div class="range">
安全调节范围 40 ~ 160
</div>

</div>


<a
class="up"
href="/U">
▲ 完全升起 · """ + str(UP_VALUE) + """
</a>


<a
class="middle"
href="/M">
● 中间位置 · """ + str(MID_VALUE) + """
</a>


<a
class="down"
href="/D">
▼ 完全下降 · """ + str(DOWN_VALUE) + """
</a>


<div class="row">

<a
class="adjust"
href="/N5">
− 5
</a>

<a
class="adjust"
href="/P5">
+ 5
</a>

</div>


<div class="row">

<a
class="adjust small"
href="/N1">
− 1
</a>

<a
class="adjust small"
href="/P1">
+ 1
</a>

</div>


<div class="footer">
底层仍为 0 ~ 360<br>
PWM 仍为 300 ~ 2700 us<br>
网页只允许 40 ~ 160
</div>

</div>

</body>

</html>
"""


# ============================================================
# 11. HTTP 发送
# ============================================================

def send_all(client, data):

    total = 0

    while total < len(data):

        sent = client.send(
            data[total:]
        )

        if not sent:
            break

        total += sent


def send_page(client):

    body = make_html().encode(
        "utf-8"
    )

    header = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=UTF-8\r\n"
        "Content-Length: "
        + str(len(body))
        + "\r\n"
        "Connection: close\r\n"
        "Cache-Control: no-store, no-cache, must-revalidate\r\n"
        "Pragma: no-cache\r\n"
        "Expires: 0\r\n"
        "\r\n"
    ).encode(
        "utf-8"
    )

    send_all(
        client,
        header
    )

    send_all(
        client,
        body
    )


# ============================================================
# 12. HTTP 请求处理
# ============================================================

def handle_client(client):

    client.settimeout(
        1
    )

    request = client.recv(
        1024
    )

    if not request:
        return

    try:

        first_line = (
            request
            .split(b"\r\n")[0]
            .decode(
                "utf-8",
                "ignore"
            )
        )

    except Exception:

        first_line = ""

    print(
        "HTTP:",
        first_line
    )

    try:

        path = (
            first_line
            .split(" ")[1]
            .split("?")[0]
        )

    except Exception:

        path = "/"

    print(
        "PATH:",
        path
    )


    if path == "/U":

        platform_up()


    elif path == "/D":

        platform_down()


    elif path == "/M":

        platform_middle()


    elif path == "/P5":

        value_plus(
            BIG_STEP
        )


    elif path == "/N5":

        value_minus(
            BIG_STEP
        )


    elif path == "/P1":

        value_plus(
            SMALL_STEP
        )


    elif path == "/N1":

        value_minus(
            SMALL_STEP
        )


    send_page(
        client
    )


# ============================================================
# 13. 启动
# ============================================================

print()
print(
    "================================"
)
print(
    "城市方舟 ESP32 Servo V2"
)
print(
    "================================"
)
print()

print(
    "SERVO -> GPIO18"
)

print(
    "LOW LEVEL -> 0 ~ 360"
)

print(
    "PWM -> 300 ~ 2700 us"
)

print(
    "WEB SAFE -> 40 ~ 160"
)

print(
    "DOWN ->",
    DOWN_VALUE
)

print(
    "UP ->",
    UP_VALUE
)

print()


# ============================================================
# 14. 开机
# ============================================================

set_platform(
    START_VALUE
)

time.sleep(
    1
)


# ============================================================
# 15. Wi-Fi
# ============================================================

sta = connect_wifi()

if sta is None:

    raise RuntimeError(
        "Wi-Fi connection failed"
    )

ESP32_IP = (
    sta.ifconfig()[0]
)

print(
    "================================"
)

print(
    "SYSTEM READY"
)

print(
    "================================"
)

print()

print(
    "ESP32 IP:"
)

print(
    ESP32_IP
)

print()

print(
    "手机浏览器打开："
)

print(
    "http://" + ESP32_IP
)

print()


# ============================================================
# 16. HTTP Server
# ============================================================

server = socket.socket(
    socket.AF_INET,
    socket.SOCK_STREAM
)

try:

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

except OSError:

    pass

server.bind(
    (
        "0.0.0.0",
        80
    )
)

server.listen(
    4
)

server.settimeout(
    0.1
)

print(
    "HTTP SERVER READY"
)

print()


# ============================================================
# 17. 主循环
# ============================================================

try:

    while True:

        if not sta.isconnected():

            print(
                "WIFI LOST"
            )

            try:

                sta.config(
                    txpower=WIFI_TX_POWER
                )

                sta.connect(
                    WIFI_SSID,
                    WIFI_PASSWORD
                )

            except Exception as e:

                print(
                    "Reconnect error:",
                    e
                )

            time.sleep(
                1
            )

            continue

        try:

            client, addr = (
                server.accept()
            )

        except OSError:

            continue

        try:

            handle_client(
                client
            )

        except Exception as e:

            print(
                "HTTP ERROR:",
                e
            )

        finally:

            try:
                client.close()
            except Exception:
                pass

        gc.collect()


except KeyboardInterrupt:

    print()
    print(
        "CTRL+C"
    )


finally:

    try:
        server.close()
    except Exception:
        pass

    print(
        "SERVER CLOSED"
    )
