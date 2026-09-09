using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class FleetCollisionVerifier
{
    private static RescueSimulationManager manager;
    private static double started;
    private static int phase;
    private static int code;
    private static float minimumGap = float.MaxValue;
    public static void Run()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/RescueSimulation.unity");
        EditorApplication.playModeStateChanged += state =>
        {
            if (state == PlayModeStateChange.EnteredPlayMode)
            {
                manager = Object.FindAnyObjectByType<RescueSimulationManager>();
                Begin();
                EditorApplication.update += Observe;
            }
            if (state == PlayModeStateChange.EnteredEditMode) EditorApplication.Exit(code);
        };
        EditorApplication.EnterPlaymode();
    }
    private static void Begin()
    {
        manager.ClearPeople();
        if (phase == 2)
        {
            manager.EmergencyStopAll();
            for (int i = 0; i < manager.boats.Length; i++)
            {
                float x = i % 2 == 0 ? -0.22f : 0.22f;
                float z = i < 2 ? -0.22f : 0.22f;
                manager.boats[i].DockAt(new Vector3(x, 0f, z), Quaternion.Euler(0f, x < 0f ? 90f : -90f, 0f));
                manager.boats[i].SetLocalRoute(new[] { new Vector3(-x, 0f, z) }, "对向会遇测试");
            }
            started = EditorApplication.timeSinceStartup;
            return;
        }
        manager.SetRescueMode(phase == 0 ? RescueSimulationManager.RescueMode.RealisticShuttle :
            RescueSimulationManager.RescueMode.OneTripAll);
        for (int i = 0; i < 12; i++)
        {
            float angle = i * Mathf.PI / 6f;
            manager.AddPerson(new Vector3(Mathf.Cos(angle) * 0.26f, 0f, Mathf.Sin(angle) * 0.26f));
        }
        manager.StartSimulation();
        started = EditorApplication.timeSinceStartup;
    }
    private static void Observe()
    {
        var fleet = manager.boats;
        for (int i = 0; i < fleet.Length; i++)
        for (int j = i + 1; j < fleet.Length; j++)
        {
            float gap = BoatController.HullGap(fleet[i], fleet[i].transform.position, fleet[i].transform.rotation,
                fleet[j], fleet[j].transform.position, fleet[j].transform.rotation);
            minimumGap = Mathf.Min(minimumGap, gap);
            if (gap < -0.0005f) { Finish(21, "hull overlap " + gap); return; }
        }
        bool encountersComplete = phase == 2;
        foreach (var boat in fleet) encountersComplete &= boat.RouteComplete;
        if (encountersComplete)
        {
            Finish(0, "PASS two rescue modes and head-on encounters; minimum hull gap=" + minimumGap);
        }
        else if (manager.RescuedCount >= 12)
        {
            Debug.Log("[FleetVerifier] mode " + phase + " delivered 12; minimum hull gap=" + minimumGap);
            phase++;
            Begin();
        }
        else if (EditorApplication.timeSinceStartup - started > 35)
        {
            foreach (var boat in fleet) Debug.Log("[FleetVerifier] " + boat.boatId + " " + boat.transform.position.ToString("F4") + " " + boat.MissionStatus + " wait=" + boat.WaitingForTraffic);
            Finish(22, "timeout delivered=" + manager.RescuedCount + " onboard=" + manager.OnboardCount);
        }
    }
    private static void Finish(int result, string message)
    {
        code = result;
        Debug.Log("[FleetVerifier] " + message);
        EditorApplication.update -= Observe;
        EditorApplication.ExitPlaymode();
    }
}
