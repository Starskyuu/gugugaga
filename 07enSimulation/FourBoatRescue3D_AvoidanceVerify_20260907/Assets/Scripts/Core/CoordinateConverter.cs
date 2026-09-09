using UnityEngine;

public static class CoordinateConverter
{
    public const float FieldSizeMeters = 0.60f;
    public const float WaterHeight = 0f;
    private const float HalfField = FieldSizeMeters * 0.5f;

    public static Vector3 CmToWorld(float xCm, float yCm, float height = WaterHeight)
    {
        return new Vector3(xCm / 100f - HalfField, height, yCm / 100f - HalfField);
    }

    public static Vector2 WorldToCm(Vector3 world)
    {
        return new Vector2((world.x + HalfField) * 100f, (world.z + HalfField) * 100f);
    }

    public static bool IsInsideField(Vector3 world)
    {
        return Mathf.Abs(world.x) <= HalfField && Mathf.Abs(world.z) <= HalfField;
    }
}
