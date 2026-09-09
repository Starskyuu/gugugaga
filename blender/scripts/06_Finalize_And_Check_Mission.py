"""Idempotent finish, pose-fit correction and saved Blender geometry checks."""
import bpy,json,math,ast
from pathlib import Path
from mathutils import Vector,Quaternion
ROOT=Path('F:/gugugaga/blender');OUT=ROOT/'PhysicsSimulation'
M=json.loads((OUT/'Rescue_Mission_Parameters.json').read_text(encoding='utf-8'));T=json.loads((OUT/'Rescue_Mission_Results.json').read_text(encoding='utf-8'));stages={x['phase']:x for x in T['stages']}
# Reuse exactly the builder's character-placement definitions.
tree=ast.parse((ROOT/'scripts/06_Build_Rescue_Mission.py').read_text(encoding='utf-8'))
defs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['interpolate_path','passenger_state','curve','visible']]
exec(compile(ast.Module(body=defs,type_ignores=[]),'mission_helpers','exec'))
s=bpy.data.scenes['SIM_06_Rescue_Mission'];bpy.context.window.scene=s
people=next(c for c in s.collection.children if c.name.startswith('MISSION_Two_Rescue_Passengers'));studio=next(c for c in s.collection.children if c.name.startswith('MISSION_Cameras_And_Lighting'))
rigs=sorted([o for o in s.objects if o.type=='ARMATURE'],key=lambda o:o.name)
for o in s.objects:
 if o.name.startswith('HUD_'):o.location.z=-.01
strapmat=bpy.data.materials.get('MISSION_Fitted_Safety_Webbing')
if not strapmat:
 strapmat=bpy.data.materials.new('MISSION_Fitted_Safety_Webbing');strapmat.diffuse_color=(.008,.012,.014,1)
for i,rig in enumerate(rigs):
 for f in sorted(set(range(1,len(T['frames'])+1,4))|{len(T['frames'])}):
  pos,yaw,sit,walk,climb=passenger_state(i,T['frames'][f-1]);rig.location=pos;rig.keyframe_insert('location',frame=f)
 for name,points,radius in [('Lap',[(-.23,.23,1.14),(0,.29,1.10),(.23,.23,1.14)],.018),('Shoulder',[(-.20,.235,1.62),(0,.25,1.4),(.18,.29,1.14)],.014)]:
  n=f'MISSION_P{i+1:02d}_Fitted_{name}_Safety_Belt';belt=bpy.data.objects.get(n)
  if not belt:
   belt=curve(people,n,points,radius,strapmat);belt.parent=rig;belt['model']='Visual fitted restraint; seated kinematic attachment, no flexible-belt dynamics'
  visible(belt,1,False)
  for f in range(1,len(T['frames'])+1,4):
   r=T['frames'][f-1];seat_fraction=passenger_state(i,r)[2];visible(belt,f,seat_fraction>.98)
if not bpy.data.objects.get('MISSION_Shelter_Fill_Light'):
 d=bpy.data.lights.new('MISSION_Shelter_Fill_Light','AREA');d.energy=.18;d.size=.08;o=bpy.data.objects.new(d.name,d);studio.objects.link(o);o.location=(.015,.103,.137);o.rotation_euler=(Vector((.015,.065,.10))-o.location).to_track_quat('-Z','Y').to_euler()
for o in list(rigs)+[o for o in people.objects if 'Fitted_' in o.name]:
 if not o.animation_data:continue
 for layer in o.animation_data.action.layers:
  for strip in layer.strips:
   for bag in strip.channelbags:
    for fc in bag.fcurves:
     for k in fc.keyframe_points:k.interpolation='CONSTANT' if fc.data_path.startswith('hide_') else 'LINEAR'
body=next(o for o in s.objects if o.name.startswith('MISSION_BOAT_SIM_BOAT_BODY'))
checks={'model_hull_70_by_50_mm':abs(body.dimensions.x-.05)<1e-6 and abs(body.dimensions.y-.07)<1e-6,'two_rigged_passengers':len(rigs)==2,'four_original_benches_retained':sum(o.name.startswith('MISSION_BASE_Continuous six person bench frame') for o in s.objects)==4,'four_fitted_belt_pieces':sum('Fitted_' in o.name for o in people.objects)==4}
max_seat_error=0.;max_body_error=0.
for f in range(1,len(T['frames'])+1,60):
 s.frame_set(f);bpy.context.view_layer.update();r=T['frames'][f-1];q=Quaternion(r['quaternion_wxyz']);origin=Vector(r['hull_origin_m']);dry=Vector(T['frames'][0]['center_of_mass_m']);max_body_error=max(max_body_error,(body.location-(origin+q@dry)).length)
 for i,rig in enumerate(rigs):
  if M['passengers'][i]['id'] in r['onboard'] and r['phase']=='RETURN_LOADED':max_seat_error=max(max_seat_error,(rig.location-(origin+q@Vector(M['passengers'][i]['seat_origin_m']))).length)
checks['baked_body_matches_solver_under_1_micron']=max_body_error<1e-6;checks['seated_passengers_follow_boat_under_0_1_mm']=max_seat_error<.0001
s.frame_set(s.frame_end);bpy.context.view_layer.update()
checks['passengers_on_shelter_bench']=all(abs(o.location.z-.08555)<1e-6 and abs(o.location.y-.0635)<1e-6 for o in rigs)
checks['north_gate_closed_after_transfer']=all(abs(abs(o.location.x)-.0185)<1e-6 for o in s.objects if o.name in ['MISSION_SIM_DOOR_1_LEFT','MISSION_SIM_DOOR_1_RIGHT'])
report={'checks':checks,'all_passed':all(checks.values()),'maximum_body_bake_error_m':max_body_error,'maximum_seated_attachment_error_m':max_seat_error,'scope':'Geometry and animation data consistency. Not general mesh intersection or character contact validation.'}
(OUT/'Rescue_Mission_Geometry_Report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['all_passed'],report
for n in ['Rescue_Mission_Parameters.json','Rescue_Mission_Validation_Report.json','Rescue_Mission_Geometry_Report.json','Rescue_Mission_Guide.md']:
 path=OUT/n
 if path.exists():
  tx=bpy.data.texts.get('MISSION_'+n) or bpy.data.texts.new('MISSION_'+n);tx.clear();tx.write(path.read_text(encoding='utf-8'))
for n in ['06_Rescue_Mission_Physics.py','06_Build_Rescue_Mission.py','06_Finalize_And_Check_Mission.py','06_Validate_Rescue_Mission.py']:
 tx=bpy.data.texts.get('MISSION_'+n) or bpy.data.texts.new('MISSION_'+n);tx.clear();tx.write((ROOT/'scripts'/n).read_text(encoding='utf-8'))
s.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'06_Rescue_Mission.blend'))
result={'file':bpy.data.filepath,'geometry':report}
