using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using UnityEngine;
namespace RescueSim
{
    public sealed class MissionTelemetry:MonoBehaviour
    {
        [Serializable] public class EventRow {public float seconds;public string subject,detail;}
        [Serializable] public class BoatRow {public int boat,onboard,reserved,contacts;public string state;public float distanceM,maxSpeedMps,maxTiltDegrees,massKg,portRpm,starboardRpm,blockedSeconds;}
        [Serializable] public class PersonRow {public int person,urgency,carrier;public string state;public float boardedAt=-1,rescuedAt=-1,waitingSeconds;}
        [Serializable] public class Configuration {public float waterLevelM,backgroundSpeedMps,headingDegrees,regionalStrength,cruiseSpeedMps;public bool regionalFlow,debris;public bool[] available;}
        [Serializable] public class Snapshot
        {
            public string runId,createdUtc,engine,scenario,outcome;
            public float simulationSeconds,completionSeconds=-1,successPercent;
            public int total,inWater,onboard,rescued,plans,recordedSamples;
            public bool truncated;
            public Configuration initialConfiguration,currentConfiguration;
            public BoatRow[] boats;public PersonRow[] people;
        }
        public RescueMission mission;
        public string scenario="Street";
        public bool autoExport=true;
        public string LastExport {get;private set;}
        public string ExportError {get;private set;}
        public float CompletionSeconds {get;private set;}=-1;
        public readonly List<EventRow> events=new List<EventRow>();
        readonly Queue<string> samples=new Queue<string>();
        BoatRow[] boats;
        PersonRow[] people;
        Vector3[] lastPosition;
        string[] lastPhases;
        RescueVictim.RescueState[] lastStates;
        Configuration initialConfiguration;
        string id,createdUtc,lastConfiguration;
        float sampleTimer;
        bool exportPending,truncated;
        static string N(float value)=>value.ToString("R",CultureInfo.InvariantCulture);
        static string Q(string value)=>"\""+(value??"").Replace("\"","\"\"")+"\"";
        public void BeginRun()
        {
            mission.Initialize();id=DateTime.UtcNow.ToString("yyyyMMdd_HHmmss",CultureInfo.InvariantCulture)+"_"+Guid.NewGuid().ToString("N").Substring(0,8);createdUtc=DateTime.UtcNow.ToString("o");
            CompletionSeconds=-1;sampleTimer=0;events.Clear();samples.Clear();truncated=false;exportPending=false;ExportError=null;
            var f=mission.fleet;boats=new BoatRow[f.dispatcher.boats.Length];people=new PersonRow[f.dispatcher.victims.Length];lastPosition=new Vector3[boats.Length];lastPhases=new string[boats.Length];lastStates=new RescueVictim.RescueState[people.Length];
            for(int i=0;i<boats.Length;i++){boats[i]=new BoatRow{boat=i+1};lastPosition[i]=f.dispatcher.boats[i].Body.position;}
            for(int i=0;i<people.Length;i++){var v=f.dispatcher.victims[i];people[i]=new PersonRow{person=v.personId,urgency=v.urgency,carrier=-1};lastStates[i]=v.state;}
            initialConfiguration=Config();lastConfiguration=JsonUtility.ToJson(initialConfiguration);Record("RUN","Started "+scenario);
        }
        public Configuration Config()
        {
            var e=mission.fleet.environment;var w=e.water;
            return new Configuration{waterLevelM=w.level,backgroundSpeedMps=w.current.magnitude,headingDegrees=Mathf.Atan2(w.current.x,w.current.z)*Mathf.Rad2Deg,regionalFlow=w.regionalFlow,regionalStrength=w.regionalStrength,cruiseSpeedMps=mission.cruiseSpeed,debris=e.debris.Any(d=>d.isActiveAndEnabled),available=(bool[])mission.fleet.dispatcher.available.Clone()};
        }
        public void Record(string subject,string detail)
        {
            events.Add(new EventRow{seconds=mission.simulationSeconds,subject=subject,detail=detail});if(events.Count>2000){events.RemoveAt(0);truncated=true;}
        }
        public void Sample(float dt)
        {
            if(boats==null)BeginRun();if(CompletionSeconds>=0)return;
            var f=mission.fleet;
            for(int i=0;i<boats.Length;i++)
            {
                var b=f.dispatcher.boats[i];var r=boats[i];r.distanceM+=RescueNavigation.FlatDistance(lastPosition[i],b.Body.position);lastPosition[i]=b.Body.position;
                r.maxSpeedMps=Mathf.Max(r.maxSpeedMps,b.Body.linearVelocity.magnitude);r.maxTiltDegrees=Mathf.Max(r.maxTiltDegrees,b.TiltDegrees);
                r.contacts=b.CollisionCount;r.onboard=b.Passengers;r.reserved=f.dispatcher.Reserved(i);r.massKg=b.Body.mass;r.portRpm=b.PortRpm;r.starboardRpm=b.StarboardRpm;r.state=mission.agents[i].phase.ToString();
                if(r.state=="Blocked"||mission.agents[i].message.StartsWith("No "))r.blockedSeconds+=dt;
                if(lastPhases[i]!=r.state){Record("B"+(i+1),r.state+" | "+mission.agents[i].message);lastPhases[i]=r.state;}
            }
            for(int i=0;i<people.Length;i++)
            {
                var v=f.dispatcher.victims[i];var p=people[i];p.state=v.state.ToString();p.urgency=v.urgency;p.carrier=v.carrier>=0?v.carrier+1:-1;p.waitingSeconds=v.waitingSeconds;
                if(lastStates[i]!=v.state)
                {
                    Record("P"+v.personId,v.Status);if(v.state==RescueVictim.RescueState.Onboard&&p.boardedAt<0)p.boardedAt=mission.simulationSeconds;
                    if(v.state==RescueVictim.RescueState.Rescued)p.rescuedAt=mission.simulationSeconds;lastStates[i]=v.state;
                }
            }
            sampleTimer-=dt;
            if(sampleTimer<=0||mission.Complete)
            {
                sampleTimer=1;string configuration=JsonUtility.ToJson(Config());if(configuration!=lastConfiguration){Record("CONFIG",configuration);lastConfiguration=configuration;}
                for(int i=0;i<boats.Length;i++)
                {
                    var b=f.dispatcher.boats[i];Vector3 p=b.Body.position;
                    samples.Enqueue(string.Join(",",N(mission.simulationSeconds),(i+1).ToString(),N(p.x),N(p.y),N(p.z),N(b.Body.rotation.eulerAngles.y),N(b.Body.linearVelocity.magnitude),N(b.PortRpm),N(b.StarboardRpm),N(b.Body.mass),b.Passengers.ToString(),Q(mission.agents[i].phase.ToString()),mission.rescued.ToString(),N(f.environment.water.level)));
                    if(samples.Count>24000){samples.Dequeue();truncated=true;}
                }
            }
            if(mission.Complete){CompletionSeconds=mission.simulationSeconds;Record("RUN","Complete: all people unloaded at refuge");exportPending=autoExport;}
        }
        public Snapshot GetSnapshot()
        {
            if(boats==null)BeginRun();var victims=mission.fleet.dispatcher.victims;
            return new Snapshot{runId=id,createdUtc=createdUtc,engine=Application.unityVersion,scenario=scenario,outcome=mission.Complete?"Complete":mission.fleet.environment.clock.paused?"Paused":!mission.running?"AutopilotsStopped":mission.agents.All(a=>a.phase==RescueMission.Phase.Disabled||a.phase==RescueMission.Phase.Manual)?"NoAutonomousBoats":mission.agents.Any(a=>a.phase==RescueMission.Phase.Blocked||a.message.StartsWith("No "))?"Blocked":"InProgress",simulationSeconds=CompletionSeconds>=0?CompletionSeconds:mission.simulationSeconds,completionSeconds=CompletionSeconds,successPercent=100f*mission.rescued/victims.Length,total=victims.Length,inWater=victims.Count(v=>v.InWater),onboard=victims.Count(v=>v.state==RescueVictim.RescueState.Onboard||v.state==RescueVictim.RescueState.Disembarking),rescued=mission.rescued,plans=mission.plans,recordedSamples=samples.Count,truncated=truncated,initialConfiguration=initialConfiguration,currentConfiguration=Config(),boats=boats,people=people};
        }
        public string Export()
        {
            try
            {
                var r=GetSnapshot();string root=Path.Combine(Application.persistentDataPath,"RescueReports");
                string folder=Path.Combine(root,id+"_"+DateTime.UtcNow.ToString("HHmmssfff",CultureInfo.InvariantCulture)+"_"+Guid.NewGuid().ToString("N").Substring(0,4));Directory.CreateDirectory(folder);
                File.WriteAllText(Path.Combine(folder,"summary.json"),JsonUtility.ToJson(r,true),Encoding.UTF8);
                File.WriteAllLines(Path.Combine(folder,"telemetry.csv"),new[]{"simulation_seconds,boat,x_m,y_m,z_m,heading_deg,speed_mps,port_rpm,starboard_rpm,mass_kg,onboard,state,rescued,water_level_m"}.Concat(samples),Encoding.UTF8);
                File.WriteAllLines(Path.Combine(folder,"boats.csv"),new[]{"boat,state,distance_m,max_speed_mps,max_tilt_deg,contact_events,blocked_seconds,onboard,mass_kg"}.Concat(boats.Select(b=>string.Join(",",b.boat.ToString(),Q(b.state),N(b.distanceM),N(b.maxSpeedMps),N(b.maxTiltDegrees),b.contacts.ToString(),N(b.blockedSeconds),b.onboard.ToString(),N(b.massKg)))),Encoding.UTF8);
                File.WriteAllLines(Path.Combine(folder,"people.csv"),new[]{"person,urgency,state,carrier,boarded_at_seconds,rescued_at_seconds,water_wait_seconds"}.Concat(people.Select(p=>string.Join(",",p.person.ToString(),p.urgency.ToString(),Q(p.state),p.carrier.ToString(),N(p.boardedAt),N(p.rescuedAt),N(p.waitingSeconds)))),Encoding.UTF8);
                File.WriteAllLines(Path.Combine(folder,"events.csv"),new[]{"simulation_seconds,subject,detail"}.Concat(events.Select(e=>N(e.seconds)+","+Q(e.subject)+","+Q(e.detail))),Encoding.UTF8);
                File.WriteAllText(Path.Combine(folder,"README.txt"),"All dimensions use SI units. Time is simulation time, not wall time. Carrier -1 and time -1 mean not yet recorded. Contact counts are per-boat contact-enter events, not unique accidents. Telemetry records approximately once per simulated second. Data collection stops at first mission completion. A new reset starts a new run. See summary.json for initial/current settings and truncation. This is a model-scale, simplified hydrodynamics simulation, not a calibrated prediction of field rescue performance.",Encoding.UTF8);
                LastExport=folder;ExportError=null;return folder;
            }
            catch(Exception error){ExportError=error.Message;Debug.LogError("Report export failed: "+error.Message);return null;}
        }
        void Update(){if(exportPending){exportPending=false;Export();}}
    }
}
