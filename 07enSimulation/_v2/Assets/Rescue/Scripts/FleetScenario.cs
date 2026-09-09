using System.Linq;
using UnityEngine;
namespace RescueSim
{
    public sealed class FleetScenario:MonoBehaviour
    {
        public FloodEnvironment environment;
        public FleetDispatcher dispatcher;
        public Vector3[] boatSpawns;
        public Quaternion[] boatRotations;
        public Color[] boatColors={new Color(.05f,.8f,1),new Color(1,.55f,.1f),new Color(.8f,.3f,1),new Color(.3f,1,.4f)};
        public int selected;
        public bool showAssignments=true;
        public Material assignmentMaterial;
        public RescueMission mission;
        Vector2 scroll;
        LineRenderer[] lines;
        Material lineMaterial;
        public FleetCameraControls CameraControls {get; private set;}
        void Start()
        {
            CameraControls=gameObject.AddComponent<FleetCameraControls>();CameraControls.Initialize(environment);
            lines=new LineRenderer[dispatcher.victims.Length];lineMaterial=new Material(assignmentMaterial);
            for(int i=0;i<lines.Length;i++)
            {
                var l=new GameObject("Assignment_Link_"+(i+1)).AddComponent<LineRenderer>();l.transform.SetParent(transform);l.sharedMaterial=lineMaterial;l.positionCount=2;l.startWidth=l.endWidth=.0006f;lines[i]=l;
            }
            SelectBoat(0);
        }
        void OnDestroy(){if(lineMaterial)Destroy(lineMaterial);}
        public void SelectBoat(int index)
        {
            if(environment.boat){environment.boat.portCommand=environment.boat.starboardCommand=0;}
            selected=Mathf.Clamp(index,0,dispatcher.boats.Length-1);environment.boat=dispatcher.boats[selected];environment.start=boatSpawns[selected];
        }
        public void ResetFleet()
        {
            if(mission)mission.ResetMission();
            for(int i=0;i<dispatcher.boats.Length;i++)dispatcher.boats[i].ResetState(new Vector3(boatSpawns[i].x,environment.water.level-.00456848f,boatSpawns[i].z),boatRotations[i]);
            foreach(var v in dispatcher.victims)v.ResetPerson();
            dispatcher.ClearAssignments();if(dispatcher.automatic)dispatcher.Dispatch();
        }
        void Update()
        {
            for(int i=0;i<4;i++)if(Input.GetKeyDown(KeyCode.Alpha1+i))SelectBoat(i);
        }
        void LateUpdate()
        {
            if(lines==null)return;
            for(int i=0;i<lines.Length;i++)
            {
                var v=dispatcher.victims[i];var l=lines[i];int b=v.assignedBoat;
                l.enabled=showAssignments&&v.isActiveAndEnabled&&b>=0;
                if(!l.enabled)continue;
                Vector3 a=dispatcher.boats[b].transform.position,p=v.transform.position;a.y=p.y=environment.water.level+.014f;
                l.SetPosition(0,a);l.SetPosition(1,p);l.startColor=l.endColor=boatColors[b];
            }
        }
        void OnGUI()
        {
            float scale=Mathf.Max(.6f,Screen.height/900f);GUI.matrix=Matrix4x4.Scale(Vector3.one*scale);
            float width=Screen.width/scale,height=Screen.height/scale;
            GUILayout.BeginArea(new Rect(width-306,16,290,height-32),GUI.skin.box);scroll=GUILayout.BeginScrollView(scroll);
            GUILayout.Label(mission?"AUTONOMOUS RESCUE / STEPS 6 + 7":"RESCUE FLEET / STEPS 4 + 5");GUILayout.Label("Central station | 4 boats | 24 seats");
            if(mission)
            {
                GUILayout.Label("Rescued: "+mission.rescued+" / "+dispatcher.victims.Length+" | Time: "+mission.simulationSeconds.ToString("F0")+"s");
                if(GUILayout.Button(mission.running?"Stop autopilots [Space]":"Resume autopilots")){if(mission.running)mission.StopAutonomy();else mission.running=true;}
                if(GUILayout.Button(mission.IsManual(selected)?"Return selected boat to AUTO":"Take selected boat MANUAL")){if(mission.IsManual(selected))mission.ResumeBoat(selected);else mission.TakeManual(selected);}
                mission.showRoutes=GUILayout.Toggle(mission.showRoutes,"Show planned navigation paths");
            }
            GUILayout.Label("Waiting: "+dispatcher.Waiting+" / People: "+(mission?dispatcher.victims.Length:dispatcher.victims.Count(v=>v.isActiveAndEnabled)));
            dispatcher.automatic=GUILayout.Toggle(dispatcher.automatic,"Auto-assign available seats");
            if(GUILayout.Button("Rebalance all assignments"))dispatcher.Dispatch(true);
            if(GUILayout.Button("Clear assignments + pause dispatch")){dispatcher.automatic=false;dispatcher.ClearAssignments();}
            showAssignments=GUILayout.Toggle(showAssignments,"Show assignment links");
            GUILayout.Label("Links show ownership, NOT sailing routes.");
            for(int i=0;i<dispatcher.boats.Length;i++)
            {
                GUI.color=boatColors[i];if(GUILayout.Button((selected==i?"> ":"")+"Boat "+(i+1)+" ["+(i+1)+"]"))SelectBoat(i);GUI.color=Color.white;
                bool active=GUILayout.Toggle(dispatcher.available[i],"Available for assignment");if(active!=dispatcher.available[i])dispatcher.SetAvailable(i,active);
                GUILayout.Label("Onboard "+dispatcher.boats[i].Passengers+" | Reserved "+dispatcher.Reserved(i)+" / "+dispatcher.Capacity(i));
                if(mission&&mission.agents!=null){GUILayout.Label(mission.agents[i].phase+" | "+mission.agents[i].message);}
                GUILayout.Label(string.Join(" ",dispatcher.Tasks(i).Select(v=>"P"+v.personId.ToString("D2"))));
            }
            if(GUILayout.Button("Reset fleet + people [R]"))environment.ResetScenario();
            GUILayout.Label("1-4 select | W/S/A/D drive | C follow/free\nLeft/Middle drag: pan | Right drag: orbit\nWheel: zoom at cursor | Arrows: move\nF: focus boat | Home: reset view");
            if(GUILayout.Button("Focus selected boat [F]"))CameraControls.FocusBoat();
            if(GUILayout.Button("Reset free view [Home]"))CameraControls.ResetView();
            GUILayout.Space(8);GUILayout.Label("PEOPLE — click to change urgency");
            foreach(var v in dispatcher.victims)
            {
                if(!v.isActiveAndEnabled&&!mission)continue;
                GUI.enabled=v.state==RescueVictim.RescueState.Water;
                if(GUILayout.Button("P"+v.personId.ToString("D2")+" "+new[]{"NORMAL","URGENT","CRITICAL"}[v.urgency]+" | "+v.waitingSeconds.ToString("F0")+"s")){v.urgency=(v.urgency+1)%3;dispatcher.Dispatch(true);}GUI.enabled=true;
                GUILayout.Label(v.Status);
            }
            GUILayout.EndScrollView();GUILayout.EndArea();
            var cam=environment.overview.enabled?environment.overview:environment.follow;
            foreach(var v in dispatcher.victims)
            {
                if(!v.isActiveAndEnabled||!v.InWater)continue;
                Vector3 p=cam.WorldToScreenPoint(v.transform.position+Vector3.up*.02f);if(p.z<=0)continue;
                float x=p.x/scale,y=(Screen.height-p.y)/scale;if(x<320||x>width-316||y<0||y>height-35)continue;
                GUI.color=v.urgency==2?new Color(1,.35f,.25f):v.urgency==1?Color.yellow:Color.white;
                GUI.Label(new Rect(x-20,y-10,90,22),"SOS P"+v.personId.ToString("D2"));GUI.color=Color.white;
            }
        }
    }
}
