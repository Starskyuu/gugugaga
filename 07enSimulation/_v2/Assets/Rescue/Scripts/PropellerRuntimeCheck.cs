using System;
using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;
namespace RescueSim
{
    public sealed class PropellerRuntimeCheck:MonoBehaviour
    {
        [Serializable] class Report {public bool passed,allFourBoatsBound,guardUnchanged;public float portRpm,starboardRpm,portVertexTravel,starboardVertexTravel,portRotationChange,elapsed;}
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Launch(){if(Array.IndexOf(Environment.GetCommandLineArgs(),"-propellerCheck")>=0)new GameObject("Propeller_Runtime_Check").AddComponent<PropellerRuntimeCheck>();}
        static Vector3 Tip(MeshFilter mesh,BoatDynamics boat)
        {
            var vertices=mesh.sharedMesh.vertices;
            return boat.transform.InverseTransformPoint(mesh.transform.TransformPoint(vertices.OrderByDescending(v=>new Vector2(v.x,v.y).sqrMagnitude).First()));
        }
        IEnumerator Start()
        {
            yield return null;
            var fleet=FindFirstObjectByType<FleetScenario>();var e=fleet.environment;var b=e.boat;e.UseSliders();e.Preset(0);e.ResetScenario();
            b.Body.constraints=RigidbodyConstraints.FreezeAll;
            var port=b.portRotor.GetComponentsInChildren<MeshFilter>().First(m=>m.name=="Port_screw_blade");
            var starboard=b.starboardRotor.GetComponentsInChildren<MeshFilter>().First(m=>m.name=="Starboard_screw_blade");
            var guard=b.GetComponentsInChildren<MeshFilter>().First(m=>m.name=="Port_propeller_safety_shroud");
            var report=new Report{allFourBoatsBound=fleet.dispatcher.boats.All(boat=>boat.portRotor.GetComponentsInChildren<MeshFilter>().Length>=4&&boat.starboardRotor.GetComponentsInChildren<MeshFilter>().Length>=4)};
            b.portCommand=.12f;b.starboardCommand=.18f;yield return new WaitForSeconds(.5f);
            yield return new WaitForEndOfFrame();
            Vector3 p=Tip(port,b),s=Tip(starboard,b),g=Tip(guard,b);Quaternion q=b.portRotor.localRotation;float time=Time.time;
            string folder=Path.GetFullPath(Path.Combine(Application.dataPath,"../../../Reports"));
            var c=e.overview;e.SetFollowCamera(false);fleet.showAssignments=false;
            // Stern close-up of the real blades; hide only the water surface
            // during this diagnostic render so submerged blades are visible.
            e.surface.gameObject.SetActive(false);
            c.transform.position=b.transform.TransformPoint(new Vector3(0,.025f,-.10f));c.transform.LookAt(b.transform.TransformPoint(new Vector3(0,.0038f,-.0388f)));c.orthographicSize=.024f;
            Capture(c,Path.Combine(folder,"Propeller_Frame_A.png"));
            yield return new WaitForSeconds(.047f);yield return new WaitForEndOfFrame();
            report.portRotationChange=Quaternion.Angle(q,b.portRotor.localRotation);report.elapsed=Time.time-time;
            report.portVertexTravel=Vector3.Distance(p,Tip(port,b));report.starboardVertexTravel=Vector3.Distance(s,Tip(starboard,b));report.guardUnchanged=Vector3.Distance(g,Tip(guard,b))<1e-7f;
            report.portRpm=b.PortRpm;report.starboardRpm=b.StarboardRpm;Capture(c,Path.Combine(folder,"Propeller_Frame_B.png"));
            report.passed=report.allFourBoatsBound&&report.guardUnchanged&&report.portVertexTravel>.0001f&&report.starboardVertexTravel>.0001f&&report.portRpm>200&&report.starboardRpm>300;
            File.WriteAllText(Path.Combine(folder,"Propeller_Runtime_Report.json"),JsonUtility.ToJson(report,true));Application.Quit(report.passed?0:1);
        }
        static void Capture(Camera camera,string path)
        {
            var rt=new RenderTexture(1200,800,24);rt.Create();camera.targetTexture=rt;camera.Render();var previous=RenderTexture.active;RenderTexture.active=rt;
            var png=new Texture2D(1200,800,TextureFormat.RGB24,false);png.ReadPixels(new Rect(0,0,1200,800),0,0);png.Apply();File.WriteAllBytes(path,png.EncodeToPNG());
            RenderTexture.active=previous;camera.targetTexture=null;rt.Release();Destroy(rt);Destroy(png);
        }
    }
}
