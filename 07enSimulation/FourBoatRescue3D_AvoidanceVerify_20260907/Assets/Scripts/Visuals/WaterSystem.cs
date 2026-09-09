using UnityEngine;

/// <summary>
/// Builds the animated water surface and exposes a wave-height sampler that is
/// shared by the physics (buoyancy) and the visuals (shader, people bobbing).
/// The wave math here MUST stay in sync with RescueWater.shader.
/// </summary>
[ExecuteAlways]
[DefaultExecutionOrder(-100)]
public class WaterSystem : MonoBehaviour
{
    public static WaterSystem Instance { get; private set; }

    [Header("Wave profile (synced with RescueWater.shader)")]
    public float waveAmplitude = 0.0016f;
    public float waterLevelY = 0f;

    [Header("Surface")]
    public float meshSize = 0.9f;
    [Min(8)] public int meshSegments = 90;

    [Header("Look")]
    public Color baseColor = new Color(0.03f, 0.42f, 0.62f);
    public Color deepColor = new Color(0.01f, 0.22f, 0.40f);
    public Color foamColor = new Color(0.85f, 0.95f, 1f);
    [Range(0f, 1f)] public float foamAmount = 0.18f;
    public float specStrength = 0.48f;
    public float shininess = 180f;
    public float edgeBlend = 0.45f;

    private Material waterMaterial;
    private float lastBuildAttempt = -10f;
    private bool loggedMissingShader;

    private static readonly Vector2 Wave1Dir = new Vector2(0.4226f, 0.9063f);
    private static readonly Vector2 Wave2Dir = new Vector2(-0.6428f, 0.7660f);
    private const float K1 = 44.8799f;   // 2*pi / 0.14
    private const float W1 = 13.4640f;   // K1 * 0.30
    private const float K2 = 114.2398f;  // 2*pi / 0.055
    private const float W2 = 62.8319f;   // K2 * 0.55

    /// <summary>Wave height at world position (calm water = waterLevelY).</summary>
    public static float HeightAt(float x, float z)
    {
        if (Instance == null)
            return 0f;
        float a1 = Instance.waveAmplitude;
        float a2 = a1 * 0.38f;
        float p1 = K1 * (x * Wave1Dir.x + z * Wave1Dir.y) - W1 * Time.time;
        float p2 = K2 * (x * Wave2Dir.x + z * Wave2Dir.y) - W2 * Time.time + 1.3f;
        return Instance.waterLevelY + a1 * Mathf.Sin(p1) + a2 * Mathf.Sin(p2);
    }

    public static float HeightAt(Vector3 worldPosition)
    {
        return HeightAt(worldPosition.x, worldPosition.z);
    }

    public void SetRoughness(float amplitude)
    {
        waveAmplitude = Mathf.Clamp(amplitude, 0f, 0.008f);
    }

    private void Awake()
    {
        Instance = this;
        BuildWaterSurface();
    }

    private void OnDestroy()
    {
        if (Instance == this)
            Instance = null;
    }

    private void Update()
    {
        if (waterMaterial == null)
        {
            // The shader may not be imported yet when the scene is generated.
            if (Time.time - lastBuildAttempt > 2f)
            {
                lastBuildAttempt = Time.time;
                BuildWaterSurface();
            }
            return;
        }
        waterMaterial.SetFloat("_WaveAmplitude", waveAmplitude);
        waterMaterial.SetFloat("_WaveTime", Time.time);
    }

    private void BuildWaterSurface()
    {
        Shader shader = Shader.Find("Custom/RescueWater");
        if (shader == null)
        {
            if (!loggedMissingShader)
            {
                loggedMissingShader = true;
                Debug.LogError("[WaterSystem] RescueWater.shader not found. Water will not render.");
            }
            return;
        }
        loggedMissingShader = false;

        MeshFilter filter = GetComponent<MeshFilter>();
        if (filter == null)
            filter = gameObject.AddComponent<MeshFilter>();
        MeshRenderer meshRenderer = GetComponent<MeshRenderer>();
        if (meshRenderer == null)
            meshRenderer = gameObject.AddComponent<MeshRenderer>();

        filter.sharedMesh = CreateWaterMesh();
        waterMaterial = new Material(shader);
        waterMaterial.SetColor("_BaseColor", baseColor);
        waterMaterial.SetColor("_DeepColor", deepColor);
        waterMaterial.SetColor("_FoamColor", foamColor);
        waterMaterial.SetFloat("_FoamAmount", foamAmount);
        waterMaterial.SetFloat("_SpecStrength", specStrength);
        waterMaterial.SetFloat("_Shininess", shininess);
        waterMaterial.SetFloat("_EdgeBlend", edgeBlend);
        meshRenderer.sharedMaterial = waterMaterial;
    }

    private Mesh CreateWaterMesh()
    {
        int rows = meshSegments + 1;
        Vector3[] vertices = new Vector3[rows * rows];
        Vector2[] uv = new Vector2[rows * rows];
        int[] triangles = new int[meshSegments * meshSegments * 6];

        float half = meshSize * 0.5f;
        float step = meshSize / meshSegments;

        for (int i = 0; i < rows; i++)
        {
            for (int j = 0; j < rows; j++)
            {
                int index = i + j * rows;
                vertices[index] = new Vector3(-half + i * step, 0f, -half + j * step);
                uv[index] = new Vector2(i / (float)meshSegments, j / (float)meshSegments);
            }
        }

        int t = 0;
        for (int i = 0; i < meshSegments; i++)
        {
            for (int j = 0; j < meshSegments; j++)
            {
                int v00 = i + j * rows;
                int v10 = (i + 1) + j * rows;
                int v01 = i + (j + 1) * rows;
                int v11 = (i + 1) + (j + 1) * rows;
                triangles[t++] = v00; triangles[t++] = v01; triangles[t++] = v10;
                triangles[t++] = v10; triangles[t++] = v01; triangles[t++] = v11;
            }
        }

        Mesh mesh = new Mesh { name = "RescueWaterMesh" };
        mesh.vertices = vertices;
        mesh.uv = uv;
        mesh.triangles = triangles;
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        return mesh;
    }
}
