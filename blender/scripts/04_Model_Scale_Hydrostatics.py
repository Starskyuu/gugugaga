"""SI-unit six-DOF rigid body + sampled hydrostatic displacement; no thrust/CFD."""
import math
import numpy as np

OUTLINE=np.array([[-.025,-.035],[.025,-.035],[.025,.019],[.022,.026],[.013,.032],[.0045,.035],[-.0045,.035],[-.013,.032],[-.022,.026],[-.025,.019]])
BOTTOM=OUTLINE*np.array([.78,.9])
Z_CHINE=.0068
Z_TOP=.009

def area(poly):
 return abs(np.sum(poly[:,0]*np.roll(poly[:,1],-1)-poly[:,1]*np.roll(poly[:,0],-1)))/2

def polygon(z):
 return BOTTOM+(OUTLINE-BOTTOM)*min(max(z/Z_CHINE,0),1)

def exact_volume(draft):
 h=min(max(draft,0),Z_CHINE)
 v=h/6*(area(polygon(0))+4*area(polygon(h/2))+area(polygon(h)))
 return v+max(0,min(draft,Z_TOP)-Z_CHINE)*area(OUTLINE)

def upright_draft(mass,rho):
 lo,hi=0.,Z_TOP
 if mass>rho*exact_volume(hi):raise ValueError('Mass exceeds conservative sealed hull displacement.')
 for _ in range(60):
  mid=(lo+hi)/2
  if rho*exact_volume(mid)>mass:hi=mid
  else:lo=mid
 return (lo+hi)/2

def samples(nx=20,ny=28,nz=18):
 dx=.05/nx;dy=.07/ny;dz=Z_TOP/nz
 x,y=np.meshgrid((np.arange(nx)+.5)*dx-.025,(np.arange(ny)+.5)*dy-.035)
 xy=np.column_stack((x.ravel(),y.ravel()));points=[];weights=[]
 for k in range(nz):
  z=(k+.5)*dz;poly=polygon(z);inside=np.ones(len(xy),dtype=bool)
  for a,b in zip(poly,np.roll(poly,-1,axis=0)):
   edge=b-a;p=xy-a;inside&=(edge[0]*p[:,1]-edge[1]*p[:,0])>=-1e-12
  pts=xy[inside]
  # Exact integrated slice volume; cross-section samples provide its spatial distribution.
  v=exact_volume((k+1)*dz)-exact_volume(k*dz)
  points.extend(np.column_stack((pts,np.full(len(pts),z))));weights.extend(np.full(len(pts),v/len(pts)))
 return np.array(points),np.array(weights),np.array([dx,dy,dz])

def quat_matrix(q):
 w,x,y,z=q
 return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]])

def qmul(a,b):
 w,x,y,z=a;v,i,j,k=b
 return np.array([w*v-x*i-y*j-z*k,w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,w*k+x*j-y*i+z*v])

def euler_quat(roll,pitch,yaw=0):
 cr,sr=math.cos(roll/2),math.sin(roll/2);cp,sp=math.cos(pitch/2),math.sin(pitch/2);cy,sy=math.cos(yaw/2),math.sin(yaw/2)
 return np.array([cr*cp*cy+sr*sp*sy,sr*cp*cy-cr*sp*sy,cr*sp*cy+sr*cp*sy,cr*cp*sy-sr*sp*cy])

def angles(q):
 r=quat_matrix(q)
 # Boat forward is +Y: longitudinal roll is rotation about Y; pitch is about X.
 return np.degrees([math.asin(np.clip(-r[2,0],-1,1)),math.atan2(r[2,1],r[2,2]),math.atan2(r[1,0],r[0,0])])

def physical_properties(params):
 mass=sum(c['mass_kg'] for c in params['mass_budget'])
 com=sum(c['mass_kg']*np.array(c['position_m']) for c in params['mass_budget'])/mass
 inertia=np.zeros((3,3))
 for item in params['mass_budget']:
  m=item['mass_kg'];d=np.array(item['dimensions_m']);r=np.array(item['position_m'])-com
  inertia+=np.diag(m/12*np.array([d[1]**2+d[2]**2,d[0]**2+d[2]**2,d[0]**2+d[1]**2]))+m*(np.dot(r,r)*np.eye(3)-np.outer(r,r))
 return mass,com,inertia

def run(params,dt=None,initial=None,duration=None,resolution=None):
 mass,com,I=physical_properties(params);rho=params['water_density_kg_m3'];g=params['gravity_m_s2'];dt=dt or params['time_step_s'];duration=duration or params['duration_s']
 pts,w,cell=samples(*(resolution or params['buoyancy_sample_grid']));local=pts-com;draft=upright_draft(mass,rho)
 init=initial or params['initial_disturbance'];q=euler_quat(math.radians(init['pitch_deg']),math.radians(init['roll_deg']))
 pos=np.array([0.,0.,com[2]-draft+init['heave_m']]);vel=np.array(init.get('velocity_m_s',[0,0,0]),dtype=float);omega=np.zeros(3)
 linear=np.array(params['linear_drag_Ns_m']);angular=np.array(params['angular_drag_Nms']);Cd=np.array(params['quadratic_drag_Cd']);proj=np.array(params['reference_areas_m2'])
 n=int(round(duration/dt));stride=max(1,int(round(1/params['bake_fps']/dt)));track=[]
 def hydro(p,q):
  R=quat_matrix(q);arms=local@R.T;z=arms[:,2]+p[2]
  # Smooth partial-cell waterline, with rotated vertical cell extent.
  extent=max(float(np.dot(np.abs(R[2]),cell)),1e-7)
  displaced=w*np.clip(.5-z/extent,0,1)
  B=rho*g*sum(displaced);mom=(arms*displaced[:,None]).sum(axis=0)*rho*g
  return R,B,np.array([mom[1],-mom[0],0]),float(sum(displaced))
 for step in range(n+1):
  R,B,torque,volume=hydro(pos,q);wet=min(1,volume/sum(w));vb=R.T@vel
  dragbody=-linear*vb-.5*rho*Cd*proj*np.abs(vb)*vb
  force=np.array([0.,0.,B-mass*g])+R@dragbody*wet
  torque-=R@(angular*(R.T@omega))*wet
  if step%stride==0 or step==n:
   track.append({'time_s':step*dt,'position_m':pos.tolist(),'quaternion_wxyz':q.tolist(),'velocity_m_s':vel.tolist(),'omega_rad_s':omega.tolist(),'buoyancy_N':float(B),'displaced_volume_m3':volume,'roll_pitch_yaw_deg':angles(q).tolist()})
  if step==n:break
  Iw=R@I@R.T;acc=force/mass;alpha=np.linalg.solve(Iw,torque-np.cross(omega,Iw@omega))
  vel+=acc*dt;pos+=vel*dt;omega+=alpha*dt;q+=.5*qmul(np.r_[0.,omega],q)*dt;q/=np.linalg.norm(q)
  if not np.isfinite(pos).all():raise RuntimeError('Non-finite physics state')
 final=track[-1]
 return {'mass_kg':mass,'center_of_mass_m':com.tolist(),'inertia_kg_m2':I.tolist(),'conservative_hull_volume_m3':exact_volume(Z_TOP),'max_displacement_mass_kg':rho*exact_volume(Z_TOP),'upright_equilibrium_draft_m':draft,'sample_count':len(pts),'time_step_s':dt,'frames':track,'final_speed_m_s':float(np.linalg.norm(vel)),'final_angular_speed_rad_s':float(np.linalg.norm(omega)),'final_force_error_fraction':abs(final['buoyancy_N']-mass*g)/(mass*g)}

def validate(params):
 baseline=run(params)
 fine=run(params,dt=params['time_step_s']/2)
 mass=baseline['mass_kg'];weight=mass*params['gravity_m_s2'];a=baseline['frames'][-1];b=fine['frames'][-1]
 dpos=float(np.linalg.norm(np.array(a['position_m'])-b['position_m']));dang=float(np.linalg.norm(np.array(a['roll_pitch_yaw_deg'])-b['roll_pitch_yaw_deg']))
 drag=run(params,initial={'roll_deg':0,'pitch_deg':0,'heave_m':0,'velocity_m_s':[.03,0,0]},duration=4)
 checks={'positive_definite_inertia':bool(np.linalg.eigvalsh(np.array(baseline['inertia_kg_m2'])).min()>0),'buoyancy_capacity_exceeds_dry_mass':bool(baseline['max_displacement_mass_kg']>mass),'settled_linear_speed_below_0_2_mm_s':baseline['final_speed_m_s']<.0002,'settled_angular_speed_below_0_01_rad_s':baseline['final_angular_speed_rad_s']<.01,'buoyancy_weight_error_below_1_percent':baseline['final_force_error_fraction']<.01,'time_step_position_difference_below_0_1_mm':dpos<.0001,'time_step_angle_difference_below_0_1_deg':dang<.1,'drag_slows_30_mm_s_drift_below_5_mm_s':abs(drag['frames'][-1]['velocity_m_s'][0])<.005}
 return baseline,{'all_passed':all(checks.values()),'checks':checks,'dry_mass_g':mass*1000,'weight_N':weight,'center_of_mass_mm':(np.array(baseline['center_of_mass_m'])*1000).tolist(),'upright_draft_mm':baseline['upright_equilibrium_draft_m']*1000,'max_displacement_g':baseline['max_displacement_mass_kg']*1000,'final_buoyancy_N':a['buoyancy_N'],'final_speed_mm_s':baseline['final_speed_m_s']*1000,'final_roll_pitch_deg':a['roll_pitch_yaw_deg'][:2],'dt_convergence_position_mm':dpos*1000,'dt_convergence_angle_deg':dang,'final_drift_speed_mm_s':drag['frames'][-1]['velocity_m_s'][0]*1000,'assumptions':'Mass, COM, inertia and drag are provisional engineering estimates, not measured calibration. Static calm freshwater; rigid body; no propulsion, waves, CFD or collision response.'}
