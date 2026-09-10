using System;
using System.Linq;
using UnityEngine;
namespace RescueSim
{
    public sealed class RescueDashboard:MonoBehaviour
    {
        public RescueMission mission;
        public MissionTelemetry telemetry;
        public bool visible=true;
        [NonSerialized] public RenderTexture captureTarget;
        public int leftTab,rightTab;
        Vector2 leftScroll,rightScroll;
        int preset=1;
        bool roofVisible=true;
        Renderer[] roof;
        GUIStyle title,label,small,button,toggle,tab,metric;
        readonly string[] presets={"Calm","Street","High water","Shallow"};
        readonly Color ink=new Color(.80f,.87f,.94f),muted=new Color(.48f,.61f,.72f),panel=new Color(.035f,.068f,.105f,.97f),accent=new Color(.12f,.83f,.76f);
        FloodEnvironment Env=>mission.fleet.environment;
        public float Scale=>Mathf.Clamp(Mathf.Min(Screen.width/1440f,Screen.height/900f),.6f,1.5f);
        void Start(){mission.Initialize();telemetry.BeginRun();roof=mission.fleet.dispatcher.station.GetComponentsInChildren<Renderer>().Where(r=>r.bounds.min.y>.125f).ToArray();}
        void Update(){if(Input.GetKeyDown(KeyCode.H))visible=!visible;}
        public bool SceneContains(Vector3 mouse)
        {
            if(!visible)return true;float s=Scale;return mouse.x>324*s&&mouse.x<Screen.width-344*s&&mouse.y>82*s&&mouse.y<Screen.height-96*s;
        }
        public void SetSpeed(float value){Time.timeScale=Mathf.Clamp(value,.5f,4);telemetry.Record("CONTROL","Simulation speed "+Time.timeScale.ToString("F1")+"x");}
        public void ApplyPreset(int index)
        {
            preset=Mathf.Clamp(index,0,3);telemetry.scenario=presets[preset];Env.Preset(preset);Env.ResetScenario();mission.running=true;Env.clock.paused=false;
        }
        public void SetRoofVisible(bool value){roofVisible=value;if(roof==null)return;foreach(var r in roof)if(r)r.enabled=value;}
        void Styles()
        {
            if(label!=null)return;
            label=new GUIStyle(GUI.skin.label){fontSize=14,wordWrap=true};label.normal.textColor=ink;
            small=new GUIStyle(label){fontSize=12};small.normal.textColor=muted;
            title=new GUIStyle(label){fontSize=23,fontStyle=FontStyle.Bold};
            metric=new GUIStyle(label){fontSize=18,fontStyle=FontStyle.Bold};
            button=new GUIStyle(GUI.skin.button){fontSize=13,wordWrap=true,padding=new RectOffset(8,8,5,5)};
            toggle=new GUIStyle(GUI.skin.toggle){fontSize=13,wordWrap=true};toggle.normal.textColor=ink;toggle.onNormal.textColor=accent;
            tab=new GUIStyle(button){fontSize=12};
        }
        static void Fill(Rect rect,Color color){Color before=GUI.color;GUI.color=color;GUI.DrawTexture(rect,Texture2D.whiteTexture);GUI.color=before;}
        bool Button(string text)=>GUILayout.Button(text,button,GUILayout.MinHeight(28));
        void Text(string text)=>GUILayout.Label(text,label);
        void Hint(string text)=>GUILayout.Label(text,small);
        void OnGUI()
        {
            if(captureTarget&&Event.current.type==EventType.Repaint)RenderTexture.active=captureTarget;
            DrawDashboard();
        }
        void DrawDashboard()
        {
            if(mission.agents==null)return;Styles();GUI.matrix=Matrix4x4.Scale(Vector3.one*Scale);float w=Screen.width/Scale,h=Screen.height/Scale;
            if(!visible){GUI.Label(new Rect(16,16,400,24),"H: show controls | C: free / follow | P: pause",label);return;}
            var f=mission.fleet;var d=f.dispatcher;var data=telemetry.GetSnapshot();
            Fill(new Rect(0,0,w,88),panel);GUI.Label(new Rect(20,12,370,34),"RESCUE CONTROL",title);GUI.Label(new Rect(22,49,350,25),"70 x 50 mm boats  /  central rescue station",small);
            float card=(w-400)/4;
            string[] metrics={"RESCUED  "+data.rescued+" / "+data.total,"ONBOARD  "+data.onboard,"IN WATER  "+data.inWater,"TIME  "+data.simulationSeconds.ToString("F1")+" s"};
            for(int i=0;i<4;i++){float x=390+i*card;GUI.Label(new Rect(x,17,card-8,28),metrics[i],metric);GUI.Label(new Rect(x,49,card-8,22),i==0?data.successPercent.ToString("F0")+"% delivered":i==1?"Includes unloading":i==2?"Includes boarding":Time.timeScale.ToString("F1")+"x simulation speed",small);}
            Fill(new Rect(0,85,w,3),new Color(.12f,.20f,.26f));Fill(new Rect(0,85,w*data.successPercent/100,3),accent);
            Fill(new Rect(12,100,300,h-188),panel);Fill(new Rect(w-332,100,320,h-188),panel);
            GUILayout.BeginArea(new Rect(24,110,276,h-208));leftTab=GUILayout.Toolbar(leftTab,new[]{"SCENARIO","CONTROL","VIEW"},tab);GUILayout.Space(10);leftScroll=GUILayout.BeginScrollView(leftScroll);
            if(leftTab==0)ScenarioPanel();else if(leftTab==1)ControlPanel();else ViewPanel();
            GUILayout.EndScrollView();GUILayout.EndArea();
            GUILayout.BeginArea(new Rect(w-320,110,296,h-208));rightTab=GUILayout.Toolbar(rightTab,new[]{"FLEET","PEOPLE","EVENTS"},tab);GUILayout.Space(10);rightScroll=GUILayout.BeginScrollView(rightScroll);
            if(rightTab==0)
            {
                for(int i=0;i<d.boats.Length;i++)
                {
                    var b=d.boats[i];GUI.color=f.boatColors[i];if(Button((f.selected==i?"> ":"")+"BOAT "+(i+1)+"  ["+(i+1)+"]"))f.SelectBoat(i);GUI.color=Color.white;
                    Text(mission.agents[i].phase.ToString().ToUpperInvariant());Hint(mission.agents[i].message);
                    Text("Onboard "+b.Passengers+" / 6  |  Reserved "+d.Reserved(i));
                    Hint("Speed "+(b.Body.linearVelocity.magnitude*1000).ToString("F0")+" mm/s  |  Mass "+(b.Body.mass*1000).ToString("F1")+" g");
                    Hint("RPM L/R "+b.PortRpm.ToString("F0")+" / "+b.StarboardRpm.ToString("F0")+"  |  Contacts "+b.CollisionCount);
                    bool value=GUILayout.Toggle(d.available[i],"Available for rescue",toggle);if(value!=d.available[i]){d.SetAvailable(i,value);telemetry.Record("B"+(i+1),value?"Enabled":"Disabled");}
                    GUILayout.Space(8);
                }
            }
            else if(rightTab==1)
            {
                Hint("Click a person to change urgency while in water.");
                foreach(var v in d.victims)
                {
                    GUI.enabled=v.state==RescueVictim.RescueState.Water;
                    if(Button("P"+v.personId.ToString("D2")+"  "+new[]{"NORMAL","URGENT","CRITICAL"}[v.urgency])){v.urgency=(v.urgency+1)%3;d.Dispatch(true);telemetry.Record("P"+v.personId,"Urgency "+v.urgency);}
                    GUI.enabled=true;Hint(v.Status+"  |  Wait "+v.waitingSeconds.ToString("F0")+" s");
                }
            }
            else
            {
                Hint("Latest events first. Export contains full retained log.");
                for(int i=telemetry.events.Count-1;i>=Mathf.Max(0,telemetry.events.Count-100);i--){var item=telemetry.events[i];Text(item.seconds.ToString("F1")+"s  "+item.subject);Hint(item.detail);GUILayout.Space(6);}
            }
            GUILayout.EndScrollView();GUILayout.EndArea();
            Fill(new Rect(0,h-76,w,76),panel);
            string status=mission.Complete?"MISSION COMPLETE":Env.clock.paused?"PHYSICS PAUSED":!mission.running?"AUTOPILOTS STOPPED":data.outcome=="NoAutonomousBoats"?"NO AUTONOMOUS BOATS":data.outcome=="Blocked"?"ROUTE BLOCKED":"RESCUE IN PROGRESS";
            GUI.Label(new Rect(20,h-64,450,26),status,metric);GUI.Label(new Rect(20,h-35,w-40,24),"P pause  |  R reset  |  Space stop AUTO  |  1-4 select  |  F focus  |  C follow/free  |  H hide UI",small);
            GUI.Label(new Rect(w-690,h-60,675,25),"Distance "+data.boats.Sum(b=>b.distanceM).ToString("F2")+" m  |  Contacts "+data.boats.Sum(b=>b.contacts)+"  |  Plans "+data.plans,label);
            var camera=Env.overview.enabled?Env.overview:Env.follow;
            foreach(var v in d.victims.Where(v=>v.isActiveAndEnabled&&v.InWater))
            {
                Vector3 p=camera.WorldToScreenPoint(v.transform.position+Vector3.up*.02f);if(p.z<=0||!SceneContains(p))continue;
                GUI.color=v.urgency==2?new Color(1,.4f,.25f):v.urgency==1?Color.yellow:Color.white;
                GUI.Label(new Rect(p.x/Scale-16,(Screen.height-p.y)/Scale-10,85,22),"SOS P"+v.personId.ToString("D2"),small);GUI.color=Color.white;
            }
        }
        void ScenarioPanel()
        {
            Text("Flood preset");preset=GUILayout.SelectionGrid(preset,presets,2,button,GUILayout.Height(60));
            if(Button("Apply preset + reset mission"))ApplyPreset(preset);
            Hint("This starts a new report run. Water controls below apply live.");GUILayout.Space(8);
            var water=Env.water;Text("Reference depth  "+((water.level-water.bottom)*1000).ToString("F0")+" mm");Env.SetLevel(GUILayout.HorizontalSlider(water.level,-.025f,.035f));
            float speed=water.current.magnitude;Text("Background current  "+(speed*1000).ToString("F1")+" mm/s");speed=GUILayout.HorizontalSlider(speed,0,.04f);
            float heading=Mathf.Atan2(water.current.x,water.current.z)*Mathf.Rad2Deg;Text("Flow direction  "+heading.ToString("F0")+" deg");heading=GUILayout.HorizontalSlider(heading,-180,180);Env.SetCurrent(speed,heading);
            water.regionalFlow=GUILayout.Toggle(water.regionalFlow,"Regional currents",toggle);Text("Regional strength  "+water.regionalStrength.ToString("F1"));water.regionalStrength=GUILayout.HorizontalSlider(water.regionalStrength,0,2);
            bool debris=Env.debris.Any(d=>d.isActiveAndEnabled);bool next=GUILayout.Toggle(debris,"Floating debris",toggle);if(next!=debris)Env.SetDebris(next);
            GUILayout.Space(12);Text("Simulation speed");GUILayout.BeginHorizontal();foreach(float factor in new[]{.5f,1,2,4})if(GUILayout.Button(factor.ToString("0.#")+"x",button))SetSpeed(factor);GUILayout.EndHorizontal();
            if(Button(Env.clock.paused?"Resume physics [P]":"Pause physics [P]"))Env.clock.paused=!Env.clock.paused;
            if(Button("Reset mission [R]"))Env.ResetScenario();
            GUILayout.Space(12);Text("Results");telemetry.autoExport=GUILayout.Toggle(telemetry.autoExport,"Auto-export on completion",toggle);
            if(Button("Export CSV + JSON now"))telemetry.Export();
            if(!string.IsNullOrEmpty(telemetry.LastExport)){Hint("Last export: "+telemetry.LastExport);if(Button("Open report folder"))Application.OpenURL(new Uri(telemetry.LastExport+System.IO.Path.DirectorySeparatorChar).AbsoluteUri);}
            if(!string.IsNullOrEmpty(telemetry.ExportError))Text("Export error: "+telemetry.ExportError);
        }
        void ControlPanel()
        {
            var f=mission.fleet;var b=Env.boat;Text("Selected: BOAT "+(f.selected+1));
            if(Button(mission.IsManual(f.selected)?"Return boat to AUTO":"Take boat MANUAL")){if(mission.IsManual(f.selected))mission.ResumeBoat(f.selected);else mission.TakeManual(f.selected);}
            if(Button(mission.running?"Stop all autopilots [Space]":"Resume autopilots")){if(mission.running)mission.StopAutonomy();else mission.running=true;}
            GUI.enabled=mission.IsManual(f.selected);Env.KeyboardControl=GUILayout.Toggle(Env.KeyboardControl,"Keyboard W/S/A/D",toggle);
            if(!Env.KeyboardControl){Text("Port motor");b.portCommand=GUILayout.HorizontalSlider(b.portCommand,-1,1);Text("Starboard motor");b.starboardCommand=GUILayout.HorizontalSlider(b.starboardCommand,-1,1);}
            if(Button("Stop selected motors"))b.portCommand=b.starboardCommand=0;GUI.enabled=true;
            GUILayout.Space(12);Text("Boat telemetry");Text("Depth "+(Env.water.DepthAt(b.Body.position)*1000).ToString("F1")+" mm");Text("Local flow "+(Env.water.VelocityAt(b.Body.position).magnitude*1000).ToString("F1")+" mm/s");Text("Tilt "+b.TiltDegrees.ToString("F1")+" deg");Text("Draft "+(b.Draft*1000).ToString("F1")+" mm");Text("RPM L/R "+b.PortRpm.ToString("F0")+" / "+b.StarboardRpm.ToString("F0"));Text(b.Capsized?"CAPSIZED":b.Grounded?"GROUNDED":b.DeckEdgeSubmerged?"DECK EDGE WET":"AFLOAT");
            GUILayout.Space(12);Text("Task allocation");f.dispatcher.automatic=GUILayout.Toggle(f.dispatcher.automatic,"Auto-assign seats",toggle);if(Button("Rebalance assignments"))f.dispatcher.Dispatch(true);
            if(Button("Release tasks + stop allocation")){f.dispatcher.automatic=false;f.dispatcher.ClearAssignments();}
        }
        void ViewPanel()
        {
            mission.showRoutes=GUILayout.Toggle(mission.showRoutes,"Navigation paths",toggle);mission.fleet.showAssignments=GUILayout.Toggle(mission.fleet.showAssignments,"Person assignment links",toggle);
            bool roofNext=GUILayout.Toggle(roofVisible,"Station roof",toggle);if(roofNext!=roofVisible)SetRoofVisible(roofNext);
            if(Button("Free / follow camera [C]"))Env.SetFollowCamera(Env.overview.enabled);
            if(Button("Focus selected boat [F]"))mission.fleet.CameraControls.FocusBoat();
            if(Button("Reset full view [Home]"))mission.fleet.CameraControls.ResetView();
            GUILayout.Space(12);Text("Camera controls");Hint("Left or middle drag: pan\nRight drag: orbit (-89 to +89 degrees)\nLook up / down freely\nWheel: zoom at cursor\nArrow keys: move\nH: hide/show panels");
            GUILayout.Space(12);Text("Scene legend");Hint("Thick colored line: navigation path\nThin link: task ownership\nCyan arrow: local water flow\nOrange outline: shallow shelf\nRed outline: fast-current area");
        }
    }
}
