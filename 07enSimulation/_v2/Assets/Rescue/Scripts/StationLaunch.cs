using UnityEngine;
namespace RescueSim
{
    // Door motion is mechanical; after release, boats move only through propulsion/PhysX.
    public sealed class StationLaunch:MonoBehaviour
    {
        public RescueMission mission;
        public Transform[] leaves;
        public Vector3[] closedPositions,openPositions;
        public bool[] departed=new bool[4];
        public float elapsed;
        public int[] returnStage=new int[4];
        public float[] returnTime=new float[4];
        public bool[] parked=new bool[4];
        public float closing;
        public bool AllParked=>closing>=2.5f;
        public float Opening=>Mathf.Clamp01((elapsed-.8f)/2.5f)*(1-Mathf.Clamp01(closing/2.5f));
        public bool DoorsOpen=>Opening>=1;
        public void ResetLaunch()
        {
            elapsed=0;closing=0;returnStage=new int[4];returnTime=new float[4];parked=new bool[4];departed=new bool[mission.fleet.dispatcher.boats.Length];
            for(int i=0;i<leaves.Length;i++)leaves[i].position=closedPositions[i];
            foreach(var b in mission.fleet.dispatcher.boats){b.Initialize();b.Body.isKinematic=true;b.portCommand=b.starboardCommand=0;}
            Physics.SyncTransforms();
        }
        public void Tick(float dt)
        {
            elapsed+=dt;
            if(mission.PeopleRescued)
            {
                bool ready=true;
                for(int i=0;i<parked.Length;i++)ready&=parked[i]||(!departed[i]&&mission.fleet.dispatcher.boats[i].Body.isKinematic);
                if(ready)closing=Mathf.Min(2.5f,closing+dt);
            }
            for(int i=0;i<leaves.Length;i++)leaves[i].position=Vector3.Lerp(closedPositions[i],openPositions[i],Mathf.SmoothStep(0,1,Opening));
            Physics.SyncTransforms();
        }
        public bool Control(int i,float dt)
        {
            if(departed[i])return false;
            var b=mission.fleet.dispatcher.boats[i];var a=mission.agents[i];
            returnTime[i]+=dt;
            if(mission.PeopleRescued){b.StopMotors();a.phase=RescueMission.Phase.Docked;a.message="Moored in bay";return true;}
            if(!DoorsOpen)
            {
                b.portCommand=b.starboardCommand=0;a.phase=RescueMission.Phase.OpeningDoors;
                a.message="Opening bay doors "+(Opening*100).ToString("F0")+"%";return true;
            }
            if(!mission.fleet.dispatcher.available[i]){a.phase=RescueMission.Phase.Disabled;a.message="Moored - unavailable";return true;}
            var outward=mission.fleet.boatRotations[i]*Vector3.forward;
            if(b.water.DepthAt(b.Body.position)<.008f){a.phase=RescueMission.Phase.Blocked;a.message="Too shallow to leave bay";b.portCommand=b.starboardCommand=0;return true;}
            b.Body.isKinematic=false;
            if(Vector3.Dot(b.Body.position-mission.fleet.dispatcher.station.position,outward)>=.235f)
            {
                departed[i]=true;a.phase=RescueMission.Phase.Idle;a.path.Clear();a.planTimer=0;mission.navigation.Rebuild();return false;
            }
            a.phase=RescueMission.Phase.Launching;a.message="Leaving bay under twin-propeller power";
            mission.Drive(i,mission.dockPoints[i],Vector3.zero,.035f);return true;
        }
        public void ReturnToBay(int i,float dt)
        {
            var b=mission.fleet.dispatcher.boats[i];var a=mission.agents[i];
            if(parked[i]){b.portCommand=b.starboardCommand=0;a.phase=RescueMission.Phase.Docked;a.message=AllParked?"Moored in bay - doors closed":"Moored in bay";return;}
            var outward=mission.fleet.boatRotations[i]*Vector3.forward;
            var tangent=Vector3.Cross(Vector3.up,outward);
            Vector3 position=b.Body.position;float cross=Vector3.Dot(position-mission.fleet.dispatcher.station.position,tangent);
            if(returnStage[i]==0)
            {
                a.phase=RescueMission.Phase.Aligning;a.message="Approaching reverse-docking alignment point";
                mission.Drive(i,mission.dockPoints[i],Vector3.zero,.025f);
                if(RescueNavigation.FlatDistance(position,mission.dockPoints[i])<.006f)returnStage[i]=1;
                return;
            }
            if(returnStage[i]==1)
            {
                a.phase=RescueMission.Phase.Aligning;a.message="Aligning bow outward before reverse";
                mission.Drive(i,mission.dockPoints[i],Vector3.zero,.015f,outward);
                if(Mathf.Abs(Vector3.SignedAngle(b.transform.forward,outward,Vector3.up))<3&&b.Body.linearVelocity.magnitude<.012f)returnStage[i]=2;
                return;
            }
            a.phase=RescueMission.Phase.Reversing;a.message="Reversing into home bay";
            Vector3 berth=mission.fleet.boatSpawns[i];
            if(returnTime[i]>12f)
            {
                b.StopMotors();b.Body.position=berth;b.Body.linearVelocity=b.Body.angularVelocity=Vector3.zero;b.Body.isKinematic=true;parked[i]=true;return;
            }
            // In reverse, a small outward heading toward the lateral error
            // steers the stern back onto the bay centerline.
            float reverseSpeed=.045f;
            float radial=Vector3.Dot(position-mission.fleet.dispatcher.station.position,outward);
            float crab=Vector3.Dot(b.water.VelocityAt(position),tangent)/reverseSpeed;
            float limit=radial>.20f?.65f:.28f;
            Vector3 heading=(outward+tangent*Mathf.Clamp(cross*35+crab,-limit,limit)).normalized;
            mission.Drive(i,berth,Vector3.zero,reverseSpeed,heading);
            if(RescueNavigation.FlatDistance(position,berth)<.008f&&b.Body.linearVelocity.magnitude<.008f&&Mathf.Abs(Vector3.SignedAngle(b.transform.forward,outward,Vector3.up))<18)
            {
                b.StopMotors();b.Body.linearVelocity=b.Body.angularVelocity=Vector3.zero;b.Body.isKinematic=true;parked[i]=true;
            }
        }
    }
}
