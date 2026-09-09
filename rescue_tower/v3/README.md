# 智能救援塔 v3 轻量版

v3 保留 v2 的自动控制、A* 路径规划、安全停车和分模块调试，同时提供两套前端：

- `static/index.html`：轻量前端，不需要 npm，访问 8080 端口。
- `frontend_full/`：原完整视觉风格前端，保留任务控制、水位和升降台状态。

## 运行

```bash
cd ~/rescue_tower/v3
chmod +x start.sh
./start.sh
```

打开 `http://树莓派IP:8080` 即可，不需要执行 `npm install`。

需要运行完整前端时：

```bash
chmod +x start_full_frontend.sh
./start_full_frontend.sh
```

首次启动会执行 `npm ci`，然后访问 `http://树莓派IP:3000`。后端仍使用 8080 端口。

## 单模块调试

```bash
python3 main.py debug planner
python3 main.py debug vision
python3 main.py debug water
python3 main.py debug boat F
python3 main.py debug boat S
python3 main.py debug lift U
python3 main.py debug lift D
python3 main.py debug web
```

离线测试：

```bash
python3 -m unittest discover -s tests -v
```

现场参数统一修改 `config.py`。配套 ESP32 程序放在 `firmware/`，其中小船速度已小幅降低，水位固件支持断线自动重连。原版水位固件也能与 v3 接收端兼容。
