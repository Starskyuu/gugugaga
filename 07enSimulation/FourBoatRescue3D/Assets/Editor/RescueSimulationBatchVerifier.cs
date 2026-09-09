using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using System.Linq;

/// <summary>
/// Headless play-mode smoke test used by CI and upgrade verification.
/// Launch with -executeMethod RescueSimulationBatchVerifier.Run.
/// </summary>
public static class RescueSimulationBatchVerifier
{
    private static RescueSimulationManager manager;
    private static BoatController boat;
    private static Vector3 initialPosition;
    private static double startedAt;
    private static int exitCode;
    private static bool completed;
    private static bool diagnosticsLogged;
    private static bool departed;
    private static bool survivorBoarded;
    private static int peakOnboard;
    private static int phase;
    private static Transform wavingArm;
    private static Quaternion wavingArmStart;
    private static bool waveObserved;
    private static bool pileObserved;
    private static bool stationAvoidanceViolation;
    private static BaseStationLift stationLift;

    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/RescueSimulation.unity", OpenSceneMode.Single);
        EditorApplication.playModeStateChanged += OnPlayModeChanged;
        EditorApplication.EnterPlaymode();
    }

    private static void OnPlayModeChanged(PlayModeStateChange state)
    {
        if (state == PlayModeStateChange.EnteredPlayMode)
        {
            manager = Object.FindAnyObjectByType<RescueSimulationManager>();
            if (manager == null || manager.boats == null || manager.boats.Length == 0 || manager.boats[0] == null)
            {
                Finish(2, "manager or fleet missing");
                return;
            }

            manager.useExternalPlanner = false;
            boat = manager.boats[0];
            string[] requiredModels =
            {
                "BaseStation_Blockout", "RaspberryPi_Blockout", "OverheadCamera_Blockout",
                "RescueBoat_Blockout", "Person_Blockout"
            };
            if (requiredModels.Any(name => Resources.Load<GameObject>("Models/Blockout/" + name) == null) ||
                !boat.GetComponentsInChildren<Transform>(true).Any(item => item.name == "BlenderBlockout_RescueBoat_Blockout"))
            {
                Finish(5, "Blender blockout resources were not loaded into the simulation");
                return;
            }
            GameObject station = GameObject.Find("BaseStation_22cm_x_15cm");
            Renderer platformRenderer = station != null
                ? station.GetComponentsInChildren<Renderer>(true)
                    .FirstOrDefault(item => item.name.Contains("BaseStation_Platform"))
                : null;
            if (station == null || platformRenderer == null ||
                platformRenderer.bounds.size.y >= Mathf.Min(platformRenderer.bounds.size.x, platformRenderer.bounds.size.z) * 0.35f)
            {
                Finish(6, "Base station FBX is not upright on Unity's Y axis");
                return;
            }
            stationLift = station.GetComponent<BaseStationLift>();
            Transform suspendedCamera = Object.FindObjectsByType<Transform>(FindObjectsSortMode.None)
                .FirstOrDefault(item => item.name == "BlenderBlockout_OverheadCamera_Blockout");
            if (stationLift == null || suspendedCamera == null || suspendedCamera.IsChildOf(station.transform) ||
                !suspendedCamera.GetComponentsInChildren<Transform>(true).Any(item => item.name.Contains("SuspensionRope")))
            {
                Finish(8, "station lift or independently suspended rope camera is missing");
                return;
            }
            if (!TryGetRenderBounds(boat.gameObject, out Bounds boatBounds) ||
                boatBounds.size.z <= boatBounds.size.y * 1.35f)
            {
                Finish(7, "Rescue boat FBX axes are not aligned with the simulation; size=" +
                    boatBounds.size.ToString("F4"));
                return;
            }
            manager.boats = new[] { boat };
            manager.multiPassengerCapacity = 4;
            manager.SetRescueMode(RescueSimulationManager.RescueMode.RealisticShuttle);
            initialPosition = boat.transform.position;
            AddSixSurvivors();
            PersonMarker firstPerson = Object.FindObjectsByType<PersonMarker>(FindObjectsSortMode.None).FirstOrDefault();
            wavingArm = firstPerson != null ? firstPerson.GetComponentsInChildren<Transform>(true)
                .FirstOrDefault(item => item.name == "Person_Arm_L") : null;
            if (wavingArm != null) wavingArmStart = wavingArm.localRotation;
            manager.StartSimulation();
            startedAt = EditorApplication.timeSinceStartup;
            EditorApplication.update += ObserveMovement;
            Debug.Log("[RescueVerifier] Play mode started at " + initialPosition.ToString("F4"));
        }
        else if (state == PlayModeStateChange.EnteredEditMode && completed)
        {
            EditorApplication.Exit(exitCode);
        }
    }

    private static void ObserveMovement()
    {
        if (boat == null)
        {
            Finish(3, "boat destroyed during test");
            return;
        }

        float distance = Vector2.Distance(
            new Vector2(initialPosition.x, initialPosition.z),
            new Vector2(boat.transform.position.x, boat.transform.position.z));
        double elapsed = EditorApplication.timeSinceStartup - startedAt;
        peakOnboard = Mathf.Max(peakOnboard, manager.OnboardCount);
        float absX = Mathf.Abs(boat.transform.position.x);
        float absZ = Mathf.Abs(boat.transform.position.z);
        float berthLaneDelta = Mathf.Min(
            Mathf.Abs(boat.transform.position.z - 0.040f),
            Mathf.Abs(boat.transform.position.z + 0.040f));
        bool insideStationSafety = absX < 0.155f && absZ < 0.125f;
        bool insideOpenBayLane = absX >= 0.100f && berthLaneDelta <= 0.020f;
        stationAvoidanceViolation |= insideStationSafety && !insideOpenBayLane;
        if (stationAvoidanceViolation)
        {
            Finish(13, "boat entered the station safety footprint outside a launch-bay lane at " +
                boat.transform.position.ToString("F4"));
            return;
        }
        if (phase == 1 && manager.OnboardCount >= 5)
        {
            PersonMarker[] onboardPeople = boat.GetComponentsInChildren<PersonMarker>(true);
            if (onboardPeople.Length >= 5)
            {
                float spread = onboardPeople.Max(item => item.transform.localPosition.y) -
                               onboardPeople.Min(item => item.transform.localPosition.y);
                pileObserved |= spread >= 0.012f;
            }
        }
        if (manager.OnboardCount > 4 && phase == 0)
        {
            Finish(9, "realistic shuttle exceeded its four-person capacity");
            return;
        }
        if (!waveObserved && wavingArm != null && Quaternion.Angle(wavingArmStart, wavingArm.localRotation) > 8f)
            waveObserved = true;
        if (!diagnosticsLogged && elapsed > 1.0)
        {
            diagnosticsLogged = true;
            Debug.Log("[RescueVerifier] DIAGNOSTICS: frame=" + Time.frameCount
                + ", timeScale=" + Time.timeScale
                + ", controllerEnabled=" + boat.enabled
                + ", active=" + boat.gameObject.activeInHierarchy
                + ", fixedTicks=" + boat.FixedTickCount
                + ", hasRoute=" + boat.HasRoute
                + ", moving=" + boat.IsMoving
                + ", kinematicMode=" + boat.useKinematicAutopilot
                + ", rigidbodyKinematic=" + (boat.Physics != null && boat.Physics.IsKinematic)
                + ", position=" + boat.transform.position.ToString("F4"));
        }
        if (!departed && distance >= 0.025f)
        {
            departed = true;
            Debug.Log("[RescueVerifier] MILESTONE: departed " + distance.ToString("F4") + " m in " + elapsed.ToString("F2") + " s.");
        }
        if (!survivorBoarded && manager.OnboardCount > 0)
        {
            survivorBoarded = true;
            Debug.Log("[RescueVerifier] MILESTONE: survivor boarded.");
        }
        if (elapsed > 2.2 && (stationLift == null || !stationLift.IsRaised))
        {
            Finish(10, "base station did not rise above the water after simulation start");
            return;
        }
        if (phase == 0 && manager.RescuedCount >= 6)
        {
            if (peakOnboard != 4 || !waveObserved)
            {
                Finish(11, "realistic mode or waving animation incomplete; peakOnboard=" + peakOnboard + ", wave=" + waveObserved);
                return;
            }
            Debug.Log("[RescueVerifier] MILESTONE: realistic shuttle delivered 6 with peak capacity 4.");
            BeginOneTripAllTest();
            return;
        }
        if (phase == 1 && manager.RescuedCount >= 6)
        {
            if (peakOnboard < 5 || !pileObserved)
            {
                Finish(12, "one-trip pile was not visible; peakOnboard=" + peakOnboard + ", pile=" + pileObserved);
                return;
            }
            Debug.Log("[RescueVerifier] PASS: station avoidance, lift, hanging camera, waving, 4-person shuttle and one-trip stacked rescue all passed.");
            Finish(0, null);
        }
        else if (elapsed > 28.0)
        {
            Finish(4, "multi-rescue mission incomplete after 20 seconds; departed=" + departed
                + ", boarded=" + survivorBoarded + ", delivered=" + manager.RescuedCount
                + ", peakOnboard=" + peakOnboard + ", distance=" + distance.ToString("F4") + " m");
        }
    }

    private static void BeginOneTripAllTest()
    {
        manager.ClearPeople();
        manager.SetRescueMode(RescueSimulationManager.RescueMode.OneTripAll);
        AddSixSurvivors();
        peakOnboard = 0;
        phase = 1;
        startedAt = EditorApplication.timeSinceStartup;
        manager.StartSimulation();
    }

    private static void AddSixSurvivors()
    {
        manager.AddPerson(new Vector3(-0.245f, 0f, -0.180f));
        manager.AddPerson(new Vector3(-0.220f, 0f, -0.225f));
        manager.AddPerson(new Vector3(-0.175f, 0f, -0.255f));
        manager.AddPerson(new Vector3(-0.115f, 0f, -0.270f));
        manager.AddPerson(new Vector3(-0.055f, 0f, -0.265f));
        manager.AddPerson(new Vector3(0.010f, 0f, -0.250f));
    }

    private static void Finish(int code, string failure)
    {
        EditorApplication.update -= ObserveMovement;
        exitCode = code;
        completed = true;
        if (!string.IsNullOrEmpty(failure))
            Debug.LogError("[RescueVerifier] FAIL: " + failure);
        if (EditorApplication.isPlaying)
            EditorApplication.ExitPlaymode();
        else
            EditorApplication.Exit(code);
    }

    private static bool TryGetRenderBounds(GameObject root, out Bounds bounds)
    {
        Renderer[] renderers = root.GetComponentsInChildren<Renderer>(true)
            .Where(renderer => renderer.enabled).ToArray();
        if (renderers.Length == 0)
        {
            bounds = default;
            return false;
        }
        bounds = renderers[0].bounds;
        for (int index = 1; index < renderers.Length; index++)
            bounds.Encapsulate(renderers[index].bounds);
        return true;
    }
}
