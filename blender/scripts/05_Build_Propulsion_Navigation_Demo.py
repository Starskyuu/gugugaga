import bpy,json,math
from mathutils import Vector
ROOT='F:/gugugaga/blender/';OUT=ROOT+'PhysicsSimulation/'
with open(OUT+'Navigation_Parameters.json',encoding='utf-8') as f:C=json.load(f)
with open(OUT+'Navigation_Validation_Report.json',encoding='utf-8') as f:report=json.load(f)
assert report['all_passed'],'Physics validation must pass first.'
with bpy.data.libraries.load(OUT+'04_Model_Scale_Physics_Setup.blend',link=False) as (src,dst):dst.scenes=[n for n in src.scenes if n=='SIM_01_Boat_Calm_Water_Float_Test']
source=dst.scenes[0];sourcebody=next(o for o in source.objects if o.name.startswith('SIM_BOAT_BODY'))
def mat(n,col,metal=0,rough=.4):
 m=bpy.data.materials.new('NAV '+n);m.diffuse_color=(*col,1);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m
water=mat('Water',(.025,.13,.18),.25,.22);wall=mat('Tank graphite',(.035,.055,.065),.2,.45);yellow=mat('Safety yellow',(.95,.62,.01));white=mat('Markings',(.75,.84,.85));orange=mat('Obstacle orange',(.85,.15,.015));green=mat('Goal green',(.10,.75,.27));blue=mat('Trajectory cyan',(.015,.62,.85))
def own(o,c,n,m):
 o.name=n
 for old in list(o.users_collection):old.objects.unlink(o)
 c.objects.link(o)
 if m:o.data.materials.append(m)
 return o
def box(c,n,loc,size,m):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=own(bpy.context.object,c,n,m);o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return o
def cyl(c,n,loc,r,h,m):
 bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=r,depth=h,location=loc);o=own(bpy.context.object,c,n,m)
 for p in o.data.polygons:p.use_smooth=True
 return o
def curve(c,n,pts,r,m,closed=False):
 d=bpy.data.curves.new(n,'CURVE');d.dimensions='3D';d.bevel_depth=r;d.bevel_resolution=2;sp=d.splines.new('POLY');sp.points.add(len(pts)-1)
 for p,v in zip(sp.points,pts):p.co=(*v,1)
 sp.use_cyclic_u=closed;o=bpy.data.objects.new(n,d);c.objects.link(o);d.materials.append(m);return o
def label(c,txt,loc,size,m=white):
 d=bpy.data.curves.new(txt,'FONT');d.body=txt;d.size=size;d.align_x='CENTER';o=bpy.data.objects.new(txt,d);c.objects.link(o);o.location=loc;d.materials.append(m);return o
def cam(s,c,n,loc,target,scale):
 d=bpy.data.cameras.new(n);o=bpy.data.objects.new(n,d);c.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=scale;d.clip_start=.0001;d.clip_end=10;return o
def create(kind,name,filename):
 data=json.load(open(OUT+filename,encoding='utf-8'));frames=data['frames'];s=bpy.data.scenes.new(name);bpy.context.window.scene=s;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;s.unit_settings.length_unit='CENTIMETERS';s.render.fps=60;s.frame_end=len(frames);s.frame_start=1;s.gravity=(0,0,-9.81)
 s.render.engine='CYCLES';s.cycles.samples=32;s.cycles.use_denoising=True;s.render.resolution_x=1500;s.render.resolution_y=1300;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
 visual=bpy.data.collections.new(name+'_Boat');env=bpy.data.collections.new(name+'_Environment');studio=bpy.data.collections.new(name+'_Studio')
 for c in [visual,env,studio]:s.collection.children.link(c)
 objects=[o for o in source.objects if o==sourcebody or o.name.startswith(('SIM_VIS_','SIM_ROTOR_'))];mapping={}
 for o in objects:
  no=o.copy();no.name=name+'_'+o.name;no.animation_data_clear();visual.objects.link(no);mapping[o]=no
 for old,no in mapping.items():
  if old.parent:no.parent=mapping.get(old.parent)
 body=mapping[sourcebody];body['solver']='05_Propulsion_Navigation_Physics.py';body['contact_mode']='Three-circle conservative hull vs vertical cylinders and tank walls; normal/friction impulse';body['physics_bake']=True;body['physics_status']='ACTIVE_CUSTOM_SOLVER_WITH_CONTACT_RESPONSE'
 rotors={side:next(o for old,o in mapping.items() if old.name.startswith('SIM_ROTOR_'+side)) for side in ['Port','Starboard']}
 follow=bpy.data.objects.new(name+'_Camera_Follow',None);studio.objects.link(follow)
 for f,state in enumerate(frames,1):
  body.location=state['position_m'];body.rotation_quaternion=state['quaternion_wxyz'];body.keyframe_insert('location',frame=f);body.keyframe_insert('rotation_quaternion',frame=f)
  follow.location=state['position_m'];follow.keyframe_insert('location',frame=f)
  for i,side in enumerate(['Port','Starboard']):
   rotor=rotors[side];rotor.rotation_euler.y=state['rotor_angle_rad'][i];rotor.keyframe_insert('rotation_euler',index=1,frame=f);rotor['rpm']=state['rpm'][i];rotor.keyframe_insert(data_path='["rpm"]',frame=f);rotor['motor_enabled']=True
 if kind=='navigation':half=.30;center=(0,0);span=.89
 elif kind=='collision':half=.16;center=(0,-.04);span=.34
 else:
  xs=[x['position_m'][0] for x in frames];ys=[x['position_m'][1] for x in frames];center=((min(xs)+max(xs))/2,(min(ys)+max(ys))/2);half=.22;span=.48
 box(env,'Water_surface_Z0',(center[0],center[1],-.00015),(2*half,2*half,.0003),water)
 box(env,'Tank_bottom',(center[0],center[1],-.025),(2*half+.01,2*half+.01,.005),wall)
 for sign in [-1,1]:
  box(env,'Tank_wall_X',(center[0]+sign*(half+.003),center[1],-.008),(.006,2*half+.012,.038),wall)
  box(env,'Tank_wall_Y',(center[0],center[1]+sign*(half+.003),-.008),(2*half,.006,.038),wall)
  box(env,'Yellow_tank_rim_X',(center[0]+sign*(half+.003),center[1],.0115),(.007,2*half+.012,.001),yellow)
  box(env,'Yellow_tank_rim_Y',(center[0],center[1]+sign*(half+.003),.0115),(2*half,.007,.001),yellow)
 spacing=.025 if kind=='navigation' else .01
 for i in range(-int(half/spacing),int(half/spacing)+1):
  for a in [0,1]:
   loc=[center[0],center[1],.000018];loc[a]+=i*spacing;size=[2*half,.000055,.00002] if a==1 else [.000055,2*half,.00002];box(env,'Scale_grid',loc,size,white)
 for obs in data['obstacles']:
  x,y=obs['center_m'];r=obs['radius_m'];o=cyl(env,obs['name'],(x,y,.022),r,.065,orange);o['collision_shape']='VERTICAL_CYLINDER';o['radius_m']=r
  cyl(env,obs['name']+'_Yellow_Band',(x,y,.041),r+.0002,.006,yellow);label(env,obs['name'],(x,y,.055),.005,wall)
 path=data['path_m']
 if path:
  curve(env,'Planned_AStar_Route',[(x,y,.00008) for x,y in path],.00055,yellow)
  for labeltxt,point,color in [('START',C['start_m'],blue),('GOAL',C['goal_m'],green)]:
   x,y=point;curve(env,labeltxt+'_Ring',[(x+.02*math.cos(t*math.pi/32),y+.02*math.sin(t*math.pi/32),.00009) for t in range(64)],.0008,color,True);label(env,labeltxt,(x,y-.030,.00012),.007,color)
 curve(env,'Computed_Physical_Trajectory',[(d['position_m'][0],d['position_m'][1],.00012) for d in frames[::4]],.00028,blue)
 title={'navigation':'AUTONOMOUS NAVIGATION / 70 mm BOAT','collision':'CONTACT RESPONSE TEST','demo':'TWIN PROPELLER THRUST TEST'}[kind]
 label(env,title,(center[0],center[1]-half-.025,.012),.008 if kind=='navigation' else .005)
 if kind=='navigation':
  label(env,'CURRENT +X: 8 mm/s  |  YELLOW: PLAN  |  CYAN: MOTION',(0,-.35,.012),.005)
  for y in [-.24,-.12,0,.12,.24]:
   curve(env,'Current_direction_arrow',[(-.26,y,.00012),(-.23,y,.00012)],.0007,blue);curve(env,'Arrow_head',[(-.241,y-.006,.00012),(-.23,y,.00012),(-.241,y+.006,.00012)],.0007,blue)
 overview=cam(s,studio,name+'_Overview',(center[0]+.42,center[1]-.55,.72),(center[0],center[1],0),span)
 close=cam(s,studio,name+'_Follow_Camera',(.09,-.13,.105),(0,0,.016),.145);close.parent=follow
 s.camera=overview
 w=bpy.data.worlds.new(name+'_World');s.world=w;w.use_nodes=True;p=next(n for n in w.node_tree.nodes if n.type=='BACKGROUND');p.inputs[0].default_value=(.28,.37,.47,1);p.inputs[1].default_value=.45
 for n,loc,power,size in [('Key',(.15,-.15,.65),3.5,.45),('Fill',(-.5,.15,.5),2.5,.4),('Rim',(.1,.55,.5),3,.35)]:
  ld=bpy.data.lights.new(name+n,'AREA');ld.energy=power;ld.size=size;o=bpy.data.objects.new(ld.name,ld);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector((center[0],center[1],0))-o.location).to_track_quat('-Z','Y').to_euler()
 s['physics_parameters']='//Navigation_Parameters.json';s['trajectory_file']='//'+filename;s['control_mode']='A_STAR_ROUTE_AND_DIFFERENTIAL_THRUST' if kind=='navigation' else 'OPEN_LOOP_PHYSICS_TEST';s['simulation_status']='BAKED_SIX_DOF_PHYSICS_NOT_LIVE';s['limitations']='Estimated thrust/drag. No CFD. Contact response for cylinder obstacles and tank walls only; no rescue workflow yet.'
 s.timeline_markers.new('START',frame=1);s.timeline_markers.new('END',frame=len(frames))
 if kind=='demo':
  for f,n in [(151,'COAST'),(241,'DIFFERENTIAL TURN'),(421,'FORWARD'),(571,'MOTORS OFF')]:s.timeline_markers.new(n,frame=f)
 if kind=='collision':
  for e in data['events'][:1]:s.timeline_markers.new('PHYSICAL COLLISION',frame=round(e['time_s']*60)+1)
 s.frame_set(1);return s
nav=create('navigation','SIM_05_Autonomous_Navigation','Navigation_Test_Results.json')
prop=create('demo','SIM_04_Twin_Propeller_Drive','Propulsion_Test_Results.json')
collision=create('collision','SIM_05_Collision_Response','Collision_Test_Results.json')
for filename in ['Navigation_Parameters.json','Navigation_Validation_Report.json']:
 tx=bpy.data.texts.load(OUT+filename);tx.name='NAV_'+filename
for filename in ['05_Propulsion_Navigation_Physics.py','04_Model_Scale_Hydrostatics.py']:
 tx=bpy.data.texts.load(ROOT+'scripts/'+filename);tx.name='NAV_'+filename
bpy.context.window.scene=nav;nav.frame_set(1)
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':area.spaces.active.clip_start=.0001;area.spaces.active.clip_end=10;area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.overlay.show_overlays=False;area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=OUT+'05_Propulsion_And_Navigation.blend')
result={'file':bpy.data.filepath,'scenes':[prop.name,nav.name,collision.name],'frames':nav.frame_end,'validation':report}
