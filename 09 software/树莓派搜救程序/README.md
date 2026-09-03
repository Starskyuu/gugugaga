# 树莓派搜救路线程序

这是可独立复制到 Raspberry Pi 5 的完整程序包，不依赖上级目录中的文件。

- `pi_rescue_service.py`：主服务
- `config.json`：场地、船速、端口与算法配置
- `rescue_core.py`、`route_planners.py`：路线算法
- `vision_input_example.py`：视觉坐标发送示例
- `route_receiver_example.py`：船端路线接收示例
- `install.sh`、`rescue-planner.service`：安装和开机启动
- `tests/`：自动测试
- `树莓派部署指南.md`：完整操作说明

在电脑上快速验证：

```powershell
python -m unittest discover -s tests -v
```

在树莓派上安装：

```bash
chmod +x install.sh
sudo ./install.sh
```
