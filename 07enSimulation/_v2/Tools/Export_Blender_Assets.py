"""Run in background Blender. Sources read only; standalone SI FBX assets."""
import bpy, json, runpy, re, math
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path('F:/gugugaga/07enSimulation/_v2');SRC=Path('F:/gugugaga/blender')
OUT=ROOT/'Assets/Rescue/Models';DATA=ROOT/'Assets/Rescue/Data'
OUT.mkdir(parents=True,exist_ok=True);DATA.mkdir(parents=True,exist_ok=True)
materials={};reports={}
def safe(n):return re.sub(r'[^A-Za-z0-9_]', '_',n).strip('_')
def remember_materials(mesh):
 for m in mesh.materials:
  if not m:continue
  color=list(m.diffuse_color);metal=0.;rough=.5
  if m.use_nodes:
   n=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
   if n:color=list(n.inputs['Base Color'].default_value);metal=n.inputs['Metallic'].default_value;rough=n.inputs['Roughness'].default_value
  materials[m.name]={'name':m.name,'color':color,'metallic':metal,'roughness':rough}
def newscene(n):
 s=bpy.data.scenes.new('EXPORT_'+n);bpy.context.window.scene=s;s.unit_settings.system='METRIC';s.unit_settings.scale_length=1;return s
def obj(s,n,mesh=None):
 o=bpy.data.objects.new(n,mesh);s.collection.objects.link(o);return o
def evaluated(o,dg,matrix):
 mesh=bpy.data.meshes.new_from_object(o.evaluated_get(dg));mesh.transform(matrix);remember_materials(mesh);return mesh
def export(s,n):
 bpy.context.window.scene=s;bpy.ops.object.select_all(action='SELECT')
 bpy.ops.export_scene.fbx(filepath=str(OUT/(n+'.fbx')),use_selection=True,global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',object_types={'MESH','EMPTY','ARMATURE'},use_mesh_modifiers=True,add_leaf_bones=False,bake_anim=False,use_custom_props=True)
 reports[n]={'objects':len(s.objects),'units':'meters','file':n+'.fbx'}

bpy.ops.wm.open_mainfile(filepath=str(SRC/'PhysicsSimulation/04_Model_Scale_Physics_Setup.blend'))
source=bpy.data.scenes['SIM_01_Boat_Calm_Water_Float_Test'];bpy.context.window.scene=source;source.frame_set(1);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
body=next(o for o in source.objects if o.name.startswith('SIM_BOAT_BODY'));com=Vector(body['center_of_mass_hull_m']);inverse=body.matrix_world.inverted();cached=[]
for o in source.objects:
 if o.name.startswith('SIM_VIS_'):
  cached.append((o.name,evaluated(o,dg,Matrix.Translation(com)@inverse@o.matrix_world),o.parent.name if o.parent else ''))
s=newscene('RescueBoat');root=obj(s,'RescueBoat');rotors={}
for side,x in [('Port',-.0135),('Starboard',.0135)]:
 rotors[side]=obj(s,'Rotor_'+side);rotors[side].parent=root;rotors[side].location=(x,-.0388,.0038)
for name,mesh,parent in cached:
 o=obj(s,safe(name.removeprefix('SIM_VIS_')),mesh);side=next((side for side in rotors if parent.startswith('SIM_ROTOR_'+side)),None)
 if side:mesh.transform(Matrix.Translation(-rotors[side].location));o.parent=rotors[side]
 else:o.parent=root
for name,loc in [('Axis_Bow',(0,.035,0)),('Axis_Up',(0,0,.03)),('Axis_Starboard',(.025,0,0)),('Hull_Origin',(0,0,0))]:o=obj(s,name);o.parent=root;o.location=loc
export(s,'RescueBoat')

# Wet-dock base already split from all boats in stage 6. It includes real slider pivots.
bpy.ops.wm.open_mainfile(filepath=str(SRC/'PhysicsSimulation/06_Rescue_Mission.blend'))
source=bpy.data.scenes['SIM_06_Rescue_Mission'];bpy.context.window.scene=source;source.frame_set(181);bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();cache=[];leafdata=[]
for c in source.collection.children:
 if c.name.startswith(('MISSION_Base_Wet_Dock','MISSION_Roof_And_Searchlights')):
  for o in c.objects:
   if o.type in {'MESH','CURVE','FONT'} and not o.hide_render:cache.append((safe(o.name),evaluated(o,dg,o.matrix_world)))
 if c.name.startswith('MISSION_Animated_Gates'):
  for leaf in c.objects:
   if leaf.get('motion')!='KINEMATIC':continue
   children=[]
   for o in leaf.children:
    if o.type=='MESH' and not o.hide_render:children.append((safe(o.name),evaluated(o,dg,leaf.matrix_world.inverted()@o.matrix_world)))
   leafdata.append((safe(leaf.name),leaf.matrix_world.copy(),children))
s=newscene('RescueBase');root=obj(s,'RescueBase')
for name,me in cache:o=obj(s,name,me);o.parent=root
for name,world,children in leafdata:
 leaf=obj(s,name);leaf.parent=root;leaf.matrix_world=world
 for name,me in children:o=obj(s,name,me);o.parent=leaf
export(s,'RescueBase')

# Reusable deforming rig retained. Separate standing and seated FBXs simplify
# load testing without importing previously baked ship motion.
bpy.ops.wm.open_mainfile(filepath=str(SRC/'RescuePerson/03_Rescue_Person_Rigged_Stand_Sit.blend'))
pc=next(c for c in bpy.data.collections if c.name=='PERSON · Rigged rescue passenger')
rig=next(o for o in pc.objects if o.type=='ARMATURE')
for name,frame in [('RescuePerson_Standing',1),('RescuePerson_Seated',60)]:
 s=newscene(name);s.collection.children.link(pc);rig.parent=None;s.frame_set(frame);rig.scale=(.01,.01,.01);bpy.context.view_layer.update()
 if frame==60:
  dg=bpy.context.evaluated_depsgraph_get();cache=[(o.name,evaluated(o,dg,o.matrix_world)) for o in pc.objects if o.type=='MESH'];s.collection.children.unlink(pc)
  root=obj(s,name)
  for n,mesh in cache:o=obj(s,safe(n),mesh);o.parent=root
 else:
  # Rigidly weighted source segments become a 17-joint transform skeleton.
  # This avoids armature-axis conversion ambiguity while retaining every joint.
  dg=bpy.context.evaluated_depsgraph_get();cache=[]
  bone_world={pb.name:rig.matrix_world@pb.matrix for pb in rig.pose.bones}
  for key,matrix in list(bone_world.items()):
   loc,rot,scale=matrix.decompose();bone_world[key]=Matrix.Translation(loc)@rot.to_matrix().to_4x4()
  for o in pc.objects:
   if o.type=='MESH':cache.append((o.name,evaluated(o,dg,o.matrix_world),o.vertex_groups[0].name))
  s.collection.children.unlink(pc);root=obj(s,name);joints={}
  for pb in rig.pose.bones:
   joint=obj(s,'Joint_'+safe(pb.name));joint.parent=joints[pb.parent.name] if pb.parent else root;joint.matrix_world=bone_world[pb.name];joints[pb.name]=joint
  for n,mesh,bone in cache:mesh.transform(bone_world[bone].inverted());o=obj(s,safe(n),mesh);o.parent=joints[bone]
 for marker,loc in [('Axis_Bow',(0,.01,0)),('Axis_Up',(0,0,.01)),('Hull_Origin',(0,0,0))]:o=obj(s,marker);o.parent=root;o.location=loc
 export(s,name)

# Runtime samples and mass budget use Unity XYZ = Blender XZY, +Z forward.
H=runpy.run_path(str(SRC/'scripts/04_Model_Scale_Hydrostatics.py'));p=json.loads((SRC/'PhysicsSimulation/Physics_Parameters.json').read_text());pts,weights,cell=H['samples'](12,18,12)
def v(a):return {'x':float(a[0]),'y':float(a[2]),'z':float(a[1])}
payload={'samples':[{'position':v(a),'volume':float(b)} for a,b in zip(pts,weights)],'cellSize':v(cell),'sealedVolume':float(sum(weights)),'massParts':[{'name':a['name'],'mass':a['mass_kg'],'position':v(a['position_m']),'size':v(a['dimensions_m'])} for a in p['mass_budget']]}
(DATA/'BoatHydrostatics.json').write_text(json.dumps(payload,separators=(',',':')),encoding='utf-8')
(DATA/'SourceMaterials.json').write_text(json.dumps({'materials':list(materials.values())},indent=2),encoding='utf-8')
(ROOT/'Reports').mkdir(exist_ok=True)
(ROOT/'Reports/Blender_Export_Report.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
print('EXPORT_COMPLETE',json.dumps(reports))
