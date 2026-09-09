import bpy, math, os
from mathutils import Vector, Matrix
from math import sin, cos, pi

OUT='F:/gugugaga/blender/UnmannedRescueBase'
os.makedirs(OUT,exist_ok=True)
boat_scene=bpy.data.scenes['无人遥控救援船 · 7×5 cm']
boat_asset=bpy.data.collections.new('BASE_ASSET · Original rescue boat')
for c in boat_scene.collection.children:
    if not c.name.startswith('09_'):boat_asset.children.link(c)
s=bpy.data.scenes.new('无人救援基地 · 四向船库与安置甲板');bpy.context.window.scene=s
s.unit_settings.system='METRIC';s.unit_settings.scale_length=.01;s.unit_settings.length_unit='CENTIMETERS'
C={}
for n in ['B01_Structure','B02_DockingBays','B03_AnimatedDoors','B04_FourBoats','B05_UpperDeck','B06_Ladders','B07_Benches_24Seats','B08_SupplyWarehouse','B09_Roof','B10_Antenna_Searchlights','B11_Studio']:
    c=bpy.data.collections.new(n);s.collection.children.link(c);C[n]=c
group='B01_Structure'
def material(name,color,metal=0,rough=.38,emission=0):
    m=bpy.data.materials.new('BASE · '+name);m.diffuse_color=(*color,1);m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    if emission:p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
    return m
white=material('Ceramic white',(.83,.87,.86));yellow=material('Safety yellow',(.98,.66,.018));orange=material('Orange access ladders',(1,.235,.014));dark=material('Graphite seals',(.027,.043,.053),0,.64)
metal=material('Marine aluminum',(.49,.59,.65),.8,.25);floor=material('Non slip floor',(.22,.29,.3),0,.8);seat=material('Bench olive cushions',(.17,.27,.19),0,.7);belt=material('Safety webbing',(.009,.014,.019),0,.9)
red=material('Release buttons',(.82,.025,.017));blue=material('Drinking water',(.045,.24,.39));cream=material('Supply crates',(.62,.53,.33));lens=material('Searchlight lens',(.72,.88,1),.25,.18,2);green=material('Ready indicators',(.04,.8,.25),0,.25,2)
def link(o,n,m):
    o.name=n
    for c in list(o.users_collection):c.objects.unlink(o)
    C[group].objects.link(o)
    if m:o.data.materials.append(m)
    return o
def mesh(n,v,f,m):
    d=bpy.data.meshes.new(n);d.from_pydata(v,[],f);d.update();o=bpy.data.objects.new(n,d);C[group].objects.link(o)
    if m:d.materials.append(m)
    return o
def bevel(o,w=.06):
    mod=o.modifiers.new('Manufactured edge radius','BEVEL');mod.width=w;mod.segments=3;return o
def box(n,loc,size,m,w=.04):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=link(bpy.context.object,n,m);o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if w:bevel(o,w)
    return o
def rod(n,a,b,r,m):
    a,b=Vector(a),Vector(b);bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=(b-a).length,location=(a+b)/2);o=link(bpy.context.object,n,m);o.rotation_mode='QUATERNION';o.rotation_quaternion=(b-a).to_track_quat('Z','Y')
    for p in o.data.polygons:p.use_smooth=True
    return bevel(o,min(.025,r*.2))
def tube(n,pts,r,m,closed=False):
    d=bpy.data.curves.new(n,'CURVE');d.dimensions='3D';d.bevel_depth=r;d.bevel_resolution=3;sp=d.splines.new('POLY');sp.points.add(len(pts)-1)
    for p,co in zip(sp.points,pts):p.co=(*co,1)
    sp.use_cyclic_u=closed;o=bpy.data.objects.new(n,d);C[group].objects.link(o);d.materials.append(m);return o
def rr(half,r):
    pts=[]
    for cx,cy,a in [(half-r,half-r,0),(-half+r,half-r,pi/2),(-half+r,-half+r,pi),(half-r,-half+r,3*pi/2)]:
        for i in range(17):
            t=a+i*pi/32;pts.append((cx+r*cos(t),cy+r*sin(t)))
    return pts
def slab(n,half,r,z,thick,m):
    p=rr(half,r);N=len(p);v=[(x,y,zz) for zz in [z-thick/2,z+thick/2] for x,y in p];f=[tuple(reversed(range(N))),tuple(range(N,2*N))]
    f.extend((i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N));return bevel(mesh(n,v,f,m),.035)
def text(n,body,loc,size,m,rot=(0,0,0)):
    d=bpy.data.curves.new(n,'FONT');d.body=body;d.align_x='CENTER';d.size=size;d.extrude=.003;o=bpy.data.objects.new(n,d);C[group].objects.link(o);o.location=loc;o.rotation_euler=rot;d.materials.append(m);return o
def parent_new(before,root):
    for o in set(C[group].objects)-before:
        if o!=root and o.parent is None:o.parent=root
def root(n,angle=0):
    o=bpy.data.objects.new(n,None);C[group].objects.link(o);o.rotation_euler.z=angle;return o

# Rounded square foundation and corner shell. Four genuine openings remain in the walls.
slab('Rounded square foundation · 28 x 28 cm',14,2.6,.2,.45,dark)
slab('Yellow lower skirt',14.08,2.65,.58,.30,yellow)
slab('Boat bay floor',13.85,2.5,.44,.12,floor)
for k in range(4):
    angle=k*pi/2;before=set(C[group].objects);r=root('Facade '+str(k+1),angle)
    for sign in [-1,1]:
        box('White facade pier',(sign*7.68,13.78,4.1),(7.36,.44,6.6),white)
        box('Yellow lower facade band',(sign*7.68,14.025,1.28),(7.36,.09,.72),yellow)
        box('Upper yellow side stripe',(sign*7.68,14.025,6.9),(7.36,.08,.34),yellow)
        for x in [sign*9.1,sign*10.2]:
            for z in [2.8,3.05,3.3]:box('Service ventilation slot',(x,14.03,z),(.68,.025,.06),dark,.015)
    box('Doorway header',(0,13.78,7.81),(22.8,.46,.58),white)
    box('Dark door threshold',(0,13.98,.61),(7.4,.55,.2),dark)
    for sign in [-1,1]:box('Door frame jamb',(sign*3.86,14,4.12),(.25,.29,7.22),metal)
    box('Door frame header',(0,14.01,7.68),(7.96,.30,.22),metal)
    parent_new(before,r)
for cx in [-11.4,11.4]:
    for cy in [-11.4,11.4]:
        a0=math.atan2(cy,cx)-pi/4;N=21;v=[]
        for z in [.75,8.1]:
            for radius in [2.12,2.6]:
                v.extend((cx+radius*cos(a0+i*pi/2/(N-1)),cy+radius*sin(a0+i*pi/2/(N-1)),z) for i in range(N))
        f=[]
        for i in range(N-1):
            f.extend([(i,i+1,N+i+1,N+i),(2*N+i,3*N+i,3*N+i+1,2*N+i+1),(i,2*N+i,2*N+i+1,i+1),(N+i,N+i+1,3*N+i+1,3*N+i)])
        f.extend([(0,N,3*N,2*N),(N-1,2*N-1,4*N-1,3*N-1)])
        bevel(mesh('Rounded white corner shell',v,f,white),.06)

group='B02_DockingBays'
box('Central structural core',(0,0,4.3),(6.4,6.4,7.4),dark,.18)
for k in range(4):
    a=k*pi/2;before=set(C[group].objects);r=root('Dock '+str(k+1),a)
    for sign in [-1,1]:
        box('Dock dividing wall',(sign*4.04,9,4.1),(.18,9.4,7.1),white)
        box('Dock side walkway',(sign*3.47,9,.86),(.64,9.4,.4),floor)
        box('Yellow berth edge',(sign*3.15,9,1.08),(.08,9.4,.06),yellow,.01)
        for y in [5.7,8.7,11.7]:box('Rubber docking fender',(sign*3.04,y,1.04),(.12,.9,.36),dark)
    box('Berth back wall',(0,4.28,4.1),(8.2,.2,7.1),white)
    box('Berth overhead light',(0,9.4,7.58),(3.8,.35,.06),lens)
    text('Berth floor identifier','BAY 0'+str(k+1),(0,12.9,.515),.4,yellow)
    parent_new(before,r)

group='B03_AnimatedDoors'
controls=[]
for k in range(4):
    a=k*pi/2;r=root('DOOR_'+str(k+1)+' · open control',a);r['open']=1.;r['clear_width_cm']=7.4;r['clear_height_cm']=7.1
    r.id_properties_ui('open').update(min=0,max=1,description='0 closed / 1 fully open. Frames 1-60 opening; 120-180 closing.')
    controls.append(r)
    for sign in [-1,1]:
        leaf=root('Sliding leaf '+str(k+1)+' '+str(sign));leaf.parent=r;leaf.location=(sign*1.85,14.22,4.1)
        before=set(C[group].objects)
        box('Watertight sliding door',(0,0,0),(3.7,.22,7.1),yellow,.09)
        box('White door inset',(0,.125,.3),(3.35,.08,4.7),white,.12)
        for z in [-2.7,2.87]:box('Door reinforcing rib',(0,.16,z),(3.38,.1,.12),dark)
        box('Door seal',(sign*1.8,0,0),(.08,.28,7),dark)
        box('Door number plate',(0,.2,.2),(1.14,.09,1.12),dark,.08)
        text('Door number','0'+str(k+1),(0,.265,-.04),.7,yellow,(pi/2,0,pi))
        rod('Sliding door pull',(-.4,.28,-1.1),(.4,.28,-1.1),.055,metal)
        for o in set(C[group].objects)-before:o.parent=leaf
        fc=leaf.driver_add('location',0);d=fc.driver;d.type='SCRIPTED';v=d.variables.new();v.name='opening';v.type='SINGLE_PROP';v.targets[0].id=r;v.targets[0].data_path='["open"]';d.expression=f'{sign}*(1.85+3.87*opening)'
    for f,val in [(1,0.),(60,1.),(120,1.),(180,0.)]:r['open']=val;r.keyframe_insert(data_path='["open"]',frame=f)
    before=set(C[group].objects)
    rod('Door overhead track',(-7.6,14.2,7.79),(7.6,14.2,7.79),.055,metal)
    box('Door ready indicator',(0,14.17,7.93),(.75,.12,.12),green)
    parent_new(before,r)
s.frame_start=1;s.frame_end=180;s.render.fps=30;s.frame_set(90)
for f,n in [(1,'DOORS CLOSED'),(60,'DOORS OPEN'),(120,'READY / 4 BOATS'),(180,'DOORS CLOSED')]:s.timeline_markers.new(n,frame=f)

group='B04_FourBoats'
for k in range(4):
    a=k*pi/2;o=bpy.data.objects.new('Rescue boat '+str(k+1)+' · original 7 cm asset',None);C[group].objects.link(o);o.instance_type='COLLECTION';o.instance_collection=boat_asset;o.location=(-9.35*sin(a),9.35*cos(a),.66);o.rotation_euler.z=a;o['boat_slot']=k+1

group='B05_UpperDeck'
slab('Upper rescue deck · flat',14,2.6,8.33,.46,white)
slab('Non slip upper deck surface',13.85,2.48,8.585,.05,floor)
tube('Yellow deck edge',[(x,y,8.52) for x,y in rr(14.02,2.6)],.1,yellow,True)
# Rail openings line up with each access ladder (local x=5.7).
for k in range(4):
    before=set(C[group].objects);r=root('Upper rail sector '+str(k+1),k*pi/2)
    for lo,hi in [(-11.3,4.75),(6.65,11.3)]:
        for z in [9.24,9.92]:rod('Perimeter handrail',(lo,13.62,z),(hi,13.62,z),.055,metal)
        n=math.ceil((hi-lo)/1.5)
        for j in range(n+1):
            x=lo+(hi-lo)*j/n;rod('Deck rail upright',(x,13.62,8.61),(x,13.62,9.96),.045,metal)
    for x in [-10.9,10.9]:
        box('Roof support column',(x,11.1,11.62),(.26,.26,6.1),white)
        box('Column yellow foot',(x,11.1,9.03),(.36,.36,.8),yellow)
    text('Deck direction marker','ACCESS 0'+str(k+1),(5.7,12.45,8.62),.27,yellow)
    parent_new(before,r)
for z in [9.24,9.92]:
    for k in range(4):
        a=k*pi/2;cx=11.05*cos(a)-11.05*sin(a);cy=11.05*sin(a)+11.05*cos(a)
        tube('Rounded corner railing',[(cx+2.57*cos(a+t*pi/32),cy+2.57*sin(a+t*pi/32),z) for t in range(17)],.055,metal)

group='B06_Ladders'
for k in range(4):
    before=set(C[group].objects);r=root('Orange access ladder '+str(k+1),k*pi/2);r['ladder']=True
    box('Lower rescue transfer landing',(5.7,14.75,.91),(2.45,3.45,.35),white,.12)
    box('Orange lower landing edge',(5.7,16.46,1.08),(2.45,.12,.12),orange)
    # Inclined marine ladder, from landing z=1.1 to deck z=8.61.
    for x in [4.95,6.45]:
        rod('Orange ladder side stringer',(x,16.1,1.1),(x,13.1,8.61),.075,orange)
        rod('Orange ladder handrail',(x,16.25,2.1),(x,13.25,9.61),.055,orange)
        rod('Handrail lower return',(x,16.1,1.1),(x,16.25,2.1),.055,orange)
        rod('Handrail upper return',(x,13.1,8.61),(x,13.25,9.61),.055,orange)
    for j in range(15):
        t=j/14;y=16.1-3*t;z=1.1+7.51*t
        box('Orange anti slip ladder tread',(5.7,y,z),(1.48,.42,.09),orange,.025)
        box('Black tread grip',(5.7,y,z+.053),(1.23,.22,.022),dark,.006)
    box('Upper transfer landing',(5.7,13.2,8.57),(1.8,1.08,.08),orange,.035)
    parent_new(before,r)

group='B07_Benches_24Seats'
for k in range(4):
    before=set(C[group].objects);r=root('BENCH '+str(k+1)+' · 6 people',k*pi/2);r['bench']=True;r['capacity']=6
    box('Continuous six person bench frame',(0,6.15,9.25),(7.25,1.36,.2),metal,.07)
    for x in [-2.85,0,2.85]:box('Bench floor mounted pedestal',(x,6.15,8.92),(.2,.85,.6),metal)
    box('Continuous bench back frame',(0,5.56,9.98),(7.25,.16,1.45),white,.075)
    box('Yellow bench back crest',(0,5.55,10.66),(7.29,.20,.15),yellow,.04)
    for j in range(6):
        x=(j-2.5)*1.15
        box('Bench '+str(k+1)+' cushion '+str(j+1),(x,6.2,9.43),(1.08,1.16,.2),seat,.095)
        box('Bench back pad',(x,5.7,10.04),(1.07,.20,1.04),seat,.08)
        box('Individual lap safety belt',(x,6.30,9.547),(1.05,.12,.035),belt,.01)
        # Individual flat shoulder belts and release hardware.
        pts=[(x-.34,5.817,10.46),(x-.20,5.84,10.05),(x+.13,5.88,9.6),(x+.25,6.3,9.574)];v=[]
        for xx,yy,zz in pts:v.extend([(xx-.052,yy,zz),(xx+.052,yy,zz)])
        o=mesh('Individual shoulder safety belt',v,[(0,1,3,2),(2,3,5,4),(4,5,7,6)],belt);o.modifiers.new('Webbing thickness','SOLIDIFY').thickness=.012;o['seat_belt']=True
        box('Seat belt buckle',(x+.18,6.30,9.59),(.19,.17,.07),metal,.025)
        box('Red buckle release',(x+.18,6.30,9.634),(.10,.085,.025),red,.01)
    for x in [-3.65,3.65]:
        tube('Bench arm rest frame',[(x,5.63,9.3),(x,5.63,9.98),(x,6.7,9.98),(x,6.7,9.3)],.05,metal)
        box('Bench padded armrest',(x,6.16,10.02),(.19,1.14,.09),dark,.04)
    parent_new(before,r)

group='B08_SupplyWarehouse'
slab('Central supply warehouse plinth',3.25,.3,8.74,.25,white)
box('Warehouse back wall',(0,3.06,10.7),(6.2,.2,3.85),white)
for x in [-3.06,3.06]:box('Warehouse side wall',(x,0,10.7),(.2,6.2,3.85),white)
for x in [-2.05,2.05]:box('Warehouse front jamb',(x,-3.06,10.7),(2.1,.2,3.85),white)
box('Warehouse lintel',(0,-3.06,12.43),(2.05,.23,.38),yellow)
slab('Warehouse yellow top',3.2,.3,12.72,.25,yellow)
# Open supply door parked beside entrance so the stock is visible.
box('Warehouse sliding door · open',(-2.10,-3.22,10.65),(1.95,.12,3.65),white)
rod('Warehouse door handle',(-1.45,-3.33,10.1),(-1.45,-3.33,10.9),.055,metal)
text('Warehouse sign','SURVIVAL SUPPLIES',(0,-3.205,12.18),.33,dark,(pi/2,0,0))
for x in [-2.2,2.2]:
    for z in [9.03,10.21,11.39]:
        box('Supply shelf',(x,.25,z),(1.32,4.7,.12),metal)
        for y in [-1.4,.1,1.6]:
            mm=blue if x<0 else cream
            box('Water canister' if x<0 else 'Emergency ration box',(x,y,z+.4),(.98,1.1,.65),mm,.075)
            box('Supply label',(x,y-.56,z+.42),(.6,.025,.22),white,.012)
            if x<0:rod('Water canister cap',(x,y,z+.72),(x,y,z+.79),.13,dark)
box('First aid crate',(0,1.9,9.18),(1.7,1.15,.8),white,.1)
box('Medical cross H',(0,1.315,9.2),(.7,.03,.17),red)
box('Medical cross V',(0,1.30,9.2),(.17,.03,.65),red)
text('Warehouse roof identifier','SUPPLY HUB',(0,0,12.861),.58,dark)

group='B09_Roof'
slab('Full rounded square rain canopy',14.85,3,14.84,.46,white)
slab('Yellow canopy fascia',14.90,3.05,14.62,.22,yellow)
slab('White canopy crown',14.25,2.5,15.09,.13,white)
for x in [-10.7,10.7]:box('Yellow roof identification band',(x,0,15.18),(1.6,23,.08),yellow,.07)
tube('Continuous rain gutter',[(x,y,15.03) for x,y in rr(14.64,2.9)],.075,metal,True)
for x in [-11.1,11.1]:
    for y in [-11.1,11.1]:rod('Roof rainwater downpipe',(x,y,14.56),(x,y,8.65),.055,metal)
text('Roof title','RESCUE / 04',(0,6.4,15.17),1.1,dark)
text('Roof subtitle','AUTONOMOUS SHELTER',(0,4.5,15.17),.5,dark)
box('Roof rescue cross H',(0,-6.6,15.19),(3.4,1.1,.05),yellow,.1)
box('Roof rescue cross V',(0,-6.6,15.22),(1.1,3.4,.05),yellow,.1)

group='B10_Antenna_Searchlights'
rod('Antenna pedestal',(0,0,15.16),(0,0,15.7),.68,white)
rod('Central antenna mast',(0,0,15.6),(0,0,20.4),.13,metal)
rod('Antenna top whip',(0,0,20.3),(0,0,22.2),.04,metal)
rod('Antenna cross element',(-.95,0,20.0),(.95,0,20.0),.04,metal)
rod('Antenna second cross element',(0,-.72,20.65),(0,.72,20.65),.035,metal)
rod('Searchlight ring mount',(0,0,16.05),(0,0,16.4),.4,metal)
for k in range(4):
    a=k*pi/2;direction=Vector((-sin(a),cos(a),-.12)).normalized();p=Vector((-1.2*sin(a),1.2*cos(a),16.48))
    rod('Searchlight support',(0,0,16.28),p,.075,metal)
    ob=rod('SEARCHLIGHT '+str(k+1)+' housing',p-direction*.36,p+direction*.36,.36,dark);ob['searchlight']=True
    rod('Searchlight white bezel',p+direction*.32,p+direction*.43,.385,white)
    rod('Searchlight optical lens',p+direction*.433,p+direction*.447,.305,lens)
    d=bpy.data.lights.new('Directional search beam '+str(k+1),'SPOT');d.energy=80;d.color=(.76,.86,1);d.spot_size=math.radians(48);d.spot_blend=.4
    o=bpy.data.objects.new(d.name,d);C[group].objects.link(o);o.location=p+direction*.46;o.rotation_euler=direction.to_track_quat('-Z','Y').to_euler()

group='B11_Studio'
studio=material('Studio backdrop',(.045,.075,.09),0,.8);box('Studio floor',(0,0,-.35),(400,400,.3),studio)
w=bpy.data.worlds.new('BASE · soft studio world');s.world=w;w.use_nodes=True;n=next(n for n in w.node_tree.nodes if n.type=='BACKGROUND');n.inputs[0].default_value=(.3,.37,.45,1);n.inputs[1].default_value=.45
def area(n,loc,power,size,col):
    d=bpy.data.lights.new(n,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=col;o=bpy.data.objects.new(n,d);C[group].objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,7))-o.location).to_track_quat('-Z','Y').to_euler()
area('BASE key',(10,-20,45),24000,25,(1,.92,.76));area('BASE fill',(-32,-8,24),18000,22,(.66,.82,1));area('BASE rim',(4,28,32),26000,18,(1,1,1));area('BASE front fill',(5,-35,13),7500,15,(1,1,1))
def cam(n,loc,target,scale):
    d=bpy.data.cameras.new(n);o=bpy.data.objects.new(n,d);C[group].objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=scale;d.clip_start=.01;return o
hero=cam('BASE Camera · exterior',(43,-54,32),(0,0,9.5),49)
deckcam=cam('BASE Camera · roof off deck',(34,-42,51),(0,0,6.7),46)
baycam=cam('BASE Camera · four berth plan',(0,0,65),(0,0,0),40)
s.camera=hero;s.render.engine='CYCLES';s.cycles.samples=48;s.cycles.use_denoising=True;s.render.resolution_x=1500;s.render.resolution_y=1300;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.view_settings.view_transform='AgX'
s['Dimensions']='28 x 28 cm rounded-square body; 29.8 cm canopy; 7.4 x 7.1 cm clear gates; 4 original boats at 1:1 scale.'
s['Operation']='Frames 1 / 180 closed, frames 60-120 open. Four DOOR controls each have an animated open custom property.'
s['Capacity']='4 benches x 6 belted seating positions = 24; 4 orange access ladders; central stocked survival warehouse; 4 directional searchlights.'
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        a.spaces.active.clip_start=.01;a.spaces.active.clip_end=1000;a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.overlay.show_overlays=False;a.spaces.active.shading.type='MATERIAL'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/02_Rescue_Base_4Boat_Basic.blend')
result={'file':bpy.data.filepath,'scene':s.name,'objects':len(s.objects),'boats':4,'benches':4,'belted_seats':24,'ladders':4,'searchlights':4,'door_clear_cm':[7.4,7.1]}
