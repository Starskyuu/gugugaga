using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace RescueSim.Editor
{
    public static class FleetValidation
    {
        [Serializable] class Check {public string name;public bool passed;public float value;}
        [Serializable] class Report {public bool allPassed;public List<Check> checks=new List<Check>();}
        public static void Validate()
        {
            EditorSceneManager.OpenScene(BuildFleetRescue.ScenePath);
            var f=UnityEngine.Object.FindFirstObjectByType<FleetScenario>();var d=f.dispatcher;var e=f.environment;var report=new Report();
            void Assert(string name,bool passed,float value=0){report.checks.Add(new Check{name=name,passed=passed,value=value});}
            foreach(var b in d.boats)b.Initialize();foreach(var v in d.victims)v.Initialize();
            Assert("station_is_center",d.station.position==Vector3.zero);
            Assert("four_boats_and_24_people",d.boats.Length==4&&d.victims.Length==24);
            Assert("unique_person_ids",d.victims.Select(v=>v.personId).Distinct().Count()==24);
            Physics.SyncTransforms();
            bool clear=true;
            foreach(var v in d.victims)clear&=Physics.OverlapSphere(v.transform.position,.006f).All(c=>c.transform.IsChildOf(v.transform));
            Assert("people_spawn_without_obstacle_overlap",clear);
            bool exits=true;
            foreach(var b in d.boats)
            {
                Vector3 start=b.transform.position+Vector3.up*.018f;
                exits&=!Physics.Raycast(start+b.transform.forward*.043f,b.transform.forward,.065f);
            }
            Assert("four_outward_launch_corridors_clear",exits);
            d.Dispatch(true);
            Assert("all_people_reserved_once",d.Waiting==0&&Enumerable.Range(0,4).Sum(d.Reserved)==24);
            Assert("six_reservations_per_boat",Enumerable.Range(0,4).All(i=>d.Reserved(i)==6));
            var owners=d.victims.Select(v=>v.assignedBoat).ToArray();d.Dispatch();Assert("valid_assignments_stable",owners.SequenceEqual(d.victims.Select(v=>v.assignedBoat)));
            d.SetAvailable(0,false);Assert("unavailable_boat_releases_tasks",d.Reserved(0)==0&&d.Waiting==6);
            Assert("automatic_dispatch_preempts_lower_priority",d.victims.Where(v=>v.urgency==2).All(v=>v.assignedBoat>=0));
            d.Dispatch(true);Assert("critical_people_prioritized_under_shortage",d.victims.Where(v=>v.urgency==2).All(v=>v.assignedBoat>=0));
            d.SetAvailable(0,true);d.boats[0].SetPassengerCount(4,false);d.Dispatch();Assert("payload_reduces_reservations",d.Reserved(0)==2&&d.Waiting==4);
            d.boats[0].SetPassengerCount(0,false);d.Dispatch();
            d.boats[1].ResetState(f.boatSpawns[1],Quaternion.Euler(180,90,0));d.Dispatch();Assert("capsized_boat_unassigned",d.Reserved(1)==0&&d.Waiting==6);
            d.boats[1].ResetState(f.boatSpawns[1],f.boatRotations[1]);d.Dispatch();
            d.victims[0].gameObject.SetActive(false);d.Dispatch();Assert("inactive_person_released",d.victims[0].assignedBoat==-1);d.victims[0].gameObject.SetActive(true);d.Dispatch();
            var old=Physics.simulationMode;Physics.simulationMode=SimulationMode.Script;
            try
            {
                e.water.regionalFlow=false;e.water.current=new Vector3(0,0,.015f);
                var p=d.victims[1];p.ResetPerson();float initial=p.Body.position.z;
                for(int k=0;k<2880;k++)
                {
                    foreach(var b in d.boats)b.ApplyForces(1f/960);
                    foreach(var v in d.victims)v.ApplyForces(1f/960);
                    foreach(var c in e.debris)c.ApplyForces();Physics.Simulate(1f/960);
                }
                Assert("person_drifts_by_physical_flow",p.Body.position.z-initial>.01f,p.Body.position.z-initial);
                Assert("person_remains_afloat",p.Body.position.y>-.006f&&p.Body.position.y<.002f,p.Body.position.y);
                Assert("waiting_time_uses_simulation_time",Mathf.Abs(p.waitingSeconds-3)<.01f,p.waitingSeconds);
                Assert("all_four_boats_remain_upright",d.boats.All(b=>b.TiltDegrees<15));
                Assert("shared_clock_has_people_and_fleet",e.clock.boats.Length==4&&e.clock.victims.Length==24);
            }
            finally{Physics.simulationMode=old;}
            report.allPassed=report.checks.All(c=>c.passed);File.WriteAllText("Reports/Fleet_Validation_Report.json",JsonUtility.ToJson(report,true));
            if(!report.allPassed)throw new Exception("Fleet tests failed: "+string.Join(", ",report.checks.Where(c=>!c.passed).Select(c=>c.name)));
            Debug.Log("FLEET_VALIDATION_PASSED "+report.checks.Count);
        }
    }
}
