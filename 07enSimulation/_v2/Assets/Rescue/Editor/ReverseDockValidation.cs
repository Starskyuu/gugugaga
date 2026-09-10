using System;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEditor.SceneManagement;
namespace RescueSim.Editor
{
    public static class ReverseDockValidation
    {
        public static void Validate()
        {
            EditorSceneManager.OpenScene(BuildRescueDashboard.ScenePath);var m=UnityEngine.Object.FindFirstObjectByType<RescueMission>();var f=m.fleet;var e=f.environment;
            e.Preset(1);m.Initialize();m.rescued=24;
            foreach(var v in f.dispatcher.victims){v.state=RescueVictim.RescueState.Rescued;v.gameObject.SetActive(false);}
            m.launch.elapsed=10;
            for(int i=0;i<4;i++){m.launch.departed[i]=true;var b=f.dispatcher.boats[i];b.ResetState(m.dockPoints[i]+Vector3.down*.00456848f,Quaternion.Euler(0,i*90+140,0));b.Body.isKinematic=false;}
            var reversed=new bool[4];var old=Physics.simulationMode;Physics.simulationMode=SimulationMode.Script;
            try
            {
                for(int frame=0;frame<120*60&&!m.Complete;frame++)
                {
                    m.Tick(1f/60);
                    for(int sub=0;sub<16;sub++){foreach(var b in f.dispatcher.boats)b.ApplyForces(1f/960);Physics.Simulate(1f/960);}
                    for(int i=0;i<4;i++){var b=f.dispatcher.boats[i];reversed[i]|=m.agents[i].phase==RescueMission.Phase.Reversing&&Vector3.Dot(b.Body.linearVelocity,b.transform.forward)<-.005f&&b.PortRpm+b.StarboardRpm<0;}
                    if(frame%300==0)File.WriteAllLines("Reports/Reverse_Progress.txt",new[]{"seconds="+m.simulationSeconds,"closing="+m.launch.closing}.Concat(m.agents.Select((a,i)=>i+" "+a.phase+" pos="+f.dispatcher.boats[i].Body.position.ToString("F4")+" yaw="+f.dispatcher.boats[i].transform.eulerAngles.y+" rpm="+f.dispatcher.boats[i].PortRpm+","+f.dispatcher.boats[i].StarboardRpm)));
                }
            }
            finally{Physics.simulationMode=old;}
            File.WriteAllText("Reports/Reverse_Check.txt","complete="+m.Complete+" seconds="+m.simulationSeconds+" physicalReverse="+string.Join(",",reversed)+" collisions="+string.Join(",",f.dispatcher.boats.Select(b=>b.CollisionCount)));
            if(!m.Complete||!reversed.All(v=>v)||f.dispatcher.boats.Any(b=>b.CollisionCount>0))throw new Exception("Reverse docking validation failed");
        }
    }
}
