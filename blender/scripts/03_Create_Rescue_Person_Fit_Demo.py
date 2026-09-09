import bpy, math, os
from mathutils import Vector, Matrix
from math import pi
OUT='F:/gugugaga/blender/RescuePerson';os.makedirs(OUT,exist_ok=True)
sourceboat=bpy.data.scenes['无人遥控救援船 · 7×5 cm']
s=bpy.data.scenes.new('救援小人 · 骨架与姿态');bpy.context.window.scene=s
s.unit_settings.system='METRIC';s.unit_settings.scale_length=.01;s.unit_settings.length_unit='CENTIMETERS'
person=bpy.data.collections.new('PERSON · Rigged rescue passenger');s.collection.children.link(person)
def mat(n,col,metal=0,rough=.5):
 m=bpy.data.materials.new('PERSON · '+n);m.diffuse_color=(*col,1);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough;return m
skin=mat('Warm skin',(.62,.35,.21));suit=mat('Marine blue clothing',(.035,.12,.17));orange=mat('Rescue orange life jacket',(1,.22,.012));black=mat('Boots and webbing',(.015,.022,.027));silver=mat('Reflective strips',(.74,.83,.85),.5,.25);hair=mat('Short hair',(.045,.028,.019));white=mat('Eye white',(.85,.89,.87));red=mat('Release buckle',(.75,.02,.015))
parts=[]
def own(o,n,m,bone):
 o.name='PERSON · '+n
 for c in list(o.users_collection):c.objects.unlink(o)
 person.objects.link(o);o.data.materials.append(m)
 if bone:parts.append((o,bone))
 return o
def ell(n,loc,scale,m,bone):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,radius=1,location=loc);o=own(bpy.context.object,n,m,bone);o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 for p in o.data.polygons:p.use_smooth=True
 return o
def box(n,loc,size,m,bone,w=.02):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=own(bpy.context.object,n,m,bone);o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if w:mod=o.modifiers.new('Soft edges','BEVEL');mod.width=w;mod.segments=3
 return o
def limb(n,a,b,r,m,bone):
 a,b=Vector(a),Vector(b);mid=(a+b)/2;o=ell(n,mid,(r,r,(b-a).length/2+r*.2),m,bone);o.rotation_mode='QUATERNION';o.rotation_quaternion=(b-a).to_track_quat('Z','Y');return o

# Separate rigidly weighted body segments keep this small simulation character easy to edit.
spec=[('root',(0,0,0),(0,0,.2),None),('pelvis',(0,0,1.1),(0,0,1.22),'root'),('spine',(0,0,1.20),(0,0,1.66),'pelvis'),('neck',(0,0,1.66),(0,0,1.80),'spine'),('head',(0,0,1.80),(0,0,2.07),'neck')]
for side,sg in [('L',-1),('R',1)]:
 spec.extend([(f'thigh.{side}',(sg*.145,0,1.1),(sg*.145,0,.52),'pelvis'),(f'shin.{side}',(sg*.145,0,.52),(sg*.145,0,.07),f'thigh.{side}'),(f'foot.{side}',(sg*.145,0,.07),(sg*.145,.16,.07),f'shin.{side}'),(f'upper_arm.{side}',(sg*.29,0,1.61),(sg*.375,0,1.30),'spine'),(f'forearm.{side}',(sg*.375,0,1.30),(sg*.39,.025,1.03),f'upper_arm.{side}'),(f'hand.{side}',(sg*.39,.025,1.03),(sg*.39,.025,.93),f'forearm.{side}')])
ad=bpy.data.armatures.new('Rescue passenger skeleton');rig=bpy.data.objects.new('PERSON_RIG · Stand 1 / Sit 60',ad);person.objects.link(rig);rig.show_in_front=True;ad.display_type='STICK'
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
for n,h,t,p in spec:
 b=ad.edit_bones.new(n);b.head=h;b.tail=t
 if p:b.parent=ad.edit_bones[p]
bpy.ops.object.mode_set(mode='OBJECT')
box('Hip trousers',(0,0,1.095),(.42,.28,.24),suit,'pelvis',.08)
ell('Torso',(0,0,1.435),(.24,.14,.27),suit,'spine')
box('Life jacket back',(0,-.115,1.46),(.49,.12,.43),orange,'spine',.05)
for sg in [-1,1]:
 box('Life jacket front float',(sg*.13,.122,1.465),(.245,.135,.43),orange,'spine',.045)
 box('Reflective shoulder patch',(sg*.13,.198,1.60),(.13,.018,.12),silver,'spine',.009)
 box('Vest lower reflective patch',(sg*.15,.196,1.32),(.11,.015,.07),silver,'spine',.008)
box('Vest black waist belt',(0,.204,1.36),(.49,.025,.05),black,'spine',.006)
box('Vest central buckle',(0,.225,1.36),(.075,.025,.065),silver,'spine',.009)
box('Vest zipper',(0,.2,1.52),(.018,.015,.27),black,'spine',.002)
limb('Neck',(0,0,1.69),(0,0,1.81),.063,skin,'neck')
ell('Head',(0,.005,1.95),(.155,.145,.20),skin,'head')
ell('Short hair cap',(0,-.025,2.065),(.157,.137,.085),hair,'head')
ell('Nose',(0,.147,1.944),(.028,.036,.039),skin,'head')
for sg in [-1,1]:
 ell('Ear',(sg*.151,0,1.95),(.031,.039,.052),skin,'head')
 ell('Eye',(sg*.058,.136,1.99),(.034,.015,.023),white,'head')
 ell('Pupil',(sg*.058,.151,1.99),(.014,.006,.016),black,'head')
 box('Eyebrow',(sg*.057,.146,2.025),(.057,.011,.009),hair,'head',.003)
box('Neutral mouth',(0,.142,1.891),(.063,.009,.011),hair,'head',.004)
for side,sg in [('L',-1),('R',1)]:
 limb('Upper trouser leg '+side,(sg*.145,0,1.1),(sg*.145,0,.52),.10,suit,'thigh.'+side)
 ell('Knee '+side,(sg*.145,0,.52),(.095,.095,.095),suit,'shin.'+side)
 limb('Lower trouser leg '+side,(sg*.145,0,.52),(sg*.145,0,.10),.08,suit,'shin.'+side)
 box('Boot '+side,(sg*.145,.068,.067),(.18,.30,.13),black,'foot.'+side,.045)
 box('Boot sole '+side,(sg*.145,.075,.013),(.182,.30,.025),black,'foot.'+side,.01)
 ell('Shoulder '+side,(sg*.29,0,1.60),(.094,.1,.10),suit,'upper_arm.'+side)
 limb('Sleeve '+side,(sg*.29,0,1.61),(sg*.375,0,1.30),.072,suit,'upper_arm.'+side)
 ell('Elbow '+side,(sg*.375,0,1.30),(.064,.065,.065),suit,'forearm.'+side)
 limb('Forearm '+side,(sg*.375,0,1.30),(sg*.39,.025,1.04),.056,suit,'forearm.'+side)
 ell('Hand '+side,(sg*.39,.025,.99),(.058,.043,.078),skin,'hand.'+side)
 ell('Thumb '+side,(sg*.35,.045,1.005),(.025,.033,.048),skin,'hand.'+side)
for o,b in parts:
 vg=o.vertex_groups.new(name=b);vg.add(list(range(len(o.data.vertices))),1,'REPLACE');mod=o.modifiers.new('Rescue skeleton deformation','ARMATURE');mod.object=rig;o.parent=rig
rig['asset_role']='Reusable rigged rescue passenger';rig['standing_height_cm']=2.15;rig['seat_contact_height_local_cm']=.975;rig['facing']='+Y';rig['poses']='Frame 1 standing; frame 60 seated. Use Pose Mode for other motions.'
for pb in rig.pose.bones:
 pb.rotation_mode='QUATERNION';pb.keyframe_insert('location',frame=1);pb.keyframe_insert('rotation_quaternion',frame=1);pb.keyframe_insert('scale',frame=1)

def orient(n,h,t):
 pb=rig.pose.bones[n];rest=pb.bone;h,t=Vector(h),Vector(t);rot=(rest.tail_local-rest.head_local).rotation_difference(t-h)
 pb.matrix=Matrix.Translation(h)@rot.to_matrix().to_4x4()@rest.matrix_local.to_3x3().to_4x4();bpy.context.view_layer.update()
for side,sg in [('L',-1),('R',1)]:
 hip=Vector((sg*.145,0,1.1));knee=hip+Vector((0,math.sqrt(.58**2-.1**2),-.1));ankle=knee+Vector((0,0,-.45))
 orient('thigh.'+side,hip,knee);orient('shin.'+side,knee,ankle);orient('foot.'+side,ankle,ankle+Vector((0,.16,0)))
 shoulder=Vector((sg*.29,0,1.61));elbow=shoulder+Vector((sg*.085,.11,-.289827));wrist=elbow+Vector((0,.265,.025))
 orient('upper_arm.'+side,shoulder,elbow);orient('forearm.'+side,elbow,wrist);orient('hand.'+side,wrist,wrist+Vector((0,.10,0)))
for pb in rig.pose.bones:
 pb.keyframe_insert('location',frame=60);pb.keyframe_insert('rotation_quaternion',frame=60);pb.keyframe_insert('scale',frame=60)
s.frame_start=1;s.frame_end=60;s.timeline_markers.new('STAND',frame=1);s.timeline_markers.new('SIT',frame=60);s.frame_set(60);bpy.context.view_layer.update()
# Freeze an independent seated rig for fitting scenes; source rig keeps animation.
seated=bpy.data.collections.new('PERSON · Seated reusable rig');mapping={}
for o in person.objects:
 no=o.copy()
 if o==rig:no.data=o.data.copy();no.animation_data_clear()
 seated.objects.link(no);mapping[o]=no
for old,no in mapping.items():
 if old.parent:no.parent=mapping.get(old.parent,old.parent)
 for mod in no.modifiers:
  if mod.type=='ARMATURE':mod.object=mapping[rig]
mapping[rig].name='PERSON_RIG · Seated ready to place'
# Preserve pose bases after removing animation.
for pb in rig.pose.bones:mapping[rig].pose.bones[pb.name].matrix_basis=pb.matrix_basis.copy()

studio=bpy.data.collections.new('PERSON · Presentation');s.collection.children.link(studio)
def studio_box(n,loc,size,m):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=n
 for c in list(o.users_collection):c.objects.unlink(o)
 studio.objects.link(o);o.scale=size;o.data.materials.append(m);return o
ground=mat('Studio ground',(.07,.11,.13),0,.8)
studio_box('Person studio floor',(0,0,-.045),(200,200,.08),ground)
def camera(scene,n,loc,target,scale):
 d=bpy.data.cameras.new(n);o=bpy.data.objects.new(n,d);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=scale;d.clip_start=.001;scene.camera=o;return o
def setup(scene):
 scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.01;scene.unit_settings.length_unit='CENTIMETERS';scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.render.resolution_x=1300;scene.render.resolution_y=1100;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
 w=bpy.data.worlds.new(scene.name+' World');scene.world=w;w.use_nodes=True;p=next(n for n in w.node_tree.nodes if n.type=='BACKGROUND');p.inputs[0].default_value=(.35,.42,.5,1);p.inputs[1].default_value=.5
def light(n,loc,power,size):
 d=bpy.data.lights.new(n,'AREA');d.energy=power;d.shape='DISK';d.size=size;o=bpy.data.objects.new(n,d);studio.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
light('Person key',(2,4,7),800,5);light('Person fill',(-4,1,4),550,4);light('Person rim',(0,-4,6),1000,3)
setup(s);camera(s,'PERSON Camera · character',(4,7,4),(0,0,1.1),3.1);s.frame_set(1)

# A standalone seated fitting scene uses copies of the real boat chair.
fit=bpy.data.scenes.new('救援小人 · 单座适配');bpy.context.window.scene=fit;setup(fit);fit.collection.children.link(studio)
chair=bpy.data.collections.new('FIT · Original boat seat');fit.collection.children.link(chair)
srcparent=bpy.data.objects['Port Seat 1 Assembly']
for old in srcparent.children:
 if any(t in old.name for t in ['safety belt','buckle','red release']):continue
 no=old.copy();no.parent=None;no.matrix_world=old.matrix_world.copy();no.location+=Vector((1.5,1.85,-1.2));chair.objects.link(no)
o=bpy.data.objects.new('Passenger seated in original chair',None);chair.objects.link(o);o.instance_type='COLLECTION';o.instance_collection=seated;o.location=(0,-.10,-.465)
camera(fit,'PERSON Camera · seat fit',(3.5,5.3,3),(0,.1,.9),2.8)

# Boat demonstration: original boat is instanced unchanged, with six seated passengers.
demo=bpy.data.scenes.new('救援演示 · 六人乘船');bpy.context.window.scene=demo;setup(demo);demo.collection.children.link(studio)
asset=bpy.data.collections.new('FIT · Original boat asset')
for c in sourceboat.collection.children:
 if not c.name.startswith('09_'):asset.children.link(c)
dc=bpy.data.collections.new('FIT · Six passengers aboard');demo.collection.children.link(dc)
ob=bpy.data.objects.new('Original rescue boat · scale 1:1',None);dc.objects.link(ob);ob.instance_type='COLLECTION';ob.instance_collection=asset
for side,x in [('Port',-1.5),('Starboard',1.5)]:
 for i,y in enumerate([-1.85,-.1,1.65],1):
  o=bpy.data.objects.new(f'Passenger {side} {i}',None);dc.objects.link(o);o.instance_type='COLLECTION';o.instance_collection=seated;o.location=(x,y-.10,.735);o['passenger']=True
camera(demo,'PERSON Camera · six aboard',(10,13,10),(0,-.1,2.3),11.4)
# Save separate character library and complete fitting project without overwriting prior boat/base files.
bpy.data.libraries.write(OUT+'/03_Rescue_Person_Rigged_Stand_Sit.blend',{person,seated},fake_user=True,compress=True)
bpy.context.window.scene=demo
for a in bpy.context.screen.areas:
 if a.type=='VIEW_3D':a.spaces.active.clip_start=.001;a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.shading.type='MATERIAL';a.spaces.active.overlay.show_overlays=False
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/03_Rescue_Person_Seat_Fit_Six_Passenger_Demo.blend')
result={'project':bpy.data.filepath,'asset':OUT+'/03_Rescue_Person_Rigged_Stand_Sit.blend','bones':len(rig.data.bones),'standing_height_cm':2.15,'passengers':6,'scenes':[s.name,fit.name,demo.name]}
