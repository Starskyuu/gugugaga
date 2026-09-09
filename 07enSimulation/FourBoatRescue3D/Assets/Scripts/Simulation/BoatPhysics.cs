using UnityEngine;

/// <summary>
/// PhysX (NVIDIA) rigidbody boat physics:
/// Archimedes buoyancy sampled at four points, uprighting torques, propeller
/// thrust, rudder yaw torque, hull resistance, soft field walls, braking and
/// a foam wake. An autopilot (BoatController) writes throttle/rudder each step.
/// </summary>
[RequireComponent(typeof(Rigidbody))]
public class BoatPhysics : MonoBehaviour
{
    [Header("Hull (origin = calm waterline)")]
    public float hullLength = 0.070f;
    public float hullBeam = 0.050f;
    [Tooltip("Max submergence before buoyancy saturates (keeps capsized boats afloat).")]
    public float hullSideDepth = 0.018f;

    [Header("Mass and buoyancy")]
    public float boatMass = 0.030f;
    public float waterDensity = 1000f;
    public float uprightingTorque = 0.055f;
    public float rollDampingTorque = 0.020f;
    [Tooltip("Vertical (heave) damping so the hull settles on the water instead of bobbing.")]
    public float heaveDamping = 1.2f;
    [Tooltip("Low-pass response of the physical waterline. Visual waves remain unchanged.")]
    public float waterlineFollowSpeed = 4f;
    [Tooltip("Locks roll and pitch for a stable small-scale simulation while leaving yaw free.")]
    public bool stabilizeRollPitch = true;

    [Header("Resistance")]
    public float lateralDrag = 3.2f;
    public float forwardDrag = 0.22f;

    [Header("Propulsion")]
    public float maxThrust = 0.032f;
    public float maxSpeed = 0.17f;
    [Tooltip("Yaw torque per rudder degree at full through-water speed. The hull yaw inertia is ~1.6e-5 kg*m2, so this must be tiny (about 4e-7) or the boat spins out of control.")]
    public float rudderTorqueScale = 0.0000004f;
    [Tooltip("Minimum rudder authority fraction kept at very low speeds so the hull can still pivot (verified value: 0.25).")]
    public float rudderSpeedFloor = 0.25f;

    [Header("Field limits")]
    public float fieldHalfSize = 0.26f;
    public float wallStiffness = 60f;

    [Header("Wake")]
    public bool wakeEnabled = true;

    [HideInInspector] public float throttleInput;
    [HideInInspector] public float rudderInput;

    private Rigidbody body;
    private bool braking;
    private ParticleSystem wakeParticles;
    private float buoyancyForcePerDepthPerPoint;
    private float equilibriumDraft;
    private float filteredWaterHeight;
    private bool waterHeightInitialized;

    public Vector3 Velocity => body != null ? body.linearVelocity : Vector3.zero;
    public bool IsKinematic => body != null && body.isKinematic;

    /// <summary>Yaw rate in degrees per second (positive = positive rotation
    /// about +Y, bow swinging from +Z toward +X).</summary>
    public float YawRateDeg => body != null ? body.angularVelocity.y * Mathf.Rad2Deg : 0f;

    public float ForwardSpeed
    {
        get
        {
            if (body == null)
                return 0f;
            Vector3 forward = transform.forward;
            forward.y = 0f;
            if (forward.sqrMagnitude < 0.0001f)
                return 0f;
            forward.Normalize();
            return Vector3.Dot(body.linearVelocity, forward);
        }
    }

    public void SetControls(float throttle, float rudderDegrees)
    {
        throttleInput = Mathf.Clamp(throttle, -1f, 1f);
        rudderInput = Mathf.Clamp(rudderDegrees, -40f, 40f);
    }

    public void Brake() => braking = true;

    public void SetDocked(bool docked)
    {
        if (body == null)
            return;

        throttleInput = 0f;
        rudderInput = 0f;
        braking = false;
        if (!body.isKinematic)
        {
            body.linearVelocity = Vector3.zero;
            body.angularVelocity = Vector3.zero;
        }
        body.isKinematic = docked;
    }

    public void DockAt(Vector3 position, Quaternion rotation)
    {
        if (body == null)
            return;
        SetDocked(false);
        // Reset interpolation history when resetting/docking; otherwise the
        // rendered hull and next navigation tick can use the old sea position.
        RigidbodyInterpolation interpolation = body.interpolation;
        body.interpolation = RigidbodyInterpolation.None;
        body.position = position;
        body.rotation = rotation;
        transform.SetPositionAndRotation(position, rotation);
        body.linearVelocity = Vector3.zero;
        body.angularVelocity = Vector3.zero;
        body.isKinematic = true;
        body.interpolation = interpolation;
    }

    public void MoveKinematic(Vector3 position, Quaternion rotation)
    {
        if (body == null)
            return;
        if (!body.isKinematic)
            SetDocked(true);
        body.MovePosition(position);
        body.MoveRotation(rotation);
    }

    private void Awake()
    {
        body = GetComponent<Rigidbody>();
        body.mass = boatMass;
        body.useGravity = true;
        body.linearDamping = 0.10f;
        body.angularDamping = 0.65f;
        body.interpolation = RigidbodyInterpolation.Interpolate;
        body.collisionDetectionMode = CollisionDetectionMode.ContinuousDynamic;
        body.solverIterations = 14;
        body.solverVelocityIterations = 5;
        body.maxAngularVelocity = 10f;
        body.centerOfMass = new Vector3(0f, -0.005f, 0f);
        if (stabilizeRollPitch)
            body.constraints = RigidbodyConstraints.FreezeRotationX | RigidbodyConstraints.FreezeRotationZ;

        buoyancyForcePerDepthPerPoint =
            waterDensity * Mathf.Abs(Physics.gravity.y) * (hullLength * hullBeam * 0.25f);
        // At the visual waterline (transform Y == water Y), the four sample
        // points must already displace the boat's weight. Previously they sat
        // at the transform origin, forcing the whole model about 8.6 mm under
        // water before any equilibrium was possible.
        equilibriumDraft = Mathf.Clamp(
            boatMass * Mathf.Abs(Physics.gravity.y) / (buoyancyForcePerDepthPerPoint * 4f),
            0.002f,
            hullSideDepth * 0.85f);

        SetupWake();
    }

    private void FixedUpdate()
    {
        if (body == null || body.isKinematic)
            return;

        ApplyBuoyancy();
        if (!stabilizeRollPitch)
            ApplyStability();
        ApplyPropulsion();
        ApplyResistance();
        ApplyBoundary();
        ClampSpeed();
        UpdateWake();
    }

    private void ApplyBuoyancy()
    {
        Vector3 forward = transform.forward;
        forward.y = 0f;
        if (forward.sqrMagnitude < 0.001f)
            forward = Vector3.forward;
        else
            forward.Normalize();
        Vector3 right = Vector3.Cross(Vector3.up, forward).normalized;

        Vector3[] offsets =
        {
            forward * (hullLength * 0.38f),   // bow
            -forward * (hullLength * 0.38f),  // stern
            right * (hullBeam * 0.36f),       // starboard
            -right * (hullBeam * 0.36f)       // port
        };

        float sampledWaterHeight = 0f;
        for (int i = 0; i < offsets.Length; i++)
            sampledWaterHeight += WaterSystem.HeightAt(transform.position + offsets[i]);
        sampledWaterHeight /= offsets.Length;

        if (!waterHeightInitialized)
        {
            filteredWaterHeight = sampledWaterHeight;
            waterHeightInitialized = true;
        }
        float follow = 1f - Mathf.Exp(-waterlineFollowSpeed * Time.fixedDeltaTime);
        filteredWaterHeight = Mathf.Lerp(filteredWaterHeight, sampledWaterHeight, follow);

        float submerged = filteredWaterHeight + equilibriumDraft - transform.position.y;
        submerged = Mathf.Clamp(submerged, 0f, hullSideDepth);
        if (submerged > 0.0004f)
            body.AddForce(Vector3.up * (submerged * buoyancyForcePerDepthPerPoint * offsets.Length));

        // Heave damping: kill vertical oscillation so the hull settles quickly.
        body.AddForce(Vector3.up * (-body.linearVelocity.y * heaveDamping));
    }

    private void ApplyStability()
    {
        // Restoring torques keep the deck upright in waves.
        float roll = Mathf.Asin(Mathf.Clamp(transform.right.y, -1f, 1f));
        float pitch = Mathf.Asin(Mathf.Clamp(-transform.forward.y, -1f, 1f));

        body.AddRelativeTorque(-pitch * uprightingTorque, 0f, -roll * uprightingTorque, ForceMode.Force);

        Vector3 localAngularVelocity = transform.InverseTransformDirection(body.angularVelocity);
        body.AddRelativeTorque(
            -localAngularVelocity.x * rollDampingTorque, 0f,
            -localAngularVelocity.z * rollDampingTorque, ForceMode.Force);
    }

    private void ApplyPropulsion()
    {
        Vector3 forward = transform.forward;
        forward.y = 0f;
        if (forward.sqrMagnitude < 0.001f)
            forward = Vector3.forward;
        else
            forward.Normalize();

        float speed = Vector3.Dot(body.linearVelocity, forward);

        if (braking && Mathf.Abs(speed) < 0.012f)
            braking = false;

        float thrust = 0f;
        if (!braking)
        {
            if (throttleInput > 0.001f && speed < maxSpeed)
            {
                float reserve = Mathf.Clamp01((maxSpeed - speed) / maxSpeed);
                float throttleScale = Mathf.Lerp(0.25f, 1f, reserve);
                thrust = throttleInput * maxThrust * throttleScale * Mathf.Cos(rudderInput * Mathf.Deg2Rad);
            }
            else if (throttleInput < -0.001f && speed > -maxSpeed * 0.5f)
            {
                thrust = throttleInput * maxThrust * 0.6f;
            }
        }

        if (Mathf.Abs(thrust) > 0.0001f)
            body.AddForceAtPosition(forward * thrust, transform.TransformPoint(0f, 0f, -hullLength * 0.45f));

        // Rudder: yaw torque proportional to rudder angle and through-water speed,
        // with a floor so the hull can still pivot when nearly stationary.
        float speedFactor = Mathf.Clamp01(Mathf.Abs(speed) / 0.03f);
        speedFactor = Mathf.Max(speedFactor, rudderSpeedFloor);
        float directionSign = speed >= 0f ? 1f : -1f;
        body.AddRelativeTorque(0f, rudderInput * rudderTorqueScale * speedFactor * directionSign, 0f, ForceMode.Force);
    }

    private void ApplyResistance()
    {
        Vector3 forward = transform.forward;
        forward.y = 0f;
        if (forward.sqrMagnitude < 0.001f)
            forward = Vector3.forward;
        else
            forward.Normalize();

        Vector3 velocity = body.linearVelocity;
        float forwardSpeed = Vector3.Dot(velocity, forward);
        Vector3 lateral = velocity - forward * forwardSpeed;

        body.AddForce(-lateral * lateralDrag, ForceMode.Acceleration);
        body.AddForce(-forward * (forwardSpeed * forwardDrag), ForceMode.Acceleration);

        if (braking)
        {
            body.AddForce(-velocity * 3.2f, ForceMode.Acceleration);
            body.AddTorque(-body.angularVelocity * 2.0f, ForceMode.Acceleration);
        }
    }

    private void ApplyBoundary()
    {
        Vector3 position = transform.position;
        Vector3 force = Vector3.zero;

        if (Mathf.Abs(position.x) > fieldHalfSize)
        {
            float overshoot = Mathf.Abs(position.x) - fieldHalfSize;
            force.x = -Mathf.Sign(position.x) * overshoot * wallStiffness;
            if (Mathf.Sign(body.linearVelocity.x) == Mathf.Sign(position.x))
                force.x -= body.linearVelocity.x * 1.2f;
        }
        if (Mathf.Abs(position.z) > fieldHalfSize)
        {
            float overshoot = Mathf.Abs(position.z) - fieldHalfSize;
            force.z = -Mathf.Sign(position.z) * overshoot * wallStiffness;
            if (Mathf.Sign(body.linearVelocity.z) == Mathf.Sign(position.z))
                force.z -= body.linearVelocity.z * 1.2f;
        }

        if (force != Vector3.zero)
            body.AddForce(force, ForceMode.Acceleration);
    }

    private void ClampSpeed()
    {
        if (body.linearVelocity.magnitude > 0.25f)
            body.linearVelocity = body.linearVelocity.normalized * 0.25f;
    }

    private void SetupWake()
    {
        if (!wakeEnabled)
            return;

        Shader particleShader = Shader.Find("Universal Render Pipeline/Particles/Unlit");
        if (particleShader == null)
        {
            wakeEnabled = false;
            Debug.LogWarning("[BoatPhysics] URP particle shader not found; wake disabled for " + name + ".");
            return;
        }

        GameObject wakeObject = new GameObject("Wake");
        wakeObject.transform.SetParent(transform, false);
        wakeObject.transform.localPosition = new Vector3(0f, -0.002f, -hullLength * 0.48f);

        wakeParticles = wakeObject.AddComponent<ParticleSystem>();
        ParticleSystem.MainModule main = wakeParticles.main;
        main.loop = true;
        main.playOnAwake = false;
        main.startLifetime = 0.8f;
        main.startSpeed = new ParticleSystem.MinMaxCurve(0.015f, 0.05f);
        main.startSize = new ParticleSystem.MinMaxCurve(0.0025f, 0.006f);
        main.maxParticles = 400;
        main.simulationSpace = ParticleSystemSimulationSpace.World;
        main.gravityModifier = 0f;
        main.startColor = new Color(0.92f, 0.98f, 1f, 0.85f);

        ParticleSystem.EmissionModule emission = wakeParticles.emission;
        emission.rateOverTime = 0f;

        ParticleSystem.ShapeModule shape = wakeParticles.shape;
        shape.shapeType = ParticleSystemShapeType.Sphere;
        shape.radius = 0.008f;

        ParticleSystem.SizeOverLifetimeModule sizeOverLifetime = wakeParticles.sizeOverLifetime;
        sizeOverLifetime.enabled = true;
        sizeOverLifetime.size = new ParticleSystem.MinMaxCurve(1f,
            new AnimationCurve(new Keyframe(0f, 0.45f), new Keyframe(1f, 1.9f)));

        ParticleSystem.ColorOverLifetimeModule colorOverLifetime = wakeParticles.colorOverLifetime;
        colorOverLifetime.enabled = true;
        Gradient gradient = new Gradient();
        gradient.SetKeys(
            new[] { new GradientColorKey(Color.white, 0f), new GradientColorKey(Color.white, 1f) },
            new[] { new GradientAlphaKey(0.9f, 0f), new GradientAlphaKey(0f, 1f) });
        colorOverLifetime.color = new ParticleSystem.MinMaxGradient(gradient);

        ParticleSystemRenderer particleRenderer = wakeObject.GetComponent<ParticleSystemRenderer>();
        particleRenderer.renderMode = ParticleSystemRenderMode.Billboard;
        particleRenderer.material = CreateFoamMaterial(particleShader);
        wakeParticles.Play();
    }

    private static Material CreateFoamMaterial(Shader shader)
    {
        Material material = new Material(shader);
        Texture2D texture = new Texture2D(64, 64, TextureFormat.RGBA32, false) { name = "WakeFoam" };
        Color[] pixels = new Color[64 * 64];
        for (int y = 0; y < 64; y++)
        {
            for (int x = 0; x < 64; x++)
            {
                float dx = (x - 31.5f) / 32f;
                float dy = (y - 31.5f) / 32f;
                float distance = Mathf.Sqrt(dx * dx + dy * dy);
                float alpha = Mathf.Clamp01(1f - distance);
                pixels[y * 64 + x] = new Color(1f, 1f, 1f, alpha * alpha);
            }
        }
        texture.SetPixels(pixels);
        texture.Apply();
        material.mainTexture = texture;
        material.SetColor("_BaseColor", Color.white);
        return material;
    }

    private void UpdateWake()
    {
        if (wakeParticles == null)
            return;
        float speed = Mathf.Abs(ForwardSpeed);
        // Unity 6 particle modules are transient handles. Fetching the module
        // here avoids the invalid cached-module exception seen in play mode.
        ParticleSystem.EmissionModule emission = wakeParticles.emission;
        emission.rateOverTime = speed > 0.015f ? Mathf.Min(320f, speed * 1500f) : 0f;
    }
}
