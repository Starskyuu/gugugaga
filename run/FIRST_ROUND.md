# 第一轮联调说明

## 已完成

- 修正场地参考点 ID 10 为 `(100, 100)`。
- 保留原有 USB 摄像头、ArUco、YOLO 与 OpenCV 显示逻辑。
- 新增线程安全的实时视觉状态缓存。
- 新增 JSON 状态接口、MJPEG 视频流和 ESP32 控制转发。
- ESP32 地址不写死，可通过启动参数或环境变量设置。
- 没有配置 ESP32 地址时，控制接口返回明确错误，不会误发命令。

## 树莓派启动方式

有本地显示器：

```bash
python3 6.py --esp32-url http://ESP32的IP
```

无显示器运行：

```bash
python3 6.py --no-display --esp32-url http://ESP32的IP
```

默认监听 `0.0.0.0:8080`。也可以指定端口：

```bash
python3 6.py --port 8080 --esp32-url http://192.168.43.120
```

也可以使用环境变量：

```bash
export ESP32_URL=http://192.168.43.120
python3 6.py --no-display
```

## 接口

- `GET /api/status`：完整系统状态。
- `GET /api/vision`：与状态接口返回相同的第一版视觉快照。
- `GET /video` 或 `/video.mjpg`：最高约 15 FPS 的 MJPEG 标注画面。
- `GET /F`、`/B`、`/L`、`/R`、`/S`：兼容原前端的控制接口。
- `GET /api/control?command=F`：JSON 控制接口。
- `POST /api/control`：请求体为 `{"command":"F"}`。

## 浏览器检查

树莓派 IP 假设为 `192.168.43.10`：

```text
http://192.168.43.10:8080/api/status
http://192.168.43.10:8080/video
```

控制命令只有在 `--esp32-url` 指向有效 ESP32 后才会转发。ESP32 原有的松手停车、700ms 超时停车和 Wi-Fi 断开停车逻辑没有修改。

## 下一步

前端需要增加“树莓派服务地址”配置，并读取 `/api/status` 与 `/video`。完成后即可在现有任务视野中显示真实画面、船坐标、人员坐标和性能状态。
