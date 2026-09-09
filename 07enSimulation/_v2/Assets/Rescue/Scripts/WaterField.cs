using System;
using UnityEngine;
namespace RescueSim
{
    public sealed class WaterField : MonoBehaviour
    {
        [Serializable] public class FlowZone
        {
            public string name; public Vector3 center,size,velocity; public float feather=.025f;
            public float Weight(Vector3 p) => Mathf.Clamp01(Mathf.Min(size.x*.5f-Mathf.Abs(p.x-center.x),size.z*.5f-Mathf.Abs(p.z-center.z))/Mathf.Max(.0001f,feather));
        }
        [Serializable] public class BedZone
        {
            public string name;public Vector3 center,size;public float height;
            public bool Contains(Vector3 p)=>Mathf.Abs(p.x-center.x)<=size.x*.5f&&Mathf.Abs(p.z-center.z)<=size.z*.5f;
        }
        public float level = 0, density = 1000, bottom = -.025f;
        public Vector3 current = Vector3.zero;
        public bool bounded;
        public Vector3 boundsCenter, boundsSize=new Vector3(1.2f,0,1.2f);
        public FlowZone[] flowZones=Array.Empty<FlowZone>();
        public BedZone[] bedZones=Array.Empty<BedZone>();
        public bool regionalFlow=true;
        [Range(0,2)]public float regionalStrength=1;
        public float SurfaceAt(Vector3 point) => level;
        public bool HasWater(Vector3 p)=> (!bounded || (Mathf.Abs(p.x-boundsCenter.x)<=boundsSize.x*.5f&&Mathf.Abs(p.z-boundsCenter.z)<=boundsSize.z*.5f))&&level>BottomAt(p);
        public float BottomAt(Vector3 p){float h=bottom;foreach(var z in bedZones)if(z.Contains(p))h=Mathf.Max(h,z.height);return h;}
        public float DepthAt(Vector3 p)=>HasWater(p)?Mathf.Max(0,level-BottomAt(p)):0;
        public Vector3 VelocityAt(Vector3 point)
        {
            if(!HasWater(point))return Vector3.zero;
            Vector3 v=current;if(regionalFlow)foreach(var z in flowZones)v+=z.velocity*z.Weight(point)*regionalStrength;
            return v;
        }
    }
}
