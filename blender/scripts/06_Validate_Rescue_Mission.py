"""Additional regression checks; does not overwrite the mission trajectory."""
import json, runpy, copy
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parents[1];O=R/'PhysicsSimulation'
S=runpy.run_path(str(R/'scripts/06_Rescue_Mission_Physics.py'))
p=json.loads((O/'Physics_Parameters.json').read_text());c=json.loads((O/'Navigation_Parameters.json').read_text());m=json.loads((O/'Rescue_Mission_Parameters.json').read_text());result=json.loads((O/'Rescue_Mission_Results.json').read_text());report=S['validate'](result,p,c,m)
w=S['MissionWorld'](p,c,m);w.moor_point=None
for k in range(round(3/w.dt)):w.step([.5,.5])
report['checks']['closed_gate_blocks_forced_exit']=bool(w.contact_steps>0 and w.hull_origin()[1]<.105)
report['closed_gate_test']={'contact_steps':w.contact_steps,'final_hull_y_m':float(w.hull_origin()[1]),'max_penetration_mm':float(w.peak_penetration*1000)}
# Same load event evaluated directly verifies inertia and COM, not just mass.
w=S['MissionWorld'](p,c,m);oldI=w.I.copy();w.change_load([a['id'] for a in m['passengers']]);newI=w.I.copy()
report['checks']['payload_changes_inertia']=bool(np.linalg.norm(newI-oldI)>1e-9)
w.change_load([])
report['checks']['unload_restores_inertia']=bool(np.max(abs(w.I-oldI))<1e-14)
report['checks']['last_person_reaches_bench_before_completion']=S['H'] is not None and m['disembark_duration_s']+m['transfer_duration_s']>=max(a['unload_offset_s'] for a in m['passengers'])+32
# Time-step sensitivity over both transit legs and both load transitions.
fine=S['simulate'](p,c,m,dt=c['time_step_s']/2)
errors=[]
for phase in ['OUTBOUND','RETURN_LOADED','BOARDING','DISEMBARKING']:
 a=next(x for x in result['stages'] if x['phase']==phase);b=next(x for x in fine['stages'] if x['phase']==phase);errors.append(abs(a['end_s']-b['end_s']))
report['max_stage_end_time_difference_s']=max(errors)
report['checks']['half_time_step_stage_times_within_50ms']=max(errors)<.05
report['checks']['half_time_step_no_mission_contact']=fine['contact_steps']==0
report['all_passed']=all(report['checks'].values())
S['N']['save_result']('Rescue_Mission_Validation_Report.json',report)
print(json.dumps(report,indent=2))
