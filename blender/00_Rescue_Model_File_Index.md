# 救援模型文件索引

## 单船救援流程（步骤6）

- [06 Rescue Mission](PhysicsSimulation/06_Rescue_Mission.blend)：约80秒开门、出库、两人登船、载人倒车返航、爬梯转移至避雨甲板的演示，动态更新载荷和重心。
- [Rescue Mission Guide](PhysicsSimulation/Rescue_Mission_Guide.md)：观看、阶段时间、物理与编排动作的区别、参数假设及重建方法。

## 双桨推进与自动绕障（步骤4—5）

- [05 Propulsion and Navigation](PhysicsSimulation/05_Propulsion_And_Navigation.blend)：双桨推进、自动绕障、水流和碰撞演示。
- [Drive and Navigation Guide](PhysicsSimulation/Drive_And_Navigation_Guide.md)：播放、参数修改及当前仿真范围。

## 模型尺度物理仿真（步骤1—3）

- [04 Model Scale Physics Setup](PhysicsSimulation/04_Model_Scale_Physics_Setup.blend)：7厘米模型船的静水漂浮基线、基地碰撞结构与人物分段准备。
- [Physics Setup Guide](PhysicsSimulation/Physics_Setup_Guide.md)：参数假设、播放方法、数值验证和当前范围。
- [Physics Parameters](PhysicsSimulation/Physics_Parameters.json)：可修改的质量、重心组成、浮力和阻尼设置。

## 主要模型

- [01 无人救援船：7×5厘米](UnmannedRescueBoat_7cm/01_Unmanned_Rescue_Boat_7x5cm.blend)
- [02 无人救援基地：八盏檐灯版，最新版](UnmannedRescueBase/02_Rescue_Base_4Boat_8EaveLights_Latest.blend)
- [02 无人救援基地：基础版](UnmannedRescueBase/02_Rescue_Base_4Boat_Basic.blend)
- [03 救援小人：独立模型、骨架与站坐姿态](RescuePerson/03_Rescue_Person_Rigged_Stand_Sit.blend)
- [03 救援小人：座椅适配与六人乘船演示](RescuePerson/03_Rescue_Person_Seat_Fit_Six_Passenger_Demo.blend)

## 命名规则

文件以“编号_模型名称_用途或视图_版本”命名。01 为船，02 为基地，03 为小人。

`.blend` 为可编辑模型；`.blend1` 为 Blender 的上一次保存备份，并非另一个模型版本；`.png` 为预览图；`.py` 为建模脚本；使用说明保留在对应模型文件夹。

本次对话生成的 28 个文件已统一命名，文件夹位置保持不变。旧项目的灰模文件和脚本未纳入本次改名。`Filename_Rename_History.json` 保存全部新旧文件名对应关系。
