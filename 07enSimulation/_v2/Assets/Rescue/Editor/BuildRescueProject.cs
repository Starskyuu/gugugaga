using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEditor.Build.Reporting;
using UnityEngine.SceneManagement;

namespace RescueSim.Editor
{
    public static class BuildRescueProject
    {
        const string Root="Assets/Rescue/";
        [Serializable] class MaterialRow { public string name;public float[] color;public float metallic,roughness; }
        [Serializable] class MaterialTable { public MaterialRow[] materials; }
        static Dictionary<string,Material> materials;
        static string Reports => Path.GetFullPath("Reports");
        static Material Material(string name,Color color)
        {
            string path=Root+"Materials/"+name+".mat";var m=AssetDatabase.LoadAssetAtPath<Material>(path);
            if(!m){m=new Material(Shader.Find("Standard"));AssetDatabase.CreateAsset(m,path);}m.color=color;return m;
        }
        static Transform Find(Transform root,string name) => root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name==name);
        static void RepairMaterials(GameObject model)
        {
            foreach(var r in model.GetComponentsInChildren<Renderer>(true))
            {
                var slots=r.sharedMaterials;
                for(int i=0;i<slots.Length;i++)
                    if(slots[i] && materials.TryGetValue(slots[i].name,out var replacement))slots[i]=replacement;
                r.sharedMaterials=slots;
            }
        }
        static GameObject Import(string file,string name,Quaternion adjustment)
        {
            var root=new GameObject(name);var asset=AssetDatabase.LoadAssetAtPath<GameObject>(Root+"Models/"+file+".fbx");
            if(!asset)throw new Exception("Missing FBX: "+file);
            var visual=(GameObject)PrefabUtility.InstantiatePrefab(asset);visual.name="Visual";visual.transform.SetParent(root.transform,false);visual.transform.localRotation=adjustment;RepairMaterials(visual);
            return root;
        }
        static Bounds Bounds(GameObject root)
        {
            var rs=root.GetComponentsInChildren<Renderer>();var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);return b;
        }
        static GameObject Box(string name,Vector3 center,Vector3 size,Material material,Transform parent=null,bool collision=true)
        {
            var o=GameObject.CreatePrimitive(PrimitiveType.Cube);o.name=name;o.transform.SetParent(parent,false);o.transform.localPosition=center;o.transform.localScale=size;o.GetComponent<Renderer>().sharedMaterial=material;
            var c=o.GetComponent<BoxCollider>();if(!collision)UnityEngine.Object.DestroyImmediate(c);else c.contactOffset=.0001f;return o;
        }
        static Camera Camera(string name,Vector3 pos,Vector3 target,float span)
        {
            var o=new GameObject(name);var c=o.AddComponent<Camera>();o.transform.position=pos;o.transform.LookAt(target);c.orthographic=true;c.orthographicSize=span/2;c.nearClipPlane=.0001f;c.farClipPlane=10;c.backgroundColor=new Color(.1f,.16f,.20f);c.clearFlags=CameraClearFlags.SolidColor;c.allowHDR=true;return c;
        }
        static void Lighting()
        {
            RenderSettings.ambientMode=UnityEngine.Rendering.AmbientMode.Flat;RenderSettings.ambientLight=new Color(.55f,.6f,.65f);
            var sun=new GameObject("Studio_Sun");var l=sun.AddComponent<Light>();l.type=LightType.Directional;l.intensity=1.5f;sun.transform.rotation=Quaternion.Euler(48,-35,0);l.shadows=LightShadows.Soft;
        }
        static Mesh HullMesh()
        {
            Vector2[] outline={new Vector2(-.025f,-.035f),new Vector2(.025f,-.035f),new Vector2(.025f,.019f),new Vector2(.022f,.026f),new Vector2(.013f,.032f),new Vector2(.0045f,.035f),new Vector2(-.0045f,.035f),new Vector2(-.013f,.032f),new Vector2(-.022f,.026f),new Vector2(-.025f,.019f)};
            var verts=new List<Vector3>();foreach(var p in outline)verts.Add(new Vector3(p.x*.78f,0,p.y*.9f));foreach(var p in outline)verts.Add(new Vector3(p.x,.0068f,p.y));foreach(var p in outline)verts.Add(new Vector3(p.x,.009f,p.y));
            var indices=new List<int>();
            for(int i=1;i<9;i++){indices.AddRange(new[]{0,i,i+1,20,20+i+1,20+i});}
            for(int ring=0;ring<2;ring++)for(int i=0;i<10;i++){int a=ring*10+i,b=ring*10+(i+1)%10,c=a+10,d=b+10;indices.AddRange(new[]{a,c,b,b,c,d});}
            var mesh=new Mesh{name="Closed_Hull_70x50mm"};mesh.SetVertices(verts);mesh.SetTriangles(indices,0);mesh.RecalculateNormals();return mesh;
        }
        [MenuItem("Rescue/Build Steps 1-2")]
        public static void Build()
        {
            Directory.CreateDirectory(Reports);
            foreach(string folder in new[]{"Prefabs","Materials","Scenes","Settings"})Directory.CreateDirectory(Root+folder);
            AssetDatabase.Refresh();materials=new Dictionary<string,Material>();
            var table=JsonUtility.FromJson<MaterialTable>(File.ReadAllText(Root+"Data/SourceMaterials.json"));int mi=0;
            foreach(var row in table.materials)
            {
                var m=Material("Source_"+(mi++).ToString("D3"),new Color(row.color[0],row.color[1],row.color[2],row.color[3]));m.SetFloat("_Metallic",row.metallic);m.SetFloat("_Glossiness",1-row.roughness);materials[row.name]=m;
            }
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);
            var probe=Import("RescueBoat","AxisProbe",Quaternion.identity);Vector3 forward=Find(probe.transform,"Axis_Bow").position-Find(probe.transform,"Hull_Origin").position;Vector3 up=Find(probe.transform,"Axis_Up").position-Find(probe.transform,"Hull_Origin").position;
            // Infer the exported coordinate basis from explicit source markers.
            Quaternion conversion=Quaternion.Inverse(Quaternion.LookRotation(forward.normalized,up.normalized));
            File.WriteAllText(Path.Combine(Reports,"Import_Axes.json"),JsonUtility.ToJson(new AxisReport{rawForward=forward,rawUp=up,correctionEuler=conversion.eulerAngles},true));UnityEngine.Object.DestroyImmediate(probe);
            var boat=Import("RescueBoat","RescueBoat_Physics",conversion);
            var profile=AssetDatabase.LoadAssetAtPath<BoatProfile>(Root+"Settings/ModelBoat.asset");
            if(!profile){profile=ScriptableObject.CreateInstance<BoatProfile>();AssetDatabase.CreateAsset(profile,Root+"Settings/ModelBoat.asset");}
            profile.hydrostatics=AssetDatabase.LoadAssetAtPath<TextAsset>(Root+"Data/BoatHydrostatics.json");EditorUtility.SetDirty(profile);
            var rb=boat.AddComponent<Rigidbody>();rb.mass=.012f;rb.useGravity=true;rb.interpolation=RigidbodyInterpolation.Interpolate;rb.collisionDetectionMode=CollisionDetectionMode.ContinuousDynamic;rb.sleepThreshold=0;
            var mesh=AssetDatabase.LoadAssetAtPath<Mesh>(Root+"Settings/HullCollider.asset");if(!mesh){mesh=HullMesh();AssetDatabase.CreateAsset(mesh,Root+"Settings/HullCollider.asset");}var collider=boat.AddComponent<MeshCollider>();collider.sharedMesh=mesh;collider.convex=true;collider.contactOffset=.0001f;
            var physicsMat=AssetDatabase.LoadAssetAtPath<PhysicsMaterial>(Root+"Settings/WetHull.asset");if(!physicsMat){physicsMat=new PhysicsMaterial("Wet_Hull"){dynamicFriction=.25f,staticFriction=.3f,bounciness=.05f};AssetDatabase.CreateAsset(physicsMat,Root+"Settings/WetHull.asset");}collider.sharedMaterial=physicsMat;
            // Attached buoy and propeller guards use simple compound boxes.
            foreach(float side in new[]{-1f,1f})
            {
                var buoy=new GameObject("Buoy_Contact_"+side);buoy.transform.SetParent(boat.transform,false);var c=buoy.AddComponent<BoxCollider>();c.center=new Vector3(side*.026f,.0105f,-.0025f);c.size=new Vector3(.004f,.013f,.05f);c.contactOffset=.0001f;c.sharedMaterial=physicsMat;
                var guard=new GameObject("Propeller_Guard_Contact_"+side);guard.transform.SetParent(boat.transform,false);c=guard.AddComponent<BoxCollider>();c.center=new Vector3(side*.0135f,.0038f,-.0383f);c.size=new Vector3(.0104f,.0104f,.0035f);c.contactOffset=.0001f;c.sharedMaterial=physicsMat;
            }
            var dyn=boat.AddComponent<BoatDynamics>();dyn.profile=profile;dyn.portRotor=Find(boat.transform,"Rotor_Port");dyn.starboardRotor=Find(boat.transform,"Rotor_Starboard");
            // Correct pivots to Unity's canonical axes, baking the imported
            // rotor wrapper basis into a fresh pivot without moving its meshes.
            foreach(var side in new[]{"Port","Starboard"})
            {
                var old=Find(boat.transform,"Rotor_"+side);var pivot=new GameObject("PhysicsRotor_"+side).transform;pivot.SetParent(boat.transform,false);pivot.localPosition=side=="Port"?profile.portMount:profile.starboardMount;
                var nestedRoot=PrefabUtility.GetNearestPrefabInstanceRoot(old.gameObject);
                if(nestedRoot)PrefabUtility.UnpackPrefabInstance(nestedRoot,PrefabUnpackMode.Completely,InteractionMode.AutomatedAction);
                old.SetParent(pivot,true);if(side=="Port")dyn.portRotor=pivot;else dyn.starboardRotor=pivot;
            }
            var standing=Import("RescuePerson_Standing","RescuePerson_Rigged",conversion);var seated=Import("RescuePerson_Seated","RescuePerson_Seated",conversion);
            var standPrefab=PrefabUtility.SaveAsPrefabAsset(standing,Root+"Prefabs/RescuePerson_Rigged.prefab");var seatPrefab=PrefabUtility.SaveAsPrefabAsset(seated,Root+"Prefabs/RescuePerson_Seated.prefab");dyn.seatedPersonPrefab=seatPrefab;
            var boatPrefab=PrefabUtility.SaveAsPrefabAsset(boat,Root+"Prefabs/RescueBoat_Physics.prefab");
            var baseModel=Import("RescueBase","RescueBase_WetDock",conversion);
            // Static compound colliders preserve four open doorways. Detailed
            // renderer meshes are not reused as a single enclosing collider.
            foreach(var mf in baseModel.GetComponentsInChildren<MeshFilter>())
            {
                string n=mf.name;
                if(n.Contains("foundation")||n.Contains("Boat_bay_floor")||n.Contains("facade_pier")||n.Contains("corner_shell")||n.Contains("dividing_wall")||n.Contains("back_wall")||n.Contains("Upper_rescue_deck")||n.Contains("Watertight_sliding_door"))
                {var c=mf.gameObject.AddComponent<BoxCollider>();c.center=mf.sharedMesh.bounds.center;c.size=mf.sharedMesh.bounds.size;c.contactOffset=.0001f;}
            }
            var basePrefab=PrefabUtility.SaveAsPrefabAsset(baseModel,Root+"Prefabs/RescueBase_WetDock.prefab");
            var report=new ImportReport{boatBounds=Bounds(boat).size,personStandingBounds=Bounds(standing).size,personSeatedBounds=Bounds(seated).size,boatBow=Find(boat.transform,"Axis_Bow").position,boatUp=Find(boat.transform,"Axis_Up").position,boatStarboard=Find(boat.transform,"Axis_Starboard").position,portPivot=dyn.portRotor.position,starboardPivot=dyn.starboardRotor.position,baseBounds=Bounds(baseModel).size,standingJoints=standing.GetComponentsInChildren<Transform>().Count(t=>t.name.StartsWith("Joint_"))};
            File.WriteAllText(Path.Combine(Reports,"Model_Import_Report.json"),JsonUtility.ToJson(report,true));
            CreateGallery(basePrefab,boatPrefab,standPrefab);
            CreateLab(boatPrefab);
            EditorBuildSettings.scenes=new[]{new EditorBuildSettingsScene(Root+"Scenes/BoatPhysicsLab.unity",true),new EditorBuildSettingsScene(Root+"Scenes/ModelGallery.unity",true)};
            PlayerSettings.productName="Rescue Boat Physics Lab";PlayerSettings.companyName="ModelScaleRescue";PlayerSettings.defaultScreenWidth=1440;PlayerSettings.defaultScreenHeight=900;PlayerSettings.fullScreenMode=FullScreenMode.Windowed;PlayerSettings.runInBackground=true;
            Physics.defaultContactOffset=.0001f;Physics.defaultSolverIterations=16;Physics.defaultSolverVelocityIterations=8;Physics.gravity=new Vector3(0,-9.81f,0);Time.fixedDeltaTime=1f/60f;
            AssetDatabase.SaveAssets();EditorSceneManager.SaveOpenScenes();Debug.Log("RESCUE_PROJECT_BUILD_COMPLETE");
        }
        static void CreateGallery(GameObject basePrefab,GameObject boatPrefab,GameObject personPrefab)
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);Lighting();
            PrefabUtility.InstantiatePrefab(basePrefab);
            for(int i=0;i<4;i++){var b=(GameObject)PrefabUtility.InstantiatePrefab(boatPrefab);b.name="Boat_"+(i+1);Quaternion q=Quaternion.Euler(0,-i*90,0);b.transform.position=q*new Vector3(0,-.00456848f,.0935f);b.transform.rotation=q;b.GetComponent<BoatDynamics>().enabled=false;b.GetComponent<Rigidbody>().isKinematic=true;}
            var p=(GameObject)PrefabUtility.InstantiatePrefab(personPrefab);p.name="Scale_Reference_Person";p.transform.position=new Vector3(.09f,.0861f,.12f);
            Box("Water_Display",new Vector3(0,-.0002f,0),new Vector3(.55f,.0003f,.55f),Material("Water",new Color(.035f,.21f,.27f)),null,false);
            Camera("Gallery_Camera",new Vector3(.4f,.33f,.5f),new Vector3(0,.07f,0),.5f).gameObject.AddComponent<AudioListener>();
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(),Root+"Scenes/ModelGallery.unity");
        }
        static void CreateLab(GameObject boatPrefab)
        {
            EditorSceneManager.NewScene(NewSceneSetup.EmptyScene,NewSceneMode.Single);Lighting();
            var w=new GameObject("Water_Field").AddComponent<WaterField>();
            var b=(GameObject)PrefabUtility.InstantiatePrefab(boatPrefab);b.transform.position=new Vector3(0,-.00456848f,0);var boat=b.GetComponent<BoatDynamics>();boat.water=w;
            Box("Water_Visual",new Vector3(0,-.0001f,0),new Vector3(.6f,.0002f,.6f),Material("Water",new Color(.035f,.21f,.27f)),null,false);
            var wall=Material("Basin",new Color(.035f,.05f,.07f));var yellow=Material("SafetyYellow",new Color(1,.66f,.025f));
            Box("Basin_Ground",new Vector3(0,-.03f,0),new Vector3(.62f,.01f,.62f),wall);
            for(int axis=0;axis<2;axis++)foreach(float sign in new[]{-1f,1f})
            {Vector3 pos=axis==0?new Vector3(sign*.305f,-.006f,0):new Vector3(0,-.006f,sign*.305f);Vector3 size=axis==0?new Vector3(.01f,.05f,.62f):new Vector3(.6f,.05f,.01f);Box("Basin_Wall",pos,size,wall);pos.y=.020f;size.y=.002f;Box("Safety_Rim",pos,size,yellow,null,false);}
            Box("Collision_Test_Block",new Vector3(.12f,.009f,.13f),new Vector3(.04f,.04f,.06f),yellow);
            for(int i=-5;i<=5;i++)foreach(bool x in new[]{false,true})Box("50mm_Grid",new Vector3(x?i*.05f:0,.00003f,x?0:i*.05f),new Vector3(x?.00012f:.6f,.00002f,x?.6f:.00012f),Material("Grid",new Color(.15f,.35f,.4f)),null,false);
            var clock=new GameObject("Physics_Clock_960Hz").AddComponent<PhysicsClock>();clock.boats=new[]{boat};
            var overview=Camera("Overview",new Vector3(.32f,.52f,-.47f),new Vector3(-.06f,0,0),.70f);overview.gameObject.AddComponent<AudioListener>();
            var follow=Camera("Follow",new Vector3(.09f,.095f,-.14f),new Vector3(0,.018f,0),.20f);follow.enabled=false;
            var lab=new GameObject("Interactive_Physics_Lab").AddComponent<PhysicsLab>();lab.boat=boat;lab.clock=clock;lab.water=w;lab.overview=overview;lab.follow=follow;
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(),Root+"Scenes/BoatPhysicsLab.unity");
        }
        public static void BuildPlayer()
        {
            Directory.CreateDirectory("Builds/Windows");var report=BuildPipeline.BuildPlayer(new BuildPlayerOptions{scenes=new[]{Root+"Scenes/BoatPhysicsLab.unity",Root+"Scenes/ModelGallery.unity"},locationPathName="Builds/Windows/RescueBoatPhysicsLab.exe",target=BuildTarget.StandaloneWindows64,options=BuildOptions.Development});
            if(report.summary.result!=BuildResult.Succeeded)throw new Exception("Player build failed");Debug.Log("RESCUE_PLAYER_BUILD_COMPLETE");
        }
        [Serializable] class AxisReport { public Vector3 rawForward,rawUp,correctionEuler; }
        [Serializable] class ImportReport { public Vector3 boatBounds,personStandingBounds,personSeatedBounds,boatBow,boatUp,boatStarboard,portPivot,starboardPivot,baseBounds;public int standingJoints; }
        public static void BuildAndValidate(){Build();PhysicsValidation.Validate();EditorSceneManager.OpenScene(Root+"Scenes/BoatPhysicsLab.unity");}
    }
}
