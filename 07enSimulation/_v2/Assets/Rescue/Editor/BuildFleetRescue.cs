using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
namespace RescueSim.Editor
{
    public static class BuildFleetRescue
    {
        const string Root="Assets/Rescue/";
        public const string ScenePath=Root+"Scenes/FleetRescue.unity";
        static void BoxSize(string name,Vector3 position,Vector3 size){var t=GameObject.Find(name).transform;t.position=position;t.localScale=size;}
        static Material Material(string name,Color color)
        {
            string path=Root+"Materials/"+name+".mat";var m=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(!m){m=new Material(Shader.Find("Standard"));AssetDatabase.CreateAsset(m,path);}m.color=color;EditorUtility.SetDirty(m);return m;
        }
        [MenuItem("Rescue/Build Steps 4 and 5 Fleet")]
        public static void Build()
        {
            // Reuse the verified flood scene without overwriting that scene.
            EditorSceneManager.OpenScene(BuildFloodEnvironment.ScenePath);
            var e=UnityEngine.Object.FindFirstObjectByType<FloodEnvironment>();var w=e.water;
            w.boundsSize=new Vector3(1.6f,0,1.6f);
            BoxSize("Physical_Seabed",new Vector3(0,-.035f,0),new Vector3(1.62f,.01f,1.62f));
            e.surface.localScale=new Vector3(1.6f,.0002f,1.6f);
            foreach(var go in SceneManager.GetActiveScene().GetRootGameObjects().Where(o=>o.name=="Boundary_Wall"))
            {
                bool x=Mathf.Abs(go.transform.position.x)>.5f;float sign=Mathf.Sign(x?go.transform.position.x:go.transform.position.z);
                go.transform.position=x?new Vector3(sign*.806f,.025f,0):new Vector3(0,.025f,sign*.806f);
                go.transform.localScale=x?new Vector3(.012f,.11f,1.62f):new Vector3(1.6f,.11f,.012f);
            }
            Vector3[] buildings={new Vector3(-.56f,0,-.56f),new Vector3(-.56f,0,.56f),new Vector3(.56f,0,-.56f),new Vector3(.56f,0,.56f),new Vector3(-.67f,0,.10f),new Vector3(.67f,0,-.10f)};
            for(int i=0;i<buildings.Length;i++)GameObject.Find("Building_"+(i+1)).transform.position=buildings[i];
            var station=GameObject.Find("Rescue_Base_Static").transform;station.position=Vector3.zero;station.name="Central_Rescue_Station";
            w.flowZones[0].center=new Vector3(0,0,.48f);w.flowZones[0].size=new Vector3(.16f,0,.30f);
            w.flowZones[1].center=new Vector3(.44f,0,0);
            w.bedZones[0].center=new Vector3(-.30f,0,.48f);
            var shelf=GameObject.Find("Shallow_Shelf_Collider").transform;shelf.position=new Vector3(-.30f,shelf.position.y,.48f);
            e.hazardMarkers[0].position=w.bedZones[0].center;e.hazardMarkers[1].position=w.flowZones[0].center;
            // Preserve the outline dimensions from step 3 by scaling its Z axis.
            e.hazardMarkers[1].localScale=new Vector3(1,1,.30f/.36f);
            for(int i=0;i<e.flowArrows.Length;i++)
            {
                float angle=i*360f/e.flowArrows.Length;Vector3 p=Quaternion.Euler(0,angle,0)*Vector3.forward*(i%2==0?.33f:.64f);p.y=.0006f;e.flowArrows[i].position=p;
            }
            for(int i=0;i<e.debris.Length;i++)e.debris[i].transform.position=Quaternion.Euler(0,i*45+22,0)*Vector3.forward*.40f+Vector3.up*.004f;
            var root=new GameObject("Fleet_And_People");var fleet=root.AddComponent<FleetScenario>();var dispatch=root.AddComponent<FleetDispatcher>();
            fleet.environment=e;fleet.dispatcher=dispatch;e.fleet=fleet;dispatch.station=station;
            var link=Material("Fleet_Assignment_Link",Color.white);link.shader=Shader.Find("Sprites/Default");EditorUtility.SetDirty(link);fleet.assignmentMaterial=link;
            dispatch.boats=new BoatDynamics[4];fleet.boatSpawns=new Vector3[4];fleet.boatRotations=new Quaternion[4];
            var prefab=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"Prefabs/RescueBoat_Physics.prefab");
            for(int i=0;i<4;i++)
            {
                var boat=i==0?e.boat:((GameObject)PrefabUtility.InstantiatePrefab(prefab)).GetComponent<BoatDynamics>();
                Quaternion rotation=Quaternion.Euler(0,i*90,0);Vector3 pos=rotation*Vector3.forward*.235f+Vector3.down*.00456848f;
                boat.name="Rescue_Boat_"+(i+1).ToString("D2");boat.transform.SetPositionAndRotation(pos,rotation);boat.water=w;boat.manualStepping=true;
                dispatch.boats[i]=boat;fleet.boatSpawns[i]=pos;fleet.boatRotations[i]=rotation;
                var marker=GameObject.CreatePrimitive(PrimitiveType.Sphere);marker.name="Fleet_Color_Marker";UnityEngine.Object.DestroyImmediate(marker.GetComponent<Collider>());
                marker.transform.SetParent(boat.transform,false);marker.transform.localPosition=new Vector3(0,.014f,-.023f);marker.transform.localScale=Vector3.one*.005f;
                marker.GetComponent<Renderer>().sharedMaterial=Material("Fleet_Boat_"+(i+1),fleet.boatColors[i]);
            }
            e.boat=dispatch.boats[0];e.start=fleet.boatSpawns[0];e.clock.boats=dispatch.boats;
            var peopleRoot=new GameObject("Water_Rescue_People").transform;
            var personPrefab=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"Prefabs/RescuePerson_Rigged.prefab");
            var jacket=Material("Victim_Flotation_Orange",new Color(1,.25f,.025f));dispatch.victims=new RescueVictim[24];
            for(int i=0;i<24;i++)
            {
                int side=i/6,j=i%6;Quaternion r=Quaternion.Euler(0,side*90,0);
                Vector3 pos=r*new Vector3(j%2==0?-.09f:.09f,0,.34f+(j/2)*.10f);pos.y=-.00275f;
                var go=new GameObject("Person_"+(i+1).ToString("D2"));go.transform.SetParent(peopleRoot);go.transform.position=pos;go.AddComponent<Rigidbody>();go.AddComponent<CapsuleCollider>();
                var victim=go.AddComponent<RescueVictim>();victim.personId=i+1;victim.urgency=j==0?2:j==2?1:0;victim.water=w;victim.spawn=pos;
                var visual=(GameObject)PrefabUtility.InstantiatePrefab(personPrefab);visual.transform.SetParent(go.transform,false);
                var renderers=visual.GetComponentsInChildren<Renderer>();var bounds=renderers[0].bounds;foreach(var renderer in renderers)bounds.Encapsulate(renderer.bounds);
                visual.transform.position+=go.transform.position-bounds.center;
                var aid=GameObject.CreatePrimitive(PrimitiveType.Cube);aid.name="Flotation_Aid";UnityEngine.Object.DestroyImmediate(aid.GetComponent<Collider>());aid.transform.SetParent(go.transform,false);aid.transform.localPosition=new Vector3(0,.0015f,0);aid.transform.localScale=new Vector3(.010f,.006f,.006f);aid.GetComponent<Renderer>().sharedMaterial=jacket;
                dispatch.victims[i]=victim;
            }
            e.clock.victims=dispatch.victims;
            e.overview.transform.position=new Vector3(1.05f,1.8f,-1.3f);e.overview.transform.LookAt(new Vector3(0,.01f,0));e.overview.orthographicSize=1.03f;
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(),ScenePath);AssetDatabase.SaveAssets();
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true),new EditorBuildSettingsScene(BuildFloodEnvironment.ScenePath,true),new EditorBuildSettingsScene(Root+"Scenes/BoatPhysicsLab.unity",true)};
            Debug.Log("FLEET_SCENE_BUILT");
        }
        public static void BuildAndValidate(){Build();FleetValidation.Validate();EditorSceneManager.OpenScene(ScenePath);}
        public static void BuildPlayer()
        {BuildPlayerAt("Builds/Fleet");}
        public static void BuildPropellerFixPlayer()
        {BuildPlayerAt("Builds/Fleet_PropellerFix");}
        static void BuildPlayerAt(string folder)
        {
            Directory.CreateDirectory(folder);var result=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ScenePath,BuildFloodEnvironment.ScenePath,Root+"Scenes/BoatPhysicsLab.unity"},locationPathName=folder+"/RescueFleetSimulation.exe",target=BuildTarget.StandaloneWindows64,options=BuildOptions.Development});
            if(result.summary.result!=BuildResult.Succeeded)throw new Exception("Fleet build failed");
        }
    }
}
