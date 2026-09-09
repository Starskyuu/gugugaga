# Unity三维四船协同搜救仿真：从零开始操作指南

## 1. 本指南要实现的最终效果

本指南用于从零搭建一个可交互的三维搜救仿真，并接入现有树莓派路线规划程序。完成后应具备以下功能：

- 显示一个 60 cm × 60 cm 的三维水面场地；
- 显示一个 22 cm × 15 cm 的中央基站；
- 导入已经完成的搜救船模型，并生成 4 艘 7 cm × 5 cm 的船；
- 基站左右两侧各布置 2 艘船，船头朝外；
- 支持手动点击水面添加人员；
- 支持随机生成 1～1000 名人员；
- Unity把船和人员坐标发送给现有Python规划程序；
- Python完成多船任务分配、访问顺序和避障路线计算；
- Unity接收4艘船的路线并播放搜救过程；
- 显示规划路线、待救人数、已救人数、算法和运行状态；
- 支持开始、暂停、重新规划、重置和全船急停。

推荐的第一版是“运动学仿真”：船只平滑转向并沿航点移动，但暂时不计算复杂浮力和水动力。第一版稳定后，再增加惯性、水流和风浪。

---

## 2. 系统组成

整个系统分成两部分：

```text
Unity三维仿真程序（Windows电脑）
  ├─三维场景
  ├─船、人和基站模型
  ├─鼠标交互与状态界面
  ├─采集模拟坐标
  └─执行规划航点
             │
             │ UDP/JSON
             ▼
Python搜救路线程序（开发时可在Windows运行，最终可放到树莓派）
  ├─接收船和人员坐标：UDP 9200
  ├─分配每艘船负责的人员
  ├─计算人员访问顺序
  ├─计算避开中央基站的路线
  └─发送逐船路线：UDP 9300
```

现有Python程序位置：

```text
F:\gugugaga\09 software\树莓派搜救程序
```

三维仿真不重新实现路径算法，只负责模拟视觉输入和执行路线。以后换成真实视觉传感器和实体船时，Python规划程序仍可继续使用。

---

## 3. 准备软件

### 3.1 安装Unity

1. 安装 Unity Hub。
2. 在Unity Hub中安装一个Unity 6长期支持版本。
3. 安装编辑器时勾选：
   - Microsoft Visual Studio Community；
   - Windows Build Support（如果需要生成独立EXE）；
   - 中文语言包可选。
4. 第一次打开Unity后确认能够新建工程。

### 3.2 安装Python

开发电脑需要Python 3.10或更高版本。打开PowerShell检查：

```powershell
python --version
```

现有规划程序只使用Python标准库，不需要额外安装算法依赖。

### 3.3 准备船模型

优先使用以下格式：

1. FBX：最推荐；
2. OBJ：可以使用，但材质通常需要单独设置；
3. Blender文件：建议先在Blender中导出为FBX；
4. GLB/GLTF：需要确认Unity项目是否安装了对应导入插件。

导出模型时应尽量做到：

- 应用缩放和旋转；
- 模型原点位于船体中心附近；
- 船头朝模型的正前方；
- 纹理与模型放在同一个资源文件夹；
- 删除看不见的高面数零件，避免4船同时运行时浪费性能。

---

## 4. 新建Unity工程

1. 打开Unity Hub。
2. 点击“新建项目”。
3. 模板选择 `Universal 3D`；如果电脑性能一般，也可以选择普通 `3D`。
4. 工程名称填写：

```text
FourBoatRescue3D
```

5. 工程位置建议选择：

```text
F:\gugugaga\07 仿真\FourBoatRescue3D
```

6. 创建工程，等待Unity完成首次导入。

不要把Unity工程直接建立在模型文件夹内部，也不要手动删除Unity生成的 `Library`、`Packages` 和 `ProjectSettings`。

---

## 5. 建立项目目录

在Unity的 `Assets` 窗口中建立以下目录：

```text
Assets/
├─Art/
│  ├─Boat/
│  ├─Person/
│  ├─BaseStation/
│  └─Materials/
├─Prefabs/
├─Scenes/
├─Scripts/
│  ├─Core/
│  ├─Networking/
│  ├─Simulation/
│  └─UI/
└─StreamingAssets/
```

将默认场景保存为：

```text
Assets/Scenes/RescueSimulation.unity
```

---

## 6. 统一尺寸和坐标系

本项目约定：

```text
1 Unity单位 = 1米
```

尺寸换算如下：

| 对象 | 实际尺寸 | Unity尺寸 |
|---|---:|---:|
| 场地 | 60 × 60 cm | 0.60 × 0.60 |
| 基站 | 22 × 15 cm | 0.22 × 0.15 |
| 船 | 7 × 5 cm | 0.07 × 0.05 |

规划程序使用二维 `X-Y` 坐标，Unity水面使用 `X-Z` 坐标：

```text
规划X → Unity X
规划Y → Unity Z
Unity Y → 高度
```

建议把场地中心放在Unity世界原点，因此换算公式为：

```text
UnityX = 坐标X厘米 ÷ 100 - 0.30
UnityZ = 坐标Y厘米 ÷ 100 - 0.30

坐标X厘米 = (UnityX + 0.30) × 100
坐标Y厘米 = (UnityZ + 0.30) × 100
```

在 `Assets/Scripts/Core` 中创建 `CoordinateConverter.cs`：

```csharp
using UnityEngine;

public static class CoordinateConverter
{
    public const float FieldSizeMeters = 0.60f;
    private const float HalfField = FieldSizeMeters / 2f;

    public static Vector3 CmToWorld(float xCm, float yCm, float height = 0f)
    {
        return new Vector3(xCm / 100f - HalfField, height,
                           yCm / 100f - HalfField);
    }

    public static Vector2 WorldToCm(Vector3 world)
    {
        return new Vector2((world.x + HalfField) * 100f,
                           (world.z + HalfField) * 100f);
    }
}
```

---

## 7. 搭建60 cm场地

### 7.1 创建场地根节点

1. 在Hierarchy中创建空对象，命名为 `Environment`。
2. 将场地、基站、灯光和边界都放在它下面。

### 7.2 创建水面

1. 创建 `3D Object > Plane`，命名为 `Water`。
2. Unity默认Plane为10×10单位，因此将Scale设为：

```text
X = 0.06
Y = 1
Z = 0.06
```

最终水面尺寸正好为0.60×0.60米。

3. Position设置为 `(0, 0, 0)`。
4. 创建蓝色半透明材质 `WaterMaterial` 并赋给水面。
5. 保留水面的Collider，用于鼠标点击放置人员。

第一版不需要真实水体插件。可以使用材质滚动、法线贴图或轻微顶点动画表现水波，但不要让视觉效果影响船的实际坐标。

### 7.3 创建边界

在水面四周创建4个细长Cube，作为场地边框：

- 左右边框长度0.60米；
- 上下边框长度0.60米；
- 高度可设0.02米；
- 厚度可设0.01米。

为边界保留Box Collider，防止船离开场地。

---

## 8. 创建中央基站

1. 创建空对象，命名为 `BaseStation`。
2. 如果已有基站模型，将模型放入该对象下面；没有模型时先使用Cube。
3. 基站平面尺寸设置为：

```text
X = 0.22 m
Z = 0.15 m
```

4. Position设置为场地中心 `(0, 0.015, 0)`。
5. 添加Box Collider，碰撞尺寸应覆盖基站主体。
6. 再创建一个半透明橙色Cube作为 `BaseSafetyZone`。

Python默认安全边距为2.5 cm，因此安全区尺寸为：

```text
X = 0.22 + 2 × 0.025 = 0.27 m
Z = 0.15 + 2 × 0.025 = 0.20 m
```

安全区只用于显示和检测，不要挡住摄像机。可以关闭其Mesh Renderer，只保留Trigger Collider。

---

## 9. 导入并配置搜救船模型

### 9.1 导入模型

1. 把船的FBX、OBJ和纹理复制到：

```text
Assets/Art/Boat/
```

2. 选中模型，检查Inspector中的Scale Factor。
3. 把模型拖到场景。
4. 使用测量工具或临时Cube对照，把船缩放为：

```text
长度 = 0.07 m
宽度 = 0.05 m
```

5. 确认船头朝本地坐标的 `+Z` 方向。

如果方向不正确，不建议直接修改模型文件本身。可以创建空父对象 `BoatRoot`，将模型作为子对象旋转，保持 `BoatRoot` 的正方向为 `+Z`。

### 9.2 添加碰撞和刚体

在 `BoatRoot` 上添加：

- Rigidbody；
- 1～3个Box Collider组成的复合碰撞体；
- 后面创建的 `BoatController`；
- 后面创建的 `LineRenderer`。

第一版Rigidbody设置：

```text
Use Gravity = 关闭
Is Kinematic = 开启
Interpolate = Interpolate
Collision Detection = Continuous Speculative
```

不要直接给高面数船模添加非凸Mesh Collider。简单复合碰撞体运行更稳定。

### 9.3 制作Prefab

1. 将配置好的 `BoatRoot` 拖到 `Assets/Prefabs`。
2. 命名为 `RescueBoat.prefab`。
3. 删除场景中的临时对象。
4. 从Prefab拖出4艘船，命名：

```text
boat_1
boat_2
boat_3
boat_4
```

推荐初始位置（规划坐标，单位cm）：

| 船 | X | Y | 船头方向 |
|---|---:|---:|---|
| boat_1 | 24 | 27 | 向左 |
| boat_2 | 24 | 33 | 向左 |
| boat_3 | 36 | 27 | 向右 |
| boat_4 | 36 | 33 | 向右 |

使用 `CoordinateConverter.CmToWorld()` 换算后放入场景。左侧船旋转到船头朝 `-X`，右侧船旋转到船头朝 `+X`。

---

## 10. 创建人员Prefab

第一版可以先使用Capsule或简单人物模型：

1. 创建Capsule，命名为 `PersonRoot`。
2. 缩放到适合场地的可见尺寸，例如高度0.025米。
3. 使用红色材质表示待救人员。
4. 添加Collider并勾选 `Is Trigger`。
5. 添加下面的 `PersonMarker.cs`。
6. 拖到 `Assets/Prefabs`，保存为 `Person.prefab`。

在 `Assets/Scripts/Simulation` 中创建 `PersonMarker.cs`：

```csharp
using UnityEngine;

public class PersonMarker : MonoBehaviour
{
    public string personId;
    public bool IsRescued { get; private set; }
    [SerializeField] private Renderer targetRenderer;
    [SerializeField] private Color waitingColor = Color.red;
    [SerializeField] private Color rescuedColor = Color.green;

    private void Awake()
    {
        if (targetRenderer == null)
            targetRenderer = GetComponentInChildren<Renderer>();
        SetRescued(false);
    }

    public void SetRescued(bool rescued)
    {
        IsRescued = rescued;
        if (targetRenderer != null)
            targetRenderer.material.color = rescued ? rescuedColor : waitingColor;
    }
}
```

---

## 11. 定义UDP数据结构

在 `Assets/Scripts/Networking` 创建 `PlannerMessages.cs`：

```csharp
using System;

[Serializable]
public class CoordinateItem
{
    public string id;
    public float x;
    public float y;
}

[Serializable]
public class VisionFrame
{
    public string type = "VISION_FRAME";
    public int frame_id;
    public double timestamp;
    public CoordinateItem[] boats;
    public CoordinateItem[] people;
}

[Serializable]
public class RouteWaypoint
{
    public float x;
    public float y;
}

[Serializable]
public class RouteTarget
{
    public string id;
    public float x;
    public float y;
}

[Serializable]
public class RoutePlan
{
    public string type;
    public int version;
    public string algorithm;
    public string coordinate_unit;
    public string boat_id;
    public string[] victim_ids;
    public RouteTarget[] targets;
    public RouteWaypoint[] waypoints;
    public float distance;
    public float estimated_time_s;
}
```

字段名称必须与Python协议保持一致，不要随意改成Unity风格的其他名字。

---

## 12. Unity与Python通信

在 `Assets/Scripts/Networking` 创建 `UdpPlannerClient.cs`：

```csharp
using System;
using System.Collections.Concurrent;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

public class UdpPlannerClient : MonoBehaviour
{
    [Header("Python/树莓派地址")]
    public string plannerIp = "127.0.0.1";
    public int visionPort = 9200;
    public int routePort = 9300;

    private UdpClient sender;
    private UdpClient receiver;
    private Thread receiveThread;
    private volatile bool running;
    private readonly ConcurrentQueue<string> messages = new();

    public event Action<RoutePlan> RouteReceived;

    private void Start()
    {
        sender = new UdpClient();
        receiver = new UdpClient(routePort);
        receiver.Client.ReceiveTimeout = 500;
        running = true;
        receiveThread = new Thread(ReceiveLoop) { IsBackground = true };
        receiveThread.Start();
    }

    public void SendFrame(VisionFrame frame)
    {
        string json = JsonUtility.ToJson(frame);
        byte[] data = Encoding.UTF8.GetBytes(json);
        sender.Send(data, data.Length, plannerIp, visionPort);
    }

    private void ReceiveLoop()
    {
        IPEndPoint remote = new IPEndPoint(IPAddress.Any, 0);
        while (running)
        {
            try
            {
                byte[] data = receiver.Receive(ref remote);
                messages.Enqueue(Encoding.UTF8.GetString(data));
            }
            catch (SocketException) { }
            catch (ObjectDisposedException) { break; }
        }
    }

    private void Update()
    {
        while (messages.TryDequeue(out string json))
        {
            RoutePlan route = JsonUtility.FromJson<RoutePlan>(json);
            if (route != null && route.type == "ROUTE_PLAN")
                RouteReceived?.Invoke(route);
        }
    }

    private void OnDestroy()
    {
        running = false;
        receiver?.Close();
        sender?.Close();
        if (receiveThread != null && receiveThread.IsAlive)
            receiveThread.Join(1000);
    }
}
```

注意：不要在接收线程中直接操作Unity物体。上面的代码先把消息放进线程安全队列，再在Unity主线程的 `Update()` 中处理。

---

## 13. 实现船只航点跟随

在 `Assets/Scripts/Simulation` 创建 `BoatController.cs`：

```csharp
using System.Collections.Generic;
using UnityEngine;

public class BoatController : MonoBehaviour
{
    public string boatId;
    public float moveSpeed = 0.08f;       // 8 cm/s
    public float turnSpeed = 180f;        // 度/秒
    public float waypointTolerance = 0.005f;
    public float rescueRadius = 0.025f;

    private readonly List<Vector3> route = new();
    private int waypointIndex;
    private int acceptedVersion = -1;
    private bool emergencyStopped;

    public bool IsMoving => !emergencyStopped && waypointIndex < route.Count;

    public void AcceptRoute(RoutePlan plan)
    {
        if (plan.boat_id != boatId || plan.version <= acceptedVersion)
            return;

        acceptedVersion = plan.version;
        route.Clear();
        waypointIndex = 0;

        if (plan.waypoints != null)
        {
            foreach (RouteWaypoint point in plan.waypoints)
                route.Add(CoordinateConverter.CmToWorld(point.x, point.y,
                                                        transform.position.y));
        }
        emergencyStopped = false;
    }

    public void EmergencyStop()
    {
        emergencyStopped = true;
    }

    public void Resume()
    {
        emergencyStopped = false;
    }

    private void Update()
    {
        if (emergencyStopped || waypointIndex >= route.Count)
            return;

        Vector3 target = route[waypointIndex];
        Vector3 direction = target - transform.position;
        direction.y = 0f;

        if (direction.magnitude <= waypointTolerance)
        {
            waypointIndex++;
            return;
        }

        Quaternion targetRotation = Quaternion.LookRotation(direction.normalized);
        transform.rotation = Quaternion.RotateTowards(
            transform.rotation, targetRotation, turnSpeed * Time.deltaTime);

        float angleError = Quaternion.Angle(transform.rotation, targetRotation);
        float throttle = Mathf.Clamp01(1f - angleError / 90f);
        transform.position = Vector3.MoveTowards(
            transform.position, target,
            moveSpeed * throttle * Time.deltaTime);
    }
}
```

第一版先使用上述方式验证算法。后续如果启用非运动学Rigidbody，应把移动代码改到 `FixedUpdate()`，并使用 `Rigidbody.MovePosition`、力和力矩。

---

## 14. 创建仿真管理器

在 `Assets/Scripts/Simulation` 创建 `RescueSimulationManager.cs`。它需要负责：

- 保存4艘船；
- 保存当前所有人员；
- 生成唯一人员编号；
- 组装 `VISION_FRAME`；
- 把帧发送给Python；
- 将收到的路线交给对应船；
- 检测人员是否获救；
- 更新待救与已救数量；
- 管理开始、暂停、急停和重置。

下面是可以使用的基础版本：

```csharp
using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

public class RescueSimulationManager : MonoBehaviour
{
    public UdpPlannerClient plannerClient;
    public BoatController[] boats;
    public PersonMarker personPrefab;
    public Transform personContainer;

    private readonly List<PersonMarker> people = new();
    private int nextPersonId = 1;
    private int frameId;
    private bool simulationRunning;

    public int WaitingCount => people.Count(p => !p.IsRescued);
    public int RescuedCount => people.Count(p => p.IsRescued);

    private void Start()
    {
        plannerClient.RouteReceived += OnRouteReceived;
    }

    private void OnDestroy()
    {
        if (plannerClient != null)
            plannerClient.RouteReceived -= OnRouteReceived;
    }

    public void AddPersonAtWorld(Vector3 worldPosition)
    {
        worldPosition.y = 0.012f;
        PersonMarker person = Instantiate(personPrefab, worldPosition,
                                          Quaternion.identity, personContainer);
        person.personId = $"person_{nextPersonId++}";
        people.Add(person);

        if (simulationRunning)
            RequestPlan();
    }

    public void StartSimulation()
    {
        simulationRunning = true;
        foreach (BoatController boat in boats)
            boat.Resume();
        RequestPlan();
    }

    public void RequestPlan()
    {
        VisionFrame frame = new VisionFrame
        {
            frame_id = ++frameId,
            timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0,
            boats = boats.Select(boat =>
            {
                Vector2 cm = CoordinateConverter.WorldToCm(boat.transform.position);
                return new CoordinateItem { id = boat.boatId, x = cm.x, y = cm.y };
            }).ToArray(),
            people = people.Where(person => !person.IsRescued).Select(person =>
            {
                Vector2 cm = CoordinateConverter.WorldToCm(person.transform.position);
                return new CoordinateItem { id = person.personId, x = cm.x, y = cm.y };
            }).ToArray()
        };
        plannerClient.SendFrame(frame);
    }

    private void OnRouteReceived(RoutePlan plan)
    {
        BoatController boat = boats.FirstOrDefault(item => item.boatId == plan.boat_id);
        if (boat != null)
            boat.AcceptRoute(plan);
    }

    private void Update()
    {
        if (!simulationRunning)
            return;

        bool changed = false;
        foreach (PersonMarker person in people.Where(item => !item.IsRescued))
        {
            foreach (BoatController boat in boats)
            {
                Vector3 difference = boat.transform.position - person.transform.position;
                difference.y = 0f;
                if (difference.magnitude <= boat.rescueRadius)
                {
                    person.SetRescued(true);
                    changed = true;
                    break;
                }
            }
        }

        if (changed)
            RequestPlan();
    }

    public void EmergencyStopAll()
    {
        foreach (BoatController boat in boats)
            boat.EmergencyStop();
        simulationRunning = false;
    }
}
```

不要每一帧都向Python发送坐标。第一版只在开始、人员变化、救援完成或用户点击“重新规划”时发送，这样不会因为连续重规划而反复重置船的航点。

---

## 15. 鼠标点击添加人员

在 `Assets/Scripts/Simulation` 创建 `PersonPlacementController.cs`：

```csharp
using UnityEngine;
using UnityEngine.EventSystems;

public class PersonPlacementController : MonoBehaviour
{
    public Camera sceneCamera;
    public RescueSimulationManager simulation;
    public LayerMask waterLayer;

    private void Update()
    {
        if (!Input.GetMouseButtonDown(0))
            return;
        if (EventSystem.current != null && EventSystem.current.IsPointerOverGameObject())
            return;

        Ray ray = sceneCamera.ScreenPointToRay(Input.mousePosition);
        if (Physics.Raycast(ray, out RaycastHit hit, 100f, waterLayer))
            simulation.AddPersonAtWorld(hit.point);
    }
}
```

配置方法：

1. 新建Layer，命名为 `Water`。
2. 把水面对象设置到该Layer。
3. 在场景中新建空对象 `InputController`。
4. 添加 `PersonPlacementController`。
5. 拖入主摄像机、仿真管理器并设置Water LayerMask。

添加人员前还应检查坐标是否位于基站安全区。建议在最终版本中用 `Physics.CheckSphere` 或二维范围判断拒绝非法位置。

---

## 16. 随机生成1～1000人

在仿真管理器中增加随机生成功能。基本逻辑：

```csharp
public void GenerateRandomPeople(int count)
{
    count = Mathf.Clamp(count, 1, 1000);
    int attempts = 0;

    while (count > 0 && attempts < 20000)
    {
        attempts++;
        float x = UnityEngine.Random.Range(-0.285f, 0.285f);
        float z = UnityEngine.Random.Range(-0.285f, 0.285f);

        // 中央安全区约为 X±0.135、Z±0.10米。
        if (Mathf.Abs(x) < 0.135f && Mathf.Abs(z) < 0.10f)
            continue;

        AddPersonAtWorld(new Vector3(x, 0.012f, z));
        count--;
    }
}
```

1000个人物如果都使用高面数模型会降低帧率。大量目标时建议：

- 使用低面数人物；
- 关闭人物阴影；
- 共享材质；
- 使用简单Collider；
- 距离较远时只显示图标或广告牌；
- 不要为每个人物创建独立Update脚本逻辑。

---

## 17. 绘制每艘船的路线

每艘船添加一个 `LineRenderer`：

- Width设置为0.002～0.004米；
- Use World Space开启；
- Material使用Unlit材质；
- 路线高度比水面高0.003米，避免闪烁。

推荐配色：

| 船 | 路线颜色 |
|---|---|
| boat_1 | 蓝色 |
| boat_2 | 橙色 |
| boat_3 | 绿色 |
| boat_4 | 紫色 |

在 `AcceptRoute()` 中将收到的航点同时传给LineRenderer。到达航点后，可以更新LineRenderer只显示剩余路线，也可以用另一条较暗的线显示已经走过的轨迹。

---

## 18. 创建用户界面

创建Canvas，并至少加入以下控件：

- 数量输入框：1～1000；
- “随机生成人员”按钮；
- “开始搜救”按钮；
- “重新规划”按钮；
- “暂停/继续”按钮；
- “重置任务”按钮；
- 红色“全船急停”按钮；
- 当前算法文字；
- 待救人数；
- 已救人数；
- 规划版本号；
- 4艘船当前状态。

按钮事件绑定示例：

```text
开始搜救 → RescueSimulationManager.StartSimulation
重新规划 → RescueSimulationManager.RequestPlan
全船急停 → RescueSimulationManager.EmergencyStopAll
```

为了方便PPT录屏，可以再添加：

- 仿真速度：0.5×、1×、2×、4×；
- 俯视、斜视、跟随船只三种摄像机；
- 显示/隐藏路线；
- 显示/隐藏基站安全区。

---

## 19. 第一次连接Python规划程序

### 19.1 启动路线接收检查

先不要打开Unity播放。在PowerShell中执行：

```powershell
cd "F:\gugugaga\09 software\树莓派搜救程序"
python -m unittest discover -s tests -v
```

确保6项树莓派程序测试全部通过。

### 19.2 启动Python服务

继续执行：

```powershell
python pi_rescue_service.py --config config.json
```

正常情况下会显示正在监听UDP 9200。

### 19.3 启动Unity

1. 打开 `RescueSimulation` 场景。
2. 确认 `UdpPlannerClient.plannerIp` 为 `127.0.0.1`。
3. 确认输入端口为9200，输出端口为9300。
4. 点击Unity播放按钮。
5. 添加几名人员。
6. 点击“开始搜救”。

Python窗口应显示规划版本、算法、目标数量和规划耗时。Unity应收到4个 `ROUTE_PLAN` 数据包。

### 19.4 常见端口错误

如果出现“每个套接字地址只允许使用一次”：

1. 检查是否启动了两个Python路线服务；
2. 检查是否打开了两个Unity播放窗口；
3. 结束旧程序后重新启动；
4. 必要时把 `config.json` 和Unity中的端口同时改成一组新端口。

---

## 20. 与树莓派连接

开发阶段Python和Unity都在同一台电脑运行，IP使用：

```text
127.0.0.1
```

树莓派部署后：

1. 电脑和树莓派连接同一个局域网；
2. 在树莓派执行 `hostname -I` 获取IP；
3. 把Unity的 `plannerIp` 改成树莓派IP；
4. 在树莓派 `config.json` 中，把 `route_output.host` 改成运行Unity电脑的IP；
5. Windows防火墙允许Unity接收UDP 9300；
6. 路由器或防火墙允许树莓派接收UDP 9200。

数据方向：

```text
Unity电脑IP:随机端口 → 树莓派IP:9200
树莓派IP:随机端口 → Unity电脑IP:9300
```

如果最终不再使用Unity产生坐标，而是接入真实视觉传感器，则由视觉模块向树莓派9200发送同样的 `VISION_FRAME` 数据。

---

## 21. 第一版验收步骤

按以下顺序测试，不要一次性测试所有功能。

### 测试1：场景尺寸

- 水面尺寸为0.60×0.60米；
- 基站尺寸为0.22×0.15米；
- 船尺寸为0.07×0.05米；
- 4艘船位置、编号和船头方向正确。

### 测试2：单船移动

- 临时给一艘船设置2～3个固定航点；
- 船能平滑转向；
- 船到达航点后切换到下一个航点；
- 船不会上下漂移或翻转。

### 测试3：人员生成

- 鼠标能够添加人员；
- 人员不会出现在基站安全区；
- 随机数量限制在1～1000；
- 重置后人员被正确清除。

### 测试4：UDP通信

- Unity能发送 `VISION_FRAME`；
- Python日志显示收到目标；
- Unity能收到4个 `ROUTE_PLAN`；
- 旧版本路线不会覆盖新版本路线。

### 测试5：四船协同

- 每个人只分配给一艘船；
- 4艘船能同时运动；
- 船不会穿过基站安全区；
- 到达人员附近后，人员变为绿色；
- 已救人数正确增加。

### 测试6：规模测试

分别测试：

```text
1人、4人、10人、12人、13人、100人、500人、1000人
```

检查算法是否自动切换：

- 1～12人：`exact_dp_astar`；
- 13～1000人：`balanced_greedy_visibility`；
- 0人：`idle`。

---

## 22. 常见问题排查

### 船运动方向旋转了90度

原因通常是模型船头没有朝本地 `+Z`。使用一个空父对象作为 `BoatRoot`，只旋转下面的可视模型。

### 船的位置整体偏移30 cm

原因是忘记了场地中心偏移。检查 `CoordinateConverter` 是否执行了 `±0.30` 米转换。

### 船穿过基站

检查：

- Python配置中的基站坐标和安全边距；
- Unity场地与规划坐标是否同方向；
- 船是否跳过了中间航点；
- 新路线是否被旧版本覆盖；
- 基站Collider和安全区显示是否与规划区域一致。

### Unity收不到路线

检查：

- Python服务是否正在运行；
- 9200和9300端口是否一致；
- IP地址是否正确；
- Windows防火墙是否放行；
- Unity Console是否出现端口占用异常；
- 是否有其他程序已经监听9300。

### 1000人时画面卡顿

检查：

- 人物模型面数；
- 是否为每个人启用了阴影；
- 是否使用了独立材质；
- 是否每个人都运行 `Update()`；
- 是否绘制了过多独立LineRenderer；
- 是否误用了复杂Mesh Collider。

### 船不停重新改变路线

不要每帧发送视觉数据。只有任务变化、救援完成或主动重新规划时才发送。真实视觉模式下，应限制重规划频率并对坐标进行滤波。

---

## 23. 第二阶段升级方向

第一版完成后，可以按下面顺序升级：

1. 加入船的加速、减速和最小转弯半径；
2. 使用Rigidbody力和力矩替代直接移动；
3. 加入水阻和轻微浮动；
4. 加入恒定或随机水流；
5. 加入视觉坐标噪声、丢帧和延迟；
6. 加入船间安全距离和动态避碰；
7. 加入电量、故障船和通信中断；
8. 记录每次实验的总航程、最大完成时间和规划耗时；
9. 对比不同算法的效率；
10. 将同一套协议接入真实树莓派和实体船。

复杂水动力不是第一版验收的必要条件。第一版最重要的是证明：

```text
坐标能够输入
→ 算法能够规划
→ 4艘船能够执行
→ 路线能够避开基站
→ 人员能够被正确救援
```

---

## 24. PPT展示建议

三维仿真演示建议控制在60～90秒：

1. 展示60×60 cm三维场地和4艘船；
2. 鼠标点击放置10名人员；
3. 点击“开始搜救”；
4. 显示Python自动选择精确算法；
5. 显示4种颜色的规划路线；
6. 展示4艘船同时出发并绕开基站；
7. 展示人员由红色变为绿色；
8. 展示已救人数最终达到10；
9. 重置后生成100或1000人；
10. 展示系统自动切换快速算法及规划耗时。

答辩时可以这样描述：

> 三维仿真作为实体系统的数字验证环境，模拟视觉模块输出船只和落水人员坐标，并使用与真实树莓派相同的UDP协议连接路线规划程序。系统根据目标数量自动选择精确算法或快速算法，再将任务顺序和避障航点下发给4艘船。这样可以在实体船下水前验证坐标转换、任务分配、路线安全性和通信流程。

---

## 25. 完成标准

满足以下条件即可认为第一版三维仿真完成：

- [ ] 已正确导入现有船模型；
- [ ] 场地、基站和船尺寸与实物比例一致；
- [ ] 4艘船初始位置和朝向正确；
- [ ] 可以点击和随机生成1～1000人；
- [ ] Unity能够向Python发送坐标；
- [ ] Unity能够接收4艘船的路线；
- [ ] 船能够依次跟踪全部航点；
- [ ] 路线不会穿过基站安全区；
- [ ] 人员到达救援范围后状态改变；
- [ ] 界面显示待救、已救、算法和船只状态；
- [ ] 急停能够立即停止4艘船；
- [ ] Windows本地联调成功；
- [ ] Unity与树莓派局域网联调成功；
- [ ] 已录制可用于PPT的演示视频。

