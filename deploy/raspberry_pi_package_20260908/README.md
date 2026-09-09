# 城市方舟树莓派部署包

本目录是树莓派部署副本，不会影响电脑上的原始工程。

## 包含内容

- `vision/6.py`：摄像头、YOLO、ArUco、实时视频和控制桥接服务。
- `vision/best.pt`：人员检测模型。
- `vision/camera_calibration_usb.json`：USB摄像头标定数据。
- `frontend/`：控制前端源码，不包含Windows生成的依赖和缓存。
- `城市方舟实时搜救系统使用手册.md`：完整使用和排障说明。
- `install_pi.sh`：树莓派Python环境安装脚本。
- `start_vision.sh`：视觉服务启动脚本。
- `start_frontend.sh`：前端启动脚本。

ESP32使用的`main.py`没有放入本包。该文件应烧录到ESP32，而不是在树莓派运行；同时其中包含无线网络配置，不应进入普通部署副本。

## 首次安装

把整个目录复制到树莓派后执行：

```bash
cd raspberry_pi_package_20260908
chmod +x install_pi.sh start_vision.sh start_frontend.sh
./install_pi.sh
```

前端需要Node.js 22.13或更高版本。确认Node.js满足要求后：

```bash
cd frontend
npm ci
```

## 启动视觉服务

只运行视觉功能：

```bash
./start_vision.sh
```

连接真实ESP32：

```bash
ESP32_URL=http://ESP32的IP ./start_vision.sh
```

视觉接口默认监听：

```text
http://树莓派IP:8080
```

## 启动前端

另开一个终端：

```bash
./start_frontend.sh
```

同一局域网中的手机或电脑访问：

```text
http://树莓派IP:3000
```

前端中的视觉服务地址填写：

```text
http://树莓派IP:8080
```

## 注意事项

- 首次实机控制前必须架空船体测试松手停车和700ms超时停车。
- 当前系统没有公网身份认证和HTTPS，不要直接映射到公网。
- 标定文件来自原USB摄像头。更换摄像头后应重新标定。
- `best.pt`可以直接运行，但树莓派5后续可转换为NCNN模型以提高性能。
