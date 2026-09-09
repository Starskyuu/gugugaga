using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

public static class RescueSceneGenerator
{
    private const int VisualVersion = 8;

    [MenuItem("Rescue Simulation/Generate Base Scene")]
    public static void GenerateBaseScene()
    {
        if (!EditorUtility.DisplayDialog("Generate rescue scene", "This will replace objects in the current scene with the rescue simulation base scene.", "Generate", "Cancel"))
            return;

        BuildScene();
    }

    /// <summary>
    /// Deterministic, dialog-free scene rebuild for CI and project upgrades.
    /// It is also exposed in the menu for quickly restoring the reference scene.
    /// </summary>
    [MenuItem("Rescue Simulation/Rebuild Reference Scene")]
    public static void RebuildReferenceScene()
    {
        EditorSceneManager.OpenScene("Assets/Scenes/RescueSimulation.unity", OpenSceneMode.Single);
        BuildScene();
        AssetDatabase.SaveAssets();
        Debug.Log("Reference scene rebuilt at visual version " + VisualVersion + ".");
    }

    private static void BuildScene()
    {
        Scene scene = SceneManager.GetActiveScene();
        foreach (GameObject existingRoot in scene.GetRootGameObjects())
            Object.DestroyImmediate(existingRoot);

        GameObject root = new GameObject("RescueSimulation");
        GameObject environment = new GameObject("Environment");
        environment.transform.SetParent(root.transform);
        CreateWater(environment.transform);
        CreateBaseStation(environment.transform);
        CreateCamera(root.transform);
        CreateLight(root.transform);
        ConfigureAmbience();

        GameObject planner = new GameObject("RoutePlannerUDP");
        planner.transform.SetParent(root.transform);
        UdpPlannerClient client = planner.AddComponent<UdpPlannerClient>();

        GameObject people = new GameObject("People");
        people.transform.SetParent(root.transform);
        BoatController[] boats = CreateBoats(root.transform);

        GameObject managerObject = new GameObject("SimulationManager");
        managerObject.transform.SetParent(root.transform);
        RescueSimulationManager manager = managerObject.AddComponent<RescueSimulationManager>();
        manager.plannerClient = client;
        manager.boats = boats;
        manager.peopleRoot = people.transform;
        manager.personSkinMaterial = CreateMaterial("Person_Skin", new Color(0.95f, 0.68f, 0.48f));
        manager.personSuitMaterial = CreateMaterial("Person_Suit", new Color(0.08f, 0.18f, 0.28f));
        manager.personVestMaterial = CreateMaterial("Person_LifeVest", new Color(1f, 0.28f, 0.035f), 0.25f, 0.05f, new Color(0.9f, 0.22f, 0.02f), 0.35f);

        EditorSceneManager.MarkSceneDirty(scene);
        EditorSceneManager.SaveScene(scene);
        Selection.activeGameObject = managerObject;
        Debug.Log("Rescue scene generated. Press Play, click water to add people, then click Start / Plan.");
    }

    private static void CreateWater(Transform parent)
    {
        GameObject water = new GameObject("Water_60cm_x_60cm");
        water.transform.SetParent(parent);
        water.transform.localPosition = Vector3.zero;
        water.AddComponent<WaterSystem>();
    }

    private static void CreateBaseStation(Transform parent)
    {
        GameObject safety = GameObject.CreatePrimitive(PrimitiveType.Cube);
        safety.name = "BaseSafetyZone_28cm_x_21cm";
        safety.transform.SetParent(parent);
        safety.transform.localPosition = new Vector3(0f, 0.004f, 0f);
        safety.transform.localScale = new Vector3(0.28f, 0.006f, 0.21f);
        safety.GetComponent<Renderer>().sharedMaterial = CreateMaterial("SafetyZone", new Color(0.95f, 0.52f, 0.10f), 0.15f, 0f);
        // Visual marker only: with physics enabled the collider would trap the
        // boats, which spawn right next to the base.
        Object.DestroyImmediate(safety.GetComponent<Collider>());

        ProceduralRescueModels.CreateBaseStation(
            parent,
            CreateMaterial("Base_Platform", new Color(0.12f, 0.16f, 0.20f), 0.45f, 0.65f),
            CreateMaterial("Base_Trim", new Color(1f, 0.48f, 0.04f), 0.30f, 0.20f),
            CreateMaterial("Base_Cabin", new Color(0.80f, 0.88f, 0.91f), 0.35f, 0.15f),
            CreateMaterial("Base_Glass", new Color(0.08f, 0.45f, 0.62f), 0.75f, 0.35f, new Color(0.10f, 0.45f, 0.60f), 0.25f),
            CreateMaterial("Base_Metal", new Color(0.35f, 0.40f, 0.44f), 0.60f, 0.80f),
            CreateMaterial("Base_Solar", new Color(0.025f, 0.11f, 0.26f), 0.80f, 0.45f));
    }

    private static BoatController[] CreateBoats(Transform parent)
    {
        string[] ids = { "boat_1", "boat_2", "boat_3", "boat_4" };
        // Four recessed berths inside the base footprint. The base collider is
        // a trigger, so rigidbody boats can visibly launch from the station.
        Vector3[] positions =
        {
            new Vector3(-0.118f, 0f, -0.040f),
            new Vector3(-0.118f, 0f,  0.040f),
            new Vector3( 0.118f, 0f, -0.040f),
            new Vector3( 0.118f, 0f,  0.040f)
        };
        Color[] colors = { new Color(0.1f, 0.5f, 1f), new Color(1f, 0.48f, 0.08f), new Color(0.2f, 0.85f, 0.35f), new Color(0.66f, 0.30f, 0.95f) };
        BoatController[] boats = new BoatController[4];

        Material hull = CreateMaterial("Boat_Hull", new Color(0.92f, 0.95f, 0.96f), 0.42f, 0.20f);
        hull.SetFloat("_Cull", 0f);
        Material dark = CreateMaterial("Boat_Dark", new Color(0.035f, 0.055f, 0.075f), 0.40f, 0.45f);
        Material glass = CreateMaterial("Boat_Glass", new Color(0.04f, 0.40f, 0.58f), 0.78f, 0.28f, new Color(0.08f, 0.42f, 0.55f), 0.3f);
        Material metal = CreateMaterial("Boat_Metal", new Color(0.42f, 0.48f, 0.53f), 0.55f, 0.78f);
        Material navRed = CreateMaterial("Nav_Red", new Color(0.85f, 0.05f, 0.03f), 0.5f, 0f, new Color(1.2f, 0.08f, 0.04f), 1.0f);
        Material navGreen = CreateMaterial("Nav_Green", new Color(0.03f, 0.75f, 0.12f), 0.5f, 0f, new Color(0.05f, 1.1f, 0.15f), 1.0f);
        Material navWhite = CreateMaterial("Nav_White", new Color(0.9f, 0.9f, 0.85f), 0.5f, 0f, new Color(1.1f, 1.05f, 0.9f), 1.0f);

        for (int index = 0; index < boats.Length; index++)
        {
            GameObject boat = ProceduralRescueModels.CreateBoat(
                ids[index], parent, positions[index],
                index < 2 ? Quaternion.Euler(0f, -90f, 0f) : Quaternion.Euler(0f, 90f, 0f),
                CreateMaterial(ids[index] + "_Accent", colors[index], 0.32f, 0.15f),
                hull, dark, glass, metal, navRed, navGreen, navWhite);
            boats[index] = boat.AddComponent<BoatController>();
            boats[index].Configure(ids[index], colors[index]);
            boat.AddComponent<BoatPhysics>();
        }
        return boats;
    }

    private static void CreateCamera(Transform parent)
    {
        GameObject cameraObject = new GameObject("Main Camera");
        cameraObject.tag = "MainCamera";
        cameraObject.transform.SetParent(parent);
        cameraObject.transform.position = new Vector3(0f, 0.70f, -0.68f);
        cameraObject.transform.rotation = Quaternion.LookRotation(Vector3.zero - cameraObject.transform.position);
        Camera camera = cameraObject.AddComponent<Camera>();
        camera.fieldOfView = 48f;
        camera.backgroundColor = new Color(0.55f, 0.75f, 0.88f);
    }

    private static void CreateLight(Transform parent)
    {
        GameObject lightObject = new GameObject("Directional Light");
        lightObject.transform.SetParent(parent);
        lightObject.transform.rotation = Quaternion.Euler(50f, -35f, 0f);
        Light light = lightObject.AddComponent<Light>();
        light.type = LightType.Directional;
        light.intensity = 1.35f;
        light.color = new Color(1f, 0.97f, 0.90f);
        light.shadows = LightShadows.Soft;
        light.shadowStrength = 0.75f;
    }

    private static void ConfigureAmbience()
    {
        RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
        RenderSettings.ambientSkyColor = new Color(0.62f, 0.78f, 0.90f);
        RenderSettings.ambientEquatorColor = new Color(0.30f, 0.44f, 0.56f);
        RenderSettings.ambientGroundColor = new Color(0.10f, 0.14f, 0.18f);
        RenderSettings.fog = true;
        RenderSettings.fogMode = FogMode.Linear;
        RenderSettings.fogColor = new Color(0.55f, 0.75f, 0.88f);
        RenderSettings.fogStartDistance = 0.30f;
        RenderSettings.fogEndDistance = 2.6f;
    }

    private static Material CreateMaterial(string materialName, Color color, float smoothness = 0.35f, float metallic = 0f,
        Color? emissionColor = null, float emissionStrength = 0f)
    {
        const string materialFolder = "Assets/Materials";
        if (!AssetDatabase.IsValidFolder(materialFolder))
            AssetDatabase.CreateFolder("Assets", "Materials");
        string assetPath = materialFolder + "/" + materialName + ".mat";
        Material material = AssetDatabase.LoadAssetAtPath<Material>(assetPath);
        if (material == null)
        {
            material = new Material(Shader.Find("Universal Render Pipeline/Lit"));
            AssetDatabase.CreateAsset(material, assetPath);
        }
        material.color = color;
        material.SetFloat("_Smoothness", smoothness);
        material.SetFloat("_Metallic", metallic);
        if (emissionColor.HasValue && emissionStrength > 0f)
        {
            material.EnableKeyword("_EMISSION");
            material.SetColor("_EmissionColor", emissionColor.Value * emissionStrength);
        }
        EditorUtility.SetDirty(material);
        return material;
    }
}
