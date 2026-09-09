# 智能救援塔 v4（v3 + PID 连续油门导航）

v4 在 v3 基础上接入 PID 导航包：自动航行从"开关式 F/L/R/S"升级为
双环 PID 连续油门（外环距离->油门，内环航向->差速），通过小船固件
新增的 `/M?A=..&B=..` 接口下发。其余功能（水位触发、升降台、A* 规划、
两套前端、手动遥控、安全停车）与 v3 完全一致。

## 与 v3 的差别

- `core/nav_control.py`：PID 包自带的纯算法库（无硬件依赖），原样引入。
- `core/navigation.py`：新增 `PidPilot`（内部完成 666.py 航向约定 -> PID
  航向约定的换算）和 `build_nav_config()`；`choose_command` 原样保留。
- `core/devices.py`：`Boat` 新增 `throttle(a, b)`；`http_command` 改为按
  期望回包校验（`/M` 的回包固定是 `M`，单字母命令回包是命令本身）。
- `core/mission.py`：`_navigate()` 每周期用 `PidPilot` 计算油门并下发；
  视觉过期/丢目标时停车并重置 PID；连续下发失败 THROTTLE_MAX_FAILS 次急停。
- `config.py`：新增 PID 参数块（毫米制），现场调参只改这里。
- `firmware/boat_main.py`：换成 PID 包的 esp32_main.py（新增 /M 接口，
  F/B/L/R/S 手动遥控原样保留，自动模式 1 秒无命令自动停车）。

## 烧录固件（必须做）

把 `firmware/boat_main.py` 烧到小船 ESP32-C3。旧固件没有 /M 接口，
不烧的话自动航行无法工作（手动遥控不受影响）。升降台、水位固件不变。

## 运行

```bash
cd ~/rescue_tower/v4
chmod +x start.sh
./start.sh
```

浏览器打开 `http://树莓派IP:8080`。完整前端同 v3：`./start_full_frontend.sh`。

## 调参（先仿真，再下水）

```bash
cd ~/rescue_tower/v4
python3 tests/sim_pid.py                        # 600mm 场地运动学仿真
python3 -m unittest discover -s tests -v        # 离线测试
```

把仿真调好的参数抄进 `config.py` 的 PID 块，再下水实测。
现场常见调整：

- 想右转却左转：`PID_TURN_SIGN` 改成 -1。
- 远处跑太慢/起不来：加大 `PID_MIN_CRUISE`。
- 终点附近绕圈进不去：加大 `PID_MIN_APPROACH` 或 `PID_ACCEPT_RADIUS_MM`。
- 蛇形：加大 `PID_HEADING_DEADBAND_DEG`。

## 单模块调试

```bash
python3 main.py debug planner
python3 main.py debug vision
python3 main.py debug water
python3 main.py debug boat F
python3 main.py debug boat S
python3 main.py debug boat --throttle 40 -35   # 测试 /M 连续油门
python3 main.py debug lift U
python3 main.py debug web
```

## 航向换算说明

666.py 输出：+Y 为 0°，顺时针为正。PID 包要求：+X 为 0°，逆时针为正。
`PidPilot.to_pid_heading(angle) = 90 - angle`（折叠到 ±180）完成换算，
位置坐标两套约定一致无需转换，全程使用毫米。

## 安全链（与 v3 一致并加强）

- 视觉坐标过期/丢失 -> 立即 `/S` 停车并重置 PID；
- 小船固件：自动模式 1 秒无 /M 命令自动停车，Wi-Fi 断开停车；
- 网页急停 / 目标丢失 / 连续下发失败 -> 停车并进入 error 状态。

现场参数统一修改 `config.py`。
