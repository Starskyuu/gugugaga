using System.IO;
using System.Linq;
using UnityEngine;
using UnityEditor.SceneManagement;
namespace RescueSim.Editor
{
    public static class LaunchDiagnostics
    {
        public static void Inspect()
        {
            EditorSceneManager.OpenScene(BuildRescueDashboard.ScenePath);
            var m=Object.FindFirstObjectByType<RescueMission>();
            Physics.SyncTransforms();
            File.WriteAllLines("Reports/Launch_Geometry.txt",m.fleet.dispatcher.station.GetComponentsInChildren<Renderer>().Where(r=>r.name.ToLower().Contains("door")||r.name.ToLower().Contains("floor")||r.name.ToLower().Contains("foundation")).Select(r=>r.name+" center="+r.bounds.center.ToString("F5")+" size="+r.bounds.size.ToString("F5"))
                .Concat(m.fleet.dispatcher.station.GetComponentsInChildren<Collider>().Select(c=>"COL "+c.name+" center="+c.bounds.center.ToString("F5")+" size="+c.bounds.size.ToString("F5"))));
        }
    }
}
