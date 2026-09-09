"""Single-boat mission: physical propulsion, load/COM changes, guarded workflow.

Hull motion is integrated, not waypoint-keyframed. Docking constrains only planar
translation/yaw; heave, roll and pitch remain dynamic. People are choreographed.
"""
import copy, json, math, runpy
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
N=runpy.run_path(str(ROOT/'scripts/05_Propulsion_Navigation_Physics.py'))
H=N['H']

class MissionWorld(N['World']):
 def __init__(self,p,c,m,dt=None):
  super().__init__(p,c,m['bay_center_m'],current=m['water_current_m_s'],dt=dt)
  self.base_p=copy.deepcopy(p);self.m=m;self.onboard=[];self.gate=0.;self.load_events=[];self.max_origin_jump=0.;self.moor_point=np.array(m['bay_center_m'])
  self.pos[:2]=self.moor_point+(H['quat_matrix'](self.q)@self.com)[:2]
 def hull_origin(self):return self.pos-H['quat_matrix'](self.q)@self.com
 def change_load(self,ids):
  old_origin=self.hull_origin();oldcom=self.com.copy();R=H['quat_matrix'](self.q)
  p=copy.deepcopy(self.base_p)
  for item in self.m['passengers']:
   if item['id'] in ids:p['mass_budget'].append({k:item[k] for k in ['mass_kg','position_m','dimensions_m']} | {'name':item['id']})
  oldmass=self.mass;self.mass,self.com,self.I=H['physical_properties'](p)
  self.local+=oldcom-self.com;self.mounts+=oldcom-self.com
  # Gentle co-moving boarding: retain the hull pose and velocity field, with no
  # invented impact impulse. The changed mass/inertia act on subsequent steps.
  self.pos=old_origin+R@self.com;self.v+=np.cross(self.w,R@(self.com-oldcom));self.onboard=list(ids)
  jump=float(np.linalg.norm(self.hull_origin()-old_origin));self.max_origin_jump=max(self.max_origin_jump,jump)
  self.load_events.append({'time_s':self.time,'onboard':list(ids),'mass_before_kg':oldmass,'mass_after_kg':self.mass,'center_of_mass_m':self.com.tolist(),'hull_origin_jump_m':jump})
 def boxes(self):
  d=.0185+.0387*self.gate
  return [('North_Bay_Left',[-.14,.044],[-.0315,.144]),('North_Bay_Right',[.0315,.044],[.14,.144]),('North_Bay_Back',[-.04,.038],[.04,.044])]+[(f'Gate_{sg}',[sg*d-.0185,.1411],[sg*d+.0185,.1433]) for sg in [-1,1]]
 def contact(self):
  if not hasattr(self,'gate'):return
  touched=False
  for iteration in range(3):
   R=H['quat_matrix'](self.q);iz=(R@self.I@R.T)[2,2]
   for oy,radius in [(-.017,.029),(0,.029),(.017,.028)]:
    arm=(R@(np.array([0.,oy,0])-self.com))[:2];center=self.pos[:2]+arm
    for name,lo,hi in self.boxes():
     lo,hi=np.array(lo),np.array(hi);nearest=np.clip(center,lo,hi);delta=center-nearest;length=float(np.linalg.norm(delta))
     if length>=radius:continue
     if length<1e-12:
      distances=[center[0]-lo[0],hi[0]-center[0],center[1]-lo[1],hi[1]-center[1]];j=int(np.argmin(distances));normal=np.array([[-1,0],[1,0],[0,-1],[0,1]][j],dtype=float);depth=radius+distances[j]
     else:normal=delta/length;depth=radius-length
     touched=True;self.peak_penetration=max(self.peak_penetration,depth);self.pos[:2]+=normal*(depth+1e-8)
     r=arm-normal*radius;pv=self.v[:2]+self.w[2]*np.array([-r[1],r[0]]);vn=float(pv@normal);cr=r[0]*normal[1]-r[1]*normal[0]
     if vn<0:
      impulse=-(1+self.c['contact_restitution'])*vn/(1/self.mass+cr*cr/iz);self.v[:2]+=normal*impulse/self.mass;self.w[2]+=cr*impulse/iz
      if iteration==0 and len(self.events)<100:self.events.append({'time_s':self.time,'obstacle':name,'normal_impulse_Ns':impulse,'penetration_m':depth})
  if touched:self.contact_steps+=1
 def step(self,cmd):
  super().step(cmd)
  if self.moor_point is not None:
   # Ideal gentle mooring: lock hull-origin XY and heading, not buoyancy DOFs.
   R=H['quat_matrix'](self.q);yaw=math.atan2(R[1,0],R[0,0]);self.q=H['qmul'](H['euler_quat'](0,0,-yaw),self.q);R=H['quat_matrix'](self.q)
   self.pos[:2]=self.moor_point+(R@self.com)[:2];self.w[2]=0.;self.v[:2]=np.cross(self.w,R@self.com)[:2]
 def record(self):
  r=super().record();origin=self.hull_origin();r.update(hull_origin_m=origin.tolist(),mass_kg=self.mass,center_of_mass_m=self.com.tolist(),inertia_kg_m2=self.I.tolist(),onboard=list(self.onboard),gate_open_fraction=self.gate,moored=self.moor_point is not None,attitude_deg=H['angles'](self.q).tolist())
  return r

def drive(w,goal):
 # Signed forward control deliberately reverses into the bay without a narrow
 # turn. Heading feedback is physical differential thrust, no pose forcing.
 R=H['quat_matrix'](w.q);origin=w.hull_origin();v_origin=w.v-np.cross(w.w,R@w.com);dy=goal[1]-origin[1]
 speed=float(np.clip(dy*1.8,-w.m['cruise_speed_m_s'],w.m['cruise_speed_m_s']));yaw=math.atan2(R[1,0],R[0,0]);vf=float((w.v-w.current)@R[:,1]);wet=w.mass/(w.rho*w.volume)
 total=w.mass*3*(speed-vf)+(w.lin[1]*speed+w.quad[1]*speed*abs(speed))*wet
 desired=float(np.clip(-(goal[0]-origin[0])*15*(1 if speed>=0 else -1),-.12,.12))
 error=N['wrap'](desired-yaw);torque=w.I[2,2]*(8*error-5*w.w[2])+w.ang[2]*wet*w.w[2]
 diff=float(np.clip(torque/.0135,-.003,.003));forces=np.array([(total-diff)/2,(total+diff)/2]);rpm=np.sign(forces)*np.sqrt(abs(forces)/max(w.K*.65,1e-12))
 return np.clip(rpm/w.c['max_rpm'],-1,1)

def simulate(p,c,m,dt=None):
 w=MissionWorld(p,c,m,dt);records=[];stages=[];phase='OPEN_GATE';phase_start=0.;max_time=150.;captured=[]
 stride=round(1/c['bake_fps']/w.dt);step=0
 def transition(name):
  nonlocal phase,phase_start
  stages.append({'phase':phase,'start_s':phase_start,'end_s':w.time});phase=name;phase_start=w.time
 def snapshot():
  r=w.record();r.update(phase=phase,phase_elapsed_s=w.time-phase_start);records.append(r)
 snapshot()
 while w.time<max_time:
  elapsed=w.time-phase_start;cmd=[0,0]
  if phase=='OPEN_GATE':
   w.gate=min(1,elapsed/m['door_open_duration_s'])
   if elapsed>=m['door_open_duration_s']:w.gate=1.;w.moor_point=None;transition('OUTBOUND')
  elif phase in ['OUTBOUND','RETURN_LOADED']:
   goal=np.array(m['pickup_center_m'] if phase=='OUTBOUND' else m['bay_center_m']);cmd=drive(w,goal);error=float(np.linalg.norm(w.hull_origin()[:2]-goal))
   if elapsed>2 and error<m['arrival_position_tolerance_m'] and np.linalg.norm(w.v[:2])<m['arrival_speed_tolerance_m_s'] and abs(H['angles'](w.q)[2])<2:
    captured.append({'time_s':w.time,'phase':phase,'position_error_m':error,'speed_m_s':float(np.linalg.norm(w.v[:2]))});w.moor_point=goal;cmd=[0,0];transition('BOARDING' if phase=='OUTBOUND' else 'DISEMBARKING')
   elif elapsed>50:raise RuntimeError('Docking timeout: '+phase+' '+str(w.record()))
  elif phase=='BOARDING':
   ids=[a['id'] for a in m['passengers'] if elapsed>=a['board_offset_s']]
   if ids!=w.onboard:w.change_load(ids)
   if elapsed>=m['boarding_duration_s']:w.moor_point=None;transition('RETURN_LOADED')
  elif phase=='DISEMBARKING':
   ids=[a['id'] for a in m['passengers'] if elapsed<a['unload_offset_s']]
   if ids!=w.onboard:w.change_load(ids)
   if elapsed>=m['disembark_duration_s']:transition('TRANSFER_TO_SHELTER')
  elif phase=='TRANSFER_TO_SHELTER':
   if elapsed>=m['transfer_duration_s']:transition('CLOSE_GATE')
  elif phase=='CLOSE_GATE':
   w.gate=max(0,1-elapsed/3)
   if elapsed>=3:transition('COMPLETE')
  elif phase=='COMPLETE':
   if elapsed>=2:break
  w.step(cmd);step+=1
  if step%stride==0:snapshot()
 if phase!='COMPLETE':raise RuntimeError('Mission did not complete')
 stages.append({'phase':phase,'start_s':phase_start,'end_s':w.time})
 return {'schema':'rescue_mission_result_v1','frames':records,'stages':stages,'load_events':w.load_events,'dock_captures':captured,'contacts':w.events,'contact_steps':w.contact_steps,'peak_penetration_m':float(w.peak_penetration),'max_load_origin_jump_m':w.max_origin_jump,'completed':True}

def validate(result,p,c,m):
 frames=result['frames'];loaded=[r for r in frames if len(r['onboard'])==2 and r['phase']=='RETURN_LOADED'];drymass=sum(x['mass_kg'] for x in p['mass_budget']);payload=sum(x['mass_kg'] for x in m['passengers'])
 draft0=H['upright_draft'](drymass,p['water_density_kg_m3']);draft2=H['upright_draft'](drymass+payload,p['water_density_kg_m3'])
 minfloor=min(r['hull_origin_m'][2]-.05*math.sin(math.radians(max(abs(r['attitude_deg'][0]),abs(r['attitude_deg'][1])))) for r in frames if r['hull_origin_m'][1]<.18)-m['wet_dock_floor_top_m']
 maxangle=max(max(abs(r['attitude_deg'][0]),abs(r['attitude_deg'][1])) for r in frames)
 checks={'workflow_completed':result['completed'],'two_loads_two_unloads':len(result['load_events'])==4,'loaded_mass_matches':bool(loaded) and all(abs(r['mass_kg']-drymass-payload)<1e-10 for r in loaded),'empty_mass_restored':abs(frames[-1]['mass_kg']-drymass)<1e-10,'hull_pose_continuous_at_load_changes':result['max_load_origin_jump_m']<1e-9,'no_mission_contact':result['contact_steps']==0,'positive_floor_clearance':minfloor>.001,'loaded_draft_increases':draft2>draft0,'roll_pitch_below_12_deg':maxangle<12,'doors_open_during_transit':all(r['gate_open_fraction']>.999 for r in frames if r['phase'] in ['OUTBOUND','RETURN_LOADED']),'reverse_rpm_on_return':any(max(r['rpm'])< -100 for r in loaded),'mooring_capture_within_1mm':all(x['position_error_m']<=.001 for x in result['dock_captures']),'center_of_mass_changes':any(np.linalg.norm(np.array(r['center_of_mass_m'])-frames[0]['center_of_mass_m'])>.001 for r in loaded)}
 return {'checks':checks,'all_passed':all(checks.values()),'empty_mass_g':drymass*1000,'loaded_mass_g':(drymass+payload)*1000,'upright_draft_empty_mm':draft0*1000,'upright_draft_loaded_mm':draft2*1000,'maximum_roll_pitch_deg':maxangle,'conservative_floor_clearance_mm':minfloor*1000,'duration_s':frames[-1]['time_s'],'limitations':'Functional/numerical validation, not measured model calibration. Only north-bay planar box contacts; people kinematic; mooring ideal.'}

if __name__=='__main__':
 p=json.loads((ROOT/'PhysicsSimulation/Physics_Parameters.json').read_text(encoding='utf-8'));c=json.loads((ROOT/'PhysicsSimulation/Navigation_Parameters.json').read_text(encoding='utf-8'));m=json.loads((ROOT/'PhysicsSimulation/Rescue_Mission_Parameters.json').read_text(encoding='utf-8'))
 result=simulate(p,c,m);report=validate(result,p,c,m)
 N['save_result']('Rescue_Mission_Results.json',result);N['save_result']('Rescue_Mission_Validation_Report.json',report);print(json.dumps(report,indent=2))
