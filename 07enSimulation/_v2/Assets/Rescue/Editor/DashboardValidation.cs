using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace RescueSim.Editor
{
    public static class DashboardValidation
    {
        [Serializable] class CaseResult {public string name,expected,outcome;public bool passed,countsValid,massValid,capacityValid;public float seconds,maxPassengers;public int rescued;public int[] contacts;}
        [Serializable] class SuiteResult {public bool passed;public List<CaseResult> cases=new List<CaseResult>();}
        public static void Validate()
        {
            var suite=new SuiteResult();
            Run("Calm_24_People",0,-1,180,true,suite);
            Run("Street_24_People",1,-1,180,true,suite);
            Run("Three_Boats_24_People",1,3,240,true,suite);
            Run("Shallow_Reject_Unsafe_Routes",3,-1,12,false,suite);
            Run("High_Water_Stress",2,-1,35,false,suite);
            suite.passed=suite.cases.All(c=>c.passed);File.WriteAllText("Reports/Step8_Validation_Report.json",JsonUtility.ToJson(suite,true));
            if(!suite.passed)throw new Exception("Step8 scenario checks failed: "+string.Join(", ",suite.cases.Where(c=>!c.passed).Select(c=>c.name)));
        }
        static void Run(string name,int preset,int disabled,float limit,bool requireCompletion,SuiteResult suite)
        {
            EditorSceneManager.OpenScene(BuildRescueDashboard.ScenePath);var ui=UnityEngine.Object.FindFirstObjectByType<RescueDashboard>();var m=ui.mission;var f=m.fleet;var e=f.environment;
            e.Preset(preset);m.Initialize();ui.telemetry.scenario=name;ui.telemetry.autoExport=false;
            for(int i=0;i<4;i++)f.dispatcher.boats[i].ResetState(new Vector3(f.boatSpawns[i].x,e.water.level-.00456848f,f.boatSpawns[i].z),f.boatRotations[i]);
            foreach(var p in f.dispatcher.victims)p.ResetPerson();foreach(var d in e.debris)d.ResetAt(new Vector3(d.transform.position.x,e.water.level+.004f,d.transform.position.z));
            if(disabled>=0)f.dispatcher.SetAvailable(disabled,false);Physics.SyncTransforms();m.navigation.Rebuild();ui.telemetry.BeginRun();
            var r=new CaseResult{name=name,expected=requireCompletion?"Complete with no more than six per boat":preset==3?"No false rescue in non-navigable shallow water":"Bounded stress run; partial rescue permitted",countsValid=true,massValid=true,capacityValid=true};
            var previous=Physics.simulationMode;Physics.simulationMode=SimulationMode.Script;
            try
            {
                for(int frame=0;frame<Mathf.RoundToInt(limit*60)&&!m.Complete;frame++)
                {
                    m.Tick(1f/60);
                    for(int sub=0;sub<16;sub++)
                    {
                        foreach(var b in f.dispatcher.boats)b.ApplyForces(1f/960);
                        foreach(var d in e.debris)if(d.isActiveAndEnabled)d.ApplyForces();
                        foreach(var v in f.dispatcher.victims)if(v.isActiveAndEnabled)v.ApplyForces(1f/960);Physics.Simulate(1f/960);
                    }
                    ui.telemetry.Sample(1f/60);
                    r.massValid&=f.dispatcher.boats.All(b=>Mathf.Abs(b.Body.mass-(.012f+.001f*b.Passengers))<2e-6f);
                    r.capacityValid&=f.dispatcher.boats.All(b=>b.Passengers>=0&&b.Passengers<=6);
                    var cargo=m.agents.SelectMany(a=>a.onboard).ToArray();r.countsValid&=cargo.Select(v=>v.personId).Distinct().Count()==cargo.Length&&m.rescued==f.dispatcher.victims.Count(v=>v.state==RescueVictim.RescueState.Rescued)&&cargo.Length==f.dispatcher.boats.Sum(b=>b.Passengers);
                    if(frame%1800==0)File.WriteAllText("Reports/Step8_Progress.json",JsonUtility.ToJson(new CaseResult{name=name,seconds=m.simulationSeconds,rescued=m.rescued,outcome=string.Join(" | ",m.agents.Select(a=>a.phase+":"+a.message))},true));
                }
            }
            finally{Physics.simulationMode=previous;}
            r.seconds=m.simulationSeconds;r.rescued=m.rescued;r.maxPassengers=m.maxPassengers;r.contacts=f.dispatcher.boats.Select(b=>b.CollisionCount).ToArray();r.outcome=m.Complete?"Complete":preset==3?"ShallowBlocked":"Partial";
            r.passed=r.countsValid&&r.massValid&&r.capacityValid&&(!requireCompletion||m.Complete)&&(preset!=3||m.rescued==0);
            suite.cases.Add(r);File.WriteAllText("Reports/Step8_Validation_Report.json",JsonUtility.ToJson(suite,true));
            Debug.Log("STEP8_CASE "+name+" passed="+r.passed+" rescued="+r.rescued);
        }
    }
}
