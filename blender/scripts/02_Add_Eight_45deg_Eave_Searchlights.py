import bpy, math
from mathutils import Vector
from math import pi, sin, cos
s=bpy.data.scenes['无人救援基地 · 四向船库与安置甲板'];bpy.context.window.scene=s
c=bpy.data.collections.new('B12_Eave_Searchlights_8');s.collection.children.link(c)
def material(n,color,metal=0,rough=.3,emission=0):
 m=bpy.data.materials.new(n);m.diffuse_color=(*color,1);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
 if emission:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
 return m
dark=material('EAVE · graphite lamp housing',(.025,.041,.05),.55)
silver=material('EAVE · brushed metal reflector',(.64,.73,.80),.9,.18)
yellow=material('EAVE · safety yellow bezel',(.98,.66,.018),.35)
lens=material('EAVE · high output LED lens',(.72,.86,1),.2,.14,3)
def own(o,n,m):
 o.name=n
 for old in list(o.users_collection):old.objects.unlink(o)
 c.objects.link(o);o.data.materials.append(m);return o
def cyl(n,a,b,r,m):
 a,b=Vector(a),Vector(b);bpy.ops.mesh.primitive_cylinder_add(vertices=40,radius=r,depth=(b-a).length,location=(a+b)/2);o=own(bpy.context.object,n,m);o.rotation_mode='QUATERNION';o.rotation_quaternion=(b-a).to_track_quat('Z','Y')
 for f in o.data.polygons:f.use_smooth=True
 mod=o.modifiers.new('Soft lamp edges','BEVEL');mod.width=.022;mod.segments=3;return o
def box(n,p,sz,m,angle):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=own(bpy.context.object,n,m);o.scale=sz;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.rotation_euler.z=angle;b=o.modifiers.new('Rounded bracket','BEVEL');b.width=.025;b.segments=3;return o
records=[]
for k,side in enumerate(['N','W','S','E']):
 a=k*pi/2;out=Vector((-sin(a),cos(a),0));tangent=Vector((cos(a),sin(a),0));direction=(out+Vector((0,0,-1))).normalized()
 for j,x in enumerate([-6.2,6.2],1):
  tag=f'EAVE_{side}_{j}';pivot=tangent*x+out*14.42+Vector((0,0,13.88));mount=tangent*x+out*14.32+Vector((0,0,14.46))
  box(tag+' roof mounting plate',mount,(1.16,.65,.09),silver,a)
  for sign in [-1,1]:
   anchor=mount+tangent*(sign*.49)
   joint=pivot+tangent*(sign*.49)
   cyl(tag+' hanging yoke',anchor,joint,.058,silver)
   cyl(tag+' tilt hinge',joint-tangent*.095,joint+tangent*.095,.13,yellow)
  cyl(tag+' 45 degree lamp body',pivot-direction*.36,pivot+direction*.37,.40,dark)
  for offset in [-.28,-.15,-.02]:
   center=pivot+direction*offset;cyl(tag+' cooling rib',center-direction*.023,center+direction*.023,.433,dark)
  cyl(tag+' yellow lens rim',pivot+direction*.35,pivot+direction*.49,.45,yellow)
  cyl(tag+' silver reflector',pivot+direction*.491,pivot+direction*.519,.392,silver)
  cyl(tag+' glowing optical face',pivot+direction*.520,pivot+direction*.531,.34,lens)
  # Lens and spotlight share the same axis, 45 degrees below the horizontal.
  ld=bpy.data.lights.new(tag+' · POWER SEARCHLIGHT','SPOT');ld.energy=2500;ld.color=(.77,.87,1);ld.spot_size=math.radians(42);ld.spot_blend=.35;ld.shadow_soft_size=.09
  lo=bpy.data.objects.new(ld.name,ld);c.objects.link(lo);lo.location=pivot+direction*.56;lo.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()
  lo['side']=side;lo['downward_angle_degrees']=45.;lo['purpose']='Roof edge outward rescue searchlight';lo['pair_index']=j
  records.append({'name':lo.name,'direction':list(direction),'power':ld.energy})
s['Eave_lighting']='8 additional roof-edge searchlights, two per side, outward/down 45 degrees; original four mast lights retained.'
s.camera=bpy.data.objects['BASE Camera · exterior'];s.frame_set(90)
for col in s.collection.children:col.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath='F:/gugugaga/blender/UnmannedRescueBase/02_Rescue_Base_4Boat_8EaveLights_Latest.blend')
result={'file':bpy.data.filepath,'added_spotlights':len(records),'lights':records}
