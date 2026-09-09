# 救援小人

以船上原座椅为基准，使用 Blender MCP 建模。穿橘黄色救生衣和蓝色衣裤，配有 17 根骨骼的关节式角色骨架。

- 站立总高约 2.17 cm，总宽约 0.896 cm；船上坐垫宽 0.92 cm。
- 03_Rescue_Person_Rigged_Stand_Sit.blend：独立小人模型，直接打开可查看站姿。时间轴第 1 帧为站姿，第 60 帧为坐姿。
- 03_Rescue_Person_Seat_Fit_Six_Passenger_Demo.blend：完整适配工程，默认显示六人乘船，另有“救援小人 · 单座适配”和“救援小人 · 骨架与姿态”场景。
- 03_Rescue_Person_Standing.png、03_Rescue_Person_Seated.png、03_Rescue_Person_Six_Aboard.png：站姿、原座椅适配和六人乘船预览。

## 后续复用

使用 Blender 的追加功能，从独立模型的 Collection 中追加“PERSON · Rigged rescue passenger”（带站坐关键帧）或“PERSON · Seated reusable rig”（独立固定坐姿骨架）。进入骨架的姿态模式可调整四肢、头部和躯干；角色正面为 +Y。

场景单位为公制，单位缩放为 0.01，即一单位代表一厘米。坐姿骨盆接触面在角色局部 Z 约 0.975 处；放置时将角色原点 Z 设为“坐垫表面高度 - 0.975”。原救援船适配位置为 X=±1.5，Y=各座位中心Y-0.10，Z=0.735。

这是一套可摆姿势的模型资产，尚未加入行走、爬梯或自主救援行为。原小船和基地文件未被覆盖。
