using System;
using System.IO;
using System.Linq;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace RescueSim.Editor
{
    public static class MissionValidation
    {
        [Serializable] class Result {public bool passed;public float seconds,maxPassengers;public int rescued,boarded,unloaded;public string[] boats;public string[] people;}
        public static void Validate()
        {
            EditorSceneManager.OpenScene(BuildRescueMission.ScenePath);var m=UnityEngine.Object.FindFirstObjectByType<RescueMission>();m.Initialize();var f=m.fleet;var e=f.environment;
            var previous=Physics.simulationMode;Physics.simulationMode=SimulationMode.Script;
            Result Report()=>new Result{passed=m.Complete&&m.maxPassengers<=6,seconds=m.simulationSeconds,rescued=m.rescued,boarded=m.boardingEvents,unloaded=m.unloadingEvents,maxPassengers=m.maxPassengers,boats=m.agents.Select((a,i)=>"B"+(i+1)+" "+a.phase+" "+a.message+" target="+(a.target?a.target.personId:0)+" pos="+f.dispatcher.boats[i].Body.position.ToString("F3")+" speed="+f.dispatcher.boats[i].Body.linearVelocity.ToString("F3")+" path="+a.path.Count+" onboard="+a.onboard.Count).ToArray(),people=f.dispatcher.victims.Where(v=>v.InWater).Select(v=>v.personId+" "+v.Body.position.ToString("F3")).ToArray()};
            try
            {
                for(int frame=0;frame<60*240&&!m.Complete;frame++)
                {
                    m.Tick(1f/60);
                    for(int sub=0;sub<16;sub++)
                    {
                        foreach(var b in f.dispatcher.boats)b.ApplyForces(1f/960);
                        foreach(var d in e.debris)if(d.isActiveAndEnabled)d.ApplyForces();
                        foreach(var v in f.dispatcher.victims)if(v.isActiveAndEnabled)v.ApplyForces(1f/960);
                        Physics.Simulate(1f/960);
                    }
                    if(frame%1800==0){File.WriteAllText("Reports/Mission_Progress.json",JsonUtility.ToJson(Report(),true));Debug.Log("MISSION_PROGRESS "+m.simulationSeconds+" rescued="+m.rescued);}
                }
                var result=Report();File.WriteAllText("Reports/Mission_Validation_Report.json",JsonUtility.ToJson(result,true));if(!result.passed)throw new Exception("Mission incomplete: "+result.rescued+" / 24");
            }
            finally{Physics.simulationMode=previous;}
        }
    }
}
