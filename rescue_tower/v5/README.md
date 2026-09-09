# 智能救援塔 v5（v4 + 禁航区规避）

v5 在 v4 基础上加入不能航行区域（禁航区）：`config.py` 的 `OBSTACLES_MM`
配好了全部禁航区矩形，A* 规划自动绕行并在禁航区外再留安全余量。
双环 PID 连续油门导航、水位触发、升降台、两套前端、手动遥控、
安全停车等其余功能与 v4 完全一致。

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

## 与 v4 的差别

- `config.py`：`OBSTACLES_MM` 填入 10 块禁航区矩形，A* 规划自动绕开，
  并在矩形外再留 `SAFETY_MARGIN_MM`（12 mm）余量，重叠区域自动合并。
- 规划的起点/目标一旦落在禁航区内，任务进入 error 并停车，不会硬闯。
- `tests/test_offline.py`、`main.py debug planner` 的示例坐标移到禁航区外，
  并新增"绕行中央禁航区"的测试。
- 固件与 PID 参数同 v4：从 v4 升级无需重烧、无需重调。

## 禁航区（v5）

`config.py` 中 `OBSTACLES_MM` 的格式是轴对齐矩形 `(x1, y1, x2, y2)`（毫米）：

- ArUco 7/9/12 号标记为中心 30×30 的区域（中心坐标取自 666.py 的
  `REFERENCE_POINTS`：7=(574,297)、9=(17,345)、12=(568,570)）；
- (70,190) 左下、(70,440) 左上、(535,180) 右下、(420,75) 左下的边角合围区；
- (130,525)-(290,525)、(350,525)-(460,525) 与上边合围的两段；
- 以 (175,210)-(430,390) 连线为对角线的中央矩形。

改场地布局时只改 `OBSTACLES_MM`；重叠矩形自动合并，无需去重。

## 烧录固件（必须做）

把 `firmware/boat_main.py` 烧到小船 ESP32-C3。旧固件没有 /M 接口，
不烧的话自动航行无法工作（手动遥控不受影响）。升降台、水位固件不变。

## 运行

```bash
cd ~/rescue_tower/v5
chmod +x start.sh
./start.sh
```

浏览器打开 `http://树莓派IP:8080`。完整前端同 v3：`./start_full_frontend.sh`。

## 调参（先仿真，再下水）

```bash
cd ~/rescue_tower/v5
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
