"""Build a new SI-scale rescue mission without modifying the original assets."""
import bpy, math, json, re
from mathutils import Vector, Matrix, Quaternion
from pathlib import Path
ROOT=Path('F:/gugugaga/blender');OUT=ROOT/'PhysicsSimulation'
T=json.loads((OUT/'Rescue_Mission_Results.json').read_text(encoding='utf-8'))
M=json.loads((OUT/'Rescue_Mission_Parameters.json').read_text(encoding='utf-8'))
REPORT=json.loads((OUT/'Rescue_Mission_Validation_Report.json').read_text(encoding='utf-8'))
assert REPORT['all_passed'],REPORT
assert not bpy.data.scenes.get('SIM_06_Rescue_Mission'),'Mission already exists: reopen the step-5 file before rebuilding.'
source=bpy.data.scenes.get('SIM_01_Boat_Calm_Water_Float_Test')
if not source:
 with bpy.data.libraries.load(str(OUT/'04_Model_Scale_Physics_Setup.blend'),link=False) as (a,b):b.scenes=['SIM_01_Boat_Calm_Water_Float_Test']
 source=b.scenes[0]
base=bpy.data.scenes.get('SIM_02_Base_Collision_And_Door_Setup')
if not base:
 with bpy.data.libraries.load(str(OUT/'04_Model_Scale_Physics_Setup.blend'),link=False) as (a,b):b.scenes=['SIM_02_Base_Collision_And_Door_Setup']
 base=b.scenes[0]
asset=next(o.instance_collection for o in base.objects if o.name.startswith('SIM_BASE_STATIC'))
with bpy.data.libraries.load(str(ROOT/'RescuePerson/03_Rescue_Person_Rigged_Stand_Sit.blend'),link=False) as (a,b):b.collections=['PERSON · Rigged rescue passenger']
pc=b.collections[0];lib=bpy.data.scenes.new('MISSION_Source_Poses');lib.collection.children.link(pc);bpy.context.window.scene=lib
prig=next(o for o in pc.objects if o.type=='ARMATURE');poses={}
for name,frame in [('stand',1),('sit',60)]:
 lib.frame_set(frame);bpy.context.view_layer.update();poses[name]={pb.name:pb.matrix_basis.copy() for pb in prig.pose.bones}

s=bpy.data.scenes.new('SIM_06_Rescue_Mission');bpy.context.window.scene=s;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;s.unit_settings.length_unit='CENTIMETERS';s.render.fps=60;s.frame_end=len(T['frames']);s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.resolution_x=1600;s.render.resolution_y=1100;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX'
def coll(n):
 c=bpy.data.collections.new(n);s.collection.children.link(c);return c
bc=coll('MISSION_Base_Wet_Dock');roof=coll('MISSION_Roof_And_Searchlights');doors=coll('MISSION_Animated_Gates');boatc=coll('MISSION_Active_Boat');others=coll('MISSION_Three_Standby_Boats');people=coll('MISSION_Two_Rescue_Passengers');env=coll('MISSION_Water_And_Transfer_Platforms');studio=coll('MISSION_Cameras_And_Lighting');hud=coll('MISSION_Status_Display')
def safe(n):return re.sub('[^A-Za-z0-9_. -]','_',n)
def mat(n,color,metal=0,rough=.4):
 m=bpy.data.materials.new('MISSION_'+n);m.diffuse_color=(*color,1);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m
water=mat('Water',(.018,.11,.15),.2,.25);orange=mat('Safety_Orange',(1,.23,.015));white=mat('Warm_White',(.8,.85,.83));dark=mat('Graphite',(.025,.05,.07));silver=mat('Aluminum',(.48,.6,.65),.75);rope=mat('Rope',(.63,.46,.22));cyan=mat('Cyan',(.015,.62,.72));yellow=mat('Yellow',(.95,.65,.02))
def own(o,c,n,m=None):
 for oc in list(o.users_collection):oc.objects.unlink(o)
 c.objects.link(o);o.name=safe(n)
 if m:o.data.materials.append(m)
 return o
def box(c,n,loc,size,m):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=own(bpy.context.object,c,n,m);o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return o
def curve(c,n,pts,r,m,closed=False):
 d=bpy.data.curves.new(n,'CURVE');d.dimensions='3D';d.bevel_depth=r;d.bevel_resolution=2;sp=d.splines.new('POLY');sp.points.add(len(pts)-1)
 for p,v in zip(sp.points,pts):p.co=(*v,1)
 sp.use_cyclic_u=closed;o=bpy.data.objects.new(n,d);c.objects.link(o);d.materials.append(m);return o
def text(c,n,body,loc,size,m=white):
 d=bpy.data.curves.new(n,'FONT');d.body=body;d.size=size;d.align_x='CENTER';o=bpy.data.objects.new(n,d);c.objects.link(o);o.location=loc;d.materials.append(m);return o
def empty(c,n):
 o=bpy.data.objects.new(n,None);c.objects.link(o);return o
def camera(n,loc,target,span):
 d=bpy.data.cameras.new(n);o=bpy.data.objects.new(n,d);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=span;d.clip_start=.0001;d.clip_end=10;return o
def transform_key(o,f,loc,q=None):
 o.location=loc;o.keyframe_insert('location',frame=f)
 if q is not None:o.rotation_mode='QUATERNION';o.rotation_quaternion=q;o.keyframe_insert('rotation_quaternion',frame=f)
def visible(o,f,on):
 o.hide_render=not on;o.hide_viewport=not on;o.keyframe_insert('hide_render',frame=f);o.keyframe_insert('hide_viewport',frame=f)

# Flatten static base geometry at exact SI scale. Only the new wet-dock copy is
# changed: lower submerged floors, skirts, and thresholds to clear the hull.
bpy.context.window.scene=base;base.frame_set(90);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();cached=[]
for c in asset.children:
 if c.name.startswith('B04'):continue
 for o in c.objects:
  if o.type not in {'MESH','CURVE','FONT'}:continue
  me=bpy.data.meshes.new_from_object(o.evaluated_get(dg));me.transform(Matrix.Scale(.01,4)@o.matrix_world)
  if o.name.startswith(('Rounded square foundation','Yellow lower skirt','Boat bay floor','Dark door threshold','Berth floor identifier')):
   top=max(v.co.z for v in me.vertices);desired=M['wet_dock_floor_top_m']-(.003 if 'foundation' in o.name else .001 if 'skirt' in o.name else 0)
   me.transform(Matrix.Translation((0,0,desired-top)))
  cached.append((o.name,me,c.name.startswith(('B09','B10','B12'))))
bpy.context.window.scene=s
for n,me,isroof in cached:
 o=bpy.data.objects.new('MISSION_BASE_'+safe(n),me);(roof if isroof else bc).objects.link(o)
o=box(bc,'North_Walkway_Extension',(0.015,.1525,.0093),(.03,.0145,.003),white);o['purpose']='Bridge existing doorway-to-ladder platform to the centerline transfer gangway'
# Copy independent door roots, leaf pivots and decorative meshes.
mapping={}
for o in base.objects:
 if o.name.startswith(('SIM_DOOR_','SIM_DOOR_VIS_')):
  no=o.copy();no.animation_data_clear();no.name='MISSION_'+safe(o.name);doors.objects.link(no);mapping[o]=no
for o,no in mapping.items():no.parent=mapping.get(o.parent)
leaves=[o for o in mapping.values() if o.get('motion')=='KINEMATIC']

srcbody=next(o for o in source.objects if o.name.startswith('SIM_BOAT_BODY'))
drycom=Vector(T['frames'][0]['center_of_mass_m'])
def boat_copy(c,prefix):
 mapping={}
 for o in source.objects:
  if o==srcbody or o.name.startswith(('SIM_VIS_','SIM_ROTOR_')):
   no=o.copy();no.animation_data_clear();no.name=prefix+safe(o.name);c.objects.link(no);mapping[o]=no
 for old,no in mapping.items():no.parent=mapping.get(old.parent)
 body=mapping[srcbody];body['physics_status']='MISSION_SIX_DOF_WITH_PAYLOAD';body['mass_reference']='Dynamic COM stored in mission results; visual pivot stays at dry COM'
 return body,[next(no for old,no in mapping.items() if old.name.startswith('SIM_ROTOR_'+side)) for side in ['Port','Starboard']],mapping
body,rotors,bmap=boat_copy(boatc,'MISSION_BOAT_')
for i in [1,2,3]:
 ob,_,_=boat_copy(others,f'STANDBY_{i+1}_');q=Quaternion((0,0,1),i*math.pi/2);origin=Vector((-.0935*math.sin(i*math.pi/2),.0935*math.cos(i*math.pi/2),-.00456848));ob.location=origin+q@drycom;ob.rotation_quaternion=q;ob['physics_status']='STATIC_STANDBY_NOT_DISPATCHED'
# Add a real bow gate to the new active-boat copy, instead of walking through
# the original continuous rails/rope. The source boat remains unchanged.
for old,no in bmap.items():
 if any(t in old.name for t in ['Top rail','Mid rail','Perimeter rescue rope']):no.hide_render=True;no.hide_viewport=True
 if 'Railing post' in old.name and no.type=='MESH':
  if sum(v.co.y for v in no.data.vertices)/len(no.data.vertices)+drycom.y>.030:no.hide_render=True;no.hide_viewport=True
outline=[(-.025,-.035),(.025,-.035),(.025,.019),(.022,.026),(.013,.032),(.0045,.035),(-.0045,.035),(-.013,.032),(-.022,.026),(-.025,.019)]
railpath=[(x*.93,y*.94) for x,y in outline];openpath=railpath[7:]+railpath[:5]
for z,r,ma in [(.0216,.0004,silver),(.0168,.00025,silver),(.02235,.00033,rope)]:
 o=curve(boatc,'MISSION_Bow_Gated_Rail',[(x,y,z) for x,y in openpath],r,ma);o.parent=body;o.location=-drycom
gate=empty(boatc,'MISSION_Bow_Access_Gate');gate.parent=body;gate.location=Vector((-.01209,.03008,0))-drycom
for z,r,ma in [(.0216,.0004,silver),(.0168,.00025,silver),(.02235,.00033,rope)]:
 o=curve(boatc,'MISSION_Bow_Gate_Bar',[(0,0,z),(.02418,0,z)],r,ma);o.parent=gate
for x in [0,.02418]:
 o=curve(boatc,'MISSION_Bow_Gate_Upright',[(x,0,.012),(x,0,.0216)],.00035,silver);o.parent=gate

# Context water, pickup platform and retractable transfer bridges.
box(env,'Flood_Test_Water',(0,.12,-.0002),(.75,.88,.0004),water)
box(env,'Submerged_Test_Bottom',(0,.12,-.025),(.75,.88,.006),dark)
box(env,'Pickup_Safe_Platform',(0,.444,.006),(.07,.05,.006),orange)
text(env,'Pickup_Label','PICKUP / 2 PEOPLE',(0,.474,.0091),.005)
text(env,'Mission_Label','SINGLE BOAT RESCUE / MODEL SCALE',(0,.526,.001),.007)
for x in [-.22,.22]:curve(env,'Model_Scale_Reference',[(x,-.12,.00004),(x,.48,.00004)],.00015,white)
pickbridge=box(env,'Pickup_Retractable_Gangway',(0,.418,.008),(.012,.028,.001),orange)
basebridge=box(env,'Base_Retractable_Gangway',(0,.140,.009),(.012,.026,.001),orange)
stages={x['phase']:x for x in T['stages']}
def tf(t):return round(t*60)+1
for ob,phase in [(pickbridge,'BOARDING'),(basebridge,'DISEMBARKING')]:
 visible(ob,1,False);visible(ob,tf(stages[phase]['start_s']),True);visible(ob,tf(stages[phase]['end_s']),False)
curve(env,'Outbound_Physical_Track',[(r['hull_origin_m'][0]-.003,r['hull_origin_m'][1],.00008) for r in T['frames'][::12] if r['phase']=='OUTBOUND'],.00025,yellow)
curve(env,'Return_Physical_Track',[(r['hull_origin_m'][0]+.003,r['hull_origin_m'][1],.00008) for r in T['frames'][::12] if r['phase']=='RETURN_LOADED'],.00025,cyan)

follow=empty(studio,'MISSION_Boat_Camera_Target')
for f,r in enumerate(T['frames'],1):
 q=Quaternion(r['quaternion_wxyz']);origin=Vector(r['hull_origin_m']);transform_key(body,f,origin+q@drycom,q);body['mass_kg']=r['mass_kg'];body.keyframe_insert(data_path='["mass_kg"]',frame=f);body['passenger_count']=len(r['onboard']);body.keyframe_insert(data_path='["passenger_count"]',frame=f)
 transform_key(follow,f,origin)
 for i,o in enumerate(rotors):o.rotation_euler.y=r['rotor_angle_rad'][i];o.keyframe_insert('rotation_euler',index=1,frame=f);o['rpm']=r['rpm'][i];o.keyframe_insert(data_path='["rpm"]',frame=f)
 for o in leaves:
  is_north=o.parent.name.endswith('SIM_DOOR_1');fraction=r['gate_open_fraction'] if is_north else 0.;o.location.x=(1 if 'RIGHT' in o.name else -1)*(.0185+.0387*fraction);o.keyframe_insert('location',frame=f)
 gate.rotation_euler.z=math.pi/2 if r['phase'] in ['BOARDING','DISEMBARKING'] else 0;gate.keyframe_insert('rotation_euler',index=2,frame=f)

def interpolate_path(points,t):
 if t<=points[0][0]:return Vector(points[0][1])
 for (a,p),(b,q) in zip(points,points[1:]):
  if t<=b:return Vector(p).lerp(Vector(q),(t-a)/(b-a))
 return Vector(points[-1][1])
def passenger_state(i,r):
 person=M['passengers'][i];t=r['time_s'];origin=Vector(r['hull_origin_m']);q=Quaternion(r['quaternion_wxyz']);seat=Vector(person['seat_origin_m']);bs=stages['BOARDING']['start_s']+person['board_offset_s']-4;be=bs+4;us=stages['DISEMBARKING']['start_s']+person['unload_offset_s']-4;ue=us+4
 wait=Vector(((-1 if i==0 else 1)*.015,.44,.009));yaw=math.pi;sit=0.;walking=False;climbing=False
 if t<bs:return wait,yaw,0,False,False
 if t<be:
  a=t-bs;entry=origin+q@Vector((0,.040,.012));middle=origin+q@Vector((0,.025,.012));stand=origin+q@Vector((seat.x,seat.y,.012));end=origin+q@seat
  pos=interpolate_path([(0,wait),(1,(0,.427,.009)),(2,entry),(2.7,middle),(3.4,stand),(4,end)],a);sit=max(0,(a-3.4)/.6);yaw=0 if a>2.7 else math.pi;walking=a<3.4
 elif t<us:return origin+q@seat,math.atan2((q.to_matrix())[1][0],(q.to_matrix())[0][0]),1,False,False
 elif t<ue:
  a=t-us;start=origin+q@seat;stand=origin+q@Vector((seat.x,seat.y,.012));middle=origin+q@Vector((0,.025,.012));entry=origin+q@Vector((0,.040,.012));pos=interpolate_path([(0,start),(.6,stand),(1.4,middle),(2.2,entry),(4,(0,.1525,.0108))],a);sit=max(0,1-a/.6);yaw=0;walking=a>.6
 else:
  a=t-ue;bx=.01725 if i==0 else .02875
  route=[(0,(0,.1525,.0108)),(3,(.05,.1525,.0108)),(5,(.087,.165,.01085)),(6,(.087,.176,.01145))]
  # Fifteen actual tread heights, with one staged step per second.
  for j in range(15):route.append((7+j,(.087,.1735-.03*j/14,.01145+.0751*j/14)))
  route += [(23,(.087,.132,.0861)),(26,(.06,.11,.0861)),(29,(bx,.079,.0861)),(31,(bx,.0635,.0861)),(32,(bx,.0635,.08555))]
  pos=interpolate_path(route,a);climbing=6<a<22;walking=a<31 and not climbing;sit=max(0,min(1,a-31));yaw=math.pi if 5<a<31 else (-math.pi/2 if a<5 else 0)
 return pos,yaw,sit,walking,climbing

rigs=[]
for i in range(2):
 mapping={}
 for old in pc.objects:
  no=old.copy();no.animation_data_clear();no.name=f'MISSION_P{i+1:02d}_'+safe(old.name)
  if old.type=='ARMATURE':no.data=old.data.copy()
  people.objects.link(no);mapping[old]=no
 for old,no in mapping.items():
  no.parent=mapping.get(old.parent)
  for mod in no.modifiers:
   if mod.type=='ARMATURE':mod.object=mapping[prig]
 rig=mapping[prig];rig.scale=(.01,)*3;rig['mass_kg']=M['passengers'][i]['mass_kg'];rig['motion_model']='Choreographed poses, no character contact dynamics';rigs.append(rig)
 # 15 fps character pose keys, plus exact attach/detach event frames; boat stays 60 fps.
 exact={tf(stages['BOARDING']['start_s']+M['passengers'][i]['board_offset_s']),tf(stages['DISEMBARKING']['start_s']+M['passengers'][i]['unload_offset_s'])}
 for f in sorted(set(range(1,len(T['frames'])+1,4))|exact|{len(T['frames'])}):
  r=T['frames'][f-1];pos,yaw,sit,walk,climb=passenger_state(i,r);q=Quaternion((0,0,1),yaw)
  if sit==1 and M['passengers'][i]['id'] in r['onboard']:q=Quaternion(r['quaternion_wxyz'])
  transform_key(rig,f,pos,q)
  for pb in rig.pose.bones:
   a=poses['stand'][pb.name];b=poses['sit'][pb.name];la,qa,sa=a.decompose();lb,qb,sb=b.decompose();pb.location=la.lerp(lb,sit);pb.rotation_mode='QUATERNION';pb.rotation_quaternion=qa.slerp(qb,sit);pb.scale=sa.lerp(sb,sit)
   if walk or climb:
    swing=math.sin(r['time_s']*2*math.pi*1.2+(i*math.pi));side=1 if pb.name.endswith('.L') else -1
    if pb.name.startswith('thigh'):pb.rotation_quaternion.rotate(Quaternion((1,0,0),side*swing*(.22 if walk else .4)))
    if pb.name.startswith('upper_arm'):pb.rotation_quaternion.rotate(Quaternion((1,0,0),-.9 if climb else -side*swing*.15))
    if pb.name.startswith('forearm') and climb:pb.rotation_quaternion.rotate(Quaternion((1,0,0),-.6))
   for channel in ['location','rotation_quaternion','scale']:pb.keyframe_insert(channel,frame=f)

overview=camera('MISSION_Camera_Overview',(.58,.86,.53),(0,.13,.045),.78)
close=camera('MISSION_Camera_Boat_Follow',(.10,.14,.10),(0,0,.02),.15);close.parent=follow
transfercam=camera('MISSION_Camera_People_Transfer',(.24,.38,.20),(.055,.12,.064),.25)
deckcam=camera('MISSION_Camera_Shelter_Seats',(.14,.27,.125),(.015,.069,.098),.15)
s.camera=overview
for phase in T['stages']:
 marker=s.timeline_markers.new(phase['phase'],frame=tf(phase['start_s']));marker.camera=overview
 if phase['phase'] in ['BOARDING']:marker.camera=close
 if phase['phase'] in ['DISEMBARKING','TRANSFER_TO_SHELTER']:marker.camera=transfercam
 if phase['phase'] in ['CLOSE_GATE','COMPLETE']:marker.camera=deckcam
# Camera-local, time-windowed phase labels; no frame handlers or auto-run needed.
for index,phase in enumerate(T['stages']):
 cam=next(m.camera for m in s.timeline_markers if m.name==phase['phase']);width=cam.data.ortho_scale;height=width*s.render.resolution_y/s.render.resolution_x
 ob=text(hud,'HUD_'+phase['phase'],phase['phase'].replace('_',' '),(0,0,0),width*.018);ob.parent=cam;ob.location=(0,height*.43,-.01);visible(ob,1,index==0)
 if index:visible(ob,tf(phase['start_s']),True)
 if index<len(T['stages'])-1:visible(ob,tf(phase['end_s']),False)
w=bpy.data.worlds.new('MISSION_World');s.world=w;w.use_nodes=True;bg=next(n for n in w.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.3,.4,.48,1);bg.inputs[1].default_value=.5
for name,loc,power,size in [('Key',(.25,.4,.75),7,.5),('Fill',(-.4,.1,.4),4,.4),('Rim',(.1,-.5,.6),5,.4)]:
 d=bpy.data.lights.new('MISSION_'+name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(d.name,d);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,.1,.04))-o.location).to_track_quat('-Z','Y').to_euler()
# Set numeric interpolation linear and visibility/gates discrete.
for ob in list(s.objects):
 if not ob.animation_data or not ob.animation_data.action:continue
 for layer in ob.animation_data.action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     discrete=fc.data_path in ['hide_render','hide_viewport'] or ob==gate
     for k in fc.keyframe_points:k.interpolation='CONSTANT' if discrete else 'LINEAR'
s['simulation_status']='BAKED_PHYSICS_WITH_KINEMATIC_MISSION_ACTIONS';s['boat_hull_size_m']=[.07,.05];s['mission_passengers']=2;s['limits']=M['limits'];s['wet_dock_changes']='Lowered foundation/floor/thresholds; new bow gate and retractable footbridges in this copy only.';s['guide']='//Rescue_Mission_Guide.md'
for filename in ['Rescue_Mission_Parameters.json','Rescue_Mission_Validation_Report.json']:
 tx=bpy.data.texts.load(str(OUT/filename));tx.name='MISSION_'+filename
for filename in ['06_Rescue_Mission_Physics.py','06_Build_Rescue_Mission.py']:
 tx=bpy.data.texts.load(str(ROOT/'scripts'/filename));tx.name='MISSION_'+filename
bpy.context.window.scene=s;s.frame_set(1)
for area in bpy.context.screen.areas:
 if area.type=='VIEW_3D':area.spaces.active.clip_start=.0001;area.spaces.active.clip_end=10;area.spaces.active.region_3d.view_perspective='CAMERA';area.spaces.active.shading.type='MATERIAL';area.spaces.active.overlay.show_overlays=False
exec(compile((ROOT/'scripts/06_Finalize_And_Check_Mission.py').read_text(encoding='utf-8'),'06_Finalize_And_Check_Mission.py','exec'))
result={'file':bpy.data.filepath,'scene':s.name,'frames':s.frame_end,'people':len(rigs),'physical_mass_g':[REPORT['empty_mass_g'],REPORT['loaded_mass_g']],'validated':REPORT['all_passed']}
