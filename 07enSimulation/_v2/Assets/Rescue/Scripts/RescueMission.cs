using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace RescueSim
{
    public sealed class RescueMission:MonoBehaviour
    {
        public enum Phase { Idle, Outbound, Approaching, Boarding, Returning, Unloading, Blocked, Disabled, Manual, Complete }
        [Serializable] public sealed class Agent
        {
            public Phase phase;public RescueVictim target;
            public List<RescueVictim> onboard=new List<RescueVictim>();
            public List<Vector3> path=new List<Vector3>();
            public int waypoint,refugeSlot;public float planTimer,transferTimer,blockedTime;
            public Vector3 transferStart,goal,lastPosition;public float travel;
            public string message="Ready";
        }
        public FleetScenario fleet;
        public RescueNavigation navigation;
        public Agent[] agents;
        public Vector3[] dockPoints,refugeSeats;
        public GameObject seatedPrefab;
        public bool running=true,showRoutes=true;
        public int manualBoat=-1;
        public float simulationSeconds,cruiseSpeed=.05f;
        public int rescued,boardingEvents,unloadingEvents,plans;
        public float maxPassengers;
        readonly List<GameObject> refugeVisuals=new List<GameObject>();
        LineRenderer[] routes;Material routeMaterial;
        float dispatchTimer;
        int nextRefugeSlot;
        bool initialized;
        public bool Complete=>rescued==fleet.dispatcher.victims.Length;
        public bool IsManual(int index)=>manualBoat==index;
        public bool AcceptsAssignments(int index)=>!initialized||(!IsManual(index)&&agents[index].phase!=Phase.Returning&&agents[index].phase!=Phase.Unloading&&agents[index].phase!=Phase.Disabled);
        public void Initialize()
        {
            if(initialized)return;
            var boats=fleet.dispatcher.boats;agents=new Agent[boats.Length];
            for(int i=0;i<agents.Length;i++){boats[i].Initialize();agents[i]=new Agent{lastPosition=boats[i].Body.position};}
            foreach(var v in fleet.dispatcher.victims)v.Initialize();
            Physics.SyncTransforms();navigation.Rebuild();initialized=true;
        }
        void Start()
        {
            Initialize();routes=new LineRenderer[agents.Length];routeMaterial=new Material(fleet.assignmentMaterial);
            for(int i=0;i<routes.Length;i++)
            {
                var l=new GameObject("Planned_Route_Boat_"+(i+1)).AddComponent<LineRenderer>();l.transform.SetParent(transform);l.sharedMaterial=routeMaterial;l.startColor=l.endColor=fleet.boatColors[i];l.startWidth=l.endWidth=.0015f;routes[i]=l;
            }
        }
        void OnDestroy(){if(routeMaterial)Destroy(routeMaterial);}
        public void StopAutonomy(){running=false;foreach(var b in fleet.dispatcher.boats)b.portCommand=b.starboardCommand=0;}
        public void TakeManual(int index)
        {
            if(manualBoat>=0)ResumeBoat(manualBoat);
            CancelTransfer(index);
            manualBoat=index;agents[index].phase=Phase.Manual;fleet.dispatcher.boats[index].portCommand=fleet.dispatcher.boats[index].starboardCommand=0;
            fleet.dispatcher.Dispatch();
        }
        public void ResumeBoat(int index)
        {
            manualBoat=-1;agents[index].target=null;agents[index].phase=agents[index].onboard.Count>0?Phase.Returning:Phase.Idle;agents[index].path.Clear();fleet.dispatcher.Dispatch();
        }
        void CancelTransfer(int index)
        {
            var a=agents[index];
            if(a.phase==Phase.Boarding&&a.target)
            {
                var v=a.target;v.state=RescueVictim.RescueState.Water;v.carrier=-1;v.assignedBoat=-1;v.Body.position=a.transferStart;v.Body.isKinematic=false;v.Body.linearVelocity=fleet.dispatcher.boats[index].Body.linearVelocity;v.GetComponent<Collider>().enabled=true;a.target=null;
            }
            if(a.phase==Phase.Unloading)
                foreach(var v in a.onboard)if(v.state==RescueVictim.RescueState.Disembarking){v.state=RescueVictim.RescueState.Onboard;v.gameObject.SetActive(false);}
            a.transferTimer=0;
        }
        public void ResetMission()
        {
            Initialize();rescued=boardingEvents=unloadingEvents=plans=0;simulationSeconds=0;maxPassengers=0;manualBoat=-1;dispatchTimer=0;nextRefugeSlot=0;
            foreach(var visual in refugeVisuals)if(visual){visual.SetActive(false);if(Application.isPlaying)Destroy(visual);else DestroyImmediate(visual);}refugeVisuals.Clear();
            for(int i=0;i<agents.Length;i++){fleet.dispatcher.boats[i].SetPassengerCount(0);agents[i]=new Agent{lastPosition=fleet.boatSpawns[i]};}
            navigation.Rebuild();
        }
        public void Tick(float dt)
        {
            Initialize();simulationSeconds+=dt;
            if(!running)return;
            dispatchTimer-=dt;if(dispatchTimer<=0&&fleet.dispatcher.automatic){dispatchTimer=1;fleet.dispatcher.Dispatch();}
            for(int i=0;i<agents.Length;i++)UpdateAgent(i,dt);
        }
        void UpdateAgent(int i,float dt)
        {
            var a=agents[i];var b=fleet.dispatcher.boats[i];a.travel+=RescueNavigation.FlatDistance(a.lastPosition,b.Body.position);a.lastPosition=b.Body.position;
            maxPassengers=Mathf.Max(maxPassengers,b.Passengers);
            if(IsManual(i))return;
            if(!fleet.dispatcher.available[i]||b.Capsized)
            {
                CancelTransfer(i);
                a.phase=Phase.Disabled;a.message=b.Capsized?"Capsized - manual recovery needed":"Unavailable";b.portCommand=b.starboardCommand=0;return;
            }
            if(a.phase==Phase.Disabled)a.phase=a.onboard.Count>0?Phase.Returning:Phase.Idle;
            if(a.phase==Phase.Boarding){Board(i,dt);return;}
            if(a.phase==Phase.Unloading){Unload(i,dt);return;}
            if(a.phase==Phase.Complete){Drive(i,dockPoints[i],Vector3.zero,.025f);return;}
            if(a.phase==Phase.Returning)
            {
                Navigate(i,dockPoints[i],Vector3.zero,dt);
                if(RescueNavigation.FlatDistance(b.Body.position,dockPoints[i])<.032f&&FlatSpeed(b.Body.linearVelocity)<.022f)
                {a.phase=Phase.Unloading;a.transferTimer=0;a.path.Clear();a.message="Transferring to refuge deck";}
                return;
            }
            if(!a.target||!a.target.InWater||a.target.assignedBoat!=i)
            {
                a.target=fleet.dispatcher.Tasks(i).Where(v=>v.state==RescueVictim.RescueState.Water).OrderByDescending(v=>v.Priority).ThenBy(v=>RescueNavigation.FlatDistance(v.transform.position,b.Body.position)).FirstOrDefault();
                a.path.Clear();a.planTimer=0;
            }
            if(a.target==null||b.Passengers>=6)
            {
                if(a.onboard.Count>0){a.phase=Phase.Returning;a.path.Clear();a.planTimer=0;return;}
                a.phase=Complete?Phase.Complete:Phase.Idle;a.message=Complete?"Mission complete":"Waiting for a reachable task";Drive(i,dockPoints[i],Vector3.zero,.025f);return;
            }
            Vector3 victim=a.target.Body.position;
            Vector3 goal=PickupPoint(i,victim);
            if(float.IsNaN(goal.x)){Block(i,"No safe pickup approach",dt);return;}
            a.phase=RescueNavigation.FlatDistance(b.Body.position,victim)<.13f?Phase.Approaching:Phase.Outbound;
            Navigate(i,goal,a.target.Body.linearVelocity,dt);
            float distance=RescueNavigation.FlatDistance(b.Body.position,victim),relative=FlatSpeed(b.Body.linearVelocity-a.target.Body.linearVelocity);
            if(distance<.061f&&relative<.023f)
            {
                a.phase=Phase.Boarding;a.transferTimer=0;a.transferStart=a.target.Body.position;
                a.target.state=RescueVictim.RescueState.Boarding;a.target.carrier=i;a.target.Body.isKinematic=true;a.target.GetComponent<Collider>().enabled=false;
                a.message="Boarding P"+a.target.personId;boardingEvents++;
            }
        }
        Vector3 PickupPoint(int i,Vector3 person)
        {
            Vector3 away=fleet.dispatcher.boats[i].Body.position-person;away.y=0;if(away.sqrMagnitude<1e-6f)away=Vector3.back;
            Vector3 best=new Vector3(float.NaN,0,0);float cost=float.PositiveInfinity;
            for(int n=0;n<16;n++)
            {
                Vector3 candidate=person+Quaternion.Euler(0,n*22.5f,0)*away.normalized*.052f;
                if(!navigation.Walkable(candidate,i))continue;
                float score=RescueNavigation.FlatDistance(candidate,fleet.dispatcher.boats[i].Body.position);
                if(score<cost){cost=score;best=candidate;}
            }
            return best;
        }
        void Block(int i,string reason,float dt)
        {
            var a=agents[i];a.phase=Phase.Blocked;a.message=reason;a.blockedTime+=dt;
            Drive(i,fleet.dispatcher.boats[i].Body.position,Vector3.zero,0);
            if(a.blockedTime>5&&a.onboard.Count>0){a.phase=Phase.Returning;a.target=null;a.planTimer=0;a.blockedTime=0;}
        }
        void Navigate(int i,Vector3 goal,Vector3 goalVelocity,float dt)
        {
            var a=agents[i];var b=fleet.dispatcher.boats[i];a.planTimer-=dt;
            if(a.planTimer<=0||a.path.Count==0)
            {
                a.path=navigation.Plan(b.Body.position,goal,i)??new List<Vector3>();a.waypoint=0;a.planTimer=1.2f;a.goal=goal;plans++;
            }
            if(a.path.Count==0){bool returning=a.phase==Phase.Returning;Block(i,"No collision-free / deep-water route",dt);if(returning)a.phase=Phase.Returning;return;}
            a.blockedTime=0;
            while(a.waypoint<a.path.Count-1&&RescueNavigation.FlatDistance(b.Body.position,a.path[a.waypoint])<.028f)a.waypoint++;
            // A higher boat ID yields when projected separation becomes unsafe.
            for(int j=0;j<i;j++)
            {
                var other=fleet.dispatcher.boats[j];Vector3 rel=other.Body.position-b.Body.position;rel.y=0;
                Vector3 dv=other.Body.linearVelocity-b.Body.linearVelocity;dv.y=0;
                float t=dv.sqrMagnitude>1e-6f?Mathf.Clamp(-Vector3.Dot(rel,dv)/dv.sqrMagnitude,0,1.5f):0;
                if((rel+dv*t).magnitude<.105f&&rel.magnitude<.18f)
                {Drive(i,b.Body.position,Vector3.zero,0);a.message="Yielding to B"+(j+1);a.planTimer=0;return;}
            }
            Vector3 next=a.path[a.waypoint];bool last=a.waypoint==a.path.Count-1;
            if(last&&navigation.ClearLine(b.Body.position,goal,i))next=goal;
            float speed=last?Mathf.Min(cruiseSpeed,Mathf.Max(.012f,RescueNavigation.FlatDistance(b.Body.position,next)*.8f)):cruiseSpeed;
            Drive(i,next,last?goalVelocity:Vector3.zero,speed);a.message=a.phase==Phase.Returning?"Returning to home dock":"Tracking collision-free path";
        }
        static float FlatSpeed(Vector3 v){v.y=0;return v.magnitude;}
        void Drive(int i,Vector3 target,Vector3 targetVelocity,float speed)
        {
            var b=fleet.dispatcher.boats[i];Vector3 error=target-b.Body.position;error.y=0;targetVelocity.y=0;
            Vector3 desired=Vector3.ClampMagnitude(error*1.3f,speed)+targetVelocity;
            Vector3 relative=b.Body.linearVelocity-b.water.VelocityAt(b.Body.position);relative.y=0;
            Vector3 local=b.transform.InverseTransformDirection(relative);
            Vector3 dragLocal=new Vector3(b.profile.linearDrag.x*local.x+.5f*b.water.density*b.profile.quadraticCd.x*b.profile.referenceArea.x*Mathf.Abs(local.x)*local.x,0,b.profile.linearDrag.z*local.z+.5f*b.water.density*b.profile.quadraticCd.z*b.profile.referenceArea.z*Mathf.Abs(local.z)*local.z);
            Vector3 force=b.Body.mass*1.8f*(desired-new Vector3(b.Body.linearVelocity.x,0,b.Body.linearVelocity.z))+b.transform.TransformDirection(dragLocal);force.y=0;
            Vector3 heading=error.magnitude>.05f?desired-b.water.VelocityAt(b.Body.position)*.6f:force;
            heading.y=0;
            float angle=heading.sqrMagnitude>1e-10f?Vector3.SignedAngle(b.transform.forward,heading,Vector3.up)*Mathf.Deg2Rad:0;
            // Allow reverse thrust for small holding corrections instead of
            // demanding a 180-degree turn at every stop.
            if(error.magnitude<.06f&&Mathf.Abs(angle)>Mathf.PI/2)angle-=Mathf.Sign(angle)*Mathf.PI;
            float rate=Mathf.Clamp(angle*1.8f,-.85f,.85f);
            float torque=b.profile.angularDrag.y*rate+.000018f*(rate-b.Body.angularVelocity.y);
            float total=Vector3.Dot(force,b.transform.forward);
            if(error.magnitude>.06f)total*=Mathf.Clamp01(Mathf.Cos(angle));
            float arm=Mathf.Abs(b.profile.portMount.x);float port=(total+torque/arm)/2,starboard=(total-torque/arm)/2;
            float max=b.water.density*b.profile.thrustCoefficient*Mathf.Pow(b.profile.propellerDiameter,4)*Mathf.Pow(b.profile.maximumRpm/60,2);
            b.portCommand=Mathf.Sign(port)*Mathf.Sqrt(Mathf.Clamp01(Mathf.Abs(port)/max));b.starboardCommand=Mathf.Sign(starboard)*Mathf.Sqrt(Mathf.Clamp01(Mathf.Abs(starboard)/max));
        }
        static readonly Vector3[] Seats={new Vector3(-.015f,.00735f,-.002f),new Vector3(.015f,.00735f,-.002f),new Vector3(-.015f,.00735f,.0155f),new Vector3(.015f,.00735f,.0155f),new Vector3(-.015f,.00735f,-.0195f),new Vector3(.015f,.00735f,-.0195f)};
        void Board(int i,float dt)
        {
            var a=agents[i];var b=fleet.dispatcher.boats[i];var person=a.target;
            Drive(i,b.Body.position,Vector3.zero,0);a.transferTimer+=dt;
            person.Body.position=Vector3.Lerp(a.transferStart,b.transform.TransformPoint(Seats[b.Passengers]+Vector3.up*.009f),Mathf.Clamp01(a.transferTimer/1.0f));
            if(a.transferTimer<1)return;
            person.state=RescueVictim.RescueState.Onboard;person.assignedBoat=-1;person.gameObject.SetActive(false);a.onboard.Add(person);b.SetPassengerCount(a.onboard.Count);
            a.target=null;a.phase=b.Passengers>=6?Phase.Returning:Phase.Idle;a.path.Clear();a.planTimer=0;fleet.dispatcher.Dispatch();
        }
        void Unload(int i,float dt)
        {
            var a=agents[i];var b=fleet.dispatcher.boats[i];Drive(i,dockPoints[i],Vector3.zero,.02f);
            if(a.onboard.Count==0){a.phase=Complete?Phase.Complete:Phase.Idle;a.planTimer=0;fleet.dispatcher.Dispatch();return;}
            var person=a.onboard[a.onboard.Count-1];
            if(a.transferTimer==0)
            {
                if(person.refugeSeat<0)person.refugeSeat=nextRefugeSlot++;
                a.refugeSlot=person.refugeSeat;
                person.state=RescueVictim.RescueState.Disembarking;person.gameObject.SetActive(true);person.Body.isKinematic=true;person.GetComponent<Collider>().enabled=false;
                a.transferStart=b.transform.TransformPoint(Seats[b.Passengers-1]+Vector3.up*.009f);
            }
            Vector3 destination=refugeSeats[a.refugeSlot%refugeSeats.Length];
            a.transferTimer+=dt;person.Body.position=Vector3.Lerp(a.transferStart,destination+Vector3.up*.009f,Mathf.Clamp01(a.transferTimer/1.2f));
            if(a.transferTimer<1.2f)return;
            person.state=RescueVictim.RescueState.Rescued;person.gameObject.SetActive(false);a.onboard.Remove(person);b.SetPassengerCount(a.onboard.Count);
            if(seatedPrefab)
            {
                var visual=Instantiate(seatedPrefab);visual.name="Refuge_Person_"+person.personId.ToString("D2");visual.transform.position=destination;visual.transform.rotation=Quaternion.Euler(0,-(a.refugeSlot/6)*90,0);refugeVisuals.Add(visual);
            }
            rescued++;unloadingEvents++;a.transferTimer=0;
            if(Complete)foreach(var agent in agents){agent.phase=Phase.Complete;agent.message="Mission complete";agent.path.Clear();}
        }
        void LateUpdate()
        {
            if(routes==null)return;
            for(int i=0;i<routes.Length;i++)
            {
                var a=agents[i];var l=routes[i];l.enabled=showRoutes&&a.path.Count>a.waypoint;
                if(!l.enabled)continue;l.positionCount=a.path.Count-a.waypoint+1;
                Vector3 p=fleet.dispatcher.boats[i].transform.position;p.y=fleet.environment.water.level+.003f;l.SetPosition(0,p);
                for(int k=a.waypoint;k<a.path.Count;k++){p=a.path[k];p.y=fleet.environment.water.level+.003f;l.SetPosition(k-a.waypoint+1,p);}
            }
        }
    }
}
