using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.SceneManagement;
namespace RescueSim.Editor
{
    public static class BuildRescueDashboard
    {
        public const string ScenePath="Assets/Rescue/Scenes/RescueControlRoom.unity";
        [MenuItem("Rescue/Build Step 8 Control Room")]
        public static void Build()
        {
            EditorSceneManager.OpenScene(BuildRescueMission.ScenePath);
            var mission=UnityEngine.Object.FindFirstObjectByType<RescueMission>();
            var dashboard=mission.gameObject.AddComponent<RescueDashboard>();var telemetry=mission.gameObject.AddComponent<MissionTelemetry>();
            dashboard.mission=mission;dashboard.telemetry=telemetry;telemetry.mission=mission;
            mission.fleet.environment.dashboard=dashboard;mission.fleet.environment.clock.telemetry=telemetry;
            BuildStationLaunch.Configure(mission);
            PlayerSettings.companyName="ModelScaleRescue";PlayerSettings.productName="Model Scale Rescue";PlayerSettings.runInBackground=true;
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(),ScenePath);AssetDatabase.SaveAssets();
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true),new EditorBuildSettingsScene(BuildRescueMission.ScenePath,true)};
        }
        public static void BuildAndValidate(){Build();DashboardValidation.Validate();EditorSceneManager.OpenScene(ScenePath);}
        public static void BuildPlayer()
        {
            Directory.CreateDirectory("Builds/ControlRoom");var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ScenePath,BuildRescueMission.ScenePath},locationPathName="Builds/ControlRoom/RescueControlRoom.exe",target=BuildTarget.StandaloneWindows64,options=BuildOptions.Development});
            if(result.summary.result!=BuildResult.Succeeded)throw new Exception("Control room build failed");
        }
    }
}
