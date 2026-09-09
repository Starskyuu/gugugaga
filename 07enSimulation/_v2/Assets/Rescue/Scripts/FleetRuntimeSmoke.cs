using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;
namespace RescueSim
{
    public sealed class FleetRuntimeSmoke:MonoBehaviour
    {
        [Serializable] class Result {public bool passed,assignment,capacity,pause,reset,selection,priority;public float drift;public string engine;}
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Launch(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-fleetSmoke")>=0)new GameObject("Fleet_Runtime_Check").AddComponent<FleetRuntimeSmoke>();}
        IEnumerator Start()
        {
            yield return null;
            var f=FindFirstObjectByType<FleetScenario>();var d=f.dispatcher;var e=f.environment;e.UseSliders();e.Preset(1);e.ResetScenario();d.Dispatch(true);
            var result=new Result{engine=Application.unityVersion};
            result.assignment=d.Waiting==0&&Enumerable.Range(0,4).All(i=>d.Reserved(i)==6);
            var person=d.victims[1];Vector3 start=person.Body.position;
            yield return new WaitForSeconds(3);result.drift=Vector3.Distance(start,person.Body.position);
            d.SetAvailable(0,false);result.capacity=d.Reserved(0)==0&&d.Waiting==6;result.priority=d.victims.Where(v=>v.urgency==2).All(v=>v.assignedBoat>=0);d.SetAvailable(0,true);
            e.clock.paused=true;float waiting=person.waitingSeconds;Vector3 pausedPosition=person.Body.position;
            yield return new WaitForSeconds(.5f);result.pause=Mathf.Abs(person.waitingSeconds-waiting)<1e-6f&&Vector3.Distance(person.Body.position,pausedPosition)<1e-6f;
            f.SelectBoat(2);result.selection=e.boat==d.boats[2];e.ResetScenario();result.reset=person.waitingSeconds==0&&Vector3.Distance(person.Body.position,new Vector3(person.spawn.x,e.water.level-.00275f,person.spawn.z))<1e-6f;
            f.SelectBoat(0);yield return null;
            string folder=Path.GetFullPath(Path.Combine(Application.dataPath,"../../../Reports"));Directory.CreateDirectory(folder);
            Capture(e.overview,Path.Combine(folder,"Runtime_Fleet_Overview.png"));
            Vector3 saved=e.overview.transform.position;Quaternion rotation=e.overview.transform.rotation;float span=e.overview.orthographicSize;
            e.overview.transform.position=new Vector3(.15f,.20f,.65f);e.overview.transform.LookAt(new Vector3(.02f,0,.43f));e.overview.orthographicSize=.16f;
            Capture(e.overview,Path.Combine(folder,"Runtime_Fleet_People_Closeup.png"));
            Capture(e.follow,Path.Combine(folder,"Runtime_Fleet_Boat_Follow.png"));
            e.overview.transform.SetPositionAndRotation(saved,rotation);e.overview.orthographicSize=span;
            result.passed=result.assignment&&result.capacity&&result.priority&&result.pause&&result.reset&&result.selection&&result.drift>.005f;
            File.WriteAllText(Path.Combine(folder,"Fleet_Runtime_Report.json"),JsonUtility.ToJson(result,true));Application.Quit(result.passed?0:1);
        }
        static void Capture(Camera camera,string path)
        {
            var rt=new RenderTexture(1440,900,24);rt.Create();camera.targetTexture=rt;camera.Render();var previous=RenderTexture.active;RenderTexture.active=rt;
            var png=new Texture2D(1440,900,TextureFormat.RGB24,false);png.ReadPixels(new Rect(0,0,1440,900),0,0);png.Apply();File.WriteAllBytes(path,png.EncodeToPNG());
            RenderTexture.active=previous;camera.targetTexture=null;rt.Release();Destroy(rt);Destroy(png);
        }
    }
}
