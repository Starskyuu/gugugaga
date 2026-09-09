import bpy, json, math, os
from mathutils import Vector, Matrix
ROOT='F:/gugugaga/blender/';OUT=ROOT+'PhysicsSimulation/'
with open(OUT+'Physics_Parameters.json',encoding='utf-8') as f:P=json.load(f)
with open(OUT+'Float_Test_Results.json',encoding='utf-8') as f:T=json.load(f)
with open(OUT+'Physics_Validation_Report.json',encoding='utf-8') as f:REPORT=json.load(f)
assert REPORT['all_passed'], 'Numerical validation must pass before scene creation.'
boat_src=bpy.data.scenes['无人遥控救援船 · 7×5 cm']
def scene(n):
 s=bpy.data.scenes.new(n);bpy.context.window.scene=s;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1.;s.unit_settings.length_unit='CENTIMETERS';s.gravity=(0,0,-P['gravity_m_s2']);s.render.fps=60;s.frame_start=1;s.frame_end=481
 s.render.engine='CYCLES';s.cycles.samples=40;s.cycles.use_denoising=True;s.render.resolution_x=1400;s.render.resolution_y=1100;s.render.resolution_percentage=100;s.view_settings.view_transform='AgX';s.render.image_settings.file_format='PNG'
 return s
def collection(s,n):
 c=bpy.data.collections.new(n);s.collection.children.link(c);return c
def material(n,color,metal=0,rough=.4):
 m=bpy.data.materials.new(n);m.diffuse_color=(*color,1);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m
watermat=material('SIM Calm freshwater',(.014,.16,.23),.32,.15);gray=material('SIM Basin floor',(.045,.075,.095),0,.8);white=material('SIM White labels',(.8,.9,.94));amber=material('SIM Measurement yellow',(.98,.65,.025))
def own(o,c,n,m=None):
 o.name=n
 for old in list(o.users_collection):old.objects.unlink(o)
 c.objects.link(o)
 if m:o.data.materials.append(m)
 return o
def cube(c,n,loc,size,m=None):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=own(bpy.context.object,c,n,m);o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);return o
def proxy(c,n,verts,faces,loc=(0,0,0),mass=None,passive=False):
 me=bpy.data.meshes.new(n);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(n,me);c.objects.link(o);o.location=loc;o.display_type='WIRE';o.hide_render=True;o.color=(1,.35,.03,1)
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.rigidbody.object_add();rb=o.rigid_body;rb.type='PASSIVE' if passive else 'ACTIVE';rb.collision_shape='CONVEX_HULL';rb.use_margin=True;rb.collision_margin=P['collision_margin_m'];rb.friction=P['collision_friction'];rb.restitution=P['collision_restitution']
 if not passive:rb.mass=mass or .001;rb.kinematic=True
 o['physics_status']='CONTACT_PROXY_PREPARED; hydro solver has no contact response';return o
def visual_mesh(src,c,n,dg,matrix):
 e=src.evaluated_get(dg);me=bpy.data.meshes.new_from_object(e);me.transform(matrix@src.matrix_world);o=bpy.data.objects.new(n,me);c.objects.link(o);return o
def camera(s,c,n,loc,target,scale):
 d=bpy.data.cameras.new(n);o=bpy.data.objects.new(n,d);c.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=scale;d.clip_start=.0001;d.clip_end=10;s.camera=o;return o
def lighting(s,c,factor=1):
 w=bpy.data.worlds.new(s.name+' World');s.world=w;w.use_nodes=True;bg=next(n for n in w.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.3,.4,.5,1);bg.inputs[1].default_value=.45
 for n,loc,power,size in [('Key',(.08,-.1,.22),10,.15),('Fill',(-.16,.06,.15),6,.12),('Rim',(.02,.18,.2),9,.1)]:
  d=bpy.data.lights.new('SIM '+n,'AREA');d.energy=power*factor*factor*.025;d.size=size*factor;o=bpy.data.objects.new(d.name,d);c.objects.link(o);o.location=Vector(loc)*factor;o.rotation_euler=(Vector((0,0,.012*factor))-o.location).to_track_quat('-Z','Y').to_euler()
def label(c,body,loc,size):
 d=bpy.data.curves.new('SIM '+body,'FONT');d.body=body;d.align_x='CENTER';d.size=size;d.extrude=.000004;o=bpy.data.objects.new(d.name,d);c.objects.link(o);o.location=loc;d.materials.append(white);return o

# Scene 1: mass-centered SI geometry and individually pivoted rotors.
bpy.context.window.scene=boat_src;bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
source_hull=next(o for o in boat_src.objects if o.name.startswith('Hull ·'))
H=[tuple(v.co*.01) for v in source_hull.data.vertices];F=[tuple(p.vertices) for p in source_hull.data.polygons]
source_meshes=[o for c in boat_src.collection.children if not c.name.startswith('09_') for o in c.objects if o.type in {'MESH','CURVE','FONT'}]
# Extract evaluated source meshes before switching away from their depsgraph.
cached=[]
for o in source_meshes:
 me=bpy.data.meshes.new_from_object(o.evaluated_get(dg));me.transform(Matrix.Scale(.01,4)@o.matrix_world);cached.append((o.name,me))
s=scene('SIM_01_Boat_Calm_Water_Float_Test');vis=collection(s,'SIM01_Visual_Boat');col=collection(s,'SIM01_Collision_Proxies');env=collection(s,'SIM01_Water_And_Measurements');studio=collection(s,'SIM01_Studio')
com=Vector(T['center_of_mass_m']);body=proxy(col,'SIM_BOAT_BODY_12g',[(Vector(v)-com)[:] for v in H],F,com,T['mass_kg']);body.rotation_mode='QUATERNION'
body['mass_kg']=T['mass_kg'];body['center_of_mass_hull_m']=T['center_of_mass_m'];body['inertia_kg_m2_flat']=[x for row in T['inertia_kg_m2'] for x in row];body['solver']='04_Model_Scale_Hydrostatics.py; SI six-DOF sampled buoyancy';body['mass_status']='PROVISIONAL_ESTIMATE'
rotors={}
for side,x in [('Port',-.0135),('Starboard',.0135)]:
 p=bpy.data.objects.new('SIM_ROTOR_'+side+'_Y_AXIS',None);vis.objects.link(p);p.parent=body;p.location=Vector((x,-.0388,.0038))-com;p.empty_display_type='ARROWS';p.empty_display_size=.003;p['axis_local']=[0,1,0];p['rpm']=0.;rotors[side]=p
for name,me in cached:
 o=bpy.data.objects.new('SIM_VIS_'+name,me);vis.objects.link(o);side='Port' if name.startswith('Port') else 'Starboard' if name.startswith('Starboard') else None
 if side and any(k in name for k in ['screw blade','propeller hub','horizontal shaft']):
  p=rotors[side];me.transform(Matrix.Translation(-(com+p.location)));o.parent=p
 else:me.transform(Matrix.Translation(-com));o.parent=body
for side,p in rotors.items():
 # A fixed pivot and limit metadata are prepared; motor drive is intentionally zero in steps 1-3.
 p['joint_type']='REVOLUTE';p['joint_limit_degrees']=[-360,360];p['motor_enabled']=False
for o in list(vis.objects):
 if 'yellow lifebuoy' in o.name:
  lo=Vector(tuple(min(v.co[i] for v in o.data.vertices) for i in range(3)));hi=Vector(tuple(max(v.co[i] for v in o.data.vertices) for i in range(3)))
  q=cube(col,'SIM_CONTACT_'+o.name,(lo+hi)/2,hi-lo);q.parent=body;q.hide_render=True;q.display_type='WIRE';q['collision_role']='Attached buoy proxy; compound contact shape pending integration'
# COM marker and zero-level surface for inspection.
bpy.ops.object.empty_add(type='SPHERE');marker=own(bpy.context.object,col,'SIM_Center_Of_Mass');marker.parent=body;marker.location=(0,0,0);marker.empty_display_size=.0015
water=cube(env,'SIM_WATER_Z_ZERO',(0,0,-.00012),(.22,.22,.00024),watermat);water['water_density_kg_m3']=1000.;water['surface_z_m']=0.;water['visual_only']=True
floor=cube(env,'SIM_Test_Basin_Floor',(0,0,-.027),(.25,.25,.004),gray)
for i in range(-10,11):
 x=i*.01
 for loc,size in [((x,0,.000018),(.00006,.22,.000025)),((0,x,.000018),(.22,.00006,.000025))]:cube(env,'SIM_10mm_Surface_Grid',loc,size,white)
label(env,'MODEL SCALE  /  70 x 50 mm',(0,-.091,.00006),.004)
label(env,'CALM WATER  |  DRY MASS 12 g',(0,-.100,.00006),.0028)
camera(s,studio,'SIM_Float_Camera',(.125,-.155,.125),(0,0,.020),.15);lighting(s,studio)
for frame,item in enumerate(T['frames'],1):
 body.location=item['position_m'];body.rotation_quaternion=item['quaternion_wxyz'];body.keyframe_insert('location',frame=frame);body.keyframe_insert('rotation_quaternion',frame=frame)
for f,n in [(1,'INITIAL HEAVE +4mm / ROLL 8deg / PITCH -5deg'),(121,'2 seconds'),(241,'4 seconds'),(481,'8 seconds / settled')]:s.timeline_markers.new(n,frame=f)
s.rigidbody_world.enabled=False;s['native_rigid_body_world']='Disabled to avoid double integration. Kinematic hull proxy follows independently calculated hydrostatic trajectory.';s['limitations']='Unpowered calm water; estimated mass/drag; contact response and capillary effects not implemented.';s['physics_parameters']='//Physics_Parameters.json';s['rebuild_script']='//../scripts/04_Rebake_Model_Scale_Float_Test.py';s.frame_set(481)

# Scene 2: use the latest base visual asset at SI scale; sliding doors and actual open bay colliders remain separate.
basepath=ROOT+'UnmannedRescueBase/02_Rescue_Base_4Boat_8EaveLights_Latest.blend'
with bpy.data.libraries.load(basepath,link=False) as (src,dst):dst.scenes=[n for n in src.scenes if n.startswith('无人救援基地')][:1]
base_src=dst.scenes[0];bpy.context.window.scene=base_src;base_src.frame_set(90);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
base_cached=[]
for o in base_src.objects:
 if o.type=='MESH' and any(o.name.startswith(n) for n in ['White facade pier','Rounded white corner shell','Doorway header','Door frame jamb','Central structural core','Dock dividing wall','Berth back wall','Rounded square foundation','Upper rescue deck','Full rounded square rain canopy']):
  me=bpy.data.meshes.new_from_object(o.evaluated_get(dg));me.transform(Matrix.Scale(.01,4)@o.matrix_world);base_cached.append((o.name,me))
door_cache=[]
for ctrl in base_src.objects:
 if not ctrl.name.startswith('DOOR_'):continue
 leaf_records=[]
 for leaf in ctrl.children:
  if not leaf.name.startswith('Sliding leaf'):continue
  children=[]
  for o in leaf.children:
   if o.type not in {'MESH','CURVE','FONT'}:continue
   me=bpy.data.meshes.new_from_object(o.evaluated_get(dg));me.transform(Matrix.Scale(.01,4)@leaf.matrix_world.inverted()@o.matrix_world);children.append((o.name,me))
  leaf_records.append((1 if leaf.location.x>0 else -1,children))
 door_cache.append((ctrl.name,float(ctrl.rotation_euler.z),leaf_records))
base=scene('SIM_02_Base_Collision_And_Door_Setup');bvis=collection(base,'SIM02_Base_Visual');bc=collection(base,'SIM02_Static_Compound_Colliders');doors=collection(base,'SIM02_Kinematic_Sliding_Doors');bstudio=collection(base,'SIM02_Studio')
asset=bpy.data.collections.new('SIM02_Base_Source_Visual_Asset')
for c in base_src.collection.children:
 if not c.name.startswith(('B11_Studio','B03_AnimatedDoors')):
  asset.children.link(c)
  for lamp in c.objects:
   if lamp.type=='LIGHT':lamp.data.energy*=.0001
inst=bpy.data.objects.new('SIM_BASE_STATIC_28cm',None);bvis.objects.link(inst);inst.instance_type='COLLECTION';inst.instance_collection=asset;inst.scale=(.01,.01,.01);inst['motion']='STATIC';inst['base_width_m']=.28
for name,me in base_cached:
 q=proxy(bc,'SIM_BASE_CONTACT_'+name,[v.co[:] for v in me.vertices],[p.vertices[:] for p in me.polygons],passive=True)
for name,angle,leaves in door_cache:
 ctrl=bpy.data.objects.new('SIM_'+name.split(' ·')[0],None);doors.objects.link(ctrl);ctrl.rotation_euler.z=angle;ctrl['joint']='PRISMATIC_LOCAL_X';ctrl['leaf_travel_m']=.0387
 for sign,children in leaves:
  p=bpy.data.objects.new(ctrl.name+('_RIGHT' if sign>0 else '_LEFT'),None);doors.objects.link(p);p.parent=ctrl;p.location=(sign*.0572,.1422,.041);p['motion']='KINEMATIC';p['limit_m']=[min(sign*.0185,sign*.0572),max(sign*.0185,sign*.0572)]
  for n,me in children:o=bpy.data.objects.new('SIM_DOOR_VIS_'+n,me);doors.objects.link(o);o.parent=p
  q=cube(bc,'SIM_DOOR_CONTACT_'+p.name,(0,0,0),(.037,.0022,.071));q.parent=p;q.hide_render=True;q.display_type='WIRE';q['collision_role']='Kinematic box collider follows slider';q['friction']=.4;q['restitution']=.05
  for f,v in [(1,.0185),(60,.0572),(120,.0572),(180,.0185)]:p.location.x=sign*v;p.keyframe_insert('location',frame=f)
base.rigidbody_world.enabled=False;base.frame_end=180;base.frame_set(90);base['collision_design']='Compound facade piers and corner walls, not a single hull across the bay doors.'
cube(bstudio,'SIM_Base_Studio_Floor',(0,0,-.0035),(3,3,.003),gray);camera(base,bstudio,'SIM_Base_Setup_Camera',(.45,-.55,.35),(0,0,.09),.5);lighting(base,bstudio,3)

# Scene 3: centimeter figurine transformed into meters, preserving its articulated bone hierarchy.
personpath=ROOT+'RescuePerson/03_Rescue_Person_Rigged_Stand_Sit.blend'
with bpy.data.libraries.load(personpath,link=False) as (src,dst):dst.collections=[n for n in src.collections if n=='PERSON · Rigged rescue passenger']
pcoll=dst.collections[0];ps=scene('SIM_03_Person_Articulated_Setup');ps.collection.children.link(pcoll);pcols=collection(ps,'SIM03_Bone_Contact_Proxies');pstudio=collection(ps,'SIM03_Studio');prig=next(o for o in pcoll.objects if o.type=='ARMATURE');prig.scale=(.01,.01,.01);prig['total_mass_kg']=P['person_mass_kg'];prig['mass_status']='Estimated 1 g model figurine; excluded from empty boat test';ps.frame_set(1);bpy.context.view_layer.update()
fractions={'pelvis':.16,'spine':.30,'neck':.02,'head':.08,'thigh.L':.10,'thigh.R':.10,'shin.L':.05,'shin.R':.05,'foot.L':.015,'foot.R':.015,'upper_arm.L':.025,'upper_arm.R':.025,'forearm.L':.02,'forearm.R':.02,'hand.L':.01,'hand.R':.01};total=sum(fractions.values())
for bone in prig.pose.bones:
 if bone.name=='root':continue
 a=prig.matrix_world@bone.head;b=prig.matrix_world@bone.tail;length=(b-a).length;radius=.001 if bone.name in ['head','pelvis','spine'] else .00055
 bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,radius=1,location=(a+b)/2);o=own(bpy.context.object,pcols,'SIM_PERSON_CONTACT_'+bone.name);o.scale=(radius,radius,length/2+radius*.25);o.rotation_mode='QUATERNION';o.rotation_quaternion=(b-a).to_track_quat('Z','Y');bpy.context.view_layer.update();world=o.matrix_world.copy();o.parent=prig;o.parent_type='BONE';o.parent_bone=bone.name;o.matrix_world=world;o.hide_render=True;o.display_type='WIRE';o['mass_kg']=P['person_mass_kg']*fractions[bone.name]/total;o['contact_status']='Bone-following capsule proxy prepared; not active ragdoll'
ps['person_total_mass_kg']=P['person_mass_kg'];ps['joint_model']='17-bone pose rig; body contact proxies follow 16 deforming bones; ragdoll dynamics not activated';ps.frame_end=60
cube(pstudio,'SIM_Person_Studio_Floor',(0,0,-.0004),(.2,.2,.0008),gray);camera(ps,pstudio,'SIM_Person_Setup_Camera',(.035,.06,.035),(0,0,.011),.03);lighting(ps,pstudio,.22)

# Bundle editable settings, solver and instructions in the project as text blocks.
for path in [OUT+'Physics_Parameters.json',OUT+'Physics_Validation_Report.json',ROOT+'scripts/04_Model_Scale_Hydrostatics.py']:
 tx=bpy.data.texts.load(path);tx.name='SIM_'+os.path.basename(path)
bpy.context.window.scene=s;s.frame_set(481)
for a in bpy.context.screen.areas:
 if a.type=='VIEW_3D':a.spaces.active.clip_start=.0001;a.spaces.active.clip_end=10;a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.overlay.show_overlays=False;a.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=OUT+'04_Model_Scale_Physics_Setup.blend')
result={'file':bpy.data.filepath,'scenes':[s.name,base.name,ps.name],'hull_dimensions_m':list(body.dimensions),'boat_mass_kg':T['mass_kg'],'rotors':list(rotors.keys()),'base_static_colliders':len(base_cached),'sliding_doors':len(door_cache),'person_contact_segments':len(pcols.objects),'trajectory_frames':len(T['frames']),'validation_passed':REPORT['all_passed']}
