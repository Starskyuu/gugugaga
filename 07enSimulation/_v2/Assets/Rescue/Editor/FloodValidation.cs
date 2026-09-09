using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
namespace RescueSim.Editor
{
    public static class FloodValidation
    {
        [Serializable]class Result{public bool allPassed;public List<Item> checks=new List<Item>();}
        [Serializable]class Item{public string name;public bool passed;public float value;}
        public static void Validate()
        {
            EditorSceneManager.OpenScene(BuildFloodEnvironment.ScenePath);var e=UnityEngine.Object.FindFirstObjectByType<FloodEnvironment>();var w=e.water;var b=e.boat;b.Initialize();var report=new Result();var old=Physics.simulationMode;Physics.simulationMode=SimulationMode.Script;
            void Check(string n,bool p,float v=0)=>report.checks.Add(new Item{name=n,passed=p,value=v});
            void Step(float seconds){for(int i=0;i<Mathf.RoundToInt(seconds*960);i++){b.ApplyForces(1f/960);foreach(var d in e.debris)if(d.gameObject.activeSelf)d.ApplyForces();Physics.Simulate(1f/960);}}
            try
            {
                Check("regional_current_differs_from_background",w.VelocityAt(new Vector3(0,0,.22f)).magnitude>w.current.magnitude+.02f);
                Check("shelf_depth_3mm",Mathf.Abs(w.DepthAt(new Vector3(-.20f,0,.26f))-.003f)<1e-6f);
                Check("open_water_depth_30mm",Mathf.Abs(w.DepthAt(Vector3.zero)-.03f)<1e-6f);
                w.level=-.01f;Check("exposed_shelf_has_no_water",!w.HasWater(new Vector3(-.20f,0,.26f))&&w.VelocityAt(new Vector3(-.20f,0,.26f))==Vector3.zero);w.level=0;
                Check("outside_domain_has_no_flow",w.VelocityAt(new Vector3(2,0,2))==Vector3.zero&&!w.HasWater(new Vector3(2,0,2)));
                e.SetDebris(false);w.regionalFlow=false;w.current=Vector3.zero;b.ResetState(new Vector3(0,-.00456848f,-.15f),Quaternion.identity);Step(3);float low=b.Body.position.y;
                w.level=.015f;Step(4);Check("rising_water_lifts_boat",b.Body.position.y-low>.013f,b.Body.position.y-low);w.level=0;
                b.ResetState(new Vector3(-.20f,.01f,.26f),Quaternion.identity);Step(4);Check("shelf_physx_contact_supports_boat",b.Body.position.y>-.004f,b.Body.position.y);Check("grounding_detected_on_shelf",b.Grounded);
                w.current=new Vector3(0,0,.015f);b.ResetState(new Vector3(0,-.00456848f,0),Quaternion.identity);e.SetDebris(true);var d0=e.debris[0];d0.ResetAt(new Vector3(.09f,.004f,-.03f));float initial=d0.Body.position.z;Step(3);Check("debris_drifts_with_flow",d0.Body.position.z-initial>.008f,d0.Body.position.z-initial);Check("debris_floats",d0.Body.position.y>-.012f&&d0.Body.position.y<.012f,d0.Body.position.y);
                e.SetDebris(false);w.current=Vector3.zero;b.ResetState(new Vector3(.19f,-.0045f,-.16f),Quaternion.Euler(0,90,0));b.portCommand=b.starboardCommand=.5f;Step(4);Check("building_stops_driven_boat",b.Body.position.x<.235f,b.Body.position.x);
                Check("danger_region_reports_strong_flow",SetFastAndRisk(e)=="STRONG CURRENT");
                Check("eight_debris_share_physics_clock",e.debris.Length==8&&e.clock.debris.Length==8);
            }
            finally{Physics.simulationMode=old;}
            report.allPassed=report.checks.All(x=>x.passed);File.WriteAllText("Reports/Flood_Validation_Report.json",JsonUtility.ToJson(report,true));
            if(!report.allPassed)throw new Exception("Flood validation failed: "+string.Join(",",report.checks.Where(x=>!x.passed).Select(x=>x.name+"="+x.value)));
            Debug.Log("FLOOD_VALIDATION_PASSED "+report.checks.Count);
        }
        static string SetFastAndRisk(FloodEnvironment e){e.water.current=new Vector3(0,0,.008f);e.water.regionalFlow=true;return e.RiskAt(new Vector3(0,0,.22f));}
    }
}
