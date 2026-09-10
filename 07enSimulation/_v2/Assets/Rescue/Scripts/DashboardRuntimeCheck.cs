using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;
namespace RescueSim
{
    public sealed class DashboardRuntimeCheck:MonoBehaviour
    {
        [Serializable] class Result {public bool passed,complete,exportValid,resetValid,pauseValid,dockedValid;public int rescued,samples;public float seconds;public string exportFolder,runId;}
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Launch(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-dashboardCheck")>=0)new GameObject("Dashboard_Runtime_Check").AddComponent<DashboardRuntimeCheck>();}
        IEnumerator Start()
        {
            yield return null;
            var ui=FindFirstObjectByType<RescueDashboard>();var m=ui.mission;var e=m.fleet.environment;var t=ui.telemetry;
            string folder=Path.GetFullPath(Path.Combine(Application.dataPath,"../../../Reports"));
            ui.ApplyPreset(1);ui.SetSpeed(3);e.clock.paused=true;float time=m.simulationSeconds;
            yield return new WaitForSecondsRealtime(.2f);var result=new Result{pauseValid=m.simulationSeconds==time};e.clock.paused=false;
            bool captured=false;
            while(!m.Complete&&m.simulationSeconds<260)
            {
                yield return new WaitForSeconds(5);
                if(!captured&&m.simulationSeconds>8)
                {
                    yield return CaptureScreen(ui,Path.Combine(folder,"Runtime_ControlRoom_UI.png"));captured=true;
                }
                File.WriteAllText(Path.Combine(folder,"Step8_Runtime_Progress.json"),JsonUtility.ToJson(t.GetSnapshot(),true));
            }
            e.clock.paused=true;ui.SetSpeed(1);yield return null;
            var data=t.GetSnapshot();result.complete=m.Complete;result.rescued=data.rescued;result.seconds=data.simulationSeconds;result.samples=data.recordedSamples;result.runId=data.runId;
            result.dockedValid=!m.launch||(m.launch.AllParked&&m.launch.parked.All(v=>v)&&m.fleet.dispatcher.boats.All(b=>b.Body.isKinematic&&b.PortRpm==0&&b.StarboardRpm==0));
            result.exportFolder=t.Export();result.exportValid=false;
            if(result.exportFolder!=null)
            {
                var saved=JsonUtility.FromJson<MissionTelemetry.Snapshot>(File.ReadAllText(Path.Combine(result.exportFolder,"summary.json")));
                result.exportValid=saved.rescued==24&&saved.boats.Length==4&&saved.people.Length==24&&saved.people.All(p=>p.boardedAt>=0&&p.rescuedAt>=p.boardedAt)&&saved.boats.All(b=>b.distanceM>0&&b.onboard==0)&&File.ReadAllLines(Path.Combine(result.exportFolder,"people.csv")).Length==25&&File.ReadAllLines(Path.Combine(result.exportFolder,"boats.csv")).Length==5&&File.ReadAllLines(Path.Combine(result.exportFolder,"telemetry.csv")).Length==saved.recordedSamples+1;
            }
            yield return CaptureScreen(ui,Path.Combine(folder,"Runtime_ControlRoom_Complete_UI.png"));
            ui.leftTab=2;ui.SetRoofVisible(false);m.fleet.CameraControls.FocusBoat();
            e.ResetScenario();result.resetValid=t.GetSnapshot().runId!=result.runId&&m.rescued==0&&t.CompletionSeconds<0&&t.GetSnapshot().recordedSamples==0;
            result.passed=result.complete&&result.exportValid&&result.resetValid&&result.pauseValid&&result.dockedValid;
            File.WriteAllText(Path.Combine(folder,"Step8_Runtime_Report.json"),JsonUtility.ToJson(result,true));Application.Quit(result.passed?0:1);
        }
        static IEnumerator CaptureScreen(RescueDashboard ui,string path)
        {
            var rt=new RenderTexture(Screen.width,Screen.height,24);rt.Create();var old=RenderTexture.active;
            var camera=ui.mission.fleet.environment.overview;camera.targetTexture=rt;camera.Render();camera.targetTexture=null;
            ui.captureTarget=rt;yield return new WaitForEndOfFrame();
            RenderTexture.active=rt;var image=new Texture2D(rt.width,rt.height,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,rt.width,rt.height),0,0);image.Apply();
            File.WriteAllBytes(path,image.EncodeToPNG());ui.captureTarget=null;RenderTexture.active=old;rt.Release();Destroy(rt);Destroy(image);
        }
    }
}
