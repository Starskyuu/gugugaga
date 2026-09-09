using UnityEngine;
namespace RescueSim
{
    [DefaultExecutionOrder(1000)]
    public sealed class PhysicsClock : MonoBehaviour
    {
        public BoatDynamics[] boats;
        public FloatingDebris[] debris=System.Array.Empty<FloatingDebris>();
        public RescueVictim[] victims=System.Array.Empty<RescueVictim>();
        [Range(1,32)] public int substeps=16;
        public bool paused;
        public RescueMission mission;
        SimulationMode previous;
        void OnEnable(){previous=Physics.simulationMode;Physics.simulationMode=SimulationMode.Script;Time.fixedDeltaTime=1f/60f;}
        void OnDisable(){Physics.simulationMode=previous;}
        void FixedUpdate()
        {
            if(paused)return;
            if(mission)mission.Tick(Time.fixedDeltaTime);
            float dt=Time.fixedDeltaTime/substeps;
            for(int i=0;i<substeps;i++)
            {
                foreach(var boat in boats)if(boat && boat.isActiveAndEnabled)boat.ApplyForces(dt);
                foreach(var item in debris)if(item && item.isActiveAndEnabled)item.ApplyForces();
                foreach(var person in victims)if(person && person.isActiveAndEnabled)person.ApplyForces(dt);
                Physics.Simulate(dt);
            }
        }
    }
}
