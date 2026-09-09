using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.SceneManagement;
namespace RescueSim.Editor
{
    public static class BuildRescueMission
    {
        public const string ScenePath="Assets/Rescue/Scenes/AutonomousRescue.unity";
        [MenuItem("Rescue/Build Steps 6 and 7 Mission")]
        public static void Build()
        {
            EditorSceneManager.OpenScene(BuildFleetRescue.ScenePath);
            var fleet=UnityEngine.Object.FindFirstObjectByType<FleetScenario>();var e=fleet.environment;
            var mission=fleet.gameObject.AddComponent<RescueMission>();var navigation=fleet.gameObject.AddComponent<RescueNavigation>();
            fleet.mission=mission;fleet.dispatcher.mission=mission;e.clock.mission=mission;mission.fleet=fleet;mission.navigation=navigation;fleet.showAssignments=false;
            navigation.water=e.water;navigation.boats=fleet.dispatcher.boats;navigation.debris=e.debris;
            mission.dockPoints=new Vector3[4];for(int i=0;i<4;i++)mission.dockPoints[i]=Quaternion.Euler(0,i*90,0)*Vector3.forward*.26f;
            mission.seatedPrefab=AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Rescue/Prefabs/RescuePerson_Seated.prefab");
            var cushions=fleet.dispatcher.station.GetComponentsInChildren<Renderer>().Where(r=>r.name.Contains("_Bench_")&&r.name.Contains("_cushion_")).OrderBy(r=>r.name).ToArray();
            if(cushions.Length!=24)throw new Exception("Expected 24 refuge bench cushions");
            mission.refugeSeats=cushions.Select(r=>new Vector3(r.bounds.center.x,r.bounds.max.y,r.bounds.center.z)).ToArray();
            File.WriteAllLines("Reports/Station_Seat_Nodes.txt",fleet.dispatcher.station.GetComponentsInChildren<Renderer>().Where(r=>r.name.ToLowerInvariant().Contains("seat")||r.name.ToLowerInvariant().Contains("bench")||r.name.Contains("deck")).Select(r=>r.name+" center="+r.bounds.center.ToString("F5")+" size="+r.bounds.size.ToString("F5")));
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(),ScenePath);AssetDatabase.SaveAssets();
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true),new EditorBuildSettingsScene(BuildFleetRescue.ScenePath,true)};
        }
        public static void BuildAndValidate(){Build();MissionValidation.Validate();EditorSceneManager.OpenScene(ScenePath);}
        public static void BuildPlayer()
        {
            Directory.CreateDirectory("Builds/Mission");var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ScenePath,BuildFleetRescue.ScenePath},locationPathName="Builds/Mission/RescueMissionSimulation.exe",target=BuildTarget.StandaloneWindows64,options=BuildOptions.Development});
            if(result.summary.result!=BuildResult.Succeeded)throw new Exception("Mission build failed");
        }
    }
}
