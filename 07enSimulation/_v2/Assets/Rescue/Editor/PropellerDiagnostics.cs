using System.IO;
using System.Linq;
using System.Text;
using UnityEditor.SceneManagement;
using UnityEngine;
namespace RescueSim.Editor
{
    public static class PropellerDiagnostics
    {
        public static void Inspect()
        {
            EditorSceneManager.OpenScene(BuildFleetRescue.ScenePath);
            var b=Object.FindFirstObjectByType<FleetScenario>().dispatcher.boats[0];b.Initialize();var report=new StringBuilder();
            foreach(var t in b.GetComponentsInChildren<Transform>())
            {
                string n=t.name.ToLowerInvariant();if(!n.Contains("rotor")&&!n.Contains("prop")&&!n.Contains("blade"))continue;
                report.AppendLine(t.name+" parent="+t.parent?.name+" children="+t.childCount+" meshes="+t.GetComponentsInChildren<MeshRenderer>().Length+" local="+t.localPosition+" boat="+b.transform.InverseTransformPoint(t.position));
            }
            b.portCommand=b.starboardCommand=.45f;for(int i=0;i<960;i++)b.ApplyForces(1f/960);
            report.AppendLine("Port RPM="+b.PortRpm+" Starboard RPM="+b.StarboardRpm);
            File.WriteAllText("Reports/Propeller_Diagnostics.txt",report.ToString());Debug.Log(report.ToString());
        }
    }
}
