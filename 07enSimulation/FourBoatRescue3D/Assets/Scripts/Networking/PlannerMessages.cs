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
