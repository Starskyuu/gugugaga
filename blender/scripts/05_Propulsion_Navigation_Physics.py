"""6-DOF hydrostatics + twin propeller thrust + uniform current + planar obstacle impulses."""
import numpy as np
import math,json,runpy,heapq
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
H=runpy.run_path(str(ROOT/'scripts/04_Model_Scale_Hydrostatics.py'))

def wrap(x):return (x+math.pi)%(2*math.pi)-math.pi

def plan(start,goal,obstacles,bounds,clearance=.064,grid=.015):
 def free(p):
  return all(bounds[i][0]+clearance<=p[i]<=bounds[i][1]-clearance for i in range(2)) and all(np.linalg.norm(np.array(p)-o['center_m'])>o['radius_m']+clearance for o in obstacles)
 def node(p):return tuple(int(round(p[i]/grid)) for i in range(2))
 def point(n):return np.array(n,dtype=float)*grid
 a,b=node(start),node(goal);queue=[(0,a)];cost={a:0};prev={}
 while queue:
  _,u=heapq.heappop(queue)
  if u==b:break
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
   v=(u[0]+dx,u[1]+dy)
   if not free(point(v)):continue
   if dx and dy and (not free(point((u[0]+dx,u[1]))) or not free(point((u[0],u[1]+dy)))):continue
   c=cost[u]+math.hypot(dx,dy)
   if c<cost.get(v,1e9):cost[v]=c;prev[v]=u;heapq.heappush(queue,(c+math.dist(v,b),v))
 if b not in cost:raise RuntimeError('No clearance-safe route found')
 path=[b]
 while path[-1]!=a:path.append(prev[path[-1]])
 path=[np.array(start)]+[point(n) for n in path[::-1][1:-1]]+[np.array(goal)]
 # Line-of-sight shortcutting retains the same inflated obstacle clearance.
 out=[path[0]];i=0
 while i<len(path)-1:
  j=len(path)-1
  while j>i+1:
   if all(free(path[i]+(path[j]-path[i])*t) for t in np.linspace(0,1,max(3,int(np.linalg.norm(path[j]-path[i])/.003)))):break
   j-=1
  out.append(path[j]);i=j
 return [p.tolist() for p in out]

class World:
 def __init__(self,p,c,start=(0,0),current=(0,0,0),obstacles=None,bounds=None,yaw=0,velocity=(0,0,0),dt=None):
  self.p=p;self.c=c;self.dt=dt or c['time_step_s'];self.mass,self.com,self.I=H['physical_properties'](p);self.rho=p['water_density_kg_m3'];self.g=p['gravity_m_s2']
  pts,self.weights,self.cell=H['samples'](*c['buoyancy_grid']);self.local=pts-self.com;self.volume=self.weights.sum();draft=H['upright_draft'](self.mass,self.rho)
  self.pos=np.array([*start,self.com[2]-draft]);self.q=H['euler_quat'](math.radians(.685),0,yaw);self.v=np.array(velocity,dtype=float);self.w=np.zeros(3);self.rpm=np.zeros(2);self.spin=np.zeros(2);self.time=0
  self.current=np.array(current);self.obstacles=obstacles or [];self.bounds=bounds;self.events=[];self.peak_penetration=0.;self.contact_steps=0
  self.lin=np.array(p['linear_drag_Ns_m']);self.ang=np.array(p['angular_drag_Nms']);self.quad=.5*self.rho*np.array(p['quadratic_drag_Cd'])*np.array(p['reference_areas_m2'])
  self.K=self.rho*c['propeller_Kt']*c['propeller_diameter_m']**4/3600
  self.mounts=np.array([[-.0135,-.0388,.0038],[.0135,-.0388,.0038]])-self.com
  self.last_thrust=np.zeros(2);self.last_B=0.;self.min_gap=1e9
 def contact(self):
  # Vertical cylinders and tank walls, horizontal normal/tangent impulses at COM height.
  # Three overlapping circles form a conservative hull/appendage footprint.
  touched=False
  for iteration in range(4):
   R=H['quat_matrix'](self.q);Iw=R@self.I@R.T;iz=Iw[2,2]
   for oy,radius in [(-.017,.029),(0,.029),(.017,.028)]:
    arm=(R@np.array([0,oy-self.com[1],0]))[:2];center=self.pos[:2]+arm;contacts=[]
    for obs in self.obstacles:
     d=center-obs['center_m'];length=float(np.linalg.norm(d));gap=length-radius-obs['radius_m'];self.min_gap=min(self.min_gap,gap)
     if gap<0:contacts.append((d/max(length,1e-12),-gap,obs['name']))
    if self.bounds:
     for axis in [0,1]:
      for side in [-1,1]:
       boundary=self.bounds[axis][0 if side<0 else 1];penetration=(boundary-center[axis]+radius) if side<0 else (center[axis]+radius-boundary)
       if penetration>0:
        normal=np.zeros(2);normal[axis]=-side;contacts.append((normal,penetration,'TankWall'))
    for n,depth,name in contacts:
     touched=True;self.peak_penetration=max(self.peak_penetration,float(depth));self.pos[:2]+=n*(depth+1e-7)
     r=arm-n*radius;pointv=self.v[:2]+self.w[2]*np.array([-r[1],r[0]]);vn=float(pointv@n);cross=r[0]*n[1]-r[1]*n[0];jn=0.
     if vn<0:
      restitution=self.c['contact_restitution'] if vn<-.01 else 0.;jn=-(1+restitution)*vn/(1/self.mass+cross*cross/iz)
      self.v[:2]+=jn*n/self.mass;self.w[2]+=jn*cross/iz
      tangent=np.array([-n[1],n[0]]);pv=self.v[:2]+self.w[2]*np.array([-r[1],r[0]]);ct=r[0]*tangent[1]-r[1]*tangent[0]
      jt=float(np.clip(-(pv@tangent)/(1/self.mass+ct*ct/iz),-self.c['contact_friction']*jn,self.c['contact_friction']*jn))
      self.v[:2]+=jt*tangent/self.mass;self.w[2]+=jt*ct/iz
     if iteration==0 and jn>1e-7 and len(self.events)<200:self.events.append({'time_s':self.time,'obstacle':name,'normal_impulse_Ns':jn,'incoming_normal_speed_m_s':vn,'penetration_m':float(depth)})
  if touched:self.contact_steps+=1
 def step(self,throttle):
  dt=self.dt;R=H['quat_matrix'](self.q);arms=self.local@R.T;z=arms[:,2]+self.pos[2];extent=max(float(np.dot(np.abs(R[2]),self.cell)),1e-7)
  displaced=self.weights*np.clip(.5-z/extent,0,1);vol=displaced.sum();B=self.rho*self.g*vol;mom=(arms*displaced[:,None]).sum(axis=0)*self.rho*self.g;wet=min(1,vol/self.volume)
  relative=R.T@(self.v-self.current);force=np.array([0,0,B-self.mass*self.g])+R@(-self.lin*relative-self.quad*np.abs(relative)*relative)*wet
  torque=np.array([mom[1],-mom[0],0])-R@(self.ang*(R.T@self.w))*wet
  target=np.clip(throttle,-1,1)*self.c['max_rpm'];self.rpm+=(target-self.rpm)*(1-math.exp(-dt/self.c['motor_response_s']))
  thrust=self.K*self.rpm*np.abs(self.rpm)
  for i,mount in enumerate(self.mounts):
   shaftz=self.pos[2]+(R@mount)[2];submerge=float(np.clip((self.c['propeller_diameter_m']/2-shaftz)/self.c['propeller_diameter_m'],0,1))
   thrust[i]*=submerge;fb=np.array([0.,thrust[i],0.]);force+=R@fb;torque+=R@np.cross(mount,fb)
  Iw=R@self.I@R.T;self.v+=force/self.mass*dt;self.pos+=self.v*dt;self.w+=np.linalg.solve(Iw,torque-np.cross(self.w,Iw@self.w))*dt
  self.q+=.5*H['qmul'](np.r_[0.,self.w],self.q)*dt;self.q/=np.linalg.norm(self.q)
  self.spin+=self.rpm/60*2*math.pi*dt*np.array([1,-1]);self.contact();self.time+=dt;self.last_thrust=thrust;self.last_B=B
  if not np.isfinite(self.pos).all() or np.linalg.norm(self.v)>3:raise RuntimeError('Unstable state')
 def record(self):
  return {'time_s':self.time,'position_m':self.pos.tolist(),'quaternion_wxyz':self.q.tolist(),'velocity_m_s':self.v.tolist(),'omega_rad_s':self.w.tolist(),'rpm':self.rpm.tolist(),'rotor_angle_rad':self.spin.tolist(),'thrust_N':self.last_thrust.tolist(),'buoyancy_N':float(self.last_B)}

class Autopilot:
 def __init__(self,path,c):self.path=[np.array(p) for p in path];self.index=1;self.c=c;self.arrived=False
 def command(self,w):
  goal=self.path[-1];distance=float(np.linalg.norm(goal-w.pos[:2]));R=H['quat_matrix'](w.q)
  if distance<self.c['arrival_radius_m']:self.arrived=True
  if self.index<len(self.path)-1 and np.linalg.norm(self.path[self.index]-w.pos[:2])<.026:self.index+=1
  target=self.path[self.index];delta=target-w.pos[:2];d=np.linalg.norm(delta)
  speed=min(self.c['cruise_speed_m_s'],max(.008,d*.9))
  ground=delta/max(d,1e-8)*speed
  if self.arrived:ground=np.clip((goal-w.pos[:2])*1.5,-.02,.02)
  relative=ground-w.current[:2];desired=math.atan2(-relative[0],relative[1]);yaw=math.atan2(R[1,0],R[0,0])
  if self.arrived:
   # Face upstream once in the arrival zone; signed thrust prevents continuous turning.
   desired=math.atan2(w.current[0],-w.current[1]) if np.linalg.norm(w.current[:2])>.001 else yaw
  error=wrap(desired-yaw)
  fwd=R[:2,1];target_fwd=float(relative@fwd) if self.arrived else max(0,float(relative@fwd))*max(0,math.cos(error))
  vf=float((w.v-w.current)@R[:,1]);wet=w.mass/(w.rho*w.volume)
  total=w.mass*2.0*(target_fwd-vf)+(w.lin[1]*target_fwd+w.quad[1]*target_fwd*abs(target_fwd))*wet
  total=float(np.clip(total,-.0015,.003));yaw_torque=w.I[2,2]*(6*error-4*w.w[2])+w.ang[2]*wet*w.w[2]
  diff=float(np.clip(yaw_torque/.0135,-.004,.004));forces=np.array([(total-diff)/2,(total+diff)/2])
  # Approximate partial disk immersion feed-forward; physical force uses actual immersion.
  rpm=np.sign(forces)*np.sqrt(np.abs(forces)/max(w.K*.65,1e-12));return np.clip(rpm/self.c['max_rpm'],-1,1)

def simulate(p,c,kind='navigation',dt=None,duration=None):
 navigation=kind=='navigation';obs=c['obstacles'] if navigation else ([{'name':'Collision_Test_Pillar','center_m':[0,.005],'radius_m':.025}] if kind=='collision' else [])
 start=c['start_m'] if navigation else ([0,-.10] if kind=='collision' else [0,0]);current=c['current_m_s'] if navigation or kind=='current' else [0,0,0]
 w=World(p,c,start,current,obs,c['tank_bounds_m'] if navigation else None,dt=dt,velocity=[0,.08,0] if kind=='collision' else [0,0,0]);duration=duration or (c['duration_s'] if navigation else 6)
 path=plan(start,c['goal_m'],obs,c['tank_bounds_m'],c['planning_clearance_m']) if navigation else [];ap=Autopilot(path,c) if navigation else None
 records=[w.record()];stride=round(1/c['bake_fps']/w.dt);steps=round(duration/w.dt)
 for k in range(steps):
  if navigation:cmd=ap.command(w)
  elif kind=='straight':cmd=[.42,.42] if w.time<3 else [0,0]
  elif kind=='turn_left':cmd=[-.35,.35]
  elif kind=='turn_right':cmd=[.35,-.35]
  elif kind=='demo':
   cmd=[.38,.38] if w.time<2.5 else ([0,0] if w.time<4 else ([-.70,.70] if w.time<7 else ([.36,.36] if w.time<9.5 else [0,0])))
  else:cmd=[0,0]
  w.step(cmd)
  if (k+1)%stride==0:records.append(w.record())
 return {'scenario':kind,'frames':records,'path_m':path,'obstacles':obs,'current_m_s':current,'mass_kg':w.mass,'center_of_mass_m':w.com.tolist(),'events':w.events,'contact_steps':w.contact_steps,'peak_penetration_m':w.peak_penetration,'min_contact_gap_m':None if w.min_gap==1e9 else w.min_gap,'arrived':ap.arrived if ap else None,'goal_error_m':float(np.linalg.norm(w.pos[:2]-c['goal_m'])) if navigation else None}

def tests(p,c):
 results={k:simulate(p,c,k,duration=4 if k!='straight' else 6) for k in ['straight','turn_left','turn_right','collision','current']}
 a=results['straight']['frames'];co=results['collision'];le=results['turn_left']['frames'][-1];ri=results['turn_right']['frames'][-1]
 checks={'equal_rpm_moves_forward':a[120]['position_m'][1]>.005,'motor_command_zero_slows_boat':np.linalg.norm(a[-1]['velocity_m_s'])<np.linalg.norm(a[120]['velocity_m_s']),'differential_commands_turn_opposite_directions':le['omega_rad_s'][2]>.05 and ri['omega_rad_s'][2]<-.05,'unpowered_current_drifts_boat':results['current']['frames'][-1]['position_m'][0]>.001,'collision_generates_impulse':len(co['events'])>0,'collision_penetration_below_0_5_mm':co['peak_penetration_m']<.0005,'collision_stops_forward_motion':co['frames'][-1]['position_m'][1]<-.045}
 return results,{'checks':{k:bool(v) for k,v in checks.items()},'all_passed':all(checks.values()),'collision_max_penetration_mm':co['peak_penetration_m']*1000,'collision_events':len(co['events']),'left_yaw_rate_rad_s':le['omega_rad_s'][2],'right_yaw_rate_rad_s':ri['omega_rad_s'][2]}

def save_result(name,data):
 text=json.dumps(data,indent=2,default=lambda value:value.item() if isinstance(value,np.generic) else value.tolist())
 with open(ROOT/'PhysicsSimulation'/name,'w',encoding='utf-8') as f:f.write(text)
