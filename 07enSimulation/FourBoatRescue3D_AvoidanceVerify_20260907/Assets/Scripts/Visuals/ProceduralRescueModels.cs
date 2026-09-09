using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Procedurally built rescue fleet visuals: a five-station hull mesh (winding
/// verified offline), detailed cabins, emissive navigation lights, pontoons,
/// fenders, a flashing beacon and floating people with life rings.
/// </summary>
public static class ProceduralRescueModels
{
    private static readonly Dictionary<string, Material> RuntimeMaterials = new Dictionary<string, Material>();
    // ------------------------------------------------------------------ Boat

    public static GameObject CreateBoat(string id, Transform parent, Vector3 position, Quaternion rotation,
        Material accent, Material hull, Material dark, Material glass, Material metal,
        Material navRed, Material navGreen, Material navWhite)
    {
        GameObject boat = new GameObject(id);
        boat.transform.SetParent(parent);
        boat.transform.position = position;
        boat.transform.rotation = rotation;

        if (AttachBlockout("RescueBoat_Blockout", boat.transform, 0.23f, Vector3.zero) != null)
        {
            BoxCollider blockoutCollider = boat.AddComponent<BoxCollider>();
            blockoutCollider.center = new Vector3(0f, 0.008f, 0f);
            blockoutCollider.size = new Vector3(0.040f, 0.026f, 0.076f);
            return boat;
        }

        MeshFilter hullFilter = boat.AddComponent<MeshFilter>();
        MeshRenderer hullRenderer = boat.AddComponent<MeshRenderer>();
        hullFilter.sharedMesh = CreateHullMesh();
        hullRenderer.sharedMaterial = hull;
        BoxCollider collider = boat.AddComponent<BoxCollider>();
        collider.center = new Vector3(0f, 0.004f, 0f);
        collider.size = new Vector3(0.046f, 0.020f, 0.066f);

        // Waterline boot stripe + deck stripe in the boat accent color.
        Part("BootStripe", boat.transform, PrimitiveType.Cube, new Vector3(0f, 0.0075f, -0.002f), new Vector3(0.0508f, 0.0035f, 0.063f), Quaternion.identity, accent);
        Part("DeckStripe", boat.transform, PrimitiveType.Cube, new Vector3(0f, 0.0146f, -0.003f), new Vector3(0.028f, 0.0012f, 0.052f), Quaternion.identity, accent);
        Part("RubRailLeft", boat.transform, PrimitiveType.Cube, new Vector3(-0.0248f, 0.010f, -0.003f), new Vector3(0.0035f, 0.0045f, 0.064f), Quaternion.identity, dark);
        Part("RubRailRight", boat.transform, PrimitiveType.Cube, new Vector3(0.0248f, 0.010f, -0.003f), new Vector3(0.0035f, 0.0045f, 0.064f), Quaternion.identity, dark);

        GameObject cabin = new GameObject("Cabin");
        cabin.transform.SetParent(boat.transform, false);
        cabin.transform.localPosition = new Vector3(0f, 0f, -0.006f);
        Part("CabinBody", cabin.transform, PrimitiveType.Cube, Vector3.zero, new Vector3(0.030f, 0.013f, 0.026f), Quaternion.identity, hull);
        Part("FrontWindow", cabin.transform, PrimitiveType.Cube, new Vector3(0f, 0.003f, 0.0135f), new Vector3(0.023f, 0.009f, 0.0015f), Quaternion.Euler(-12f, 0f, 0f), glass);
        Part("LeftWindow", cabin.transform, PrimitiveType.Cube, new Vector3(-0.0156f, 0.003f, 0f), new Vector3(0.0015f, 0.008f, 0.014f), Quaternion.identity, glass);
        Part("RightWindow", cabin.transform, PrimitiveType.Cube, new Vector3(0.0156f, 0.003f, 0f), new Vector3(0.0015f, 0.008f, 0.014f), Quaternion.identity, glass);
        Part("Roof", cabin.transform, PrimitiveType.Cube, new Vector3(0f, 0.0088f, 0f), new Vector3(0.035f, 0.0025f, 0.031f), Quaternion.identity, accent);

        // Framed glazing, wipers and a readable cockpit interior.
        Part("WindshieldTopFrame", cabin.transform, PrimitiveType.Cube, new Vector3(0f, 0.008f, 0.0142f), new Vector3(0.027f, 0.0015f, 0.0012f), Quaternion.Euler(-12f, 0f, 0f), dark);
        Part("WindshieldCenterFrame", cabin.transform, PrimitiveType.Cube, new Vector3(0f, 0.003f, 0.0145f), new Vector3(0.0013f, 0.010f, 0.0011f), Quaternion.Euler(-12f, 0f, 0f), dark);
        Part("WiperLeft", cabin.transform, PrimitiveType.Cube, new Vector3(-0.006f, 0.002f, 0.0153f), new Vector3(0.0008f, 0.007f, 0.0007f), Quaternion.Euler(-12f, 0f, -18f), metal);
        Part("WiperRight", cabin.transform, PrimitiveType.Cube, new Vector3(0.006f, 0.002f, 0.0153f), new Vector3(0.0008f, 0.007f, 0.0007f), Quaternion.Euler(-12f, 0f, 18f), metal);
        Part("HelmConsole", cabin.transform, PrimitiveType.Cube, new Vector3(0f, -0.001f, 0.008f), new Vector3(0.020f, 0.006f, 0.006f), Quaternion.Euler(-12f, 0f, 0f), dark);
        Part("HelmScreen", cabin.transform, PrimitiveType.Cube, new Vector3(-0.005f, 0.002f, 0.0113f), new Vector3(0.006f, 0.004f, 0.0008f), Quaternion.Euler(-12f, 0f, 0f), navGreen);
        MeshPart("SteeringWheel", cabin.transform, CreateTorusMesh(0.0035f, 0.0007f, 18, 6), new Vector3(0.006f, 0.001f, 0.0118f), Vector3.one, Quaternion.identity, dark);
        Part("PilotSeat", cabin.transform, PrimitiveType.Cube, new Vector3(0.007f, -0.001f, -0.004f), new Vector3(0.008f, 0.008f, 0.009f), Quaternion.identity, dark);
        Part("ObserverSeat", cabin.transform, PrimitiveType.Cube, new Vector3(-0.007f, -0.001f, -0.004f), new Vector3(0.008f, 0.008f, 0.009f), Quaternion.identity, dark);

        // Foredeck rescue equipment and perimeter handrails.
        Part("ForedeckHatch", boat.transform, PrimitiveType.Cube, new Vector3(0f, 0.016f, 0.020f), new Vector3(0.018f, 0.0018f, 0.014f), Quaternion.Euler(-3f, 0f, 0f), dark);
        Part("HatchHandle", boat.transform, PrimitiveType.Cube, new Vector3(0f, 0.0174f, 0.020f), new Vector3(0.006f, 0.001f, 0.0012f), Quaternion.identity, metal);
        Part("BowRailLeft", boat.transform, PrimitiveType.Cylinder, new Vector3(-0.017f, 0.024f, 0.021f), new Vector3(0.0012f, 0.020f, 0.0012f), Quaternion.Euler(72f, 0f, -8f), metal);
        Part("BowRailRight", boat.transform, PrimitiveType.Cylinder, new Vector3(0.017f, 0.024f, 0.021f), new Vector3(0.0012f, 0.020f, 0.0012f), Quaternion.Euler(72f, 0f, 8f), metal);
        Part("BowPulpit", boat.transform, PrimitiveType.Cube, new Vector3(0f, 0.027f, 0.031f), new Vector3(0.026f, 0.0015f, 0.0015f), Quaternion.identity, metal);
        Part("SearchlightBody", boat.transform, PrimitiveType.Cylinder, new Vector3(0f, 0.019f, 0.028f), new Vector3(0.0045f, 0.006f, 0.0045f), Quaternion.Euler(90f, 0f, 0f), dark);
        Part("SearchlightLens", boat.transform, PrimitiveType.Sphere, new Vector3(0f, 0.020f, 0.032f), new Vector3(0.004f, 0.004f, 0.0018f), Quaternion.identity, navWhite);

        for (int side = -1; side <= 1; side += 2)
        {
            Part(side < 0 ? "PortGrabRail" : "StarboardGrabRail", boat.transform, PrimitiveType.Cube,
                new Vector3(side * 0.020f, 0.023f, 0.002f), new Vector3(0.0014f, 0.0014f, 0.040f), Quaternion.identity, metal);
            Part(side < 0 ? "PortStep" : "StarboardStep", boat.transform, PrimitiveType.Cube,
                new Vector3(side * 0.027f, 0.011f, -0.005f), new Vector3(0.004f, 0.002f, 0.030f), Quaternion.identity, accent);
            Part(side < 0 ? "PortNamePlate" : "StarboardNamePlate", boat.transform, PrimitiveType.Cube,
                new Vector3(side * 0.0262f, 0.012f, 0.012f), new Vector3(0.001f, 0.005f, 0.015f), Quaternion.identity, dark);
        }

        Part("RadarMast", boat.transform, PrimitiveType.Cylinder, new Vector3(0f, 0.036f, -0.008f), new Vector3(0.0012f, 0.011f, 0.0012f), Quaternion.identity, metal);
        Part("RadarBar", boat.transform, PrimitiveType.Cube, new Vector3(0f, 0.042f, -0.008f), new Vector3(0.016f, 0.002f, 0.0025f), Quaternion.identity, dark);
        Part("MastheadLight", boat.transform, PrimitiveType.Sphere, new Vector3(0f, 0.0436f, -0.008f), Vector3.one * 0.0018f, Quaternion.identity, navWhite);
        Part("NavLightPort", boat.transform, PrimitiveType.Sphere, new Vector3(-0.0235f, 0.009f, 0.031f), Vector3.one * 0.0022f, Quaternion.identity, navRed);
        Part("NavLightStarboard", boat.transform, PrimitiveType.Sphere, new Vector3(0.0235f, 0.009f, 0.031f), Vector3.one * 0.0022f, Quaternion.identity, navGreen);
        Part("SternLight", boat.transform, PrimitiveType.Sphere, new Vector3(0f, 0.012f, -0.034f), Vector3.one * 0.0018f, Quaternion.identity, navWhite);

        Part("EngineCowl", boat.transform, PrimitiveType.Cube, new Vector3(0f, 0.0175f, -0.028f), new Vector3(0.030f, 0.006f, 0.012f), Quaternion.identity, dark);
        Part("OutboardLeft", boat.transform, PrimitiveType.Cylinder, new Vector3(-0.008f, 0.011f, -0.033f), new Vector3(0.003f, 0.012f, 0.003f), Quaternion.Euler(90f, 0f, 0f), dark);
        Part("OutboardRight", boat.transform, PrimitiveType.Cylinder, new Vector3(0.008f, 0.011f, -0.033f), new Vector3(0.003f, 0.012f, 0.003f), Quaternion.Euler(90f, 0f, 0f), dark);
        Part("PropLeft", boat.transform, PrimitiveType.Cylinder, new Vector3(-0.008f, 0.003f, -0.034f), new Vector3(0.0035f, 0.0025f, 0.0035f), Quaternion.Euler(90f, 0f, 0f), metal);
        Part("PropRight", boat.transform, PrimitiveType.Cylinder, new Vector3(0.008f, 0.003f, -0.034f), new Vector3(0.0035f, 0.0025f, 0.0035f), Quaternion.Euler(90f, 0f, 0f), metal);

        Part("SternRail", boat.transform, PrimitiveType.Cube, new Vector3(0f, 0.022f, -0.033f), new Vector3(0.034f, 0.002f, 0.002f), Quaternion.identity, metal);
        MeshPart("LifeRing", boat.transform, CreateTorusMesh(0.0055f, 0.0016f), new Vector3(0f, 0.020f, -0.0328f), Vector3.one, Quaternion.identity, accent);
        Part("Antenna", boat.transform, PrimitiveType.Cylinder, new Vector3(0.010f, 0.024f, -0.030f), new Vector3(0.0006f, 0.020f, 0.0006f), Quaternion.Euler(0f, 0f, -12f), metal);
        Part("RescueBasket", boat.transform, PrimitiveType.Cube, new Vector3(-0.015f, 0.020f, -0.022f), new Vector3(0.012f, 0.006f, 0.012f), Quaternion.identity, accent);
        Part("MedicalCase", boat.transform, PrimitiveType.Cube, new Vector3(0.015f, 0.020f, -0.022f), new Vector3(0.011f, 0.007f, 0.012f), Quaternion.identity, hull);
        Part("MedicalCrossV", boat.transform, PrimitiveType.Cube, new Vector3(0.015f, 0.020f, -0.0282f), new Vector3(0.002f, 0.006f, 0.0008f), Quaternion.identity, navRed);
        Part("MedicalCrossH", boat.transform, PrimitiveType.Cube, new Vector3(0.015f, 0.020f, -0.0283f), new Vector3(0.006f, 0.002f, 0.0008f), Quaternion.identity, navRed);
        MeshPart("RopeCoil", boat.transform, CreateTorusMesh(0.0048f, 0.0008f, 20, 6), new Vector3(-0.016f, 0.024f, -0.018f), Vector3.one, Quaternion.Euler(90f, 0f, 0f), metal);
        Part("ThermalCamera", boat.transform, PrimitiveType.Sphere, new Vector3(-0.009f, 0.038f, -0.008f), new Vector3(0.0032f, 0.0032f, 0.004f), Quaternion.identity, dark);
        Part("CameraLens", boat.transform, PrimitiveType.Sphere, new Vector3(-0.009f, 0.038f, -0.0045f), new Vector3(0.0018f, 0.0018f, 0.001f), Quaternion.identity, glass);
        return boat;
    }

    // ------------------------------------------------------------- Base station

    public static GameObject CreateBaseStation(Transform parent, Material platform, Material trim,
        Material cabin, Material glass, Material metal, Material solar)
    {
        GameObject root = new GameObject("BaseStation_22cm_x_15cm");
        root.transform.SetParent(parent, false);
        BoxCollider collider = root.AddComponent<BoxCollider>();
        collider.center = new Vector3(0f, 0.025f, 0f);
        collider.size = new Vector3(0.22f, 0.05f, 0.15f);
        // Geometry-only dock: a solid collider here would block the physics
        // boats, which launch from its corners.
        collider.isTrigger = true;

        if (AttachBlockout("BaseStation_Blockout", root.transform, 0.35f, Vector3.zero) != null)
        {
            AttachBlockout("RaspberryPi_Blockout", root.transform, 0.35f, new Vector3(0.040f, 0.116f, -0.010f));
            Transform cameraParent = parent != null ? parent : root.transform;
            if (FindDescendant(cameraParent, "BlenderBlockout_OverheadCamera_Blockout") == null)
                AttachBlockout("OverheadCamera_Blockout", cameraParent, 0.35f, new Vector3(0f, 0.379f, 0.070f));
            return root;
        }

        // Four recessed launch bays make the vessels read as stored inside the
        // station instead of merely parked beside it. Boats sit over these
        // dark wells and leave through the nearest outside corner.
        Vector3[] bayCenters =
        {
            new Vector3(-0.118f, -0.0015f, -0.040f),
            new Vector3(-0.118f, -0.0015f,  0.040f),
            new Vector3( 0.118f, -0.0015f, -0.040f),
            new Vector3( 0.118f, -0.0015f,  0.040f)
        };

        // ---- Floating hull: skirt, pontoons and rubber fenders -------------
        Part("HullSkirt", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.012f, 0f), new Vector3(0.214f, 0.018f, 0.144f), Quaternion.identity, platform);
        Part("PontoonLeft", root.transform, PrimitiveType.Cylinder, new Vector3(-0.088f, -0.006f, 0f), new Vector3(0.009f, 0.115f, 0.009f), Quaternion.Euler(90f, 0f, 0f), metal);
        Part("PontoonRight", root.transform, PrimitiveType.Cylinder, new Vector3(0.088f, -0.006f, 0f), new Vector3(0.009f, 0.115f, 0.009f), Quaternion.Euler(90f, 0f, 0f), metal);
        Part("PontoonCapLF", root.transform, PrimitiveType.Cylinder, new Vector3(-0.088f, -0.006f, 0.058f), new Vector3(0.0096f, 0.008f, 0.0096f), Quaternion.identity, trim);
        Part("PontoonCapLB", root.transform, PrimitiveType.Cylinder, new Vector3(-0.088f, -0.006f, -0.058f), new Vector3(0.0096f, 0.008f, 0.0096f), Quaternion.identity, trim);
        Part("PontoonCapRF", root.transform, PrimitiveType.Cylinder, new Vector3(0.088f, -0.006f, 0.058f), new Vector3(0.0096f, 0.008f, 0.0096f), Quaternion.identity, trim);
        Part("PontoonCapRB", root.transform, PrimitiveType.Cylinder, new Vector3(0.088f, -0.006f, -0.058f), new Vector3(0.0096f, 0.008f, 0.0096f), Quaternion.identity, trim);

        for (int i = 0; i < 3; i++)
        {
            float z = -0.05f + i * 0.05f;
            Part("FenderL" + i, root.transform, PrimitiveType.Cylinder, new Vector3(-0.109f, 0.014f, z), new Vector3(0.007f, 0.014f, 0.007f), Quaternion.identity, platform);
            Part("FenderR" + i, root.transform, PrimitiveType.Cylinder, new Vector3(0.109f, 0.014f, z), new Vector3(0.007f, 0.014f, 0.007f), Quaternion.identity, platform);
        }
        Part("CornerFenderLF", root.transform, PrimitiveType.Cylinder, new Vector3(-0.104f, 0.020f, 0.066f), new Vector3(0.010f, 0.020f, 0.010f), Quaternion.identity, trim);
        Part("CornerFenderLB", root.transform, PrimitiveType.Cylinder, new Vector3(-0.104f, 0.020f, -0.066f), new Vector3(0.010f, 0.020f, 0.010f), Quaternion.identity, trim);
        Part("CornerFenderRF", root.transform, PrimitiveType.Cylinder, new Vector3(0.104f, 0.020f, 0.066f), new Vector3(0.010f, 0.020f, 0.010f), Quaternion.identity, trim);
        Part("CornerFenderRB", root.transform, PrimitiveType.Cylinder, new Vector3(0.104f, 0.020f, -0.066f), new Vector3(0.010f, 0.020f, 0.010f), Quaternion.identity, trim);

        // ---- Deck: light planking, orange edge band, bollards, cleats ------
        Part("MainDeck", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.021f, 0f), new Vector3(0.216f, 0.005f, 0.146f), Quaternion.identity, cabin);
        for (int i = 0; i < bayCenters.Length; i++)
        {
            Part("LaunchBay_" + (i + 1), root.transform, PrimitiveType.Cube, bayCenters[i], new Vector3(0.075f, 0.0015f, 0.056f), Quaternion.identity, platform);
            Part("BayGuide_" + (i + 1), root.transform, PrimitiveType.Cube,
                bayCenters[i] + new Vector3(i < 2 ? -0.027f : 0.027f, 0.0012f, 0f),
                new Vector3(0.0025f, 0.002f, 0.065f), Quaternion.identity, trim);
        }
        for (int i = 0; i < 4; i++)
        {
            float x = -0.06f + i * 0.04f;
            Part("DeckPlank" + i, root.transform, PrimitiveType.Cube, new Vector3(x, 0.0237f, 0f), new Vector3(0.002f, 0.0008f, 0.136f), Quaternion.identity, platform);
        }
        Part("EdgeBandFront", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.027f, 0.072f), new Vector3(0.220f, 0.003f, 0.004f), Quaternion.identity, trim);
        Part("EdgeBandBack", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.027f, -0.072f), new Vector3(0.220f, 0.003f, 0.004f), Quaternion.identity, trim);
        Part("EdgeBandLeft", root.transform, PrimitiveType.Cube, new Vector3(-0.108f, 0.027f, 0f), new Vector3(0.004f, 0.003f, 0.144f), Quaternion.identity, trim);
        Part("EdgeBandRight", root.transform, PrimitiveType.Cube, new Vector3(0.108f, 0.027f, 0f), new Vector3(0.004f, 0.003f, 0.144f), Quaternion.identity, trim);

        Part("BollardLF", root.transform, PrimitiveType.Cylinder, new Vector3(-0.100f, 0.033f, 0.062f), new Vector3(0.008f, 0.012f, 0.008f), Quaternion.identity, metal);
        Part("BollardLB", root.transform, PrimitiveType.Cylinder, new Vector3(-0.100f, 0.033f, -0.062f), new Vector3(0.008f, 0.012f, 0.008f), Quaternion.identity, metal);
        Part("BollardRF", root.transform, PrimitiveType.Cylinder, new Vector3(0.100f, 0.033f, 0.062f), new Vector3(0.008f, 0.012f, 0.008f), Quaternion.identity, metal);
        Part("BollardRB", root.transform, PrimitiveType.Cylinder, new Vector3(0.100f, 0.033f, -0.062f), new Vector3(0.008f, 0.012f, 0.008f), Quaternion.identity, metal);
        Part("CleatLF", root.transform, PrimitiveType.Cube, new Vector3(-0.111f, 0.030f, 0.030f), new Vector3(0.008f, 0.003f, 0.014f), Quaternion.identity, metal);
        Part("CleatLB", root.transform, PrimitiveType.Cube, new Vector3(-0.111f, 0.030f, -0.030f), new Vector3(0.008f, 0.003f, 0.014f), Quaternion.identity, metal);
        Part("CleatRF", root.transform, PrimitiveType.Cube, new Vector3(0.111f, 0.030f, 0.030f), new Vector3(0.008f, 0.003f, 0.014f), Quaternion.identity, metal);
        Part("CleatRB", root.transform, PrimitiveType.Cube, new Vector3(0.111f, 0.030f, -0.030f), new Vector3(0.008f, 0.003f, 0.014f), Quaternion.identity, metal);

        // ---- Perimeter railing --------------------------------------------
        for (int i = -2; i <= 2; i++)
        {
            float x = i * 0.053f;
            Part("RailPostF" + (i + 2), root.transform, PrimitiveType.Cylinder, new Vector3(x, 0.043f, 0.070f), new Vector3(0.0024f, 0.016f, 0.0024f), Quaternion.identity, metal);
            Part("RailPostB" + (i + 2), root.transform, PrimitiveType.Cylinder, new Vector3(x, 0.043f, -0.070f), new Vector3(0.0024f, 0.016f, 0.0024f), Quaternion.identity, metal);
        }
        for (int i = -1; i <= 1; i++)
        {
            float z = i * 0.047f;
            Part("RailPostL" + (i + 1), root.transform, PrimitiveType.Cylinder, new Vector3(-0.106f, 0.043f, z), new Vector3(0.0024f, 0.016f, 0.0024f), Quaternion.identity, metal);
            Part("RailPostR" + (i + 1), root.transform, PrimitiveType.Cylinder, new Vector3(0.106f, 0.043f, z), new Vector3(0.0024f, 0.016f, 0.0024f), Quaternion.identity, metal);
        }
        Part("RailBarFront", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.051f, 0.070f), new Vector3(0.216f, 0.0024f, 0.0024f), Quaternion.identity, metal);
        Part("RailBarBack", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.051f, -0.070f), new Vector3(0.216f, 0.0024f, 0.0024f), Quaternion.identity, metal);
        Part("RailBarLeft", root.transform, PrimitiveType.Cube, new Vector3(-0.106f, 0.051f, 0f), new Vector3(0.0024f, 0.0024f, 0.144f), Quaternion.identity, metal);
        Part("RailBarRight", root.transform, PrimitiveType.Cube, new Vector3(0.106f, 0.051f, 0f), new Vector3(0.0024f, 0.0024f, 0.144f), Quaternion.identity, metal);

        // Life ring hung on the front railing.
        MeshPart("LifeRing", root.transform, CreateTorusMesh(0.0075f, 0.0022f), new Vector3(0.040f, 0.050f, 0.0712f), Vector3.one, Quaternion.identity, trim);

        // Boarding ladder on the front edge.
        Part("LadderRailL", root.transform, PrimitiveType.Cylinder, new Vector3(-0.012f, 0.013f, 0.074f), new Vector3(0.0016f, 0.028f, 0.0016f), Quaternion.identity, metal);
        Part("LadderRailR", root.transform, PrimitiveType.Cylinder, new Vector3(0.012f, 0.013f, 0.074f), new Vector3(0.0016f, 0.028f, 0.0016f), Quaternion.identity, metal);
        for (int i = 0; i < 3; i++)
            Part("LadderRung" + i, root.transform, PrimitiveType.Cylinder, new Vector3(0f, 0.004f + i * 0.007f, 0.074f), new Vector3(0.0012f, 0.025f, 0.0012f), Quaternion.Euler(90f, 0f, 0f), metal);

        // ---- Command center on a plinth with access steps ------------------
        GameObject command = new GameObject("CommandCenter");
        command.transform.SetParent(root.transform, false);
        command.transform.localPosition = new Vector3(0f, 0.051f, 0f);

        Part("Plinth", command.transform, PrimitiveType.Cube, Vector3.zero, new Vector3(0.106f, 0.024f, 0.082f), Quaternion.identity, platform);
        Part("Step1", command.transform, PrimitiveType.Cube, new Vector3(0f, -0.025f, 0.031f), new Vector3(0.070f, 0.006f, 0.028f), Quaternion.identity, platform);
        Part("Step2", command.transform, PrimitiveType.Cube, new Vector3(0f, -0.016f, 0.031f), new Vector3(0.058f, 0.006f, 0.024f), Quaternion.identity, platform);

        Part("Cabin", command.transform, PrimitiveType.Cube, new Vector3(0f, 0.033f, 0f), new Vector3(0.096f, 0.042f, 0.072f), Quaternion.identity, cabin);
        Part("FrontGlass", command.transform, PrimitiveType.Cube, new Vector3(0f, 0.037f, 0.0362f), new Vector3(0.078f, 0.022f, 0.0018f), Quaternion.identity, glass);
        Part("RearGlass", command.transform, PrimitiveType.Cube, new Vector3(0.024f, 0.037f, -0.0362f), new Vector3(0.030f, 0.020f, 0.0018f), Quaternion.identity, glass);
        Part("RearDoor", command.transform, PrimitiveType.Cube, new Vector3(-0.024f, 0.024f, -0.0362f), new Vector3(0.020f, 0.020f, 0.0016f), Quaternion.identity, platform);
        Part("DoorPane", command.transform, PrimitiveType.Cube, new Vector3(-0.024f, 0.029f, -0.0364f), new Vector3(0.012f, 0.010f, 0.0008f), Quaternion.identity, glass);
        Part("LeftGlass", command.transform, PrimitiveType.Cube, new Vector3(-0.0482f, 0.037f, 0f), new Vector3(0.0018f, 0.020f, 0.050f), Quaternion.identity, glass);
        Part("RightGlass", command.transform, PrimitiveType.Cube, new Vector3(0.0482f, 0.037f, 0f), new Vector3(0.0018f, 0.020f, 0.050f), Quaternion.identity, glass);
        for (int i = -1; i <= 1; i++)
            Part("Mullion" + (i + 1), command.transform, PrimitiveType.Cube, new Vector3(i * 0.026f, 0.037f, 0.0366f), new Vector3(0.003f, 0.023f, 0.0008f), Quaternion.identity, cabin);

        Part("Roof", command.transform, PrimitiveType.Cube, new Vector3(0f, 0.058f, 0f), new Vector3(0.110f, 0.006f, 0.086f), Quaternion.identity, trim);
        Part("RoofFasciaFront", command.transform, PrimitiveType.Cube, new Vector3(0f, 0.056f, 0.0438f), new Vector3(0.112f, 0.002f, 0.002f), Quaternion.identity, metal);
        Part("RoofFasciaBack", command.transform, PrimitiveType.Cube, new Vector3(0f, 0.056f, -0.0438f), new Vector3(0.112f, 0.002f, 0.002f), Quaternion.identity, metal);
        Part("RoofFasciaLeft", command.transform, PrimitiveType.Cube, new Vector3(-0.0558f, 0.056f, 0f), new Vector3(0.002f, 0.002f, 0.087f), Quaternion.identity, metal);
        Part("RoofFasciaRight", command.transform, PrimitiveType.Cube, new Vector3(0.0558f, 0.056f, 0f), new Vector3(0.002f, 0.002f, 0.087f), Quaternion.identity, metal);

        Part("RoofPostLF", command.transform, PrimitiveType.Cylinder, new Vector3(-0.048f, 0.065f, 0.036f), new Vector3(0.002f, 0.008f, 0.002f), Quaternion.identity, metal);
        Part("RoofPostLB", command.transform, PrimitiveType.Cylinder, new Vector3(-0.048f, 0.065f, -0.036f), new Vector3(0.002f, 0.008f, 0.002f), Quaternion.identity, metal);
        Part("RoofPostRF", command.transform, PrimitiveType.Cylinder, new Vector3(0.048f, 0.065f, 0.036f), new Vector3(0.002f, 0.008f, 0.002f), Quaternion.identity, metal);
        Part("RoofPostRB", command.transform, PrimitiveType.Cylinder, new Vector3(0.048f, 0.065f, -0.036f), new Vector3(0.002f, 0.008f, 0.002f), Quaternion.identity, metal);
        Part("RoofRailFront", command.transform, PrimitiveType.Cube, new Vector3(0f, 0.0695f, 0.036f), new Vector3(0.100f, 0.002f, 0.002f), Quaternion.identity, metal);
        Part("RoofRailBack", command.transform, PrimitiveType.Cube, new Vector3(0f, 0.0695f, -0.036f), new Vector3(0.100f, 0.002f, 0.002f), Quaternion.identity, metal);
        Part("RoofRailLeft", command.transform, PrimitiveType.Cube, new Vector3(-0.048f, 0.0695f, 0f), new Vector3(0.002f, 0.002f, 0.076f), Quaternion.identity, metal);
        Part("RoofRailRight", command.transform, PrimitiveType.Cube, new Vector3(0.048f, 0.0695f, 0f), new Vector3(0.002f, 0.002f, 0.076f), Quaternion.identity, metal);

        Part("SolarLF", command.transform, PrimitiveType.Cube, new Vector3(-0.026f, 0.064f, 0.014f), new Vector3(0.040f, 0.0022f, 0.024f), Quaternion.Euler(0f, 0f, 8f), solar);
        Part("SolarLB", command.transform, PrimitiveType.Cube, new Vector3(-0.026f, 0.064f, -0.014f), new Vector3(0.040f, 0.0022f, 0.024f), Quaternion.Euler(0f, 0f, 8f), solar);
        Part("SolarRF", command.transform, PrimitiveType.Cube, new Vector3(0.026f, 0.064f, 0.014f), new Vector3(0.040f, 0.0022f, 0.024f), Quaternion.Euler(0f, 0f, -8f), solar);
        Part("SolarRB", command.transform, PrimitiveType.Cube, new Vector3(0.026f, 0.064f, -0.014f), new Vector3(0.040f, 0.0022f, 0.024f), Quaternion.Euler(0f, 0f, -8f), solar);

        // ---- Radar, beacon, antennas and flag ------------------------------
        Part("RadarTower", root.transform, PrimitiveType.Cylinder, new Vector3(0f, 0.135f, 0f), new Vector3(0.006f, 0.060f, 0.006f), Quaternion.identity, metal);
        Part("RadarBraceL", root.transform, PrimitiveType.Cube, new Vector3(-0.020f, 0.115f, 0f), new Vector3(0.042f, 0.0016f, 0.0016f), Quaternion.Euler(0f, 0f, 35f), metal);
        Part("RadarBraceR", root.transform, PrimitiveType.Cube, new Vector3(0.020f, 0.115f, 0f), new Vector3(0.042f, 0.0016f, 0.0016f), Quaternion.Euler(0f, 0f, -35f), metal);
        Part("RadarDish", root.transform, PrimitiveType.Sphere, new Vector3(0f, 0.173f, 0f), new Vector3(0.040f, 0.007f, 0.020f), Quaternion.Euler(0f, 25f, 12f), cabin);
        Part("RadarFeedHorn", root.transform, PrimitiveType.Sphere, new Vector3(0f, 0.168f, 0.006f), Vector3.one * 0.004f, Quaternion.identity, metal);

        Part("BeaconMount", root.transform, PrimitiveType.Cylinder, new Vector3(0f, 0.184f, 0f), new Vector3(0.004f, 0.010f, 0.004f), Quaternion.identity, metal);
        GameObject beacon = Part("Beacon", root.transform, PrimitiveType.Sphere, new Vector3(0f, 0.194f, 0f), Vector3.one * 0.010f, Quaternion.identity, trim);
        beacon.AddComponent<BeaconFlasher>();

        Part("Antenna", root.transform, PrimitiveType.Cylinder, new Vector3(0.035f, 0.120f, -0.045f), new Vector3(0.0008f, 0.030f, 0.0008f), Quaternion.Euler(0f, 0f, 10f), metal);
        Part("Antenna2", root.transform, PrimitiveType.Cylinder, new Vector3(-0.045f, 0.120f, 0.040f), new Vector3(0.0008f, 0.030f, 0.0008f), Quaternion.Euler(0f, 0f, -10f), metal);

        Part("FlagPole", root.transform, PrimitiveType.Cylinder, new Vector3(0f, 0.135f, 0.060f), new Vector3(0.001f, 0.055f, 0.001f), Quaternion.identity, metal);
        Part("Flag", root.transform, PrimitiveType.Cube, new Vector3(0.0105f, 0.150f, 0.060f), new Vector3(0.020f, 0.013f, 0.0015f), Quaternion.identity, trim);
        Part("FlagFinial", root.transform, PrimitiveType.Sphere, new Vector3(0f, 0.164f, 0.060f), Vector3.one * 0.003f, Quaternion.identity, metal);

        for (int side = -1; side <= 1; side += 2)
        {
            Part(side < 0 ? "LeftDockPost" : "RightDockPost", root.transform, PrimitiveType.Cylinder, new Vector3(side * 0.105f, 0.048f, -0.045f), new Vector3(0.003f, 0.030f, 0.003f), Quaternion.identity, metal);
            Part(side < 0 ? "LeftDockLight" : "RightDockLight", root.transform, PrimitiveType.Sphere, new Vector3(side * 0.105f, 0.064f, -0.045f), Vector3.one * 0.010f, Quaternion.identity, trim);
        }

        // Side-dock gantries, guide lamps and service equipment make each
        // launch slot read as a real internal boat bay.
        for (int side = -1; side <= 1; side += 2)
        {
            for (int lane = -1; lane <= 1; lane += 2)
            {
                float z = lane * 0.040f;
                string prefix = (side < 0 ? "West" : "East") + (lane < 0 ? "South" : "North");
                Part(prefix + "GantryPostA", root.transform, PrimitiveType.Cylinder, new Vector3(side * 0.105f, 0.037f, z - 0.025f), new Vector3(0.0018f, 0.024f, 0.0018f), Quaternion.identity, metal);
                Part(prefix + "GantryPostB", root.transform, PrimitiveType.Cylinder, new Vector3(side * 0.105f, 0.037f, z + 0.025f), new Vector3(0.0018f, 0.024f, 0.0018f), Quaternion.identity, metal);
                Part(prefix + "GantryBeam", root.transform, PrimitiveType.Cube, new Vector3(side * 0.105f, 0.050f, z), new Vector3(0.003f, 0.003f, 0.054f), Quaternion.identity, trim);
                Part(prefix + "GuideLampA", root.transform, PrimitiveType.Sphere, new Vector3(side * 0.108f, 0.052f, z - 0.020f), Vector3.one * 0.0028f, Quaternion.identity, trim);
                Part(prefix + "GuideLampB", root.transform, PrimitiveType.Sphere, new Vector3(side * 0.108f, 0.052f, z + 0.020f), Vector3.one * 0.0028f, Quaternion.identity, trim);
            }
        }

        Part("DeckCranePedestal", root.transform, PrimitiveType.Cylinder, new Vector3(0.075f, 0.041f, 0f), new Vector3(0.008f, 0.020f, 0.008f), Quaternion.identity, metal);
        Part("DeckCraneBoom", root.transform, PrimitiveType.Cube, new Vector3(0.082f, 0.060f, 0.010f), new Vector3(0.004f, 0.004f, 0.040f), Quaternion.Euler(25f, 0f, 0f), trim);
        Part("DeckCraneHook", root.transform, PrimitiveType.Cylinder, new Vector3(0.082f, 0.047f, 0.028f), new Vector3(0.001f, 0.014f, 0.001f), Quaternion.identity, metal);
        Part("FuelCabinet", root.transform, PrimitiveType.Cube, new Vector3(-0.074f, 0.041f, 0f), new Vector3(0.024f, 0.030f, 0.030f), Quaternion.identity, platform);
        Part("FuelCabinetDoor", root.transform, PrimitiveType.Cube, new Vector3(-0.074f, 0.041f, 0.0155f), new Vector3(0.019f, 0.024f, 0.0015f), Quaternion.identity, trim);
        return root;
    }

    // ----------------------------------------------------------------- Person

    public static GameObject CreatePerson(string id, Vector3 position, Transform parent,
        Material skin, Material suit, Material vest)
    {
        GameObject root = new GameObject(id);
        root.transform.SetParent(parent, false);
        root.transform.position = position;

        if (AttachBlockout("Person_Blockout", root.transform, 1f, Vector3.zero) != null)
        {
            root.transform.localScale = Vector3.one * 0.17f;
            PersonMarker blockoutMarker = root.AddComponent<PersonMarker>();
            blockoutMarker.personId = id;
            blockoutMarker.onboardScale = 0.17f;
            return root;
        }

        // Correct rescue-scene scale: an adult is roughly one quarter of the
        // 7 cm vessel length, not the same length as the whole boat.
        root.transform.localScale = Vector3.one * 0.42f;

        // Float ring around the torso with rope tie points.
        MeshPart("FloatRing", root.transform, CreateTorusMesh(0.0052f, 0.0019f), new Vector3(0f, 0.006f, 0f), Vector3.one, Quaternion.Euler(90f, 0f, 0f), vest);
        Part("RingTieFront", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.0075f, 0.0052f), new Vector3(0.003f, 0.003f, 0.0015f), Quaternion.identity, suit);
        Part("RingTieBack", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.0075f, -0.0052f), new Vector3(0.003f, 0.003f, 0.0015f), Quaternion.identity, suit);

        // Torso reclining in the water.
        Part("Body", root.transform, PrimitiveType.Capsule, new Vector3(0f, 0.014f, 0f), new Vector3(0.010f, 0.013f, 0.010f), Quaternion.Euler(72f, 0f, 0f), suit);

        // Life vest: panels, collar, straps and whistle.
        Part("VestFront", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.017f, -0.001f), new Vector3(0.019f, 0.013f, 0.011f), Quaternion.Euler(72f, 0f, 0f), vest);
        Part("VestBack", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.0165f, 0.0015f), new Vector3(0.018f, 0.012f, 0.010f), Quaternion.Euler(72f, 0f, 0f), vest);
        MeshPart("VestCollar", root.transform, CreateTorusMesh(0.0045f, 0.0016f), new Vector3(0f, 0.0195f, 0.0095f), Vector3.one, Quaternion.Euler(90f, 0f, 0f), vest);
        Part("StrapLeft", root.transform, PrimitiveType.Cube, new Vector3(-0.0065f, 0.017f, -0.0005f), new Vector3(0.003f, 0.012f, 0.001f), Quaternion.Euler(72f, 0f, 0f), suit);
        Part("StrapRight", root.transform, PrimitiveType.Cube, new Vector3(0.0065f, 0.017f, -0.0005f), new Vector3(0.003f, 0.012f, 0.001f), Quaternion.Euler(72f, 0f, 0f), suit);
        Part("Whistle", root.transform, PrimitiveType.Sphere, new Vector3(0.009f, 0.0195f, 0.004f), Vector3.one * 0.0018f, Quaternion.identity, suit);

        // Head, neck, hair and simple face. The extra silhouette and color
        // breaks make the figure recognizable from the simulation camera.
        Part("Neck", root.transform, PrimitiveType.Cylinder, new Vector3(0f, 0.021f, 0.008f), new Vector3(0.0038f, 0.0045f, 0.0038f), Quaternion.Euler(72f, 0f, 0f), skin);
        Part("Head", root.transform, PrimitiveType.Sphere, new Vector3(0f, 0.022f, 0.013f), Vector3.one * 0.011f, Quaternion.identity, skin);
        Part("Hair", root.transform, PrimitiveType.Sphere, new Vector3(0f, 0.027f, 0.0122f), new Vector3(0.0112f, 0.007f, 0.0112f), Quaternion.identity, suit);
        Part("EyeLeft", root.transform, PrimitiveType.Sphere, new Vector3(-0.0035f, 0.023f, 0.0232f), Vector3.one * 0.00115f, Quaternion.identity, suit);
        Part("EyeRight", root.transform, PrimitiveType.Sphere, new Vector3(0.0035f, 0.023f, 0.0232f), Vector3.one * 0.00115f, Quaternion.identity, suit);
        Part("Nose", root.transform, PrimitiveType.Sphere, new Vector3(0f, 0.0205f, 0.0238f), new Vector3(0.0012f, 0.0015f, 0.0012f), Quaternion.identity, skin);
        Part("EarLeft", root.transform, PrimitiveType.Sphere, new Vector3(-0.0102f, 0.022f, 0.013f), new Vector3(0.0016f, 0.0026f, 0.0012f), Quaternion.identity, skin);
        Part("EarRight", root.transform, PrimitiveType.Sphere, new Vector3(0.0102f, 0.022f, 0.013f), new Vector3(0.0016f, 0.0026f, 0.0012f), Quaternion.identity, skin);
        Part("Mouth", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.0178f, 0.0237f), new Vector3(0.0035f, 0.0007f, 0.0007f), Quaternion.identity, suit);
        Part("VestReflectiveBand", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.020f, -0.0062f), new Vector3(0.017f, 0.002f, 0.001f), Quaternion.Euler(72f, 0f, 0f), skin);
        Part("VestBuckle", root.transform, PrimitiveType.Cube, new Vector3(0f, 0.014f, -0.0065f), new Vector3(0.003f, 0.002f, 0.0012f), Quaternion.Euler(72f, 0f, 0f), suit);

        // Lower body remains partly submerged, but gives a coherent human
        // silhouette when the survivor is later scaled and placed on deck.
        Part("Hip", root.transform, PrimitiveType.Capsule, new Vector3(0f, 0.009f, -0.009f), new Vector3(0.008f, 0.008f, 0.008f), Quaternion.Euler(72f, 0f, 0f), suit);
        Part("LegLeft", root.transform, PrimitiveType.Cylinder, new Vector3(-0.005f, 0.006f, -0.020f), new Vector3(0.0035f, 0.012f, 0.0035f), Quaternion.Euler(72f, 0f, 8f), suit);
        Part("LegRight", root.transform, PrimitiveType.Cylinder, new Vector3(0.005f, 0.006f, -0.020f), new Vector3(0.0035f, 0.012f, 0.0035f), Quaternion.Euler(72f, 0f, -8f), suit);
        Part("BootLeft", root.transform, PrimitiveType.Capsule, new Vector3(-0.0065f, 0.003f, -0.031f), new Vector3(0.004f, 0.006f, 0.004f), Quaternion.Euler(72f, 0f, 8f), suit);
        Part("BootRight", root.transform, PrimitiveType.Capsule, new Vector3(0.0065f, 0.003f, -0.031f), new Vector3(0.004f, 0.006f, 0.004f), Quaternion.Euler(72f, 0f, -8f), suit);

        // Arms: left raised waving, right spread for balance; hands at the ends.
        Part("LeftArm", root.transform, PrimitiveType.Cylinder, new Vector3(-0.013f, 0.020f, 0.004f), new Vector3(0.0032f, 0.011f, 0.0032f), Quaternion.Euler(0f, 0f, 110f), skin);
        Part("RightArm", root.transform, PrimitiveType.Cylinder, new Vector3(0.013f, 0.015f, 0.005f), new Vector3(0.0032f, 0.011f, 0.0032f), Quaternion.Euler(0f, 0f, -60f), skin);
        Part("LeftHand", root.transform, PrimitiveType.Sphere, new Vector3(-0.0185f, 0.0265f, 0.004f), Vector3.one * 0.0038f, Quaternion.identity, skin);
        Part("RightHand", root.transform, PrimitiveType.Sphere, new Vector3(0.0185f, 0.0095f, 0.005f), Vector3.one * 0.0038f, Quaternion.identity, skin);

        PersonMarker marker = root.AddComponent<PersonMarker>();
        marker.personId = id;
        return root;
    }

    /// <summary>
    /// Adds the v8 detail layer to scenes generated by older versions without
    /// replacing or resaving the user's scene hierarchy.
    /// </summary>
    public static void EnhanceExistingScene()
    {
        if (InstallBlenderBlockouts())
            return;

        string[] ids = { "boat_1", "boat_2", "boat_3", "boat_4" };
        foreach (string id in ids)
        {
            GameObject boat = GameObject.Find(id);
            if (boat == null || FindDescendant(boat.transform, "ForedeckHatch") != null)
                continue;

            Material hull = MaterialOf(boat.transform, id, null);
            Material accent = MaterialOf(boat.transform, "DeckStripe", hull);
            Material dark = MaterialOf(boat.transform, "EngineCowl", hull);
            Material glass = MaterialOf(boat.transform, "FrontWindow", hull);
            Material metal = MaterialOf(boat.transform, "RadarMast", hull);
            Material white = MaterialOf(boat.transform, "MastheadLight", hull);

            Part("ForedeckHatch", boat.transform, PrimitiveType.Cube, new Vector3(0f, 0.016f, 0.020f), new Vector3(0.018f, 0.0018f, 0.014f), Quaternion.identity, dark);
            Part("HatchHandle", boat.transform, PrimitiveType.Cube, new Vector3(0f, 0.0174f, 0.020f), new Vector3(0.006f, 0.001f, 0.0012f), Quaternion.identity, metal);
            Part("BowRailLeft", boat.transform, PrimitiveType.Cylinder, new Vector3(-0.017f, 0.024f, 0.021f), new Vector3(0.0012f, 0.020f, 0.0012f), Quaternion.Euler(72f, 0f, -8f), metal);
            Part("BowRailRight", boat.transform, PrimitiveType.Cylinder, new Vector3(0.017f, 0.024f, 0.021f), new Vector3(0.0012f, 0.020f, 0.0012f), Quaternion.Euler(72f, 0f, 8f), metal);
            Part("BowPulpit", boat.transform, PrimitiveType.Cube, new Vector3(0f, 0.027f, 0.031f), new Vector3(0.026f, 0.0015f, 0.0015f), Quaternion.identity, metal);
            Part("SearchlightBody", boat.transform, PrimitiveType.Cylinder, new Vector3(0f, 0.019f, 0.028f), new Vector3(0.0045f, 0.006f, 0.0045f), Quaternion.Euler(90f, 0f, 0f), dark);
            Part("SearchlightLens", boat.transform, PrimitiveType.Sphere, new Vector3(0f, 0.020f, 0.032f), new Vector3(0.004f, 0.004f, 0.0018f), Quaternion.identity, white);
            Part("RescueBasket", boat.transform, PrimitiveType.Cube, new Vector3(-0.015f, 0.020f, -0.022f), new Vector3(0.012f, 0.006f, 0.012f), Quaternion.identity, accent);
            Part("MedicalCase", boat.transform, PrimitiveType.Cube, new Vector3(0.015f, 0.020f, -0.022f), new Vector3(0.011f, 0.007f, 0.012f), Quaternion.identity, hull);
            Part("ThermalCamera", boat.transform, PrimitiveType.Sphere, new Vector3(-0.009f, 0.038f, -0.008f), new Vector3(0.0032f, 0.0032f, 0.004f), Quaternion.identity, dark);
            Part("CameraLens", boat.transform, PrimitiveType.Sphere, new Vector3(-0.009f, 0.038f, -0.0045f), new Vector3(0.0018f, 0.0018f, 0.001f), Quaternion.identity, glass);
        }

        GameObject station = GameObject.Find("BaseStation_22cm_x_15cm");
        if (station != null && FindDescendant(station.transform, "DeckCranePedestal") == null)
        {
            Material platform = MaterialOf(station.transform, "HullSkirt", null);
            Material trim = MaterialOf(station.transform, "EdgeBandFront", platform);
            Material metal = MaterialOf(station.transform, "RadarTower", platform);
            Part("DeckCranePedestal", station.transform, PrimitiveType.Cylinder, new Vector3(0.075f, 0.041f, 0f), new Vector3(0.008f, 0.020f, 0.008f), Quaternion.identity, metal);
            Part("DeckCraneBoom", station.transform, PrimitiveType.Cube, new Vector3(0.082f, 0.060f, 0.010f), new Vector3(0.004f, 0.004f, 0.040f), Quaternion.Euler(25f, 0f, 0f), trim);
            Part("FuelCabinet", station.transform, PrimitiveType.Cube, new Vector3(-0.074f, 0.041f, 0f), new Vector3(0.024f, 0.030f, 0.030f), Quaternion.identity, platform);
            for (int side = -1; side <= 1; side += 2)
            {
                Part(side < 0 ? "WestDockHeader" : "EastDockHeader", station.transform, PrimitiveType.Cube,
                    new Vector3(side * 0.108f, 0.052f, 0f), new Vector3(0.003f, 0.003f, 0.140f), Quaternion.identity, trim);
            }
        }
    }

    private static bool InstallBlenderBlockouts()
    {
        if (Resources.Load<GameObject>("Models/Blockout/RescueBoat_Blockout") == null)
            return false;

        string[] ids = { "boat_1", "boat_2", "boat_3", "boat_4" };
        foreach (string id in ids)
        {
            GameObject boat = GameObject.Find(id);
            if (boat == null || FindDescendant(boat.transform, "BlenderBlockout_RescueBoat_Blockout") != null)
                continue;
            ClearVisualChildren(boat.transform);
            Renderer rootRenderer = boat.GetComponent<Renderer>();
            if (rootRenderer != null)
                rootRenderer.enabled = false;
            AttachBlockout("RescueBoat_Blockout", boat.transform, 0.23f, Vector3.zero);
        }

        GameObject station = GameObject.Find("BaseStation_22cm_x_15cm");
        if (station != null && FindDescendant(station.transform, "BlenderBlockout_BaseStation_Blockout") == null)
        {
            ClearVisualChildren(station.transform);
            Renderer rootRenderer = station.GetComponent<Renderer>();
            if (rootRenderer != null)
                rootRenderer.enabled = false;
            AttachBlockout("BaseStation_Blockout", station.transform, 0.35f, Vector3.zero);
            AttachBlockout("RaspberryPi_Blockout", station.transform, 0.35f, new Vector3(0.040f, 0.116f, -0.010f));
            Transform cameraParent = station.transform.parent != null ? station.transform.parent : station.transform;
            if (FindDescendant(cameraParent, "BlenderBlockout_OverheadCamera_Blockout") == null)
                AttachBlockout("OverheadCamera_Blockout", cameraParent, 0.35f, new Vector3(0f, 0.379f, 0.070f));
        }
        return true;
    }

    private static GameObject AttachBlockout(string resourceName, Transform parent, float scale, Vector3 localPosition)
    {
        GameObject prefab = Resources.Load<GameObject>("Models/Blockout/" + resourceName);
        if (prefab == null)
            return null;
        GameObject instance = Object.Instantiate(prefab, parent, false);
        // Unity stores Blender Z-up -> Unity Y-up correction on the imported
        // FBX root. Preserve it; forcing identity rotates the station sideways.
        Quaternion importedRotation = instance.transform.localRotation;
        Vector3 importedScale = instance.transform.localScale;
        if (resourceName == "RescueBoat_Blockout")
            importedRotation = Quaternion.Euler(0f, -90f, 0f) * importedRotation;
        instance.name = "BlenderBlockout_" + resourceName;
        instance.transform.localPosition = localPosition;
        instance.transform.localRotation = importedRotation;
        instance.transform.localScale = importedScale * scale;
        ApplyGameMaterials(instance);
        return instance;
    }

    private static void ApplyGameMaterials(GameObject root)
    {
        foreach (Renderer renderer in root.GetComponentsInChildren<Renderer>(true))
        {
            string name = renderer.gameObject.name.ToLowerInvariant();
            string key = "deck";
            Color color = new Color(0.38f, 0.44f, 0.47f);
            float metallic = 0.28f;
            float smoothness = 0.40f;
            if (name.Contains("vest") || name.Contains("collar") || name.Contains("lifering") || name.Contains("navlight") || name.Contains("safetystripe"))
            { key = "orange"; color = new Color(1f, 0.20f, 0.035f); metallic = 0.10f; smoothness = 0.42f; }
            else if (name.Contains("head") || name.Contains("hand"))
            { key = "skin"; color = new Color(0.62f, 0.34f, 0.22f); metallic = 0f; smoothness = 0.18f; }
            else if (name.Contains("person"))
            { key = "suit"; color = new Color(0.025f, 0.065f, 0.10f); metallic = 0.02f; smoothness = 0.22f; }
            else if (name.Contains("window") || name.Contains("windscreen") || name.Contains("lens"))
            { key = "glass"; color = new Color(0.025f, 0.16f, 0.22f); metallic = 0.18f; smoothness = 0.88f; }
            else if (name.Contains("rope"))
            { key = "rope"; color = new Color(0.32f, 0.21f, 0.10f); metallic = 0f; smoothness = 0.08f; }
            else if (name.Contains("raspberrypi_board"))
            { key = "pcb"; color = new Color(0.025f, 0.32f, 0.12f); metallic = 0.12f; smoothness = 0.32f; }
            else if (name.Contains("fender") || name.Contains("float") || name.Contains("seat") || name.Contains("console") || name.Contains("camera_housing"))
            { key = "rubber"; color = new Color(0.012f, 0.020f, 0.025f); metallic = 0.02f; smoothness = 0.20f; }
            else if (name.Contains("rail") || name.Contains("bollard") || name.Contains("mast") || name.Contains("engine") || name.Contains("mount"))
            { key = "metal"; color = new Color(0.29f, 0.34f, 0.38f); metallic = 0.86f; smoothness = 0.70f; }
            else if (name.Contains("rescueboat"))
            { key = "boat"; color = new Color(0.76f, 0.84f, 0.87f); metallic = 0.18f; smoothness = 0.62f; }
            else if (name.Contains("roof"))
            { key = "roof"; color = new Color(0.92f, 0.16f, 0.035f); metallic = 0.18f; smoothness = 0.50f; }
            renderer.sharedMaterial = GetRuntimeMaterial(key, color, metallic, smoothness);
        }
    }

    private static Material GetRuntimeMaterial(string key, Color color, float metallic, float smoothness)
    {
        if (RuntimeMaterials.TryGetValue(key, out Material material) && material != null)
            return material;
        Shader shader = Shader.Find("Universal Render Pipeline/Lit");
        if (shader == null)
            shader = Shader.Find("Standard");
        material = new Material(shader) { name = "Runtime_" + key };
        material.color = color;
        if (material.HasProperty("_Metallic")) material.SetFloat("_Metallic", metallic);
        if (material.HasProperty("_Smoothness")) material.SetFloat("_Smoothness", smoothness);
        RuntimeMaterials[key] = material;
        return material;
    }

    private static void ClearVisualChildren(Transform root)
    {
        for (int index = root.childCount - 1; index >= 0; index--)
        {
            GameObject child = root.GetChild(index).gameObject;
            if (Application.isPlaying)
                Object.Destroy(child);
            else
                Object.DestroyImmediate(child);
        }
    }

    private static Transform FindDescendant(Transform root, string objectName)
    {
        foreach (Transform child in root.GetComponentsInChildren<Transform>(true))
            if (child.name == objectName)
                return child;
        return null;
    }

    private static Material MaterialOf(Transform root, string objectName, Material fallback)
    {
        Transform target = FindDescendant(root, objectName);
        Renderer renderer = target != null ? target.GetComponent<Renderer>() : null;
        if (renderer == null && root.name == objectName)
            renderer = root.GetComponent<Renderer>();
        return renderer != null ? renderer.sharedMaterial : fallback;
    }

    // --------------------------------------------------------------- Hull mesh

    private static Mesh CreateHullMesh()
    {
        // Five stations, origin at calm waterline, bow toward +Z.
        // Triangle winding verified offline: every face normal points outward.
        Vector3[] vertices =
        {
            new Vector3(-0.02300f, 0.01400f, -0.03500f),
            new Vector3(0.02300f, 0.01400f, -0.03500f),
            new Vector3(-0.01900f, -0.00150f, -0.03500f),
            new Vector3(0.01900f, -0.00150f, -0.03500f),
            new Vector3(0.00000f, -0.00400f, -0.03500f),
            new Vector3(-0.02500f, 0.01400f, -0.01500f),
            new Vector3(0.02500f, 0.01400f, -0.01500f),
            new Vector3(-0.02100f, -0.00200f, -0.01500f),
            new Vector3(0.02100f, -0.00200f, -0.01500f),
            new Vector3(0.00000f, -0.00500f, -0.01500f),
            new Vector3(-0.02500f, 0.01400f, 0.00500f),
            new Vector3(0.02500f, 0.01400f, 0.00500f),
            new Vector3(-0.02100f, -0.00200f, 0.00500f),
            new Vector3(0.02100f, -0.00200f, 0.00500f),
            new Vector3(0.00000f, -0.00500f, 0.00500f),
            new Vector3(-0.01600f, 0.01300f, 0.02400f),
            new Vector3(0.01600f, 0.01300f, 0.02400f),
            new Vector3(-0.01100f, -0.00100f, 0.02400f),
            new Vector3(0.01100f, -0.00100f, 0.02400f),
            new Vector3(0.00000f, -0.00300f, 0.02400f),
            new Vector3(-0.00400f, 0.01200f, 0.03500f),
            new Vector3(0.00400f, 0.01200f, 0.03500f),
            new Vector3(-0.00250f, -0.00050f, 0.03500f),
            new Vector3(0.00250f, -0.00050f, 0.03500f),
            new Vector3(0.00000f, -0.00100f, 0.03500f)
        };
        int[] triangles =
        {
            0,6,1,
            0,5,6,
            0,2,7,
            0,7,5,
            1,8,3,
            1,6,8,
            2,4,9,
            2,9,7,
            3,9,4,
            3,8,9,
            5,11,6,
            5,10,11,
            5,7,12,
            5,12,10,
            6,13,8,
            6,11,13,
            7,9,14,
            7,14,12,
            8,14,9,
            8,13,14,
            10,16,11,
            10,15,16,
            10,12,17,
            10,17,15,
            11,18,13,
            11,16,18,
            12,14,19,
            12,19,17,
            13,19,14,
            13,18,19,
            15,21,16,
            15,20,21,
            15,17,22,
            15,22,20,
            16,23,18,
            16,21,23,
            17,19,24,
            17,24,22,
            18,24,19,
            18,23,24,
            0,1,3,
            0,3,4,
            0,4,2,
            20,23,21,
            20,24,23,
            20,22,24
        };

        Mesh mesh = new Mesh { name = "RescueBoatHull" };
        mesh.vertices = vertices;
        mesh.triangles = triangles;
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        return mesh;
    }

    // --------------------------------------------------------------- Torus mesh

    /// <summary>
    /// Unity's PrimitiveType has no Torus, so life rings are built procedurally.
    /// The ring lies in the X-Y plane facing +Z; rotate it for other attitudes.
    /// </summary>
    private static Mesh CreateTorusMesh(float outerRadius, float tubeRadius, int segments = 24, int tubeSegments = 8)
    {
        int vertexCount = (segments + 1) * (tubeSegments + 1);
        Vector3[] vertices = new Vector3[vertexCount];
        int[] triangles = new int[segments * tubeSegments * 6];

        int vi = 0;
        for (int i = 0; i <= segments; i++)
        {
            float theta = (float)i / segments * Mathf.PI * 2f;
            float cosT = Mathf.Cos(theta);
            float sinT = Mathf.Sin(theta);
            Vector3 center = new Vector3(cosT * outerRadius, sinT * outerRadius, 0f);
            for (int j = 0; j <= tubeSegments; j++)
            {
                float phi = (float)j / tubeSegments * Mathf.PI * 2f;
                vertices[vi++] = center + new Vector3(Mathf.Cos(phi) * cosT, Mathf.Cos(phi) * sinT, Mathf.Sin(phi)) * tubeRadius;
            }
        }

        int ti = 0;
        int stride = tubeSegments + 1;
        for (int i = 0; i < segments; i++)
        {
            for (int j = 0; j < tubeSegments; j++)
            {
                int a = i * stride + j;
                int b = (i + 1) * stride + j;
                int c = (i + 1) * stride + j + 1;
                int d = i * stride + j + 1;
                triangles[ti++] = a; triangles[ti++] = c; triangles[ti++] = b;
                triangles[ti++] = a; triangles[ti++] = d; triangles[ti++] = c;
            }
        }

        Mesh mesh = new Mesh { name = "LifeRingTorus" };
        mesh.vertices = vertices;
        mesh.triangles = triangles;
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        return mesh;
    }

    // ---------------------------------------------------------------- Helpers

    private static GameObject Part(string name, Transform parent, PrimitiveType primitive,
        Vector3 localPosition, Vector3 localScale, Quaternion localRotation, Material material)
    {
        GameObject part = GameObject.CreatePrimitive(primitive);
        part.name = name;
        part.transform.SetParent(parent, false);
        part.transform.localPosition = localPosition;
        part.transform.localRotation = localRotation;
        part.transform.localScale = localScale;
        Collider partCollider = part.GetComponent<Collider>();
        if (partCollider != null)
        {
            if (Application.isPlaying)
                Object.Destroy(partCollider);
            else
                Object.DestroyImmediate(partCollider);
        }
        part.GetComponent<Renderer>().sharedMaterial = material;
        return part;
    }

    /// <summary>Builds a part from a custom mesh (no collider, renderer only).</summary>
    private static GameObject MeshPart(string name, Transform parent, Mesh mesh,
        Vector3 localPosition, Vector3 localScale, Quaternion localRotation, Material material)
    {
        GameObject part = new GameObject(name);
        part.transform.SetParent(parent, false);
        part.transform.localPosition = localPosition;
        part.transform.localRotation = localRotation;
        part.transform.localScale = localScale;
        MeshFilter meshFilter = part.AddComponent<MeshFilter>();
        meshFilter.sharedMesh = mesh;
        MeshRenderer meshRenderer = part.AddComponent<MeshRenderer>();
        meshRenderer.sharedMaterial = material;
        return part;
    }
}

/// <summary>Pulses the beacon light emission on its own material instance.</summary>
public class BeaconFlasher : MonoBehaviour
{
    public Color emissionColor = new Color(1f, 0.08f, 0.02f);
    public float flashSpeed = 2.6f;

    private Material instanceMaterial;

    private void Awake()
    {
        Renderer cachedRenderer = GetComponent<Renderer>();
        if (cachedRenderer != null)
        {
            instanceMaterial = cachedRenderer.material;
            instanceMaterial.EnableKeyword("_EMISSION");
        }
    }

    private void Update()
    {
        if (instanceMaterial == null)
            return;
        float pulse = 0.25f + 0.75f * Mathf.Pow(Mathf.Max(0f, Mathf.Sin(Time.time * Mathf.PI * flashSpeed)), 2f);
        instanceMaterial.SetColor("_EmissionColor", emissionColor * pulse);
    }
}
