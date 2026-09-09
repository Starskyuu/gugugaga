"""Run in Blender after editing thrust/drag settings; recompute, validate, then rebake."""
import bpy,json,runpy,numpy as np
ROOT='F:/gugugaga/blender/';OUT=ROOT+'PhysicsSimulation/'
P=json.load(open(OUT+'Physics_Parameters.json',encoding='utf-8'));C=json.load(open(OUT+'Navigation_Parameters.json',encoding='utf-8'))
module=runpy.run_path(ROOT+'scripts/05_Propulsion_Navigation_Physics.py')
old=bpy.data.texts.get('NAV_Navigation_Parameters.json')
if old:
 previous=json.loads(old.as_string())
 for field in ['obstacles','tank_bounds_m','start_m','goal_m','current_m_s']:
  if C[field]!=previous[field]:raise RuntimeError('Environment changed: generate new results in a fresh Blender session, then run 05_Build_Propulsion_Navigation_Demo.py to rebuild matching geometry.')
 _,com,_=module['H']['physical_properties'](P)
 body=next(o for o in bpy.data.scenes['SIM_05_Autonomous_Navigation'].objects if 'SIM_BOAT_BODY' in o.name)
 if np.linalg.norm(com-np.array(body['center_of_mass_hull_m']))>1e-9:raise RuntimeError('Mass center changed: rebuild the step-3 body geometry first.')
tests,report=module['tests'](P,C);nav=module['simulate'](P,C);fine=module['simulate'](P,C,dt=C['time_step_s']/2);demo=module['simulate'](P,C,'demo',duration=12)
end=np.array(nav['frames'][-1]['position_m']);endfine=np.array(fine['frames'][-1]['position_m'])
report['checks'].update({'autopilot_reaches_goal':bool(nav['arrived']),'autopilot_no_contact':nav['contact_steps']==0,'final_goal_error_below_20mm':nav['goal_error_m']<.02,'time_step_endpoint_difference_below_2mm':float(np.linalg.norm(end-endfine))<.002})
w=module['World'](P,C,start=(.25,0),bounds=C['tank_bounds_m'],velocity=(.10,0,0))
for _ in range(round(2/w.dt)):w.step([0,0])
report['checks'].update({'tank_wall_generates_contact':len(w.events)>0,'tank_wall_blocks_exit':bool(w.pos[0]<.272)});report['all_passed']=all(report['checks'].values());report['goal_error_mm']=nav['goal_error_m']*1000;report['endpoint_convergence_mm']=float(np.linalg.norm(end-endfine))*1000
if not report['all_passed']:raise RuntimeError('Validation failed; existing animation preserved: '+str(report))
cases=[('SIM_05_Autonomous_Navigation','Navigation_Test_Results.json',nav),('SIM_04_Twin_Propeller_Drive','Propulsion_Test_Results.json',demo),('SIM_05_Collision_Response','Collision_Test_Results.json',tests['collision'])]
for scene_name,filename,data in cases:
 module['save_result'](filename,data)
 if scene_name not in bpy.data.scenes:continue
 s=bpy.data.scenes[scene_name];bpy.context.window.scene=s;body=next(o for o in s.objects if 'SIM_BOAT_BODY' in o.name);follow=bpy.data.objects[scene_name+'_Camera_Follow'];rotors=[next(o for o in s.objects if 'SIM_ROTOR_'+side in o.name) for side in ['Port','Starboard']]
 for obj in [body,follow,*rotors]:obj.animation_data_clear()
 for frame,state in enumerate(data['frames'],1):
  body.location=state['position_m'];body.rotation_quaternion=state['quaternion_wxyz'];body.keyframe_insert('location',frame=frame);body.keyframe_insert('rotation_quaternion',frame=frame);follow.location=state['position_m'];follow.keyframe_insert('location',frame=frame)
  for i,rotor in enumerate(rotors):rotor.rotation_euler.y=state['rotor_angle_rad'][i];rotor.keyframe_insert('rotation_euler',index=1,frame=frame);rotor['rpm']=state['rpm'][i];rotor.keyframe_insert(data_path='["rpm"]',frame=frame)
 # Update the cyan trajectory to match the new physics.
 path=next(o for o in s.objects if o.name.startswith('Computed_Physical_Trajectory'));sp=path.data.splines[0];values=data['frames'][::4]
 if len(sp.points)==len(values):
  for point,state in zip(sp.points,values):point.co=(state['position_m'][0],state['position_m'][1],.00012,1)
 else:
  path.data.splines.clear();sp=path.data.splines.new('POLY');sp.points.add(len(values)-1)
  for point,state in zip(sp.points,values):point.co=(state['position_m'][0],state['position_m'][1],.00012,1)
 s.frame_end=len(data['frames']);s.frame_set(1)
module['save_result']('Navigation_Validation_Report.json',report)
for filename in ['Navigation_Parameters.json','Navigation_Validation_Report.json']:
 tx=bpy.data.texts.get('NAV_'+filename)
 if tx:tx.clear();tx.write(open(OUT+filename,encoding='utf-8').read())
if 'SIM_05_Autonomous_Navigation' in bpy.data.scenes:
 bpy.context.window.scene=bpy.data.scenes['SIM_05_Autonomous_Navigation'];bpy.ops.wm.save_as_mainfile(filepath=OUT+'05_Propulsion_And_Navigation.blend')
result=report
