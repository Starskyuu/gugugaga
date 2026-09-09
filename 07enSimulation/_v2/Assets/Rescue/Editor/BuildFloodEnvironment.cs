using System;
using System.IO;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.Build.Reporting;
using UnityEngine.SceneManagement;
namespace RescueSim.Editor
{
    public static class BuildFloodEnvironment
    {
        const string Root="Assets/Rescue/";public const string ScenePath=Root+"Scenes/FloodEnvironment.unity";
        static Material Mat(string n,Color c)
        {
            string p=Root+"Materials/Flood_"+n+".mat";var m=AssetDatabase.LoadAssetAtPath<Material>(p);
            if(!m){m=new Material(Shader.Find("Standard"));AssetDatabase.CreateAsset(m,p);}m.color=c;m.SetFloat("_Glossiness",.2f);EditorUtility.SetDirty(m);return m;
        }
        static GameObject Box(string n,Vector3 p,Vector3 size,Material m,Transform parent=null,bool collision=true)
        {
            var o=GameObject.CreatePrimitive(PrimitiveType.Cube);o.name=n;o.transform.SetParent(parent,false);o.transform.localPosition=p;o.transform.localScale=size;o.GetComponent<Renderer>().sharedMaterial=m;
            if(collision)o.GetComponent<Collider>().contactOffset=.0001f;else UnityEngine.Object.DestroyImmediate(o.GetComponent<Collider>());return o;
        }
        static Camera Cam(string n,Vector3 p,Vector3 target,float span)
        {
            var c=new GameObject(n).AddComponent<Camera>();c.transform.position=p;c.transform.LookAt(target);c.orthographic=true;c.orthographicSize=span/2;c.nearClipPlane=.0001f;c.farClipPlane=10;c.backgroundColor=new Color(.07f,.13f,.18f);c.clearFlags=CameraClearFlags.SolidColor;return c;
        }
        static Transform Outline(string n,Vector3 center,Vector3 size,Material m)
        {
            var root=new GameObject(n).transform;root.position=center;
            foreach(float sign in new[]{-1f,1f}){Box("Edge_X",new Vector3(sign*size.x/2,0,0),new Vector3(.001f,.0004f,size.z),m,root,false);Box("Edge_Z",new Vector3(0,0,sign*size.z/2),new Vector3(size.x,.0004f,.001f),m,root,false);}return root;
        }
        [MenuItem("Rescue/Build Step 3 Flood Environment")]
        public static void Build()
        {
            Directory.CreateDirectory("Reports");EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var concrete=Mat("Buildings",new Color(.46f,.52f,.54f));var roof=Mat("Roof",new Color(.18f,.25f,.29f));var sand=Mat("Shallow",new Color(.72f,.51f,.20f));var waterMat=Mat("Water",new Color(.025f,.14f,.2f));var windows=Mat("Windows",new Color(.035f,.1f,.16f));var cyan=Mat("Flow",new Color(.05f,.85f,.95f));var orange=Mat("Orange",new Color(1,.4f,.02f));var red=Mat("Danger",new Color(.95f,.07f,.025f));var wood=Mat("Wood",new Color(.4f,.22f,.085f));
            var w=new GameObject("Flood_Water_Field").AddComponent<WaterField>();w.bottom=-.03f;w.bounded=true;w.current=new Vector3(0,0,.008f);
            w.flowZones=new[]{new WaterField.FlowZone{name="Central_Fast_Channel",center=new Vector3(0,0,.22f),size=new Vector3(.16f,0,.36f),velocity=new Vector3(0,0,.03f),feather=.03f},new WaterField.FlowZone{name="Cross_Street_Flow",center=new Vector3(.18f,0,-.02f),size=new Vector3(.30f,0,.14f),velocity=new Vector3(-.014f,0,0),feather=.035f}};
            w.bedZones=new[]{new WaterField.BedZone{name="Shallow_Shelf",center=new Vector3(-.20f,0,.26f),size=new Vector3(.16f,0,.08f),height=-.003f}};
            Box("Physical_Seabed",new Vector3(0,-.035f,0),new Vector3(1.22f,.01f,1.22f),roof);
            var surface=Box("Flood_Surface",new Vector3(0,-.0001f,0),new Vector3(1.2f,.0002f,1.2f),waterMat,null,false).transform;
            foreach(var zone in w.bedZones)Box(zone.name+"_Collider",new Vector3(zone.center.x,(zone.height+w.bottom)/2,zone.center.z),new Vector3(zone.size.x,zone.height-w.bottom,zone.size.z),sand);
            for(int axis=0;axis<2;axis++)foreach(float sign in new[]{-1f,1f})Box("Boundary_Wall",axis==0?new Vector3(sign*.606f,.025f,0):new Vector3(0,.025f,sign*.606f),axis==0?new Vector3(.012f,.11f,1.22f):new Vector3(1.2f,.11f,.012f),roof);
            int count=0;
            foreach(float x in new[]{-.34f,.34f})foreach(float z in new[]{-.16f,.12f,.42f})
            {
                float height=.11f+(count%3)*.035f;var building=new GameObject("Building_"+(++count)).transform;building.position=new Vector3(x,0,z);
                Box("Solid_Building",new Vector3(0,(height+w.bottom)/2,0),new Vector3(.18f,height-w.bottom,.17f),concrete,building);
                Box("Roof_Cap",new Vector3(0,height+.003f,0),new Vector3(.19f,.006f,.18f),roof,building);
                for(int floor=0;floor<3;floor++)for(int column=0;column<3;column++)foreach(float side in new[]{-1f,1f})Box("Window",new Vector3((column-1)*.05f,.03f+floor*.027f,side*.0855f),new Vector3(.028f,.014f,.001f),windows,building,false);
            }
            var basePrefab=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"Prefabs/RescueBase_WetDock.prefab");var baseObject=(GameObject)PrefabUtility.InstantiatePrefab(basePrefab);baseObject.name="Rescue_Base_Static";baseObject.transform.position=new Vector3(0,0,-.40f);
            var bp=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"Prefabs/RescueBoat_Physics.prefab");var bo=(GameObject)PrefabUtility.InstantiatePrefab(bp);bo.name="Boat_Environment_Test";bo.transform.position=new Vector3(0,-.00456848f,-.15f);var boat=bo.GetComponent<BoatDynamics>();boat.water=w;
            var pieces=new FloatingDebris[8];
            Vector3[] positions={new Vector3(-.08f,.004f,-.06f),new Vector3(.09f,.004f,.03f),new Vector3(.06f,.004f,.16f),new Vector3(-.05f,.004f,.30f),new Vector3(.18f,.004f,.26f),new Vector3(-.16f,.004f,.02f),new Vector3(.07f,.004f,.46f),new Vector3(-.12f,.004f,.46f)};
            for(int i=0;i<pieces.Length;i++)
            {
                Vector3 size=new Vector3(.020f+(i%3)*.003f,.012f,.018f);var go=Box("Floating_Crate_"+(i+1),positions[i],size,wood);go.AddComponent<Rigidbody>();var d=go.AddComponent<FloatingDebris>();d.water=w;d.size=size;pieces[i]=d;
                Box("Crate_Strap",Vector3.zero,new Vector3(.12f,1.01f,1.01f),orange,go.transform,false);
            }
            var clock=new GameObject("Shared_PhysX_Clock").AddComponent<PhysicsClock>();clock.boats=new[]{boat};clock.debris=pieces;
            var markers=new[]{Outline("Shallow_Area",w.bedZones[0].center,w.bedZones[0].size,orange),Outline("Fast_Current_Area",w.flowZones[0].center,w.flowZones[0].size,red)};
            var arrows=new System.Collections.Generic.List<Transform>();
            for(int x=-2;x<=2;x++)for(int z=-1;z<=3;z++)
            {
                Vector3 p=new Vector3(x*.095f,.0006f,z*.14f);var ar=new GameObject("Local_Flow_Arrow").transform;ar.position=p;
                Box("Stem",Vector3.zero,new Vector3(.0012f,.0003f,.024f),cyan,ar,false);
                foreach(float sign in new[]{-1f,1f}){var head=Box("Head",new Vector3(sign*.003f,0,.009f),new Vector3(.0012f,.0003f,.009f),cyan,ar,false);head.transform.localRotation=Quaternion.Euler(0,-sign*45,0);}arrows.Add(ar);
            }
            RenderSettings.ambientMode=UnityEngine.Rendering.AmbientMode.Flat;RenderSettings.ambientLight=new Color(.48f,.53f,.57f);var light=new GameObject("Sun").AddComponent<Light>();light.type=LightType.Directional;light.intensity=1.2f;light.transform.rotation=Quaternion.Euler(50,-25,0);
            var overview=Cam("Flood_Overview",new Vector3(.8f,1.3f,-1.05f),new Vector3(-.06f,.01f,.02f),1.55f);overview.gameObject.AddComponent<AudioListener>();var follow=Cam("Boat_Follow",new Vector3(.1f,.15f,-.33f),bo.transform.position,.25f);follow.enabled=false;
            var env=new GameObject("Flood_Controls").AddComponent<FloodEnvironment>();env.water=w;env.boat=boat;env.clock=clock;env.surface=surface;env.debris=pieces;env.hazardMarkers=markers;env.flowArrows=arrows.ToArray();env.overview=overview;env.follow=follow;env.start=bo.transform.position;
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(),ScenePath);
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(ScenePath,true),new EditorBuildSettingsScene(Root+"Scenes/BoatPhysicsLab.unity",true),new EditorBuildSettingsScene(Root+"Scenes/ModelGallery.unity",true)};
            AssetDatabase.SaveAssets();Debug.Log("FLOOD_ENVIRONMENT_BUILT");
        }
        public static void BuildAndValidate(){Build();FloodValidation.Validate();PhysicsValidation.Validate();EditorSceneManager.OpenScene(ScenePath);}
        public static void BuildPlayer()
        {
            Directory.CreateDirectory("Builds/Flood");var r=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{ScenePath,Root+"Scenes/BoatPhysicsLab.unity",Root+"Scenes/ModelGallery.unity"},locationPathName="Builds/Flood/RescueFloodEnvironment.exe",target=BuildTarget.StandaloneWindows64,options=BuildOptions.Development});
            if(r.summary.result!=BuildResult.Succeeded)throw new Exception("Flood player build failed");
        }
    }
}
