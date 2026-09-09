using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

namespace RescueSim.Editor
{
    public static class PhysicsValidation
    {
        [Serializable] public class CheckResult { public string name;public bool passed;public float value,limit; }
        [Serializable] public class Report { public string engine;public bool allPassed;public List<CheckResult> checks=new List<CheckResult>();public string scope; }
        static Report report;static GameObject boatPrefab;static WaterField water;static float dt=1f/960;
        static BoatDynamics Spawn()
        {
            var o=(GameObject)PrefabUtility.InstantiatePrefab(boatPrefab);var b=o.GetComponent<BoatDynamics>();b.water=water;b.manualStepping=true;b.Initialize();b.ResetState(new Vector3(0,-.00456848f,0),Quaternion.identity);return b;
        }
        static void Run(BoatDynamics b,float seconds,float step=0)
        {
            if(step<=0)step=dt;
            for(int i=0;i<Mathf.RoundToInt(seconds/step);i++){b.ApplyForces(step);Physics.Simulate(step);}
            if(!float.IsFinite(b.Body.position.y))throw new Exception("Non-finite physics result");
        }
        static void Remove(BoatDynamics b){UnityEngine.Object.DestroyImmediate(b.gameObject);}
        static void Check(string name,bool passed,float value=0,float limit=0){report.checks.Add(new CheckResult{name=name,passed=passed,value=value,limit=limit});}
        [MenuItem("Rescue/Validate PhysX Steps 1-2")]
        public static void Validate()
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);var oldMode=Physics.simulationMode;Physics.simulationMode=SimulationMode.Script;Physics.gravity=new Vector3(0,-9.81f,0);Physics.autoSyncTransforms=false;
            report=new Report{engine="Unity "+Application.unityVersion+" / PhysX / ForceMode.Force",scope="Live engine integration tests at true 70 mm hull scale. Estimated parameters; no CFD or multi-boat scheduling."};
            water=new GameObject("TestWater").AddComponent<WaterField>();boatPrefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Rescue/Prefabs/RescueBoat_Physics.prefab");
            try
            {
                var b=Spawn();Check("dry_mass_12g",Mathf.Abs(b.Body.mass-.012f)<1e-7f,b.Body.mass,.012f);
                var hull=b.GetComponent<MeshCollider>();Check("hull_dimensions_70x50mm",Mathf.Abs(hull.sharedMesh.bounds.size.x-.05f)<1e-6f&&Mathf.Abs(hull.sharedMesh.bounds.size.z-.07f)<1e-6f);
                Transform bow=b.GetComponentsInChildren<Transform>().First(t=>t.name=="Axis_Bow");Transform starboard=b.GetComponentsInChildren<Transform>().First(t=>t.name=="Axis_Starboard");
                Vector3 bp=b.transform.InverseTransformPoint(bow.position),sp=b.transform.InverseTransformPoint(starboard.position);
                Check("import_bow_positive_Z",Vector3.Distance(bp,new Vector3(0,0,.035f))<.00001f,bp.z,.035f);
                Check("import_starboard_positive_X",Vector3.Distance(sp,new Vector3(.025f,0,0))<.00001f,sp.x,.025f);
                Check("shaft_positions_match_force_points",Vector3.Distance(b.portRotor.localPosition,b.profile.portMount)<1e-6f && Vector3.Distance(b.starboardRotor.localPosition,b.profile.starboardMount)<1e-6f);
                Run(b,8);float emptyDraft=b.Draft;Vector3 emptyPosition=b.Body.position;Vector3 inertia=b.Body.inertiaTensor;
                Check("empty_calm_water_equilibrium",Mathf.Abs(emptyDraft-.00456848f)<.0006f,emptyDraft,.00456848f);
                Check("buoyancy_balances_weight",Mathf.Abs(b.Buoyancy-b.Body.mass*9.81f)<.002f,b.Buoyancy,.11772f);
                Check("empty_speed_settles",b.Body.linearVelocity.magnitude<.001f,b.Body.linearVelocity.magnitude,.001f);
                b.SetPassengerCount(6,false);Run(b,8);float loadedDraft=b.Draft;
                Check("six_passengers_increase_mass",Mathf.Abs(b.Body.mass-.018f)<1e-7,b.Body.mass,.018f);
                Check("loaded_draft_increases",loadedDraft>emptyDraft+.001f,loadedDraft-emptyDraft,.001f);
                Check("payload_changes_inertia",Vector3.Distance(inertia,b.Body.inertiaTensor)>1e-8f);
                Check("loaded_boat_stable",b.TiltDegrees<12 && b.Body.linearVelocity.magnitude<.002f,b.TiltDegrees,12);
                b.SetPassengerCount(0,false);Run(b,8);Check("unload_restores_draft",Mathf.Abs(b.Draft-emptyDraft)<.0001f,b.Draft-emptyDraft,.0001f);Remove(b);
                b=Spawn();b.ResetState(new Vector3(0,-.001f,0),Quaternion.Euler(5,0,8));Run(b,8);Check("disturbed_boat_recovers",b.TiltDegrees<3,b.TiltDegrees,3);Remove(b);
                b=Spawn();b.portCommand=b.starboardCommand=.42f;Run(b,3);float speed=b.Body.linearVelocity.magnitude;Check("equal_rpm_drives_forward",b.Body.position.z>.02f,b.Body.position.z,.02f);Check("equal_rpm_approximately_straight",Mathf.Abs(b.Body.position.x)<.002f,b.Body.position.x,.002f);b.portCommand=b.starboardCommand=0;Run(b,3);Check("motor_cut_coasts_to_stop",b.Body.linearVelocity.magnitude<speed*.45f,b.Body.linearVelocity.magnitude/speed,.45f);Remove(b);
                b=Spawn();b.portCommand=.35f;b.starboardCommand=-.35f;Run(b,3);float right=b.Body.angularVelocity.y;Remove(b);b=Spawn();b.portCommand=-.35f;b.starboardCommand=.35f;Run(b,3);float left=b.Body.angularVelocity.y;Check("opposite_differential_turns",right>.04f&&left<-.04f,right,.04f);Remove(b);
                b=Spawn();b.portCommand=b.starboardCommand=-.4f;Run(b,3);Check("negative_rpm_reverses",b.Body.position.z<-.02f,b.Body.position.z,-.02f);Remove(b);
                water.current=new Vector3(.008f,0,0);b=Spawn();Run(b,4);Check("unpowered_current_drift",b.Body.position.x>.005f,b.Body.position.x,.005f);Remove(b);water.current=Vector3.zero;
                var wall=GameObject.CreatePrimitive(PrimitiveType.Cube);wall.name="ContactWall";wall.transform.position=new Vector3(0,.02f,.075f);wall.transform.localScale=new Vector3(.2f,.1f,.01f);wall.GetComponent<Collider>().contactOffset=.0001f;
                b=Spawn();b.Body.linearVelocity=new Vector3(0,0,.08f);Physics.SyncTransforms();Run(b,2);Check("physx_wall_blocks_hull",b.Body.position.z<.04f,b.Body.position.z,.04f);Check("physx_contact_changes_velocity",b.Body.linearVelocity.z<.005f,b.Body.linearVelocity.z,.005f);Remove(b);UnityEngine.Object.DestroyImmediate(wall);
                b=Spawn();Run(b,8,dt/2);Check("half_step_float_agrees_under_0_1mm",Vector3.Distance(b.Body.position,emptyPosition)<.0001f,Vector3.Distance(b.Body.position,emptyPosition),.0001f);Remove(b);
                b=Spawn();b.ResetState(new Vector3(0,0,0),Quaternion.Euler(0,0,110));Check("capsize_state_detected",b.Capsized);Remove(b);
                var floor=GameObject.CreatePrimitive(PrimitiveType.Cube);floor.name="GroundingFloor";floor.transform.position=new Vector3(0,-.002f,0);floor.transform.localScale=new Vector3(.3f,.01f,.3f);floor.GetComponent<Collider>().contactOffset=.0001f;water.bottom=.003f;
                b=Spawn();b.ResetState(new Vector3(0,.008f,0),Quaternion.identity);Physics.SyncTransforms();Run(b,3);Check("seabed_prevents_sinking",b.Body.position.y>.0025f,b.Body.position.y,.0025f);Remove(b);UnityEngine.Object.DestroyImmediate(floor);
            }
            finally {Physics.simulationMode=oldMode;}
            report.allPassed=report.checks.All(c=>c.passed);Directory.CreateDirectory("Reports");File.WriteAllText("Reports/PhysX_Validation_Report.json",JsonUtility.ToJson(report,true));
            Debug.Log("PHYSX_VALIDATION: "+report.checks.Count+" checks, passed="+report.allPassed);
            if(!report.allPassed)throw new Exception("Physics checks failed: "+string.Join(", ",report.checks.Where(c=>!c.passed).Select(c=>c.name+"="+c.value)));
        }
    }
}
