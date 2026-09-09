import bpy, math
from mathutils import Vector
s=bpy.context.scene
for root in bpy.data.collections['B06_Ladders'].objects:
    if not root.get('ladder'):continue
    for o in root.children:
        o.location.x+=3;o.location.y+=1.25
        if o.name.startswith('Upper transfer landing'):
            o.location.y=14.05;o.scale.y=1.7/1.08
    # Protected transfer platform runs from the clear doorway to the outside ladder.
    bpy.ops.mesh.primitive_cube_add(size=1)
    o=bpy.context.object;o.name='Doorway to ladder transfer walkway'
    for c in list(o.users_collection):c.objects.unlink(o)
    bpy.data.collections['B06_Ladders'].objects.link(o)
    o.parent=root;o.location=(6.0,15.25,.93);o.scale=(6.7,1.45,.30);o.data.materials.append(bpy.data.materials['BASE · Ceramic white'])
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    b=o.modifiers.new('Platform rounded edges','BEVEL');b.width=.06;b.segments=3
    bpy.ops.mesh.primitive_cube_add(size=1)
    q=bpy.context.object;q.name='Yellow transfer platform edge'
    for c in list(q.users_collection):c.objects.unlink(q)
    bpy.data.collections['B06_Ladders'].objects.link(q);q.parent=root;q.location=(6,15.99,1.095);q.scale=(6.7,.09,.05);q.data.materials.append(bpy.data.materials['BASE · Safety yellow'])
for root in bpy.data.collections['B05_UpperDeck'].objects:
    if not root.name.startswith('Upper rail sector'):continue
    for o in root.children:
        if o.name.startswith('Perimeter handrail'):
            if o.location.x<4:
                o.location.x=(-11.3+7.75)/2;o.scale.z=(7.75+11.3)/(4.75+11.3)
            else:
                o.location.x=(9.65+11.3)/2;o.scale.z=(11.3-9.65)/(11.3-6.65)
        elif o.name.startswith('Deck rail upright'):
            x=o.location.x
            o.location.x=-11.3+(x+11.3)*(7.75+11.3)/(4.75+11.3) if x<5 else 9.65+(x-6.65)*(11.3-9.65)/(11.3-6.65)
        elif o.name.startswith('Deck direction marker'):o.location.x+=3
for n in ['B09_Roof','B10_Antenna_Searchlights']:bpy.data.collections[n].hide_render=False
s.camera=bpy.data.objects['BASE Camera · exterior']
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath='F:/gugugaga/blender/UnmannedRescueBase/02_Rescue_Base_4Boat_Basic.blend')
result={'refined':'External ladder paths now clear of sliding doors and facade walls.'}
