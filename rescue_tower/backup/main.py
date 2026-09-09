# ============================================================
# 城市方舟 - ESP32-C3 Super Mini 双电机网页遥控
# ============================================================
#
# 网络模式：
#   ESP32-C3 连接 Mate 70 Pro 热点
#
# 热点：
#   SSID     = Mate 70 Pro
#   Password = 87654321
#
# ESP32-C3 Super Mini 特殊设置：
#   Wi-Fi TX Power = 2 dBm
#
#
# DRV8833 接线：
#
#   AIN1  -> GPIO7
#   AIN2  -> GPIO6
#
#   BIN1  -> GPIO3
#   BIN2  -> GPIO10
#
#   STBY  -> GPIO8
#
#
# 控制逻辑：
#
#   ↑ 前进：
#       A 正转
#       B 正转
#
#   ↓ 后退：
#       A 反转
#       B 反转
#
#   ← 左转：
#       A 反转
#       B 正转
#
#   → 右转：
#       A 正转
#       B 反转
#
#   STOP：
#       两侧停止
#
#
# 安全功能：
#
#   1. 松手停车
#   2. 700ms 无命令自动停车
#   3. Wi-Fi 断开自动停车
#   4. Ctrl+C 自动停车
#
# ============================================================


import network
import socket
import time

from machine import Pin, PWM


# ============================================================
# 1. Wi-Fi 参数
# ============================================================

WIFI_SSID = "Mate 70 Pro"
WIFI_PASSWORD = "87654321"

# 你的 Super Mini 实测可连接的发射功率
WIFI_TX_POWER = 2


# ============================================================
# 2. DRV8833 引脚
# ============================================================

# A 通道
AIN1_PIN = 7
AIN2_PIN = 6

# B 通道
BIN1_PIN = 3
BIN2_PIN = 10

# 驱动使能
STBY_PIN = 8


# ============================================================
# 3. PWM / 电机速度
# ============================================================

PWM_FREQ = 20000

MAX_SPEED = 55

FORWARD_SPEED = 40
BACKWARD_SPEED = 35
TURN_SPEED = 35


# ============================================================
# 4. 电机方向修正
# ============================================================
#
# 如果 ↑ 的时候某一侧反了：
#
# MOTOR_A_REVERSE = True
#
# 或：
#
# MOTOR_B_REVERSE = True
#
# 不需要重新改下面代码。
# ============================================================

MOTOR_A_REVERSE = False
MOTOR_B_REVERSE = False


# ============================================================
# 5. 安全停车时间
# ============================================================

SAFETY_TIMEOUT_MS = 700


# ============================================================
# 6. 初始化 DRV8833
# ============================================================

# 启动时先关闭驱动
stby = Pin(
    STBY_PIN,
    Pin.OUT
)

stby.value(0)


# A 通道
ain1 = PWM(
    Pin(AIN1_PIN),
    freq=PWM_FREQ,
    duty_u16=0
)

ain2 = PWM(
    Pin(AIN2_PIN),
    freq=PWM_FREQ,
    duty_u16=0
)


# B 通道
bin1 = PWM(
    Pin(BIN1_PIN),
    freq=PWM_FREQ,
    duty_u16=0
)

bin2 = PWM(
    Pin(BIN2_PIN),
    freq=PWM_FREQ,
    duty_u16=0
)


# 全部初始化完后打开驱动
stby.value(1)


# ============================================================
# 7. 电机控制底层
# ============================================================

def speed_to_duty(speed):
    """
    百分比速度转换为 PWM duty_u16
    """

    speed = abs(speed)

    if speed > MAX_SPEED:
        speed = MAX_SPEED

    return int(
        speed * 65535 / 100
    )


def set_motor(
    pwm1,
    pwm2,
    speed,
    reverse=False
):
    """
    控制一个电机

    speed > 0 ：正转
    speed < 0 ：反转
    speed = 0 ：停止
    """

    if reverse:
        speed = -speed

    duty = speed_to_duty(
        speed
    )


    if speed > 0:

        pwm1.duty_u16(
            duty
        )

        pwm2.duty_u16(
            0
        )


    elif speed < 0:

        pwm1.duty_u16(
            0
        )

        pwm2.duty_u16(
            duty
        )


    else:

        pwm1.duty_u16(
            0
        )

        pwm2.duty_u16(
            0
        )


def set_motors(
    motor_a_speed,
    motor_b_speed
):

    set_motor(
        ain1,
        ain2,
        motor_a_speed,
        MOTOR_A_REVERSE
    )

    set_motor(
        bin1,
        bin2,
        motor_b_speed,
        MOTOR_B_REVERSE
    )


def stop():

    set_motors(
        0,
        0
    )


# ============================================================
# 8. 运动函数
# ============================================================

def forward():

    print("MOTOR -> FORWARD")

    set_motors(
        FORWARD_SPEED,
        FORWARD_SPEED
    )


def backward():

    print("MOTOR -> BACKWARD")

    set_motors(
        -BACKWARD_SPEED,
        -BACKWARD_SPEED
    )


def turn_left():

    print("MOTOR -> LEFT")

    set_motors(
        -TURN_SPEED,
        TURN_SPEED
    )


def turn_right():

    print("MOTOR -> RIGHT")

    set_motors(
        TURN_SPEED,
        -TURN_SPEED
    )


def motor_stop():

    print("MOTOR -> STOP")

    stop()


# ============================================================
# 9. Wi-Fi
# ============================================================

def connect_wifi():

    sta = network.WLAN(
        network.WLAN.IF_STA
    )


    # --------------------------------------------------------
    # 完全重置 Wi-Fi
    # --------------------------------------------------------

    sta.active(False)

    time.sleep(1)

    sta.active(True)

    time.sleep(1)


    # --------------------------------------------------------
    # Super Mini 关键参数
    # --------------------------------------------------------

    sta.config(
        txpower=WIFI_TX_POWER
    )


    print(
        "Wi-Fi TX Power =",
        sta.config("txpower"),
        "dBm"
    )


    # --------------------------------------------------------
    # 清除旧连接
    # --------------------------------------------------------

    try:

        sta.disconnect()

    except Exception:

        pass


    time.sleep_ms(
        300
    )


    # --------------------------------------------------------
    # 开始连接
    # --------------------------------------------------------

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


    # 最多等待 30 秒
    for i in range(30):


        if sta.isconnected():

            info = sta.ifconfig()


            print()

            print(
                "Wi-Fi CONNECTED"
            )

            print(
                "IP:",
                info[0]
            )

            print(
                "Gateway:",
                info[2]
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
#
# 这次不再使用复杂 touchstart + mousedown 双事件。
#
# 统一使用 Pointer Events：
#
# pointerdown
# pointerup
# pointercancel
#
# 手机和电脑共用。
#
# 命令 URL 也改成最简单：
#
# /F
# /B
# /L
# /R
# /S
#
# ============================================================


HTML = """<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<meta
name="viewport"
content="width=device-width,
initial-scale=1.0,
maximum-scale=1.0,
user-scalable=no">

<title>城市方舟</title>


<style>

html,
body {

    margin: 0;

    padding: 0;

    width: 100%;

    height: 100%;

    background: #101010;

    color: white;

    font-family: Arial, sans-serif;

    text-align: center;

    touch-action: none;

    overflow: hidden;
}


h1 {

    margin-top: 25px;

    margin-bottom: 5px;

}


.subtitle {

    color: #888;

    font-size: 14px;

}


#status {

    margin-top: 20px;

    margin-bottom: 20px;

    font-size: 18px;

    color: #bbb;

}


.controller {

    width: 330px;

    margin: 0 auto;

}


.row {

    display: flex;

    justify-content: center;

    gap: 15px;

    margin: 15px 0;

}


.control {

    width: 90px;

    height: 90px;

    border: 0;

    border-radius: 22px;

    background: #333;

    color: white;

    font-size: 42px;

    font-weight: bold;

    touch-action: none;

    -webkit-user-select: none;

    user-select: none;
}


.control.active {

    background: #666;

    transform: scale(0.95);
}


.stop {

    background: #900;

    font-size: 18px;
}


.stop.active {

    background: #d00000;
}


#debug {

    margin-top: 20px;

    font-size: 13px;

    color: #666;
}

</style>

</head>


<body>


<h1>
城市方舟
</h1>


<div class="subtitle">
ESP32-C3 Rescue Boat
</div>


<div id="status">
READY
</div>


<div class="controller">


<div class="row">

<button
class="control"
data-command="F">
↑
</button>

</div>


<div class="row">


<button
class="control"
data-command="L">
←
</button>


<button
class="control stop"
data-command="S">
STOP
</button>


<button
class="control"
data-command="R">
→
</button>


</div>


<div class="row">

<button
class="control"
data-command="B">
↓
</button>

</div>


</div>


<div id="debug">
Waiting...
</div>


<script>


let activeCommand = null;

let commandTimer = null;


// ========================================================
// 发送命令
// ========================================================

function sendCommand(command) {


    document.getElementById(
        "debug"
    ).innerText =
        "SEND: " + command;


    // ----------------------------------------------------
    // 加随机参数，彻底禁止浏览器缓存请求
    // ----------------------------------------------------

    const url =
        "/" +
        command +
        "?t=" +
        Date.now();


    fetch(
        url,
        {
            method: "GET",
            cache: "no-store"
        }
    )

    .then(
        function(response) {

            document.getElementById(
                "debug"
            ).innerText =
                "OK: " + command;

        }
    )

    .catch(
        function(error) {

            document.getElementById(
                "debug"
            ).innerText =
                "ERROR: " + error;

        }
    );

}


// ========================================================
// 开始运动
// ========================================================

function startMove(
    command,
    button
) {


    if (
        command === "S"
    ) {

        stopMove();

        return;

    }


    // ----------------------------------------------------
    // 防止重复 timer
    // ----------------------------------------------------

    if (
        commandTimer !== null
    ) {

        clearInterval(
            commandTimer
        );

        commandTimer =
            null;

    }


    activeCommand =
        command;


    button.classList.add(
        "active"
    );


    document.getElementById(
        "status"
    ).innerText =
        "RUN: " + command;


    // 马上发送一次
    sendCommand(
        command
    );


    // ----------------------------------------------------
    // 每 200ms 发送一次心跳
    // ----------------------------------------------------

    commandTimer =
        setInterval(

            function() {


                if (
                    activeCommand !== null
                ) {


                    sendCommand(
                        activeCommand
                    );


                }


            },

            200

        );

}


// ========================================================
// 停止
// ========================================================

function stopMove() {


    activeCommand =
        null;


    if (
        commandTimer !== null
    ) {


        clearInterval(
            commandTimer
        );


        commandTimer =
            null;

    }


    document
        .querySelectorAll(
            ".control"
        )
        .forEach(

            function(button) {

                button.classList.remove(
                    "active"
                );

            }

        );


    document.getElementById(
        "status"
    ).innerText =
        "STOP";


    sendCommand(
        "S"
    );

}


// ========================================================
// 注册按钮
// ========================================================

document
.querySelectorAll(
    ".control"
)
.forEach(

    function(button) {


        const command =
            button.dataset.command;


        // ------------------------------------------------
        // 按下
        // ------------------------------------------------

        button.addEventListener(

            "pointerdown",

            function(event) {


                event.preventDefault();


                try {

                    button.setPointerCapture(
                        event.pointerId
                    );

                }

                catch(e) {

                }


                startMove(
                    command,
                    button
                );

            }

        );


        // ------------------------------------------------
        // 松开
        // ------------------------------------------------

        button.addEventListener(

            "pointerup",

            function(event) {


                event.preventDefault();


                if (
                    command !== "S"
                ) {


                    stopMove();


                }


            }

        );


        // ------------------------------------------------
        // Pointer 被系统取消
        // ------------------------------------------------

        button.addEventListener(

            "pointercancel",

            function() {


                if (
                    command !== "S"
                ) {


                    stopMove();


                }


            }

        );


    }

);


// ========================================================
// 页面切后台
// ========================================================

document.addEventListener(

    "visibilitychange",

    function() {


        if (
            document.hidden
        ) {


            stopMove();


        }


    }

);


// ========================================================
// 窗口失去焦点
// ========================================================

window.addEventListener(

    "blur",

    function() {


        stopMove();


    }

);


</script>


</body>

</html>
"""


# ============================================================
# 11. HTTP 工具
# ============================================================

def send_all(
    client,
    data
):

    total = 0


    while total < len(data):


        sent = client.send(
            data[total:]
        )


        if not sent:

            break


        total += sent


def send_response(
    client,
    body,
    content_type="text/plain"
):


    header = (

        "HTTP/1.1 200 OK\r\n"

        "Content-Type: "
        + content_type
        + "\r\n"

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

def handle_client(
    client
):


    client.settimeout(
        1
    )


    request = client.recv(
        1024
    )


    if not request:

        return None


    # --------------------------------------------------------
    # 把请求第一行打印到 Thonny
    #
    # 这是这版最重要的调试功能。
    # --------------------------------------------------------

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


        first_line = str(
            request[:100]
        )


    print(
        "HTTP:",
        first_line
    )


    # ========================================================
    # 前进
    # ========================================================

    if (
        b"GET /F"
        in request
    ):


        forward()


        send_response(
            client,
            b"F"
        )


        return "F"


    # ========================================================
    # 后退
    # ========================================================

    elif (
        b"GET /B"
        in request
    ):


        backward()


        send_response(
            client,
            b"B"
        )


        return "B"


    # ========================================================
    # 左转
    # ========================================================

    elif (
        b"GET /L"
        in request
    ):


        turn_left()


        send_response(
            client,
            b"L"
        )


        return "L"


    # ========================================================
    # 右转
    # ========================================================

    elif (
        b"GET /R"
        in request
    ):


        turn_right()


        send_response(
            client,
            b"R"
        )


        return "R"


    # ========================================================
    # 停车
    # ========================================================

    elif (
        b"GET /S"
        in request
    ):


        motor_stop()


        send_response(
            client,
            b"S"
        )


        return "S"


    # ========================================================
    # 网页
    # ========================================================

    else:


        html = HTML.encode(
            "utf-8"
        )


        send_response(
            client,
            html,
            "text/html; charset=UTF-8"
        )


        return None


# ============================================================
# 13. 启动
# ============================================================

stop()


print()

print(
    "================================"
)

print(
    "城市方舟 ESP32-C3 Super Mini"
)

print(
    "================================"
)

print()

print(
    "AIN1 -> GPIO7"
)

print(
    "AIN2 -> GPIO6"
)

print(
    "BIN1 -> GPIO3"
)

print(
    "BIN2 -> GPIO10"
)

print(
    "STBY -> GPIO8"
)

print()


# ============================================================
# 14. Wi-Fi
# ============================================================

sta = connect_wifi()


if sta is None:


    stop()


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
    "打开浏览器："
)

print(
    "http://"
    + ESP32_IP
)

print()


# ============================================================
# 15. HTTP Server
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
# 16. 控制状态
# ============================================================

last_command_time = (
    time.ticks_ms()
)


motor_running = False

last_command = None


# ============================================================
# 17. 主循环
# ============================================================

try:


    while True:


        # ====================================================
        # Wi-Fi 断开保护
        # ====================================================

        if not sta.isconnected():


            stop()


            motor_running = False


            print(
                "WIFI LOST -> STOP"
            )


            try:


                sta.config(
                    txpower=WIFI_TX_POWER
                )


                sta.connect(
                    WIFI_SSID,
                    WIFI_PASSWORD
                )


            except Exception:

                pass


            time.sleep(
                1
            )


            continue


        # ====================================================
        # 指令超时保护
        # ====================================================

        if motor_running:


            now = (
                time.ticks_ms()
            )


            elapsed = (
                time.ticks_diff(
                    now,
                    last_command_time
                )
            )


            if (
                elapsed
                >
                SAFETY_TIMEOUT_MS
            ):


                stop()


                motor_running = False


                last_command = "S"


                print(
                    "TIMEOUT -> STOP"
                )


        # ====================================================
        # HTTP
        # ====================================================

        try:


            client, addr = (
                server.accept()
            )


        except OSError:


            continue


        try:


            command = handle_client(
                client
            )


            # ------------------------------------------------
            # 运动命令
            # ------------------------------------------------

            if command in (
                "F",
                "B",
                "L",
                "R"
            ):


                last_command_time = (
                    time.ticks_ms()
                )


                motor_running = True


                if command != last_command:


                    print(
                        "COMMAND:",
                        command
                    )


                last_command = (
                    command
                )


            # ------------------------------------------------
            # STOP
            # ------------------------------------------------

            elif command == "S":


                motor_running = False


                last_command = "S"


                print(
                    "COMMAND: S"
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


# ============================================================
# 18. Ctrl+C
# ============================================================

except KeyboardInterrupt:


    print()

    print(
        "CTRL+C"
    )


# ============================================================
# 19. 退出
# ============================================================

finally:


    stop()


    print(
        "MOTOR STOPPED"
    )


    try:


        server.close()


    except Exception:


        pass


    print(
        "SERVER CLOSED"
    )