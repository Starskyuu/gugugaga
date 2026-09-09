using UnityEngine;
namespace RescueSim
{
    [RequireComponent(typeof(Rigidbody))]
    public sealed class FloatingDebris:MonoBehaviour
    {
        public WaterField water;public Vector3 size=new Vector3(.024f,.012f,.018f);
        public float materialDensity=350;
        public Rigidbody Body{get;private set;}
        public void Initialize()
        {
            if(Body)return;Body=GetComponent<Rigidbody>();Body.mass=materialDensity*size.x*size.y*size.z;
            Body.linearDamping=Body.angularDamping=0;Body.sleepThreshold=0;Body.interpolation=RigidbodyInterpolation.Interpolate;Body.collisionDetectionMode=CollisionDetectionMode.ContinuousDynamic;
        }
        void Awake(){Initialize();}
        public void ApplyForces()
        {
            Initialize();if(!water)return;
            float cellVolume=size.x*size.y*size.z/8;
            float height=Mathf.Abs((Body.rotation*Vector3.right).y)*size.x/2+Mathf.Abs((Body.rotation*Vector3.up).y)*size.y/2+Mathf.Abs((Body.rotation*Vector3.forward).y)*size.z/2;
            float wet=0;
            for(int x=-1;x<=1;x+=2)for(int y=-1;y<=1;y+=2)for(int z=-1;z<=1;z+=2)
            {
                Vector3 p=Body.position+Body.rotation*Vector3.Scale(size,new Vector3(x,y,z)*.25f);
                float f=water.HasWater(p)?Mathf.Clamp01(.5f+(water.level-p.y)/Mathf.Max(height,1e-6f)):0;wet+=f/8;
                Body.AddForceAtPosition(Vector3.up*(water.density*9.81f*cellVolume*f),p);
            }
            // Isotropic drag for simple rigid floating crates (not a fluid body).
            Vector3 relative=Body.linearVelocity-water.VelocityAt(Body.position);
            Body.AddForce(-relative*(.006f+.12f*relative.magnitude)*wet);
            Body.AddTorque(-Body.angularVelocity*.0000008f*wet);
        }
        public void ResetAt(Vector3 p){Initialize();Body.position=p;Body.rotation=Quaternion.identity;Body.linearVelocity=Body.angularVelocity=Vector3.zero;Body.WakeUp();}
    }
}
