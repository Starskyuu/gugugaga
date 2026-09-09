using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
namespace RescueSim
{
    public sealed class FleetDispatcher:MonoBehaviour
    {
        public BoatDynamics[] boats;
        public RescueVictim[] victims;
        public bool[] available={true,true,true,true};
        public Transform station;
        public RescueMission mission;
        public bool automatic=true;
        public float interval=1;
        public int revision;
        float elapsed;
        public bool Usable(int index)=>index>=0&&index<boats.Length&&available[index]&&boats[index]&&boats[index].isActiveAndEnabled&&!boats[index].Capsized&&(!mission||mission.AcceptsAssignments(index));
        public int Reserved(int index)=>victims.Count(v=>v&&v.InWater&&v.isActiveAndEnabled&&v.assignedBoat==index);
        public int Waiting=>victims.Count(v=>v&&v.InWater&&v.isActiveAndEnabled&&v.assignedBoat<0);
        public int Capacity(int index)=>Mathf.Max(0,6-boats[index].Passengers);
        public IEnumerable<RescueVictim> Tasks(int index)=>victims.Where(v=>v&&v.InWater&&v.isActiveAndEnabled&&v.assignedBoat==index).OrderByDescending(v=>v.Priority).ThenBy(v=>(v.transform.position-boats[index].transform.position).sqrMagnitude);
        public void ClearAssignments(){foreach(var v in victims)if(v&&!v.Locked)v.assignedBoat=-1;revision++;}
        public void SetAvailable(int index,bool value){available[index]=value;if(!value)boats[index].portCommand=boats[index].starboardCommand=0;Dispatch();}
        public void Dispatch(bool rebalance=false)
        {
            foreach(var boat in boats)boat.Initialize();
            if(rebalance)ClearAssignments();
            foreach(var v in victims)
                if(v&&!v.Locked&&(!v.isActiveAndEnabled||!v.InWater||!Usable(v.assignedBoat)))v.assignedBoat=-1;
            // Keep valid reservations stable. Release lowest-priority overflow
            // when payload changes; do not count a reservation as a passenger.
            for(int b=0;b<boats.Length;b++)
                foreach(var v in Tasks(b).Skip(Usable(b)?Capacity(b):0).ToArray())v.assignedBoat=-1;
            foreach(var v in victims.Where(v=>v&&v.isActiveAndEnabled&&v.InWater&&v.assignedBoat<0).OrderByDescending(v=>v.Priority).ThenBy(v=>v.personId))
            {
                int best=-1;float bestCost=float.PositiveInfinity;
                for(int b=0;b<boats.Length;b++)
                {
                    if(!Usable(b)||Reserved(b)>=Capacity(b))continue;
                    // Heuristic travel estimate plus workload. This is task
                    // assignment only, not an obstacle-aware path or an ETA.
                    float cost=Vector3.Distance(boats[b].transform.position,v.transform.position)/.04f+Reserved(b)*3;
                    if(cost<bestCost){bestCost=cost;best=b;}
                }
                if(best<0)
                {
                    var lower=victims.Where(p=>p&&p.isActiveAndEnabled&&!p.Locked&&Usable(p.assignedBoat)&&p.Priority+1<v.Priority).OrderBy(p=>p.Priority).ThenByDescending(p=>p.personId).FirstOrDefault();
                    if(lower){best=lower.assignedBoat;lower.assignedBoat=-1;}
                }
                if(best>=0)v.assignedBoat=best;
            }
            revision++;
        }
        void Start(){Dispatch();}
        void Update()
        {
            if(mission)return;
            var clock=GetComponent<FleetScenario>()?.environment.clock;
            if(!automatic||(clock&&clock.paused))return;
            elapsed+=Time.deltaTime;if(elapsed>=interval){elapsed=0;Dispatch();}
        }
    }
}
