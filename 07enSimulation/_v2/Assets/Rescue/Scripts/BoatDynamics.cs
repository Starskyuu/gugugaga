using System;
using System.Collections.Generic;
using UnityEngine;

namespace RescueSim
{
    [RequireComponent(typeof(Rigidbody))]
    public sealed class BoatDynamics : MonoBehaviour
    {
        public BoatProfile profile;
        public WaterField water;
        public Transform portRotor, starboardRotor;
        public GameObject seatedPersonPrefab;
        [Range(-1,1)] public float portCommand, starboardCommand;
        public bool manualStepping;
        public Rigidbody Body { get; private set; }
        public float PortRpm { get; private set; }
        public float StarboardRpm { get; private set; }
        public float PortThrust { get; private set; }
        public float StarboardThrust { get; private set; }
        public float DisplacedVolume { get; private set; }
        public float Buoyancy { get; private set; }
        public float Draft => water ? water.level - Body.position.y : 0;
        public int Passengers { get; private set; }
        public int CollisionCount { get; private set; }
        public float LastCollisionImpulse { get; private set; }
        public bool Grounded { get; private set; }
        public bool Capsized => Vector3.Dot(Body.rotation*Vector3.up,Vector3.up)<0;
        public bool DeckEdgeSubmerged { get; private set; }
        public float TiltDegrees => Vector3.Angle(Body.rotation*Vector3.up,Vector3.up);
        public HydroData Data { get; private set; }
        readonly List<GameObject> passengers = new List<GameObject>();
        Quaternion portRest, starboardRest;
        double portAngle,starboardAngle;
        static readonly Vector3[] Seats = {
            new Vector3(-.015f,.00735f,-.002f),new Vector3(.015f,.00735f,-.002f),
            new Vector3(-.015f,.00735f,.0155f),new Vector3(.015f,.00735f,.0155f),
            new Vector3(-.015f,.00735f,-.0195f),new Vector3(.015f,.00735f,-.0195f)};

        void Awake() { if (enabled && profile) Initialize(); }
        public void Initialize()
        {
            if (Data!=null) return;
            Body=GetComponent<Rigidbody>(); Data=profile.Read();
            Body.useGravity=true; Body.isKinematic=false; Body.linearDamping=0; Body.angularDamping=0;
            Body.maxAngularVelocity=30; Body.maxDepenetrationVelocity=.3f;
            Body.sleepThreshold=0; Body.interpolation=RigidbodyInterpolation.Interpolate;
            Body.collisionDetectionMode=CollisionDetectionMode.ContinuousDynamic;
            Body.solverIterations=16; Body.solverVelocityIterations=8;
            BindRotorGeometry("Rotor_Port",portRotor);
            BindRotorGeometry("Rotor_Starboard",starboardRotor);
            portRest=portRotor ? portRotor.localRotation : Quaternion.identity;
            starboardRest=starboardRotor ? starboardRotor.localRotation : Quaternion.identity;
            ApplyMass();
        }
        void FixedUpdate()
        {
            // Normally the shared clock calls this immediately before each
            // PhysX substep. This fallback supports prefab use with FixedUpdate.
            if (!manualStepping && Physics.simulationMode==SimulationMode.FixedUpdate) ApplyForces(Time.fixedDeltaTime);
        }
        public void SetPassengerCount(int count, bool visuals=true)
        {
            Initialize(); count=Mathf.Clamp(count,0,6); Passengers=count;ApplyMass();
            if (!visuals) return;
            foreach(var p in passengers) if(p) {p.SetActive(false); if(Application.isPlaying) Destroy(p);else DestroyImmediate(p);}
            passengers.Clear();
            if(!seatedPersonPrefab) return;
            for(int i=0;i<count;i++)
            {
                var person=Instantiate(seatedPersonPrefab,transform);person.name="Payload_Passenger_"+(i+1);
                person.transform.localPosition=Seats[i];person.transform.localRotation=Quaternion.identity;
                passengers.Add(person);
            }
        }
        void ApplyMass()
        {
            var parts=new List<MassPart>(Data.massParts);
            for(int i=0;i<Passengers;i++) parts.Add(new MassPart {name="Passenger_"+i,mass=profile.personMass,
                position=new Vector3(Seats[i].x,.021f,Seats[i].z+.002f),size=new Vector3(.008f,.018f,.009f)});
            MassProperties.Calculate(parts,out float m,out Vector3 com,out Vector3 inertia,out Quaternion rotation);
            // Rigidbody origin does not move when COM changes. Match a gently
            // attached payload's velocity field at the new combined COM.
            Vector3 old=Body.worldCenterOfMass;
            Body.mass=m;Body.centerOfMass=com;Body.inertiaTensor=inertia;Body.inertiaTensorRotation=rotation;
            Body.linearVelocity+=Vector3.Cross(Body.angularVelocity,Body.worldCenterOfMass-old);
            Body.WakeUp();
        }
        public void ApplyForces(float dt)
        {
            Initialize(); if(!water || Body.isKinematic) return;
            Quaternion rotation=Body.rotation; Vector3 origin=Body.position, up=rotation*Vector3.up;
            Vector3 axisX=rotation*Vector3.right,axisZ=rotation*Vector3.forward;
            float extent=Mathf.Max(1e-7f,Mathf.Abs(axisX.y)*Data.cellSize.x+Mathf.Abs(up.y)*Data.cellSize.y+Mathf.Abs(axisZ.y)*Data.cellSize.z);
            float volume=0;Vector3 firstMoment=Vector3.zero;
            foreach(var cell in Data.samples)
            {
                Vector3 arm=rotation*cell.position;Vector3 point=origin+arm;
                float displaced=water.HasWater(point)?cell.volume*Mathf.Clamp01(.5f+(water.SurfaceAt(point)-point.y)/extent):0;
                volume+=displaced;firstMoment+=arm*displaced;
            }
            DisplacedVolume=volume;Buoyancy=water.density*(-Physics.gravity.y)*volume;
            if(volume>1e-12f) Body.AddForceAtPosition(Vector3.up*Buoyancy,origin+firstMoment/volume,ForceMode.Force);
            float wet=Mathf.Clamp01(volume/Data.sealedVolume);
            Vector3 relative=Quaternion.Inverse(rotation)*(Body.linearVelocity-water.VelocityAt(Body.worldCenterOfMass));
            Vector3 force=Vector3.zero;
            for(int i=0;i<3;i++) force[i]=(-profile.linearDrag[i]*relative[i]-.5f*water.density*profile.quadraticCd[i]*profile.referenceArea[i]*Mathf.Abs(relative[i])*relative[i])*wet;
            Body.AddForce(rotation*force,ForceMode.Force);
            Vector3 angular=Quaternion.Inverse(rotation)*Body.angularVelocity;
            Body.AddTorque(rotation*(-Vector3.Scale(profile.angularDrag,angular))*wet,ForceMode.Force);
            float response=1-Mathf.Exp(-dt/Mathf.Max(.001f,profile.motorResponse));
            PortRpm=Mathf.Lerp(PortRpm,Mathf.Clamp(portCommand,-1,1)*profile.maximumRpm,response);
            StarboardRpm=Mathf.Lerp(StarboardRpm,Mathf.Clamp(starboardCommand,-1,1)*profile.maximumRpm,response);
            PortThrust=PropellerForce(PortRpm,profile.portMount);StarboardThrust=PropellerForce(StarboardRpm,profile.starboardMount);
            portAngle+=PortRpm*6.0*dt;starboardAngle-=StarboardRpm*6.0*dt;
            float minEdge=float.MaxValue;
            foreach(var corner in new[]{new Vector3(-.022f,.009f,-.03f),new Vector3(.022f,.009f,-.03f),new Vector3(-.022f,.009f,.022f),new Vector3(.022f,.009f,.022f)})
                minEdge=Mathf.Min(minEdge,(origin+rotation*corner).y-water.level);
            DeckEdgeSubmerged=minEdge<0;
            float lowest=origin.y;
            foreach(var point in new[]{new Vector3(-.0135f,-.0014f,-.0383f),new Vector3(.0135f,-.0014f,-.0383f),new Vector3(-.0195f,0,.027f),new Vector3(.0195f,0,.027f)})
                lowest=Mathf.Min(lowest,(origin+rotation*point).y);
            Grounded=lowest-water.BottomAt(origin)<.0006f;
        }
        float PropellerForce(float rpm,Vector3 localMount)
        {
            Vector3 point=Body.position+Body.rotation*localMount;
            float d=profile.propellerDiameter;
            float immersion=water.HasWater(point)?Mathf.Clamp01((water.SurfaceAt(point)-point.y+d*.5f)/d):0;
            float n=rpm/60;float thrust=water.density*profile.thrustCoefficient*d*d*d*d*n*Mathf.Abs(n)*immersion;
            Body.AddForceAtPosition(Body.rotation*Vector3.forward*thrust,point,ForceMode.Force);return thrust;
        }
        void BindRotorGeometry(string sourceName,Transform pivot)
        {
            if(!pivot)return;
            // Imported nested FBX prefabs can restore their original hierarchy
            // on reload, leaving a saved physics pivot empty. Bind the actual
            // mesh wrapper after instantiation, preserving its world placement.
            foreach(var source in GetComponentsInChildren<Transform>(true))
                if(source.name==sourceName&&source!=pivot&&!source.IsChildOf(pivot))
                {
#if UNITY_EDITOR
                    if(!Application.isPlaying)
                    {
                        var instance=UnityEditor.PrefabUtility.GetOutermostPrefabInstanceRoot(source.gameObject);
                        if(instance)UnityEditor.PrefabUtility.UnpackPrefabInstance(instance,UnityEditor.PrefabUnpackMode.Completely,UnityEditor.InteractionMode.AutomatedAction);
                    }
#endif
                    source.SetParent(pivot,true);break;
                }
        }
        void LateUpdate()=>UpdateRotorVisuals();
        public void UpdateRotorVisuals()
        {
            if(portRotor)portRotor.localRotation=portRest*Quaternion.AngleAxis((float)(portAngle%360),Vector3.forward);
            if(starboardRotor)starboardRotor.localRotation=starboardRest*Quaternion.AngleAxis((float)(starboardAngle%360),Vector3.forward);
        }
        public void ResetState(Vector3 position,Quaternion rotation)
        {
            Initialize();portCommand=starboardCommand=0;PortRpm=StarboardRpm=0;portAngle=starboardAngle=0;
            bool moored=Body.isKinematic;Body.isKinematic=false;
            Body.position=position;Body.rotation=rotation;Body.linearVelocity=Body.angularVelocity=Vector3.zero;
            Body.isKinematic=moored;
            CollisionCount=0;LastCollisionImpulse=0;Body.WakeUp();Physics.SyncTransforms();
        }
        public void StopMotors(){portCommand=starboardCommand=0;PortRpm=StarboardRpm=0;}
        void OnCollisionEnter(Collision c){CollisionCount++;LastCollisionImpulse=c.impulse.magnitude;}
        void OnDrawGizmosSelected()
        {
            if(!profile)return;Gizmos.color=Color.yellow;
            Gizmos.DrawWireCube(transform.TransformPoint(new Vector3(0,.0045f,0)),new Vector3(.05f,.009f,.07f));
            if(Body){Gizmos.color=Color.magenta;Gizmos.DrawSphere(Body.worldCenterOfMass,.0015f);}
        }
    }
}
