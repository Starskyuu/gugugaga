using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;
namespace RescueSim
{
    public sealed class MissionRuntimeCheck:MonoBehaviour
    {
        [Serializable] class Result
        {
            public bool passed,allPeopleRescued,massCorrect,resetCorrect,pauseCorrect,manualCorrect,detourCorrect,shallowRejected;
            public float seconds,maxPassengers;public int rescued,boardingEvents,unloadingEvents,plans;public float[] travel;public string[] states;
        }
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Launch(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-missionCheck")>=0)new GameObject("Mission_Runtime_Check").AddComponent<MissionRuntimeCheck>();}
        IEnumerator Start()
        {
            yield return null;
            var m=FindFirstObjectByType<RescueMission>();var f=m.fleet;var e=f.environment;
            var result=new Result();string folder=Path.GetFullPath(Path.Combine(Application.dataPath,"../../../Reports"));
            e.clock.paused=true;float initial=m.simulationSeconds;Vector3 pos=f.dispatcher.boats[0].Body.position;
            yield return new WaitForSeconds(.2f);result.pauseCorrect=m.simulationSeconds==initial&&Vector3.Distance(pos,f.dispatcher.boats[0].Body.position)<1e-7f;
            m.TakeManual(0);result.manualCorrect=m.IsManual(0)&&!f.dispatcher.Usable(0);m.ResumeBoat(0);result.manualCorrect&=!m.IsManual(0);
            var from=new Vector3(-.32f,0,-.30f);var to=new Vector3(.32f,0,.30f);var path=m.navigation.Plan(from,to,0);
            result.detourCorrect=path!=null&&path.Count>1&&!m.navigation.ClearLine(from,to,0);
            result.shallowRejected=!m.navigation.Walkable(e.water.bedZones[0].center,0);
            e.ResetScenario();e.clock.paused=false;m.running=true;Time.timeScale=3;
            bool captured=false;
            while(!m.Complete&&m.simulationSeconds<210)
            {
                yield return new WaitForSeconds(5);
                if(!captured&&m.simulationSeconds>8){Capture(e.overview,Path.Combine(folder,"Runtime_Mission_Outbound.png"));captured=true;}
                File.WriteAllText(Path.Combine(folder,"Mission_Runtime_Progress.json"),JsonUtility.ToJson(new Result{seconds=m.simulationSeconds,rescued=m.rescued,boardingEvents=m.boardingEvents,states=m.agents.Select(a=>a.phase+" "+a.message+" target="+(a.target?a.target.personId:0)+" onboard="+a.onboard.Count).ToArray()},true));
            }
            e.clock.paused=true;Time.timeScale=1;
            result.seconds=m.simulationSeconds;result.rescued=m.rescued;result.boardingEvents=m.boardingEvents;result.unloadingEvents=m.unloadingEvents;result.plans=m.plans;result.maxPassengers=m.maxPassengers;
            result.allPeopleRescued=m.Complete&&f.dispatcher.victims.All(v=>v.state==RescueVictim.RescueState.Rescued);
            result.massCorrect=f.dispatcher.boats.All(b=>b.Passengers==0&&Mathf.Abs(b.Body.mass-.012f)<1e-6f);
            result.travel=m.agents.Select(a=>a.travel).ToArray();result.states=m.agents.Select(a=>a.phase.ToString()).ToArray();
            Capture(e.overview,Path.Combine(folder,"Runtime_Mission_Complete.png"));
            // Show the refuge benches for result inspection, with only the
            // opaque roof hidden for this diagnostic camera capture.
            foreach(var r in f.dispatcher.station.GetComponentsInChildren<Renderer>())if(r.bounds.min.y>.125f)r.enabled=false;
            e.overview.transform.position=new Vector3(.15f,.23f,-.18f);e.overview.transform.LookAt(new Vector3(0,.095f,0));e.overview.orthographicSize=.115f;
            Capture(e.overview,Path.Combine(folder,"Runtime_Mission_Refuge.png"));
            e.ResetScenario();result.resetCorrect=m.rescued==0&&f.dispatcher.victims.All(v=>v.isActiveAndEnabled&&v.state==RescueVictim.RescueState.Water)&&f.dispatcher.boats.All(b=>b.Passengers==0);
            result.passed=result.allPeopleRescued&&result.massCorrect&&result.resetCorrect&&result.pauseCorrect&&result.manualCorrect&&result.detourCorrect&&result.shallowRejected&&result.maxPassengers<=6;
            File.WriteAllText(Path.Combine(folder,"Mission_Runtime_Report.json"),JsonUtility.ToJson(result,true));Application.Quit(result.passed?0:1);
        }
        static void Capture(Camera camera,string path)
        {
            var rt=new RenderTexture(1440,900,24);rt.Create();camera.targetTexture=rt;camera.Render();var old=RenderTexture.active;RenderTexture.active=rt;
            var png=new Texture2D(1440,900,TextureFormat.RGB24,false);png.ReadPixels(new Rect(0,0,1440,900),0,0);png.Apply();File.WriteAllBytes(path,png.EncodeToPNG());RenderTexture.active=old;camera.targetTexture=null;rt.Release();Destroy(rt);Destroy(png);
        }
    }
}
