using UnityEngine;
namespace RescueSim
{
    public sealed class PhysicsLab : MonoBehaviour
    {
        public BoatDynamics boat;public PhysicsClock clock;public WaterField water;
        public Camera overview,follow;
        bool keyboard=true,followView;float flow;
        public void UseSliders(){keyboard=false;}
        public void ShowFollowCamera(){if(!followView)SwitchCamera();}
        void Update()
        {
            if(keyboard)
            {
                float drive=(Input.GetKey(KeyCode.W)? .45f:0)-(Input.GetKey(KeyCode.S)? .45f:0);
                float turn=(Input.GetKey(KeyCode.D)? .35f:0)-(Input.GetKey(KeyCode.A)? .35f:0);
                boat.portCommand=Mathf.Clamp(drive+turn,-1,1);boat.starboardCommand=Mathf.Clamp(drive-turn,-1,1);
            }
            if(Input.GetKeyDown(KeyCode.Space)){boat.portCommand=boat.starboardCommand=0;}
            if(Input.GetKeyDown(KeyCode.R))ResetBoat();
            if(Input.GetKeyDown(KeyCode.C))SwitchCamera();
            if(Input.GetKeyDown(KeyCode.P))clock.paused=!clock.paused;
            if(follow && boat){follow.transform.position=boat.transform.position+new Vector3(.09f,.095f,-.14f);follow.transform.LookAt(boat.transform.position+Vector3.up*.018f);}
        }
        void ResetBoat(){boat.ResetState(new Vector3(0,-.00456848f,0),Quaternion.identity);}
        void SwitchCamera(){followView=!followView;overview.enabled=!followView;follow.enabled=followView;}
        void OnGUI()
        {
            float scale=Mathf.Max(.65f,Screen.height/850f);GUI.matrix=Matrix4x4.Scale(Vector3.one*scale);
            GUILayout.BeginArea(new Rect(18,18,300,780),GUI.skin.box);
            GUILayout.Label("RESCUE BOAT / PHYSICS LAB");GUILayout.Label("70 x 50 mm | Unity PhysX | SI units");
            GUILayout.Space(8);keyboard=GUILayout.Toggle(keyboard,"Keyboard control (W/S/A/D)");
            if(!keyboard){GUILayout.Label("Port motor");boat.portCommand=GUILayout.HorizontalSlider(boat.portCommand,-1,1);GUILayout.Label("Starboard motor");boat.starboardCommand=GUILayout.HorizontalSlider(boat.starboardCommand,-1,1);}
            if(GUILayout.Button("STOP MOTORS [Space]")){boat.portCommand=boat.starboardCommand=0;}
            if(GUILayout.Button("RESET BOAT [R]"))ResetBoat();
            if(GUILayout.Button(clock.paused?"RESUME [P]":"PAUSE [P]"))clock.paused=!clock.paused;
            if(GUILayout.Button("SWITCH CAMERA [C]"))SwitchCamera();
            GUILayout.Space(8);GUILayout.Label("Payload: "+boat.Passengers+" / 6 (1 g each)");
            GUILayout.BeginHorizontal();if(GUILayout.Button("+ Passenger"))boat.SetPassengerCount(boat.Passengers+1);if(GUILayout.Button("- Passenger"))boat.SetPassengerCount(boat.Passengers-1);GUILayout.EndHorizontal();
            if(GUILayout.Button("EMPTY BOAT"))boat.SetPassengerCount(0);
            GUILayout.Label("Cross-current: "+(flow*1000).ToString("F1")+" mm/s");flow=GUILayout.HorizontalSlider(flow,-.025f,.025f);water.current=new Vector3(flow,0,0);
            if(GUILayout.Button("CALM WATER")){flow=0;water.current=Vector3.zero;}
            if(GUILayout.Button("ROLL DISTURBANCE"))boat.Body.AddTorque(boat.transform.forward*.0000006f,ForceMode.Impulse);
            if(GUILayout.Button("CAPSIZE TEST"))boat.ResetState(new Vector3(0,-.004f,0),Quaternion.Euler(0,0,110));
            GUILayout.Space(12);
            GUILayout.Label("Mass: "+(boat.Body.mass*1000).ToString("F2")+" g");
            GUILayout.Label("Speed: "+(boat.Body.linearVelocity.magnitude*1000).ToString("F1")+" mm/s");
            GUILayout.Label("Origin draft: "+(boat.Draft*1000).ToString("F2")+" mm");
            GUILayout.Label("Tilt: "+boat.TiltDegrees.ToString("F2")+" deg");
            GUILayout.Label("RPM P / S: "+boat.PortRpm.ToString("F0")+" / "+boat.StarboardRpm.ToString("F0"));
            GUILayout.Label("Thrust: "+(boat.PortThrust*1000).ToString("F2")+" / "+(boat.StarboardThrust*1000).ToString("F2")+" mN");
            GUILayout.Label("Buoyancy: "+(boat.Buoyancy*1000).ToString("F1")+" mN");
            GUILayout.Label("COM (mm): "+(boat.Body.centerOfMass*1000).ToString("F2"));
            GUILayout.Label("Contacts: "+boat.CollisionCount);
            GUILayout.Label("State: "+(boat.Capsized?"CAPSIZED":boat.Grounded?"GROUNDED":boat.DeckEdgeSubmerged?"DECK EDGE WET":"AFLOAT"));
            GUILayout.Space(8);GUILayout.Label("Mass and hydrodynamic coefficients are provisional. Water uses a force model; no CFD.");
            GUILayout.EndArea();
        }
    }
}
