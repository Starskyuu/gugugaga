"""Run from Blender's Text Editor, or via MCP execute code, after editing Physics_Parameters.json."""
import bpy,json,runpy,os
ROOT='F:/gugugaga/blender/';OUT=ROOT+'PhysicsSimulation/'
with open(OUT+'Physics_Parameters.json',encoding='utf-8') as f:params=json.load(f)
module=runpy.run_path(ROOT+'scripts/04_Model_Scale_Hydrostatics.py')
data,report=module['validate'](params)
if not report['all_passed']:raise RuntimeError('Validation failed; animation was not replaced. '+str(report))
s=bpy.data.scenes['SIM_01_Boat_Calm_Water_Float_Test'];bpy.context.window.scene=s;o=bpy.data.objects['SIM_BOAT_BODY_12g']
# Rebuilding geometry is required if COM changes: vertices are mass-centered.
if max(abs(a-b) for a,b in zip(data['center_of_mass_m'],o['center_of_mass_hull_m']))>1e-9:raise RuntimeError('COM changed. Rebuild the physics setup so collider and visual coordinates remain consistent.')
o.animation_data_clear();o.rigid_body.mass=data['mass_kg'];o['mass_kg']=data['mass_kg']
for f,item in enumerate(data['frames'],1):o.location=item['position_m'];o.rotation_quaternion=item['quaternion_wxyz'];o.keyframe_insert('location',frame=f);o.keyframe_insert('rotation_quaternion',frame=f)
s.frame_end=len(data['frames']);s.render.fps=params['bake_fps'];s.frame_set(s.frame_end)
for name,value in [('Float_Test_Results.json',data),('Physics_Validation_Report.json',report)]:
 with open(OUT+name,'w',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
bpy.ops.wm.save_as_mainfile(filepath=OUT+'04_Model_Scale_Physics_Setup.blend')
result=report
