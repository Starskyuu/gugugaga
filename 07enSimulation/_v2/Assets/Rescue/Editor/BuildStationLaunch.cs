using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
namespace RescueSim.Editor
{
    public static class BuildStationLaunch
    {
        public static void Configure(RescueMission mission)
        {
            var station=mission.fleet.dispatcher.station;
            var root=PrefabUtility.GetOutermostPrefabInstanceRoot(station.gameObject);
            if(root)PrefabUtility.UnpackPrefabInstance(root,PrefabUnpackMode.Completely,InteractionMode.AutomatedAction);
            var panels=station.GetComponentsInChildren<Renderer>().Where(r=>r.name.Contains("MISSION_SIM_DOOR_VIS_Watertight_sliding_door")).OrderBy(r=>r.name).ToArray();
            if(panels.Length!=8)throw new Exception("Expected eight sliding door leaves");
            var centers=panels.Select(r=>r.bounds.center).ToArray();
            var launch=mission.gameObject.AddComponent<StationLaunch>();launch.mission=mission;mission.launch=launch;
            launch.leaves=new Transform[8];launch.closedPositions=new Vector3[8];launch.openPositions=new Vector3[8];
            for(int i=0;i<8;i++)
            {
                var t=new GameObject("Animated_Bay_Door_"+(i+1)).transform;t.SetParent(station,true);t.position=centers[i];launch.leaves[i]=t;
                bool z=Mathf.Abs(centers[i].z)>Mathf.Abs(centers[i].x);var tangent=z?Vector3.right:Vector3.forward;
                float along=Vector3.Dot(centers[i],tangent);float sign=Mathf.Sign(along);
                launch.closedPositions[i]=centers[i]+tangent*(sign*.0185f-along);
                launch.openPositions[i]=centers[i]+tangent*(sign*.0572f-along);
            }
            foreach(var r in station.GetComponentsInChildren<Renderer>().Where(r=>r.name.StartsWith("MISSION_SIM_DOOR_VIS_")).ToArray())
            {
                int best=Enumerable.Range(0,8).OrderBy(i=>(r.bounds.center-centers[i]).sqrMagnitude).First();
                r.transform.SetParent(launch.leaves[best],true);
            }
            for(int i=0;i<8;i++)launch.leaves[i].position=launch.closedPositions[i];
            for(int i=0;i<4;i++)
            {
                var f=mission.fleet;var rotation=Quaternion.Euler(0,i*90,0);var pos=rotation*Vector3.forward*.0935f+Vector3.down*.00456848f;
                f.boatSpawns[i]=pos;f.boatRotations[i]=rotation;f.dispatcher.boats[i].transform.SetPositionAndRotation(pos,rotation);
            }
            mission.fleet.environment.start=mission.fleet.boatSpawns[0];
        }
        public static void Build(){BuildRescueDashboard.Build();BuildRescueDashboard.BuildPlayer();}
    }
}
