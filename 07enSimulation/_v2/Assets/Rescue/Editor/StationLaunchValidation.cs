using System;
using System.IO;
using System.Linq;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace RescueSim.Editor
{
    public static class StationLaunchValidation
    {
        [Serializable] class Result {public int preset,rescued;public bool allDeparted,heldUntilOpen,cameraValid,resetValid,complete;public float seconds;public int[] collisions;public string[] phases;}
        public static void Validate(){Run(0);Run(1);}
        static void Run(int preset)
        {
            EditorSceneManager.OpenScene(BuildRescueDashboard.ScenePath);
            var m=UnityEngine.Object.FindFirstObjectByType<RescueMission>();var f=m.fleet;var e=f.environment;
            e.Preset(preset);m.Initialize();f.ResetFleet();Physics.SyncTransforms();
            var r=new Result{preset=preset,heldUntilOpen=true};
            var controls=f.gameObject.AddComponent<FleetCameraControls>();controls.Initialize(e);
            controls.Orbit(new Vector2(200,500));float low=e.overview.transform.eulerAngles.x;if(low>180)low-=360;
            controls.Pan(new Vector2(600,400),new Vector2(650,420));controls.Zoom(1,new Vector2(650,420));
            controls.Orbit(new Vector2(-200,-1000));float high=e.overview.transform.eulerAngles.x;
            r.cameraValid=low<0&&high>80&&!float.IsNaN(e.overview.transform.position.x);controls.ResetView();
            var oldMode=Physics.simulationMode;Physics.simulationMode=SimulationMode.Script;
            try
            {
                for(int frame=0;frame<260*60&&!m.Complete;frame++)
                {
                    m.Tick(1f/60);
                    if(m.launch.elapsed<3.3f)for(int i=0;i<4;i++)r.heldUntilOpen&=RescueNavigation.FlatDistance(f.dispatcher.boats[i].Body.position,f.boatSpawns[i])<.0001f;
                    for(int sub=0;sub<16;sub++)
                    {
                        foreach(var b in f.dispatcher.boats)b.ApplyForces(1f/960);
                        foreach(var d in e.debris)if(d.isActiveAndEnabled)d.ApplyForces();
                        foreach(var v in f.dispatcher.victims)if(v.isActiveAndEnabled)v.ApplyForces(1f/960);
                        Physics.Simulate(1f/960);
                    }
                    if(frame%600==0)
                    {
                        r.seconds=m.simulationSeconds;r.rescued=m.rescued;r.phases=m.agents.Select((a,i)=>a.phase+" "+f.dispatcher.boats[i].Body.position.ToString("F4")).ToArray();
                        File.WriteAllText("Reports/Launch_Progress.json",JsonUtility.ToJson(r,true));
                    }
                    if(preset==0&&(frame==0||frame==110||frame==420))Capture(e.overview,"Reports/Launch_Frame_"+frame+".png");
                }
                r.complete=m.Complete;r.seconds=m.simulationSeconds;r.rescued=m.rescued;r.allDeparted=m.launch.departed.All(v=>v);r.collisions=f.dispatcher.boats.Select(b=>b.CollisionCount).ToArray();
                f.ResetFleet();r.resetValid=m.launch.Opening==0&&m.launch.departed.All(v=>!v)&&f.dispatcher.boats.All(b=>b.Body.isKinematic);
            }
            finally{Physics.simulationMode=oldMode;}
            File.WriteAllText("Reports/Launch_Validation_"+preset+".json",JsonUtility.ToJson(r,true));
            if(!r.complete||!r.allDeparted||r.rescued!=24||!r.heldUntilOpen||!r.cameraValid||!r.resetValid)throw new Exception("Launch validation failed preset "+preset);
        }
        static void Capture(Camera c,string path)
        {
            var pos=c.transform.position;var rot=c.transform.rotation;float size=c.orthographicSize;
            c.transform.position=new Vector3(.36f,.21f,.45f);c.transform.LookAt(new Vector3(0,.035f,0));c.orthographicSize=.24f;
            var rt=new RenderTexture(1440,1000,24);rt.Create();var old=RenderTexture.active;var image=new Texture2D(1440,1000,TextureFormat.RGB24,false);
            c.targetTexture=rt;c.Render();RenderTexture.active=rt;image.ReadPixels(new Rect(0,0,1440,1000),0,0);image.Apply();File.WriteAllBytes(path,image.EncodeToPNG());c.targetTexture=null;RenderTexture.active=old;rt.Release();UnityEngine.Object.DestroyImmediate(rt);UnityEngine.Object.DestroyImmediate(image);
            c.transform.SetPositionAndRotation(pos,rot);c.orthographicSize=size;
        }
    }
}
