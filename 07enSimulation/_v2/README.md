# Model-Scale Rescue — Unity Steps 1–7

第6–7步自动救援版：`Builds/Mission/RescueMissionSimulation.exe`。4艘船自动规划、差速航行、接人并返回中心基地，详见 [Autonomous Rescue Guide](Autonomous_Rescue_Guide.md)。此版本包含自由相机与螺旋桨绑定修复。

最新螺旋桨修复版：`Builds/Fleet_PropellerFix/RescueFleetSimulation.exe`。修复了空旋转节点未绑定实际桨叶的问题，包含自由相机。打包时旧程序仍在运行，因此使用独立输出目录；请启动这个新版。

第4–5步：运行 `Builds/Fleet/RescueFleetSimulation.exe`。救援站位于中心，24名待救人员随水流漂浮，4艘船自动分配救援名额。参见 [Fleet Rescue Guide](Fleet_Rescue_Guide.md)。目前可手动驾驶选中的船，自动避障航行与接送流程属于后续第6–7步。

第3步新增洪水环境：运行 `Builds/Flood/RescueFloodEnvironment.exe`，操作和范围见 [Flood Environment Guide](Flood_Environment_Guide.md)。原第1–2步实验室仍保留，以下说明适用于原实验室。

工程位置：`F:\gugugaga\07enSimulation\_v2`。使用本机已安装的 **Unity 6000.6.0f1**。

## 直接观看和操作

运行 `Builds/Windows/RescueBoatPhysicsLab.exe`。也可以在 Unity Hub 中添加本目录，打开 `Assets/Rescue/Scenes/BoatPhysicsLab.unity`，点击 Play。

- W / S：双桨前进、倒车；A / D：差速转向。
- Space：停桨，船会继续滑行并受水阻减速。
- R：复位船体；P：暂停/继续物理计算；C：全景/跟随视角。
- 取消左侧 `Keyboard control`，可以分别拖动两台电机的油门。
- `+ Passenger` / `- Passenger`：增加/减少一个1克模型乘员，同时更新质量、重心、惯量和人物外观。
- 水流滑块：设置横向水流；`ROLL DISTURBANCE`：施加横摇扰动；`CAPSIZE TEST`：查看倾覆状态。

`Assets/Rescue/Scenes/ModelGallery.unity` 展示基地、四艘船和人物的相同比例。该场景的船是静态展示，四船救援调度尚未实现。

## 已完成的第1步

- 独立导出、导入四个米制FBX：船、基地、站姿人物、坐姿人物。
- Unity 世界坐标：X向右，Y向上，Z为船头方向；1 Unity单位=1米。船体0.07×0.05米，完整外廓包含螺旋桨和救生圈。
- 双桨独立旋转节点，作用点为X=±0.0135、Y=0.0038、Z=-0.0388米。
- 基地的滑门保留独立节点；底板采用已有06号工程中的湿船库副本，原Blender文件不变。
- 站姿人物保留17个可摆动的刚性分段关节，避免FBX蒙皮轴向转换导致人物横躺；坐姿资产是用于载荷测试的固定姿态外观。后续行走/登船动画可以在关节上制作。
- `Prefabs` 中有可复用的船舶物理预制体、基地和两种人物预制体；`Reports/Model_Import_Report.json` 记录导入尺寸、轴向和旋转点。

## 已完成的第2步

船体位置、速度、姿态和碰撞由 **Unity PhysX Rigidbody** 实时积分。自定义模块在每个物理子步施加牛顿制力和力矩：

1. 对封闭排水船体进行体积分区，按浸水比例累计排水体积及浮心；在浮心施加 `ρgV` 浮力。
2. 相对水流计算船体坐标系中的线性和二次阻力，并施加角阻尼。
3. 两台电机具有0.12秒响应时间；推力为 `ρ Kt D⁴ n|n|`，n单位为转/秒，按桨盘浸水比例修正。推力作用在各自桨轴位置，产生前进和转向响应。
4. 乘员加入/移除时重算总质量、重心、完整惯量矩阵及其主轴，传给Rigidbody；保持船体原点连续。
5. 船体凸碰撞体、救生圈/桨罩简化复合碰撞体与水池边界、障碍物进行PhysX接触计算。
6. 显示搁浅接近、倾覆和甲板边缘浸水状态。状态用于诊断；当前没有船舱进水量或损伤积累模型。

实际船运动没有使用Blender烘焙轨迹。只有桨叶显示角度由RPM积分驱动；高RPM在显示器上可能有视觉混叠。

物理主时钟为60Hz，每次包含16个PhysX子步，积分步长为1/960秒。小模型接触偏移为0.1毫米；船长和质量没有放大。可以在 `PhysicsClock` 修改子步数，但修改后应重新进行精度对照。

## 参数与验证

空载质量暂定12克；乘员每个1克、最多6个，因此满载18克。质量、重心分布、Kt=0.18、水阻等沿用模型初始估算，可在 `Assets/Rescue/Settings/ModelBoat.asset` 中调整。源质量组成和浮力分区数据在 `Data/BoatHydrostatics.json`。

`Reports/PhysX_Validation_Report.json` 是在本机Unity/PhysX中实际运行的自动检查结果，包括导入方向和尺寸、空载浮力平衡、六人载荷、扰动恢复、前进/倒车/差速转向、停桨减速、水流漂移、撞墙、触底和时间步长对照。

`Reports/Runtime_Smoke_Report.json` 和 `Runtime_Physics_Lab.png` 用于检查Windows程序运行时的实时推进、增载及画面。测试通过不等同于实物标定。模型没有CFD、波浪、表面张力、实际进水和乘员足底/安全带受力计算；第3–8步的洪水环境、人员搜救、四船调度和导航控制尚待接入。

## 后续接入点

- 调度/航迹控制器通过 `BoatDynamics.portCommand`、`starboardCommand` 输入[-1,1]油门。
- 登船管理调用 `SetPassengerCount` 更新载荷；正式救援时可扩展为具有位置和质量的逐人载荷接口。
- `WaterField.SurfaceAt` 和 `VelocityAt` 可扩展为分区水深、空间变化流速和波浪采样。
- `PhysicsClock.boats` 可以注册四艘动态船，所有船共享同一PhysX子步。

## 重建

Unity菜单 `Rescue > Build Steps 1-2` 会重新生成本阶段的场景和预制体；先保存你希望保留的手工编辑。`Rescue > Validate PhysX Steps 1-2` 在空测试场景运行验证。

`Tools/Export_Blender_Assets.py` 在Blender后台读取原项目并导出FBX和数据。导出后用Unity构建菜单重新生成预制体。`Tools/Build_And_Verify.ps1` 可重建工程、验证并生成Windows程序；运行脚本前关闭占用此工程的Unity窗口。

实现依据：[Unity AddForceAtPosition](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Rigidbody.AddForceAtPosition.html)、[Physics.Simulate](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Physics.Simulate.html)、[Rigidbody惯量张量](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/Rigidbody-inertiaTensor.html)。
