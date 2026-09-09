from machine import Pin, ADC
import network
import socket
import time


# =====================================================
# 1. 水位传感器
# =====================================================

# 水位传感器信号线接 GPIO3
water_sensor = ADC(Pin(3))

# 设置 ADC 输入范围
water_sensor.atten(ADC.ATTN_11DB)


# =====================================================
# 2. 手机热点信息
# =====================================================

WIFI_SSID = "Mate 70 Pro"
WIFI_PASSWORD = "87654321"


# =====================================================
# 3. 树莓派的信息
# =====================================================

# 这里填写“树莓派的 IP 地址”
RASPBERRY_PI_IP = "192.168.43.12"

# 和树莓派程序中的 PORT 保持一致
PORT = 5000


# =====================================================
# 4. 连接手机热点
# =====================================================

wifi = network.WLAN(network.STA_IF)

wifi.active(True)

print("==============================")
print("ESP32-S3 水位通信程序")
print("==============================")

print("正在连接手机热点...")

wifi.connect(WIFI_SSID, WIFI_PASSWORD)


# 等待连接
while not wifi.isconnected():

    print("等待 Wi-Fi...")

    time.sleep(1)


# =====================================================
# 5. 打印 ESP32 的网络信息
# =====================================================

print()
print("Wi-Fi 连接成功！")
print("ESP32 IP 地址：", wifi.ifconfig()[0])
print("网关：", wifi.ifconfig()[2])
print()


# =====================================================
# 6. 创建 TCP Socket
# =====================================================

# =====================================================
# 7. 持续连接和发送
# =====================================================

# 每条数据加换行，树莓派可以准确区分相邻数据；断网后会自动重连。
while True:
    client = None
    try:
        print("正在连接树莓派...")
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5)
        client.connect((RASPBERRY_PI_IP, PORT))
        print("树莓派连接成功！")

        while True:
            water_value = water_sensor.read_u16()
            message = "Water:" + str(water_value) + "\n"
            client.sendall(message.encode())
            print("发送：", message.strip())
            time.sleep(1)
    except Exception as error:
        print("连接中断，3 秒后重连：", error)
        time.sleep(3)
    finally:
        if client:
            try:
                client.close()
            except Exception:
                pass
