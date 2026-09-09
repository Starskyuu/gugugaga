# Autonomous Rescue — Steps 6 and 7

## 启动

运行 `Builds/Mission/RescueMissionSimulation.exe`。Unity 场景为 `Assets/Rescue/Scenes/AutonomousRescue.unity`，工程继续位于 `_v2`，船体保持7×5厘米。

启动后4艘船自动执行救援，默认24名待救人员分布在中心基地四周。观察右侧 Rescued 计数、每船状态和人员列表。分享时压缩整个 `Builds/Mission` 文件夹，不要只发送 EXE。

## 第6步：导航与控制

规划器根据场景真实碰撞体建立25毫米栅格，把建筑、基地墙体和边界按船体安全距离扩大，同时检查船体周围水深。A* 搜索考虑逆流代价，并简化成可跟踪的航点。漂浮物和其他船的位置进入规划，路线会定期重算；预测船间距离过近时，高编号船让行。

船体运动由原有 PhysX 刚体、浮力、水阻和双螺旋桨推力求解。控制器根据位置、速度、水流和朝向误差计算左右桨命令，不沿航线修改船体位置或旋转。彩色较粗折线是计划航线；原先较细的人员归属连线可以另行开启。

这是局部水流近似下的栅格导航与反馈控制，不是全局最优航行求解，也不是CFD。路线及避让会随实际漂移和载荷变化；极端水位/水流可能让任务阻塞或船倾覆。

## 第7步：救援流程

状态依次包括 Outbound、Approaching、Boarding、Returning、Unloading、Complete。接近人员时减速，只有距离和相对速度满足条件才开始上船。上船后增加1克载荷、更新重心惯量并显示座位上的乘员；满6人或当前任务已完成时返航。

船回到各自方向的基地外侧接驳点，低速停靠后逐人下船，移到基地原有长凳的24个座位。Rescued 只在下船完成后增加；已分配、正在登船和船上人员都不会提前算作获救。完成全部人员转移后，船在接驳点保持位置。

登船/下船采用简化运动过渡，转移中的人物暂时关闭碰撞；并非人体关节动力学或逐级爬梯动画。接驳发生在基地外侧，当前没有自动滑门动画或驶入舱内的精细泊船动作。

## 操作

- 默认 AUTO 自动航行。1–4 选船仅改变查看对象，不会中断其他船。
- 右侧 Take selected boat MANUAL：接管所选船，W/S/A/D 和左右油门滑块才控制它；Return selected boat to AUTO：交回自动控制。
- Stop autopilots / Space：停止自动控制，物理仍继续，船会漂移；Resume autopilots 恢复。
- P：暂停/继续整个物理模拟；R：复位全部船、人员、载荷和获救计数。相机仍可操作。
- 左键/中键拖动平移，右键旋转，滚轮缩放，方向键移动；F 聚焦所选船，Home 恢复全景，C 自由/跟随视角。
- 保留洪水四种预设、水位/流速控制、漂浮物开关和人员紧急程度设置。Blocked 表示暂时没有安全路径或接近点，应查看水位、障碍和可用船状态。
- 停用某艘船会释放其水面任务供其他船认领；已在船上的人员仍在该船上。重新启用可继续返航。倾覆等需要人工恢复的情况不会被自动宣称救援成功。

## 验证与重建

- `Reports/Mission_Validation_Report.json`：编辑器内实际 PhysX 完整任务结果。
- `Reports/Mission_Runtime_Report.json`：独立程序完整救援、人数/载重、障碍绕行、浅水拒绝、暂停、手动接管与复位检查。
- `Reports/Runtime_Mission_Outbound.png`、`Runtime_Mission_Complete.png`：实际程序相机画面；`Runtime_Mission_Refuge.png` 为检查长凳人员而隐藏高处遮挡物的诊断图。以上不含屏幕控制面板。
- 测试启动参数 `-missionCheck` 使用加速模拟时间运行检查，正常打开程序没有此参数，以正常模拟速度运行。
- 关闭 Unity 后运行 `Tools/Build_Mission_And_Verify.ps1` 重建和检查。会重建生成的 AutonomousRescue 场景，手工修改前请另存。
