using System;
using UnityEngine;

namespace RescueSim
{
    [Serializable] public struct VolumeCell { public Vector3 position; public float volume; }
    [Serializable] public struct MassPart { public string name; public float mass; public Vector3 position, size; }
    [Serializable] public class HydroData { public VolumeCell[] samples; public Vector3 cellSize; public float sealedVolume; public MassPart[] massParts; }

    [CreateAssetMenu(menuName = "Rescue/Boat Profile")]
    public sealed class BoatProfile : ScriptableObject
    {
        public TextAsset hydrostatics;
        public float hullLength = .07f, hullBeam = .05f, sealedHeight = .009f;
        public Vector3 linearDrag = new Vector3(.015f, .12f, .01f);
        public Vector3 quadraticCd = new Vector3(1.1f, .9f, .7f);
        public Vector3 referenceArea = new Vector3(.00035f, .003f, .00025f);
        public Vector3 angularDrag = new Vector3(.00018f, .00006f, .00018f);
        public float propellerDiameter = .0086f, thrustCoefficient = .18f, maximumRpm = 2600f, motorResponse = .12f;
        public Vector3 portMount = new Vector3(-.0135f, .0038f, -.0388f);
        public Vector3 starboardMount = new Vector3(.0135f, .0038f, -.0388f);
        public float personMass = .001f;
        public string parameterStatus = "Estimated model mass, inertia and water coefficients; not experimentally calibrated.";
        public HydroData Read() => JsonUtility.FromJson<HydroData>(hydrostatics.text);
    }
}
