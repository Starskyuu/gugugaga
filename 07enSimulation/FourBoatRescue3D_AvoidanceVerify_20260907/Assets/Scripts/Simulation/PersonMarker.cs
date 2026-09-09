using UnityEngine;

/// <summary>
/// A person waiting for rescue. Floats on the animated water surface with a
/// gentle bob and sway; rescue state is resolved by distance in the manager.
/// </summary>
public class PersonMarker : MonoBehaviour
{
    public enum RescueState
    {
        Waiting,
        OnBoat,
        Delivered
    }

    public string personId;
    public RescueState State { get; private set; }
    public bool IsRescued => State != RescueState.Waiting;
    public BoatController RescueBoat { get; private set; }

    public float bobAmplitude = 0.0012f;
    public float bobSpeed = 1.6f;
    public float swayDegrees = 6f;
    public float onboardScale = 0.46f;

    private Vector3 basePosition;
    private float phase;
    private Transform leftArm;
    private Transform rightArm;
    private Quaternion leftArmRest;
    private Quaternion rightArmRest;

    private void Awake()
    {
        basePosition = transform.position;
        phase = Random.value * Mathf.PI * 2f;
        leftArm = FindDescendant("Person_Arm_L") ?? FindDescendant("LeftArm");
        rightArm = FindDescendant("Person_Arm_R") ?? FindDescendant("RightArm");
        if (leftArm != null) leftArmRest = leftArm.localRotation;
        if (rightArm != null) rightArmRest = rightArm.localRotation;
    }

    public void SetRescued(bool rescued)
    {
        State = rescued ? RescueState.Delivered : RescueState.Waiting;
    }

    public void Board(BoatController boat, int seatIndex, bool piled = false)
    {
        if (boat == null || State != RescueState.Waiting)
            return;

        State = RescueState.OnBoat;
        RescueBoat = boat;
        transform.SetParent(boat.transform, false);

        // Visible survivor positions behind the cabin. Parenting to the hull
        // makes the person follow the rigidbody without a second physics body.
        int slot = seatIndex % 4;
        int layer = piled ? seatIndex / 4 : 0;
        float side = slot % 2 == 0 ? -0.010f : 0.010f;
        float row = slot / 2;
        transform.localPosition = new Vector3(side, 0.018f + layer * 0.014f, -0.020f + row * 0.014f);
        transform.localRotation = Quaternion.Euler(piled ? layer * 8f : 0f, 180f + (slot - 1.5f) * 8f, piled ? (slot % 2 == 0 ? -7f : 7f) : 0f);
        transform.localScale = Vector3.one * onboardScale;
        if (leftArm != null) leftArm.localRotation = leftArmRest;
        if (rightArm != null) rightArm.localRotation = rightArmRest;
    }

    public void MarkDelivered()
    {
        State = RescueState.Delivered;
    }

    private void Update()
    {
        if (State != RescueState.Waiting)
            return;

        float time = Time.time;
        float waveHeight = WaterSystem.HeightAt(basePosition.x, basePosition.z);
        float bob = Mathf.Sin(time * bobSpeed + phase) * bobAmplitude;
        transform.position = new Vector3(basePosition.x, waveHeight + 0.012f + bob, basePosition.z);
        transform.rotation = Quaternion.Euler(
            Mathf.Sin(time * 0.9f + phase) * swayDegrees,
            0f,
            Mathf.Cos(time * 0.7f + phase) * swayDegrees);

        float wave = Mathf.Sin(time * 5.2f + phase) * 52f;
        if (leftArm != null)
            leftArm.localRotation = leftArmRest * Quaternion.Euler(wave, 0f, 16f);
        if (rightArm != null)
            rightArm.localRotation = rightArmRest * Quaternion.Euler(-wave * 0.72f, 0f, -16f);
    }

    private Transform FindDescendant(string targetName)
    {
        foreach (Transform child in GetComponentsInChildren<Transform>(true))
            if (child.name == targetName)
                return child;
        return null;
    }
}
