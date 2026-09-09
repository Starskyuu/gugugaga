using System.Collections;
using UnityEngine;

/// <summary>Raises the station from a submerged standby position when a mission starts.</summary>
public class BaseStationLift : MonoBehaviour
{
    public float liftDistance = 0.075f;
    public float liftDuration = 1.6f;
    public float raisedOffset = 0.008f;

    private float raisedY;
    private float loweredY;
    private Coroutine liftRoutine;
    public bool IsRaised { get; private set; }

    public void PrepareLowered()
    {
        raisedY = raisedOffset;
        loweredY = raisedY - liftDistance;
        if (liftRoutine != null)
            StopCoroutine(liftRoutine);
        SetHeight(loweredY);
        IsRaised = false;
    }

    public void Raise()
    {
        if (liftRoutine != null)
            StopCoroutine(liftRoutine);
        liftRoutine = StartCoroutine(RaiseRoutine());
    }

    private IEnumerator RaiseRoutine()
    {
        float from = transform.localPosition.y;
        float elapsed = 0f;
        while (elapsed < liftDuration)
        {
            elapsed += Time.deltaTime;
            float t = Mathf.Clamp01(elapsed / Mathf.Max(0.01f, liftDuration));
            t = t * t * (3f - 2f * t);
            SetHeight(Mathf.Lerp(from, raisedY, t));
            yield return null;
        }
        SetHeight(raisedY);
        IsRaised = true;
        liftRoutine = null;
    }

    private void SetHeight(float y)
    {
        Vector3 position = transform.localPosition;
        position.y = y;
        transform.localPosition = position;
    }
}
