using System;
using System.Collections;
using System.IO;
using UnityEngine;
namespace RescueSim
{
    // Opt-in build verification only; never runs during an ordinary launch.
    public sealed class RuntimeSmoke : MonoBehaviour
    {
        [Serializable] class Result {public bool passed;public float mass,speed,draft,tilt,travel;public int passengers;public string engine;}
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Launch()
        {
            if(Array.IndexOf(Environment.GetCommandLineArgs(),"-rescueSmoke")>=0)new GameObject("Runtime_Smoke_Check").AddComponent<RuntimeSmoke>();
        }
        IEnumerator Start()
        {
            yield return null;
            var lab=FindFirstObjectByType<PhysicsLab>();lab.UseSliders();var b=lab.boat;
            Vector3 start=b.Body.position;b.portCommand=b.starboardCommand=.35f;
            yield return new WaitForSeconds(2);
            float travel=b.Body.position.z-start.z;b.portCommand=b.starboardCommand=0;b.SetPassengerCount(2);lab.ShowFollowCamera();
            yield return new WaitForSeconds(5);
            string folder=Path.GetFullPath(Path.Combine(Application.dataPath,"../../../Reports"));Directory.CreateDirectory(folder);
            // Explicit offscreen rendering also works when the smoke-test
            // process has no visible desktop window. The image is a camera
            // preview; runtime controls are checked through the same public API.
            var rt=new RenderTexture(1440,900,24);rt.Create();var camera=lab.follow;
            camera.targetTexture=rt;camera.Render();var previous=RenderTexture.active;RenderTexture.active=rt;
            var image=new Texture2D(1440,900,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,1440,900),0,0);image.Apply();
            File.WriteAllBytes(Path.Combine(folder,"Runtime_Physics_Lab.png"),image.EncodeToPNG());RenderTexture.active=previous;camera.targetTexture=null;rt.Release();Destroy(rt);Destroy(image);
            var result=new Result {mass=b.Body.mass,speed=b.Body.linearVelocity.magnitude,draft=b.Draft,tilt=b.TiltDegrees,travel=travel,passengers=b.Passengers,engine=Application.unityVersion};
            result.passed=travel>.005f&&Mathf.Abs(result.mass-.014f)<1e-6f&&result.draft>0&&result.tilt<12;
            File.WriteAllText(Path.Combine(folder,"Runtime_Smoke_Report.json"),JsonUtility.ToJson(result,true));
            yield return new WaitForSeconds(2);Application.Quit(result.passed?0:1);
        }
    }
}
