using System;
using UnityEngine;
namespace RescueSim
{
    public sealed class FloodEnvironment:MonoBehaviour
    {
        public WaterField water;public BoatDynamics boat;public PhysicsClock clock;
        public Transform surface;public Transform[] hazardMarkers,flowArrows;
        public FloatingDebris[] debris;public Camera overview,follow;
        public Vector3 start=new Vector3(0,-.00456848f,-.40f);
        public FleetScenario fleet;
        Vector3[] debrisStart;bool close,keyboard=true;float heading=0,speed=.008f;Vector2 scroll;
        void Awake(){debrisStart=new Vector3[debris.Length];for(int i=0;i<debris.Length;i++)debrisStart[i]=debris[i].transform.position;}
        public void SetLevel(float y){water.level=y;RefreshMarkers();}
        public void SetCurrent(float metresPerSecond,float degrees){speed=metresPerSecond;heading=degrees;water.current=Quaternion.Euler(0,degrees,0)*Vector3.forward*speed;}
        public void Preset(int i)
        {
            if(i==0){SetLevel(0);SetCurrent(0,0);water.regionalFlow=false;}
            if(i==1){SetLevel(0);SetCurrent(.008f,0);water.regionalFlow=true;water.regionalStrength=1;}
            if(i==2){SetLevel(.015f);SetCurrent(.025f,25);water.regionalFlow=true;water.regionalStrength=1.5f;}
            if(i==3){SetLevel(-.023f);SetCurrent(.004f,0);water.regionalFlow=false;}
        }
        public void ResetScenario()
        {
            if(fleet)fleet.ResetFleet();else boat.ResetState(new Vector3(start.x,water.level-.00456848f,start.z),Quaternion.identity);
            for(int i=0;i<debris.Length;i++)debris[i].ResetAt(new Vector3(debrisStart[i].x,water.level+.004f,debrisStart[i].z));
        }
        public void SetDebris(bool enabled){foreach(var d in debris)d.gameObject.SetActive(enabled);}
        public void UseSliders(){keyboard=false;}
        public void SetFollowCamera(bool value){close=value;overview.enabled=!close;follow.enabled=close;}
        public string RiskAt(Vector3 p)
        {
            if(!water.HasWater(p))return "DRY / NOT NAVIGABLE";
            if(water.DepthAt(p)<.008f)return "SHALLOW WATER";
            if(water.VelocityAt(p).magnitude>.025f)return "STRONG CURRENT";
            return "NORMAL";
        }
        void RefreshMarkers()
        {
            surface.position=new Vector3(surface.position.x,water.level-.0001f,surface.position.z);
            foreach(var m in hazardMarkers)m.position=new Vector3(m.position.x,Mathf.Max(water.level,water.BottomAt(m.position))+.0004f,m.position.z);
            foreach(var arrow in flowArrows)
            {
                Vector3 p=arrow.position;p.y=water.level+.0006f;arrow.position=p;
                Vector3 v=water.VelocityAt(p);arrow.gameObject.SetActive(v.magnitude>.0001f);
                if(v.magnitude>.0001f){arrow.rotation=Quaternion.LookRotation(v,Vector3.up);float scale=Mathf.Clamp(v.magnitude/.015f,.4f,2);arrow.localScale=new Vector3(1,1,scale);}
            }
        }
        void Update()
        {
            bool manual=!fleet||!fleet.mission||fleet.mission.IsManual(fleet.selected);
            if(keyboard&&manual)
            {
                float drive=(Input.GetKey(KeyCode.W)?.45f:0)-(Input.GetKey(KeyCode.S)?.45f:0),turn=(Input.GetKey(KeyCode.D)?.35f:0)-(Input.GetKey(KeyCode.A)?.35f:0);
                boat.portCommand=drive+turn;boat.starboardCommand=drive-turn;
            }
            if(Input.GetKeyDown(KeyCode.Space)&&fleet&&fleet.mission&&!manual)fleet.mission.StopAutonomy();
            if(Input.GetKey(KeyCode.Space)&&manual)boat.portCommand=boat.starboardCommand=0;
            if(Input.GetKeyDown(KeyCode.R))ResetScenario();
            if(Input.GetKeyDown(KeyCode.P))clock.paused=!clock.paused;
            if(Input.GetKeyDown(KeyCode.C))SetFollowCamera(!close);
            Vector3 cameraOffset=fleet?boat.transform.rotation*new Vector3(.12f,.20f,.20f):new Vector3(.10f,.15f,-.18f);
            follow.transform.position=boat.transform.position+cameraOffset;follow.transform.LookAt(boat.transform.position+Vector3.up*.01f);
            RefreshMarkers();
        }
        void OnGUI()
        {
            float scale=Mathf.Max(.6f,Screen.height/900f);GUI.matrix=Matrix4x4.Scale(Vector3.one*scale);
            GUILayout.BeginArea(new Rect(16,16,300,Screen.height/scale-32),GUI.skin.box);
            scroll=GUILayout.BeginScrollView(scroll);
            GUILayout.Label(fleet?"FLOOD / SELECTED BOAT "+(fleet.selected+1):"FLOOD ENVIRONMENT / STEP 3");GUILayout.Label("Model scale | 70 x 50 mm boat");
            GUILayout.BeginHorizontal();if(GUILayout.Button("Calm"))Preset(0);if(GUILayout.Button("Street"))Preset(1);GUILayout.EndHorizontal();
            GUILayout.BeginHorizontal();if(GUILayout.Button("High water"))Preset(2);if(GUILayout.Button("Shallow"))Preset(3);GUILayout.EndHorizontal();
            GUILayout.Label("Reference depth: "+((water.level-water.bottom)*1000).ToString("F0")+" mm");SetLevel(GUILayout.HorizontalSlider(water.level,-.025f,.035f));
            GUILayout.Label("Background current: "+(speed*1000).ToString("F1")+" mm/s");float sp=GUILayout.HorizontalSlider(speed,0,.04f);
            GUILayout.Label("Flow heading: "+heading.ToString("F0")+" deg");float h=GUILayout.HorizontalSlider(heading,-180,180);SetCurrent(sp,h);
            water.regionalFlow=GUILayout.Toggle(water.regionalFlow,"Enable regional currents");GUILayout.Label("Regional flow strength");water.regionalStrength=GUILayout.HorizontalSlider(water.regionalStrength,0,2);
            GUILayout.Space(8);GUI.enabled=!fleet||!fleet.mission||fleet.mission.IsManual(fleet.selected);keyboard=GUILayout.Toggle(keyboard,"Keyboard W/S/A/D (manual)");
            if(!keyboard){GUILayout.Label("Port / Starboard throttle");boat.portCommand=GUILayout.HorizontalSlider(boat.portCommand,-1,1);boat.starboardCommand=GUILayout.HorizontalSlider(boat.starboardCommand,-1,1);}
            if(GUILayout.Button("Stop motors [Space]"))boat.portCommand=boat.starboardCommand=0;
            GUI.enabled=true;
            if(GUILayout.Button(clock.paused?"Resume [P]":"Pause [P]"))clock.paused=!clock.paused;
            if(GUILayout.Button("Reset boat + debris [R]"))ResetScenario();
            if(GUILayout.Button("Switch camera [C]"))SetFollowCamera(!close);
            bool on=debris.Length>0&&debris[0].gameObject.activeSelf;bool next=GUILayout.Toggle(on,"Floating debris (physical collisions)");if(next!=on)SetDebris(next);
            if(!fleet||!fleet.mission){GUILayout.BeginHorizontal();if(GUILayout.Button("+ Passenger"))boat.SetPassengerCount(boat.Passengers+1);if(GUILayout.Button("- Passenger"))boat.SetPassengerCount(boat.Passengers-1);GUILayout.EndHorizontal();}
            GUILayout.Space(8);Vector3 p=boat.Body.position;
            GUILayout.Label("Local depth: "+(water.DepthAt(p)*1000).ToString("F1")+" mm");GUILayout.Label("Local flow: "+(water.VelocityAt(p).magnitude*1000).ToString("F1")+" mm/s");
            GUILayout.Label("Boat speed: "+(boat.Body.linearVelocity.magnitude*1000).ToString("F1")+" mm/s");GUILayout.Label("Mass: "+(boat.Body.mass*1000).ToString("F1")+" g | People: "+boat.Passengers);
            GUILayout.Label("Contacts: "+boat.CollisionCount+" | Tilt: "+boat.TiltDegrees.ToString("F1")+" deg");GUILayout.Label("Area: "+RiskAt(p));GUILayout.Label("Boat: "+(boat.Capsized?"CAPSIZED":boat.Grounded?"GROUNDED":boat.DeckEdgeSubmerged?"DECK EDGE WET":"AFLOAT"));
            GUILayout.Label("Propellers RPM L/R: "+boat.PortRpm.ToString("F0")+" / "+boat.StarboardRpm.ToString("F0"));
            GUILayout.Space(8);GUILayout.Label("Cyan arrows = imposed local flow\nOrange outline = shallow shelf\nRed outline = fast-current region");GUILayout.Label("Uniform water surface; prescribed flow, no CFD. Water level changes are scenario controls.");
            GUILayout.EndScrollView();GUILayout.EndArea();
        }
    }
}
