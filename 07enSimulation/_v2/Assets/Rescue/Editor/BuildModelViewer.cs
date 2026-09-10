using System;
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.Build.Reporting;
using UnityEngine;
using UnityEngine.SceneManagement;
namespace RescueSim.Editor
{
    public static class BuildModelViewer
    {
        public static void Build()
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var viewer=new GameObject("ModelViewer").AddComponent<ModelViewer>();
            string[] prefabs={"RescueBoat_Physics","RescueBase_WetDock","RescuePerson_Rigged","RescuePerson_Seated"};
            viewer.models=new GameObject[prefabs.Length];
            for(int i=0;i<prefabs.Length;i++)
            {
                var model=(GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Rescue/Prefabs/"+prefabs[i]+".prefab"));
                foreach(var behaviour in model.GetComponentsInChildren<MonoBehaviour>(true))behaviour.enabled=false;
                foreach(var body in model.GetComponentsInChildren<Rigidbody>(true))body.isKinematic=true;
                viewer.models[i]=model;model.SetActive(false);
            }
            RenderSettings.ambientMode=UnityEngine.Rendering.AmbientMode.Flat;RenderSettings.ambientLight=new Color(.68f,.70f,.74f);
            var key=new GameObject("Studio_Key").AddComponent<Light>();key.type=LightType.Directional;key.intensity=1.1f;key.transform.rotation=Quaternion.Euler(45,-35,0);
            var fill=new GameObject("Studio_Fill").AddComponent<Light>();fill.type=LightType.Directional;fill.intensity=.55f;fill.transform.rotation=Quaternion.Euler(25,145,0);
            viewer.view=new GameObject("Viewer_Camera").AddComponent<Camera>();viewer.view.clearFlags=CameraClearFlags.SolidColor;viewer.view.backgroundColor=new Color(.88f,.90f,.92f);viewer.view.fieldOfView=38;
            const string scene="Assets/Rescue/Scenes/ModelViewer.unity";
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(),scene);
            Directory.CreateDirectory("Builds/ModelViewer");
            var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{scene},locationPathName="Builds/ModelViewer/RescueModelViewer.exe",target=BuildTarget.StandaloneWindows64,options=BuildOptions.None});
            if(result.summary.result!=BuildResult.Succeeded)throw new Exception("Model viewer build failed");
        }
    }
}
