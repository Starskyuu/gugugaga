using UnityEngine;
namespace RescueSim
{
    // A one-gram, upright person with a buoyancy aid. This is a simplified
    // flotation proxy, not a human physiology or articulated-body simulation.
    [RequireComponent(typeof(Rigidbody),typeof(CapsuleCollider))]
    public sealed class RescueVictim:MonoBehaviour
    {
        public enum RescueState { Water, Boarding, Onboard, Disembarking, Rescued }
        public RescueState state;
        public int carrier=-1;
        public int refugeSeat=-1;
        public bool InWater=>state==RescueState.Water||state==RescueState.Boarding;
        public bool Locked=>state==RescueState.Boarding;
        public int personId;
        [Range(0,2)] public int urgency;
        public WaterField water;
        public float waitingSeconds;
        public int assignedBoat=-1;
        public Rigidbody Body {get; private set;}
        public Vector3 spawn;
        public string Status => state==RescueState.Water?(assignedBoat<0?"WAITING":"ASSIGNED B"+(assignedBoat+1)):state.ToString().ToUpperInvariant()+(carrier>=0?" B"+(carrier+1):"");
        public float Priority => urgency*100+Mathf.Min(waitingSeconds/10,90);
        public void Initialize()
        {
            if(Body)return;
            Body=GetComponent<Rigidbody>();Body.mass=.001f;Body.useGravity=true;
            Body.constraints=RigidbodyConstraints.FreezeRotation;
            Body.linearDamping=0;Body.angularDamping=0;Body.sleepThreshold=0;
            Body.interpolation=RigidbodyInterpolation.Interpolate;Body.collisionDetectionMode=CollisionDetectionMode.ContinuousDynamic;
            var c=GetComponent<CapsuleCollider>();c.radius=.0045f;c.height=.022f;c.contactOffset=.0001f;
        }
        void Awake(){Initialize();}
        public void ApplyForces(float dt)
        {
            Initialize();if(!InWater)return;waitingSeconds+=dt;if(!water||Body.isKinematic)return;
            float wet=water.HasWater(Body.position)?Mathf.Clamp01(.5f+(water.level-Body.position.y)/.022f):0;
            Body.AddForce(Vector3.up*(water.density*-Physics.gravity.y*.0000016f*wet));
            Vector3 relative=Body.linearVelocity-water.VelocityAt(Body.position);
            Body.AddForce(-relative*(.003f+.03f*relative.magnitude)*wet);
        }
        public void ResetPerson()
        {
            gameObject.SetActive(true);Initialize();state=RescueState.Water;carrier=-1;refugeSeat=-1;Body.isKinematic=false;GetComponent<Collider>().enabled=true;assignedBoat=-1;waitingSeconds=0;
            Body.position=new Vector3(spawn.x,water.level-.00275f,spawn.z);
            Body.rotation=Quaternion.identity;Body.linearVelocity=Body.angularVelocity=Vector3.zero;Body.WakeUp();
        }
    }
}
