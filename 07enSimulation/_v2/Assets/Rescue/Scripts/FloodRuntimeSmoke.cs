using System;
using System.Collections;
using System.IO;
using UnityEngine;
namespace RescueSim
{
    // Explicit opt-in verification; ordinary launches never execute this.
    public sealed class FloodRuntimeSmoke:MonoBehaviour
    {
        [Serializable] class Result { public bool passed;public float debrisTravel,waterRise;public int debrisCount;public string engine; }
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Launch(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-floodSmoke")>=0)new GameObject("Flood_Runtime_Check").AddComponent<FloodRuntimeSmoke>();}
        IEnumerator Start()
        {
            yield return null;
            var e=FindFirstObjectByType<FloodEnvironment>();e.UseSliders();e.Preset(1);e.ResetScenario();
            Vector3 initial=e.debris[0].transform.position;
            yield return new WaitForSeconds(3);
            float travel=Vector3.Distance(initial,e.debris[0].transform.position),oldLevel=e.water.level;
            e.Preset(2);float rise=e.water.level-oldLevel;
            yield return new WaitForSeconds(2);
            e.Preset(1);e.ResetScenario();
            yield return new WaitForSeconds(1);
            string folder=Path.GetFullPath(Path.Combine(Application.dataPath,"../../../Reports"));Directory.CreateDirectory(folder);
            var rt=new RenderTexture(1440,900,24);rt.Create();var cam=e.overview;cam.targetTexture=rt;cam.Render();
            var previous=RenderTexture.active;RenderTexture.active=rt;
            var png=new Texture2D(1440,900,TextureFormat.RGB24,false);png.ReadPixels(new Rect(0,0,1440,900),0,0);png.Apply();
            File.WriteAllBytes(Path.Combine(folder,"Runtime_Flood_Environment.png"),png.EncodeToPNG());RenderTexture.active=previous;cam.targetTexture=null;rt.Release();Destroy(rt);Destroy(png);
            var result=new Result{passed=travel>.005f&&Mathf.Abs(rise-.015f)<1e-6f&&e.debris.Length==8,debrisTravel=travel,waterRise=rise,debrisCount=e.debris.Length,engine=Application.unityVersion};
            File.WriteAllText(Path.Combine(folder,"Flood_Runtime_Report.json"),JsonUtility.ToJson(result,true));Application.Quit(result.passed?0:1);
        }
    }
}
