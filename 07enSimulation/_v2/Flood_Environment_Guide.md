# Flood Environment — Step 3

## 启动

双击 `Builds/Flood/RescueFloodEnvironment.exe`。Unity 中打开 `Assets/Rescue/Scenes/FloodEnvironment.unity` 并点击 Play 也可以。版本为 Unity 6000.6.0f1，所有新增文件、对象和控件使用英文名称。

## 操作

- W/S 前进倒车，A/D 双桨差速转向；Space 停止推力（不是瞬间刹车）。
- C 切换全景/跟随；R 复位船和漂浮物；P 暂停/继续物理。
- 左侧 Reference depth 调节主河床水深5–65毫米；Background current 调节背景流速0–40毫米/秒，Flow heading 调节流向。
- Enable regional currents 控制局部急流和横向水流，Regional flow strength 调节局部增量。
- Calm 为静水，Street 为街区水流，High water 为高水位强流，Shallow 为低水位浅水。切换预设不会自动移动船，可随后按 R 复位。
- 取消 Keyboard 后，可分别调节左右电机；Floating debris 控制8个漂浮障碍物；Passenger 按钮用于已有质量载荷测试。
- 青色箭头表示预设流向/相对强度；橘色框为浅滩，红色框为急流区域。Local depth/flow 显示船当前位置的水深和流速。

## 场景和物理

1.2×1.2米模型尺度水域，船体仍为7×5厘米；包含原基地、6栋有碰撞体的建筑、边界、浅滩和8个有浮力及碰撞的木箱。当前只有1艘可驾驶物理船。

主河床高度为−30毫米；浅滩顶为−3毫米。默认水位0，主水深30毫米、浅滩水深3毫米；降低水位可以使浅滩露出。水深查询与实体浅滩地面一致，船可真实搁浅。涨水改变浸没体积与浮力，水流通过相对水速改变船/漂浮物阻力，建筑与木箱接触由 PhysX 求解。

船与漂浮物使用统一960Hz子步物理时钟。场景用明确的区域速度场叠加背景流；力在物理子步内施加，不用沿路径直接修改船的位置来假装航行。

## 验证与重建

- `Reports/Flood_Validation_Report.json`：13项实际物理检查，包括涨水、局部水流、露滩、漂浮物漂移和建筑阻挡。
- `Reports/PhysX_Validation_Report.json`：原25项船舶物理回归检查。
- `Reports/Flood_Runtime_Report.json`：独立程序的漂浮物运动、预设水位和对象数量检查；通过同一公开控制接口调用，不是鼠标点击测试。
- `Reports/Runtime_Flood_Environment.png`：独立程序相机实际渲染，不含屏幕控制面板。
- 关闭 Unity 后运行 `Tools/Build_Flood_And_Verify.ps1` 可重建第3步场景、验证和程序。它会重建生成的洪水场景，手工编辑前请另存。原 `Build_And_Verify.ps1` 仅用于第1–2步。

## 当前边界

这是平水面、指定速度场与刚体水动力近似，不是洪水传播/自由液面CFD求解器，不自动计算建筑绕流、波浪或湍流；水位滑块直接修改整个水面的高度。红框是配置的潜在急流范围，实际风险以 Local flow/Area 为准。参数尚未由实物水池试验标定，不能据此宣称现实救援安全性。

本步不包含水面呼救人员生成、四船分配、路径规划和自动接送；这些属于后续步骤。载荷按钮也不是完整救援人员系统。
