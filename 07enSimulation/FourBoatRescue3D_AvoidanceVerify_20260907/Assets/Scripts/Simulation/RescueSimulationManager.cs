using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.InputSystem;

/// <summary>
/// Owns the complete rescue loop. A deterministic local dispatcher is the
/// default so the Unity scene works without the optional Python/UDP service.
/// </summary>
public class RescueSimulationManager : MonoBehaviour
{
    public enum RescueMode
    {
        OneTripAll,
        RealisticShuttle
    }

    [Header("Scene references")]
    public UdpPlannerClient plannerClient;
    public BoatController[] boats;
    public Transform peopleRoot;
    public Material personSkinMaterial;
    public Material personSuitMaterial;
    public Material personVestMaterial;

    [Header("Planning")]
    [Tooltip("Use routes returned by the optional UDP planner instead of the built-in dispatcher.")]
    public bool useExternalPlanner;
    public float pickupRadius = 0.030f;
    public float dockRadius = 0.020f;
    [Tooltip("OneTripAll piles all assigned survivors aboard. RealisticShuttle returns at four passengers.")]
    public RescueMode rescueMode = RescueMode.OneTripAll;
    [Range(1, 4)] public int multiPassengerCapacity = 4;

    private readonly List<PersonMarker> people = new List<PersonMarker>();
    private readonly Dictionary<BoatController, PersonMarker> assignments = new Dictionary<BoatController, PersonMarker>();
    private readonly Dictionary<BoatController, List<PersonMarker>> passengers = new Dictionary<BoatController, List<PersonMarker>>();
    private readonly Dictionary<BoatController, Vector3> homePositions = new Dictionary<BoatController, Vector3>();
    private readonly Dictionary<BoatController, Quaternion> homeRotations = new Dictionary<BoatController, Quaternion>();
    private readonly HashSet<BoatController> patrolBoats = new HashSet<BoatController>();
    private readonly HashSet<BoatController> returningBoats = new HashSet<BoatController>();
    private BaseStationLift baseStationLift;

    private int nextPersonId = 1;
    private int frameId;
    private int totalRescued;
    private bool simulationRunning;
    private float externalPlanRequestedAt;
    private bool externalRouteReceived;
    private string selectedAlgorithm = "本地就绪";
    private string eventMessage = "点击水面布置落水者，然后开始救援";

    private GUIStyle panelStyle;
    private GUIStyle titleStyle;
    private GUIStyle labelStyle;
    private GUIStyle mutedStyle;
    private GUIStyle statStyle;
    private GUIStyle primaryButtonStyle;
    private GUIStyle dangerButtonStyle;
    private GUIStyle secondaryButtonStyle;
    private Texture2D panelTexture;
    private Texture2D primaryTexture;
    private Texture2D dangerTexture;
    private Texture2D secondaryTexture;

    public int WaitingCount => people.Count(person => person != null && person.State == PersonMarker.RescueState.Waiting);
    public int OnboardCount => people.Count(person => person != null && person.State == PersonMarker.RescueState.OnBoat);
    public int RescuedCount => totalRescued;
    public bool SimulationRunning => simulationRunning;
    public RescueMode CurrentRescueMode => rescueMode;

    private void Start()
    {
        if (plannerClient != null)
            plannerClient.RouteReceived += OnRouteReceived;

        InitializeFleet();
    }

    private void InitializeFleet()
    {
        QualitySettings.antiAliasing = 4;
        Application.targetFrameRate = 60;
        if (Camera.main != null)
        {
            Camera.main.allowHDR = true;
            Camera.main.allowMSAA = true;
        }
        if (homePositions.Count == 0)
        {
            BoatController[] fleet = ValidBoats().ToArray();
            for (int index = 0; index < fleet.Length; index++)
            {
                BoatController boat = fleet[index];
                Vector3 berth = GetInternalBerth(index, boat.transform.position);
                Quaternion berthRotation = index < 2 ? Quaternion.Euler(0f, -90f, 0f) : Quaternion.Euler(0f, 90f, 0f);
                boat.transform.SetPositionAndRotation(berth, berthRotation);
                homePositions[boat] = boat.transform.position;
                homeRotations[boat] = boat.transform.rotation;
                boat.DockAt(homePositions[boat], homeRotations[boat]);
            }
        }
        EnsureRuntimeLaunchBays();
        ProceduralRescueModels.EnhanceExistingScene();
        GameObject station = GameObject.Find("BaseStation_22cm_x_15cm");
        if (station != null)
        {
            baseStationLift = station.GetComponent<BaseStationLift>();
            if (baseStationLift == null)
                baseStationLift = station.AddComponent<BaseStationLift>();
            baseStationLift.PrepareLowered();
        }
    }

    private void OnDestroy()
    {
        if (plannerClient != null)
            plannerClient.RouteReceived -= OnRouteReceived;

        Destroy(panelTexture);
        Destroy(primaryTexture);
        Destroy(dangerTexture);
        Destroy(secondaryTexture);
    }

    private void Update()
    {
        if (Mouse.current != null && Mouse.current.leftButton.wasPressedThisFrame && Mouse.current.position.ReadValue().x > 385f)
            TryAddPersonAtMouse();

        if (!simulationRunning)
            return;

        if (useExternalPlanner)
        {
            if (!externalRouteReceived && Time.time - externalPlanRequestedAt > 1.5f)
            {
                useExternalPlanner = false;
                selectedAlgorithm = "UDP 超时，已切换本地调度";
                eventMessage = "外部规划无响应，本地自动驾驶已接管";
                if (WaitingCount > 0)
                    DispatchIdleBoats();
                else
                    LaunchPatrolCycle();
            }
            else
            {
                return;
            }
        }

        HandlePickups();
        HandleArrivals();
        HandlePatrolArrivals();
        DispatchIdleBoats();
    }

    public void AddPerson(Vector3 worldPosition)
    {
        if (WaitingCount >= 1000 || !CoordinateConverter.IsInsideField(worldPosition) || IsInsideBaseSafety(worldPosition))
            return;

        string personName = "person_" + nextPersonId;
        GameObject markerObject = ProceduralRescueModels.CreatePerson(
            personName,
            new Vector3(worldPosition.x, 0.012f, worldPosition.z),
            peopleRoot,
            personSkinMaterial,
            personSuitMaterial,
            personVestMaterial);
        PersonMarker marker = markerObject.GetComponent<PersonMarker>();
        marker.personId = markerObject.name;
        people.Add(marker);
        nextPersonId++;
        eventMessage = "已布置 " + marker.personId;

        if (simulationRunning && !useExternalPlanner)
            DispatchIdleBoats();
    }

    public void GenerateRandomPeople(int count)
    {
        count = Mathf.Clamp(count, 1, 1000 - WaitingCount);
        int attempts = 0;
        while (count > 0 && attempts++ < 30000)
        {
            Vector3 point = new Vector3(UnityEngine.Random.Range(-0.285f, 0.285f), 0f, UnityEngine.Random.Range(-0.285f, 0.285f));
            if (!IsInsideBaseSafety(point))
            {
                AddPerson(point);
                count--;
            }
        }
        eventMessage = "随机救援场景已生成";
    }

    public void StartSimulation()
    {
        InitializeFleet();
        useExternalPlanner = false;
        baseStationLift?.Raise();
        simulationRunning = true;
        foreach (BoatController boat in ValidBoats())
            boat.Resume();

        if (useExternalPlanner)
        {
            selectedAlgorithm = "UDP 外部规划";
            eventMessage = "已请求外部航线";
            externalRouteReceived = false;
            externalPlanRequestedAt = Time.time;
            RequestPlan();
        }
        else
        {
            selectedAlgorithm = rescueMode == RescueMode.OneTripAll
                ? "一次救完 · 堆叠载员"
                : "往返现实模拟 · 4 人上限";
            if (WaitingCount > 0)
            {
                eventMessage = "救援任务已启动";
                DispatchIdleBoats();
            }
            else
            {
                eventMessage = "无落水者，执行船队出航自检";
                LaunchPatrolCycle();
            }
        }
        Debug.Log("[RescueSimulation] Start pressed. waiting=" + WaitingCount + ", external=" + useExternalPlanner);
    }

    public void SetRescueMode(RescueMode mode)
    {
        if (simulationRunning)
            return;

        rescueMode = mode;
        useExternalPlanner = false;
        if (mode == RescueMode.OneTripAll)
        {
            selectedAlgorithm = "一次救完 · 不限载员";
            eventMessage = "船只连续救援，人员将在甲板上可视化堆叠";
        }
        else
        {
            selectedAlgorithm = "往返现实模拟 · 最多 4 人";
            eventMessage = "每艘船最多搭载 4 人，返港后再次出航";
        }
    }

    public void RequestPlan()
    {
        if (plannerClient == null)
            return;
        VisionFrame frame = new VisionFrame
        {
            frame_id = ++frameId,
            timestamp = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() / 1000.0,
            boats = ValidBoats().Select(boat =>
            {
                Vector2 cm = CoordinateConverter.WorldToCm(boat.transform.position);
                return new CoordinateItem { id = boat.boatId, x = cm.x, y = cm.y };
            }).ToArray(),
            people = people.Where(person => person != null && person.State == PersonMarker.RescueState.Waiting).Select(person =>
            {
                Vector2 cm = CoordinateConverter.WorldToCm(person.transform.position);
                return new CoordinateItem { id = person.personId, x = cm.x, y = cm.y };
            }).ToArray()
        };
        plannerClient.SendFrame(frame);
    }

    public void EmergencyStopAll()
    {
        simulationRunning = false;
        baseStationLift?.PrepareLowered();
        foreach (BoatController boat in ValidBoats())
            boat.EmergencyStop();
        eventMessage = "全部船只已紧急停止";
    }

    public void ClearPeople()
    {
        foreach (PersonMarker person in people)
            if (person != null)
                Destroy(person.gameObject);
        people.Clear();
        assignments.Clear();
        passengers.Clear();
        patrolBoats.Clear();
        returningBoats.Clear();
        nextPersonId = 1;
        totalRescued = 0;
        simulationRunning = false;
        baseStationLift?.PrepareLowered();

        foreach (BoatController boat in ValidBoats())
        {
            if (homePositions.TryGetValue(boat, out Vector3 home))
                boat.DockAt(home, homeRotations[boat]);
        }
        eventMessage = "场景已清空，船只返回泊位";
    }

    private void DispatchIdleBoats()
    {
        HashSet<PersonMarker> claimed = new HashSet<PersonMarker>(assignments.Values);
        foreach (BoatController boat in ValidBoats())
        {
            if (assignments.ContainsKey(boat) || patrolBoats.Contains(boat) || returningBoats.Contains(boat))
                continue;

            int onboard = PassengerCount(boat);
            if (onboard > 0 && rescueMode == RescueMode.RealisticShuttle && onboard >= multiPassengerCapacity)
            {
                SendBoatHome(boat);
                continue;
            }

            PersonMarker target = people
                .Where(person => person != null && person.State == PersonMarker.RescueState.Waiting && !claimed.Contains(person))
                .OrderBy(person => HorizontalDistance(boat.transform.position, person.transform.position))
                .FirstOrDefault();
            if (target == null)
            {
                if (onboard > 0)
                    SendBoatHome(boat);
                continue;
            }

            assignments[boat] = target;
            claimed.Add(target);
            Vector3 home = homePositions[boat];
            if (onboard == 0)
            {
                boat.SetLocalRoute(BuildOutboundRoute(home, target.transform.position), "驶向 " + target.personId);
            }
            else
            {
                boat.SetLocalRoute(BuildStationSafeRoute(boat.transform.position, target.transform.position),
                    "继续救援 " + target.personId + " · " +
                    (rescueMode == RescueMode.OneTripAll ? onboard + "/∞" : onboard + "/" + multiPassengerCapacity));
            }
            Debug.Log("[RescueSimulation] " + boat.boatId + " dispatched to " + target.personId + ".");
        }
    }

    private void LaunchPatrolCycle()
    {
        BoatController[] fleet = ValidBoats().ToArray();
        for (int index = 0; index < fleet.Length; index++)
        {
            BoatController boat = fleet[index];
            if (assignments.ContainsKey(boat) || patrolBoats.Contains(boat))
                continue;
            Vector3 home = homePositions[boat];
            float side = home.x < 0f ? -1f : 1f;
            Vector3 patrolPoint = new Vector3(side * 0.235f, 0f, home.z * 1.9f);
            List<Vector3> patrolRoute = new List<Vector3>(BuildOutboundRoute(home, patrolPoint));
            patrolRoute.AddRange(BuildReturnRoute(patrolPoint, home));
            boat.SetLocalRoute(patrolRoute, "出航自检");
            patrolBoats.Add(boat);
            Debug.Log("[RescueSimulation] " + boat.boatId + " patrol route installed.");
        }
    }

    private void HandlePatrolArrivals()
    {
        foreach (BoatController boat in patrolBoats.ToArray())
        {
            if (!boat.RouteComplete)
                continue;
            boat.DockAt(homePositions[boat], homeRotations[boat]);
            patrolBoats.Remove(boat);
            eventMessage = boat.boatId + " 已完成出航自检并返港";
        }
    }

    private void HandlePickups()
    {
        foreach (KeyValuePair<BoatController, PersonMarker> pair in assignments.ToArray())
        {
            BoatController boat = pair.Key;
            PersonMarker person = pair.Value;
            if (person == null || person.State != PersonMarker.RescueState.Waiting)
                continue;

            float radius = Mathf.Max(pickupRadius, boat.rescueRadius);
            if (HorizontalDistance(boat.transform.position, person.transform.position) <= radius)
            {
                List<PersonMarker> manifest = GetPassengerManifest(boat);
                person.Board(boat, manifest.Count, rescueMode == RescueMode.OneTripAll);
                manifest.Add(person);
                assignments.Remove(boat);

                bool hasCapacity = rescueMode == RescueMode.OneTripAll || manifest.Count < multiPassengerCapacity;
                bool canContinue = hasCapacity && WaitingCount > 0;
                if (canContinue)
                {
                    boat.SetMissionStatus("继续搜救 · " +
                        (rescueMode == RescueMode.OneTripAll ? manifest.Count + "/∞" : manifest.Count + "/" + multiPassengerCapacity));
                    eventMessage = boat.boatId + " 已救起 " + person.personId + "，继续寻找下一人";
                }
                else
                {
                    SendBoatHome(boat);
                    eventMessage = boat.boatId + " 载员 " + manifest.Count + " 人，正在返航";
                }
            }
            else if (boat.RouteComplete)
            {
                boat.SetLocalRoute(BuildStationSafeRoute(boat.transform.position, person.transform.position),
                    "重新接近 " + person.personId);
            }
        }
    }

    private void HandleArrivals()
    {
        foreach (KeyValuePair<BoatController, List<PersonMarker>> pair in passengers.ToArray())
        {
            BoatController boat = pair.Key;
            List<PersonMarker> manifest = pair.Value;
            if (manifest == null || manifest.Count == 0 || assignments.ContainsKey(boat))
                continue;
            Vector3 home = homePositions[boat];
            if (HorizontalDistance(boat.transform.position, home) > dockRadius && !boat.RouteComplete)
                continue;

            boat.DockAt(home, homeRotations[boat]);
            int delivered = 0;
            foreach (PersonMarker passenger in manifest.ToArray())
            {
                if (passenger == null)
                    continue;
                passenger.MarkDelivered();
                people.Remove(passenger);
                Destroy(passenger.gameObject);
                delivered++;
            }
            passengers.Remove(boat);
            assignments.Remove(boat);
            returningBoats.Remove(boat);
            totalRescued += delivered;
            eventMessage = boat.boatId + " 已将 " + delivered + " 人安全送达基站";
        }
    }

    private List<PersonMarker> GetPassengerManifest(BoatController boat)
    {
        if (!passengers.TryGetValue(boat, out List<PersonMarker> manifest))
        {
            manifest = new List<PersonMarker>();
            passengers[boat] = manifest;
        }
        return manifest;
    }

    private int PassengerCount(BoatController boat)
    {
        return passengers.TryGetValue(boat, out List<PersonMarker> manifest) && manifest != null
            ? manifest.Count
            : 0;
    }

    private void SendBoatHome(BoatController boat)
    {
        if (boat == null || !homePositions.TryGetValue(boat, out Vector3 home))
            return;
        if (!returningBoats.Add(boat))
            return;
        int count = PassengerCount(boat);
        boat.SetLocalRoute(BuildReturnRoute(boat.transform.position, home),
            count > 0 ? "载员返航 · " + count + " 人" : "返航");
    }

    private static IReadOnlyList<Vector3> BuildOutboundRoute(Vector3 berth, Vector3 destination)
    {
        Vector3 mouth = GetBerthMouth(berth);
        Vector3 clearance = GetClearancePoint(berth);
        List<Vector3> route = new List<Vector3> { mouth, clearance };
        AppendStationSafeSegment(route, clearance, destination);
        return route;
    }

    private static IReadOnlyList<Vector3> BuildReturnRoute(Vector3 current, Vector3 berth)
    {
        Vector3 clearance = GetClearancePoint(berth);
        List<Vector3> route = new List<Vector3>();
        AppendStationSafeSegment(route, current, clearance);
        route.Add(GetBerthMouth(berth));
        route.Add(berth);
        return route;
    }

    private static IReadOnlyList<Vector3> BuildStationSafeRoute(Vector3 current, Vector3 destination)
    {
        List<Vector3> route = new List<Vector3>();
        AppendStationSafeSegment(route, current, destination);
        return route;
    }

    private static Vector3 GetBerthMouth(Vector3 berth)
    {
        float side = berth.x < 0f ? -1f : 1f;
        return new Vector3(side * 0.170f, 0f, berth.z);
    }

    private static Vector3 GetClearancePoint(Vector3 berth)
    {
        float side = berth.x < 0f ? -1f : 1f;
        return new Vector3(side * 0.205f, 0f, berth.z);
    }

    private static void AppendStationSafeSegment(List<Vector3> route, Vector3 start, Vector3 destination)
    {
        if (!SegmentCrossesStationSafety(start, destination))
        {
            route.Add(destination);
            return;
        }

        const float bypassX = 0.205f;
        const float bypassZ = 0.160f;
        float startSide = Mathf.Abs(start.x) > 0.015f
            ? Mathf.Sign(start.x)
            : (Mathf.Abs(destination.x) > 0.015f ? Mathf.Sign(destination.x) : 1f);
        float destinationSide = Mathf.Abs(destination.x) > 0.015f ? Mathf.Sign(destination.x) : startSide;

        Vector3 upperStart = new Vector3(startSide * bypassX, 0f, bypassZ);
        Vector3 upperEnd = new Vector3(destinationSide * bypassX, 0f, bypassZ);
        Vector3 lowerStart = new Vector3(startSide * bypassX, 0f, -bypassZ);
        Vector3 lowerEnd = new Vector3(destinationSide * bypassX, 0f, -bypassZ);
        float upperLength = HorizontalDistance(start, upperStart) + HorizontalDistance(upperStart, upperEnd) +
                            HorizontalDistance(upperEnd, destination);
        float lowerLength = HorizontalDistance(start, lowerStart) + HorizontalDistance(lowerStart, lowerEnd) +
                            HorizontalDistance(lowerEnd, destination);
        Vector3 first = upperLength <= lowerLength ? upperStart : lowerStart;
        Vector3 second = upperLength <= lowerLength ? upperEnd : lowerEnd;
        route.Add(first);
        if (HorizontalDistance(first, second) > 0.005f)
            route.Add(second);
        route.Add(destination);
    }

    private static bool SegmentCrossesStationSafety(Vector3 start, Vector3 end)
    {
        // Expanded footprint includes fenders and half a boat width. Sampling is
        // deterministic and ample for the short, straight waypoint segments here.
        const float halfX = 0.155f;
        const float halfZ = 0.125f;
        for (int index = 1; index < 24; index++)
        {
            Vector3 sample = Vector3.Lerp(start, end, index / 24f);
            if (Mathf.Abs(sample.x) < halfX && Mathf.Abs(sample.z) < halfZ)
                return true;
        }
        return false;
    }

    private static Vector3 GetInternalBerth(int index, Vector3 fallback)
    {
        Vector3[] berths =
        {
            // Side-entry berths: roughly half of each hull remains inside the
            // base footprint and half is visible beyond the side fenders.
            new Vector3(-0.118f, 0f, -0.040f),
            new Vector3(-0.118f, 0f,  0.040f),
            new Vector3( 0.118f, 0f, -0.040f),
            new Vector3( 0.118f, 0f,  0.040f)
        };
        return index >= 0 && index < berths.Length ? berths[index] : fallback;
    }

    private static void EnsureRuntimeLaunchBays()
    {
        if (GameObject.Find("LaunchBay_Runtime_1") != null || GameObject.Find("LaunchBay_1") != null)
            return;

        Shader shader = Shader.Find("Universal Render Pipeline/Lit");
        if (shader == null)
            return;
        Material bayMaterial = new Material(shader) { color = new Color(0.025f, 0.055f, 0.075f) };
        bayMaterial.SetFloat("_Smoothness", 0.5f);

        for (int index = 0; index < 4; index++)
        {
            Vector3 berth = GetInternalBerth(index, Vector3.zero);
            GameObject bay = GameObject.CreatePrimitive(PrimitiveType.Cube);
            bay.name = "LaunchBay_Runtime_" + (index + 1);
            bay.transform.position = new Vector3(berth.x, -0.0015f, berth.z);
            bay.transform.localScale = new Vector3(0.075f, 0.0015f, 0.056f);
            bay.GetComponent<Renderer>().sharedMaterial = bayMaterial;
            Destroy(bay.GetComponent<Collider>());
        }
    }

    private IEnumerable<BoatController> ValidBoats()
    {
        return boats == null ? Enumerable.Empty<BoatController>() : boats.Where(boat => boat != null);
    }

    private void OnRouteReceived(RoutePlan plan)
    {
        if (!useExternalPlanner)
            return;
        selectedAlgorithm = plan.algorithm;
        externalRouteReceived = true;
        BoatController boat = ValidBoats().FirstOrDefault(item => item.boatId == plan.boat_id);
        if (boat != null)
            boat.AcceptRoute(plan);
    }

    private void TryAddPersonAtMouse()
    {
        Camera camera = Camera.main;
        if (camera == null || Mouse.current == null)
            return;
        Plane waterPlane = new Plane(Vector3.up, Vector3.zero);
        Ray ray = camera.ScreenPointToRay(Mouse.current.position.ReadValue());
        if (waterPlane.Raycast(ray, out float distance))
            AddPerson(ray.GetPoint(distance));
    }

    private static bool IsInsideBaseSafety(Vector3 position)
    {
        return Mathf.Abs(position.x) <= 0.14f && Mathf.Abs(position.z) <= 0.105f;
    }

    private static float HorizontalDistance(Vector3 a, Vector3 b)
    {
        float dx = a.x - b.x;
        float dz = a.z - b.z;
        return Mathf.Sqrt(dx * dx + dz * dz);
    }

    private void OnGUI()
    {
        EnsureGuiStyles();
        float scale = Mathf.Clamp(Screen.height / 900f, 0.82f, 1.15f);
        GUI.matrix = Matrix4x4.Scale(new Vector3(scale, scale, 1f));

        GUI.Box(new Rect(18, 18, 350, 632), GUIContent.none, panelStyle);
        GUI.Label(new Rect(38, 34, 310, 34), "海上协同救援仿真", titleStyle);
        GUI.Label(new Rect(39, 68, 300, 22), simulationRunning ? "● 任务运行中" : "● 系统待命", mutedStyle);

        DrawStat(new Rect(38, 102, 92, 64), WaitingCount.ToString(), "待救");
        DrawStat(new Rect(138, 102, 92, 64), OnboardCount.ToString(), "船上");
        DrawStat(new Rect(238, 102, 92, 64), RescuedCount.ToString(), "已送达");

        GUI.Label(new Rect(38, 181, 292, 22), "规划：" + selectedAlgorithm, labelStyle);
        GUI.Label(new Rect(38, 207, 292, 38), eventMessage, mutedStyle);

        GUI.Label(new Rect(38, 246, 292, 20), "救援模式", labelStyle);
        GUI.enabled = !simulationRunning;
        if (GUI.Button(new Rect(38, 270, 140, 34), rescueMode == RescueMode.OneTripAll ? "✓ 一次救完" : "一次救完", secondaryButtonStyle))
            SetRescueMode(RescueMode.OneTripAll);
        if (GUI.Button(new Rect(190, 270, 140, 34), rescueMode == RescueMode.RealisticShuttle ? "✓ 往返现实" : "往返现实", secondaryButtonStyle))
            SetRescueMode(RescueMode.RealisticShuttle);
        GUI.enabled = true;

        if (GUI.Button(new Rect(38, 316, 140, 38), "随机添加 10 人", secondaryButtonStyle)) GenerateRandomPeople(10);
        if (GUI.Button(new Rect(190, 316, 140, 38), "清空场景", secondaryButtonStyle)) ClearPeople();
        if (GUI.Button(new Rect(38, 364, 292, 44), simulationRunning ? "重新规划任务" : "开始救援模拟", primaryButtonStyle)) StartSimulation();
        if (GUI.Button(new Rect(38, 418, 292, 38), "紧急停止全部船只", dangerButtonStyle)) EmergencyStopAll();

        GUI.Label(new Rect(38, 468, 292, 22), "船队状态", labelStyle);
        int row = 0;
        foreach (BoatController boat in ValidBoats())
        {
            GUI.color = boat.routeColor;
            GUI.DrawTexture(new Rect(39, 500 + row * 18, 6, 6), Texture2D.whiteTexture);
            GUI.color = Color.white;
            GUI.Label(new Rect(52, 490 + row * 18, 278, 22), boat.boatId + "  ·  " + boat.MissionStatus, mutedStyle);
            row++;
        }

        GUI.Label(new Rect(38, 568, 292, 22), "海况", labelStyle);
        if (GUI.Button(new Rect(38, 596, 140, 34), "平静海面", secondaryButtonStyle)) SetWaves(0.0008f);
        if (GUI.Button(new Rect(190, 596, 140, 34), "较大风浪", secondaryButtonStyle)) SetWaves(0.0032f);

        GUI.matrix = Matrix4x4.identity;
    }

    private void DrawStat(Rect rect, string value, string caption)
    {
        GUI.Box(rect, GUIContent.none, statStyle);
        GUI.Label(new Rect(rect.x, rect.y + 5, rect.width, 28), value, titleStyle);
        GUI.Label(new Rect(rect.x, rect.y + 34, rect.width, 22), caption, mutedStyle);
    }

    private void EnsureGuiStyles()
    {
        if (panelStyle != null)
            return;

        panelTexture = MakeTexture(new Color(0.025f, 0.055f, 0.085f, 0.94f));
        primaryTexture = MakeTexture(new Color(0.02f, 0.55f, 0.72f, 0.98f));
        dangerTexture = MakeTexture(new Color(0.78f, 0.18f, 0.16f, 0.96f));
        secondaryTexture = MakeTexture(new Color(0.10f, 0.17f, 0.23f, 0.98f));

        panelStyle = new GUIStyle(GUI.skin.box) { normal = { background = panelTexture } };
        titleStyle = new GUIStyle(GUI.skin.label) { fontSize = 21, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleLeft, normal = { textColor = Color.white } };
        labelStyle = new GUIStyle(GUI.skin.label) { fontSize = 13, fontStyle = FontStyle.Bold, normal = { textColor = new Color(0.86f, 0.94f, 0.98f) } };
        mutedStyle = new GUIStyle(GUI.skin.label) { fontSize = 12, wordWrap = true, alignment = TextAnchor.MiddleLeft, normal = { textColor = new Color(0.62f, 0.75f, 0.82f) } };
        statStyle = new GUIStyle(GUI.skin.box) { normal = { background = secondaryTexture } };
        primaryButtonStyle = MakeButtonStyle(primaryTexture, 14);
        dangerButtonStyle = MakeButtonStyle(dangerTexture, 13);
        secondaryButtonStyle = MakeButtonStyle(secondaryTexture, 12);
    }

    private static GUIStyle MakeButtonStyle(Texture2D background, int fontSize)
    {
        GUIStyle style = new GUIStyle(GUI.skin.button)
        {
            fontSize = fontSize,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter
        };
        style.normal.background = background;
        style.normal.textColor = Color.white;
        style.hover.textColor = Color.white;
        style.active.textColor = Color.white;
        return style;
    }

    private static Texture2D MakeTexture(Color color)
    {
        Texture2D texture = new Texture2D(1, 1, TextureFormat.RGBA32, false);
        texture.SetPixel(0, 0, color);
        texture.Apply();
        return texture;
    }

    private static void SetWaves(float amplitude)
    {
        if (WaterSystem.Instance != null)
            WaterSystem.Instance.SetRoughness(amplitude);
    }
}
