import bpy, math, os, json
from mathutils import Vector
from math import sin, cos, pi

OUT = 'F:/gugugaga/blender/UnmannedRescueBoat_7cm'
os.makedirs(OUT, exist_ok=True)
scene = bpy.data.scenes.new('无人遥控救援船 · 7×5 cm')
bpy.context.window.scene = scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01
scene.unit_settings.length_unit = 'CENTIMETERS'
collections = {}
for name in ['01_Hull','02_Railing','03_Seats','04_Lifebuoys','05_Ropes','06_Propellers','07_Antenna','08_Details','09_Studio']:
    c = bpy.data.collections.new(name); scene.collection.children.link(c); collections[name] = c
group = '01_Hull'
def mat(name, color, metal=0, rough=.35):
    m=bpy.data.materials.new(name); m.diffuse_color=(*color,1); m.use_nodes=True
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'); p.inputs['Base Color'].default_value=(*color,1); p.inputs['Metallic'].default_value=metal; p.inputs['Roughness'].default_value=rough
    return m
yellow=mat('Rescue yellow',(.95,.69,.015)); green=mat('Rescue green',(.08,.36,.035)); dark=mat('Graphite rubber',(.022,.035,.038),0,.6)
silver=mat('Brushed marine aluminum',(.58,.65,.7),.85,.23); rope=mat('Warm braided rescue rope',(.63,.46,.22),0,.85)
seatmat=mat('Seat dark green',(.055,.13,.11),0,.7); beltmat=mat('Black safety webbing',(.009,.012,.014),0,.9); white=mat('Ivory markings',(.86,.92,.81)); red=mat('Buckle release',(.7,.025,.012))
def link(o,name,m):
    o.name=name
    for c in list(o.users_collection): c.objects.unlink(o)
    collections[group].objects.link(o)
    if m: o.data.materials.append(m)
    return o
def mesh(name,v,f,m):
    me=bpy.data.meshes.new(name); me.from_pydata(v,[],f); me.update(); o=bpy.data.objects.new(name,me); collections[group].objects.link(o)
    if m: me.materials.append(m)
    return o
def bevel(o,w=.04):
    b=o.modifiers.new('Soft manufactured edges','BEVEL'); b.width=w; b.segments=3
    return o
def box(name,loc,size,m,w=.035):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=link(bpy.context.object,name,m); o.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if w: bevel(o,w)
    return o
def tube(name,pts,r,m,closed=False):
    cu=bpy.data.curves.new(name,'CURVE'); cu.dimensions='3D'; cu.resolution_u=12; cu.bevel_depth=r; cu.bevel_resolution=3
    sp=cu.splines.new('POLY'); sp.points.add(len(pts)-1)
    for p,co in zip(sp.points,pts): p.co=(*co,1)
    sp.use_cyclic_u=closed; o=bpy.data.objects.new(name,cu); collections[group].objects.link(o); cu.materials.append(m); return o
def rod(name,a,b,r,m):
    a,b=Vector(a),Vector(b); bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=r,depth=(b-a).length,location=(a+b)/2)
    o=link(bpy.context.object,name,m); o.rotation_mode='QUATERNION'; o.rotation_quaternion=(b-a).to_track_quat('Z','Y')
    for p in o.data.polygons:p.use_smooth=True
    bevel(o,min(r*.2,.018)); return o
def torus(name,loc,R,r,m,rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_segments=64,minor_segments=12,major_radius=R,minor_radius=r,location=loc,rotation=rot)
    o=link(bpy.context.object,name,m)
    for p in o.data.polygons:p.use_smooth=True
    return o
outline=[(-2.5,-3.5),(2.5,-3.5),(2.5,1.9),(2.2,2.6),(1.3,3.2),(.45,3.5),(-.45,3.5),(-1.3,3.2),(-2.2,2.6),(-2.5,1.9)]
def hull_layer(name,levels,m):
    verts=[(x*s,y*t,z) for s,t,z in levels for x,y in outline]; n=len(outline); faces=[tuple(reversed(range(n)))]
    for k in range(len(levels)-1):
        for i in range(n):faces.append((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i))
    faces.append(tuple((len(levels)-1)*n+i for i in range(n)))
    return bevel(mesh(name,verts,faces,m),.025)
hull=hull_layer('Hull · 7 cm length × 5 cm beam',[(.78,.9,0),(1,1,.68),(1,1,.9)],green)
hull_layer('Yellow hull band',[(1,1,.9),(1,1,1.12)],yellow)
hull_layer('Green working deck',[(.97,.98,1.12),(.97,.98,1.2)],green)
tube('Continuous rubber rubbing strake',[(x*.994,y*.994,.79) for x,y in outline],.045,dark,True)
for x in [-1.77,-.9,0,.9,1.77]:
    box('Alternating yellow deck stripe',(x,.0,1.209),(.14,5.9,.018),yellow,.009)
group='02_Railing'
railpath=[(x*.93,y*.94) for x,y in outline]
for i,(x,y) in enumerate(railpath):rod('Railing post %02d'%i,(x,y,1.2),(x,y,2.16),.035,silver)
for x in [-2.325,2.325]:
    for y in [-2.2,-.8,.65]:rod('Side railing stanchion',(x,y,1.2),(x,y,2.16),.035,silver)
tube('Top rail · height 1 cm',[(x,y,2.16) for x,y in railpath],.04,silver,True)
tube('Mid rail',[(x,y,1.68) for x,y in railpath],.025,silver,True)
group='03_Seats'
for side,x in [('Port',-1.5),('Starboard',1.5)]:
    for i,y in enumerate([-1.85,-.1,1.65],1):
        prefix=f'{side} Seat {i}'
        root=bpy.data.objects.new(prefix+' Assembly',None); collections[group].objects.link(root); root['seat']=True
        prior=set(collections[group].objects)
        rod(prefix+' pedestal',(x,y,1.2),(x,y,1.48),.13,silver)
        box(prefix+' base',(x,y,1.51),(1.02,.98,.12),silver)
        box(prefix+' cushion',(x,y+.04,1.63),(.92,.88,.16),seatmat,.08)
        box(prefix+' backrest',(x,y-.42,1.98),(.95,.17,.72),seatmat,.07)
        box(prefix+' yellow head pad',(x,y-.405,2.3),(.75,.19,.13),yellow,.045)
        for sx in [-.53,.53]:
            tube(prefix+' arm support',[(x+sx,y-.36,1.55),(x+sx,y-.36,1.98),(x+sx,y+.35,1.98),(x+sx,y+.35,1.55)],.025,silver)
            box(prefix+' padded armrest',(x+sx,y,2.01),(.14,.8,.09),dark,.035)
        # Flat diagonal shoulder webbing and lap belt, each with a visible red release buckle.
        ribbon=[(x-.33,y-.315,2.25),(x-.22,y-.29,2.02),(x+.05,y-.29,1.77),(x+.25,y+.2,1.725)]
        vv=[]
        for xx,yy,zz in ribbon:vv.extend([(xx-.055,yy,zz),(xx+.055,yy,zz)])
        ob=mesh(prefix+' shoulder safety belt',vv,[(0,1,3,2),(2,3,5,4),(4,5,7,6)],beltmat)
        so=ob.modifiers.new('Webbing thickness','SOLIDIFY');so.thickness=.014
        box(prefix+' lap safety belt',(x,y+.2,1.729),(.88,.11,.025),beltmat,.009)
        box(prefix+' buckle',(x+.15,y+.2,1.754),(.17,.14,.04),silver,.02)
        box(prefix+' red release',(x+.15,y+.2,1.778),(.09,.075,.018),red,.01)
        for o in set(collections[group].objects)-prior:o.parent=root
group='04_Lifebuoys'
for side,s in [('Port',-1),('Starboard',1)]:
    for i,y in enumerate([-1.5,1.4],1):
        x=s*2.62; z=1.12
        o=torus(f'{side} yellow lifebuoy {i}',(x,y,z),.43,.125,yellow,(0,pi/2,0));o['lifebuoy']=True
        # Outer grab line and four ties, with visible lashings up to the railing.
        tube(f'{side} buoy {i} grab rope',[(x+s*.06,y+.585*cos(t*2*pi/96),z+.585*sin(t*2*pi/96)) for t in range(96)],.022,rope,True)
        for a in [0,pi/2,pi,3*pi/2]:
            yy=y+.43*cos(a);zz=z+.43*sin(a)
            tube('Buoy binding',[(x+.155*cos(t*2*pi/32),yy+.14*sin(t*2*pi/32)*cos(a),zz+.14*sin(t*2*pi/32)*sin(a)) for t in range(32)],.025,rope,True)
        for dy in [-.22,.22]:
            tube('Buoy tied to rail',[(s*2.325,y+dy,2.18),(x+s*.15,y+dy,1.59),(x+s*.14,y+dy,1.31),(x-s*.13,y+dy,1.37),(s*2.325,y+dy,2.18)],.023,rope)
group='05_Ropes'
tube('Perimeter rescue rope · continuous loop',[(x,y,2.235) for x,y in railpath],.033,rope,True)
for s in [-1,1]:
    for y in [-2.45,.05]:
        pts=[]
        for j in range(241):
            t=j/240*2*pi*3; r=.255+.009*t/(2*pi)
            pts.append((s*(2.39+.014*t/(2*pi)),y+r*cos(t),1.86+r*sin(t)))
        o=tube('Side coiled rescue rope',pts,.021,rope);o['side_rope_coil']=True
        tube('Coil rail fastening',[(s*2.39,y-.05,2.13),(s*2.29,y-.05,2.28),(s*2.29,y+.05,2.28),(s*2.42,y+.05,2.08)],.023,rope)
group='06_Propellers'
for side,x in [('Port',-1.35),('Starboard',1.35)]:
    rod(side+' motor pod',(x,-2.96,.38),(x,-3.65,.38),.19,dark)
    rod(side+' horizontal shaft',(x,-3.45,.38),(x,-3.99,.38),.06,silver)
    torus(side+' propeller safety shroud',(x,-3.83,.38),.47,.05,silver,(pi/2,0,0))
    for a in [0,2*pi/3,4*pi/3]:
        rod(side+' guard strut',(x,-3.79,.38),(x+.46*cos(a),-3.79,.38+.46*sin(a)),.018,silver)
        vv=[]
        for rr,tt,yy in [(0.08,-.25,0),(.25,-.15,.04),(.43,.18,.015),(.43,.55,-.035),(.25,.43,-.04),(.08,.2,0)]:
            vv.append((x+rr*cos(a+tt),-3.88+yy,.38+rr*sin(a+tt)))
        blade=mesh(side+' screw blade',vv,[tuple(range(6))],silver); so=blade.modifiers.new('Blade thickness','SOLIDIFY');so.thickness=.025;bevel(blade,.012)
    ob=rod(side+' propeller hub',(x,-3.84,.38),(x,-4.015,.38),.105,silver);ob['propeller']=True
group='07_Antenna'
rod('Antenna mounting flange',(0,-2.35,1.2),(0,-2.35,1.32),.24,silver)
rod('Antenna metal mast',(0,-2.35,1.32),(0,-2.35,5.2),.065,silver)
for z in [1.6,3,4.65]:rod('Mast collar',(0,-2.35,z),(0,-2.35,z+.08),.085,silver)
center=Vector((0,-2.35,5.38)); normal=Vector((0,.94,.342)).normalized(); u=Vector((1,0,0));v=normal.cross(u)
verts=[]; rings=13; seg=64
for j in range(rings):
    r=.90*j/(rings-1)
    for i in range(seg):
        t=i*2*pi/seg; p=center+u*r*cos(t)+v*r*sin(t)+normal*(.24*(r/.90)**2);verts.append(tuple(p))
faces=[]
for j in range(rings-1):
    for i in range(seg):faces.append((j*seg+i,j*seg+(i+1)%seg,(j+1)*seg+(i+1)%seg,(j+1)*seg+i))
dish=mesh('Metal parabolic dish antenna',verts,faces,silver)
for p in dish.data.polygons:p.use_smooth=True
sol=dish.modifiers.new('Metal dish shell','SOLIDIFY');sol.thickness=.025
rim=[tuple(center+u*.9*cos(t*2*pi/96)+v*.9*sin(t*2*pi/96)+normal*.24) for t in range(96)]
tube('Rolled dish rim',rim,.025,silver,True)
focus=center+normal*.57
for a in [pi/2,pi/2+2*pi/3,pi/2+4*pi/3]:
    rod('Dish feed support',center+u*.79*cos(a)+v*.79*sin(a)+normal*.18,focus,.018,silver)
rod('Dish feed receiver',focus-normal*.06,focus+normal*.09,.065,silver)
# Normalize full antenna assembly to precisely 5 cm above its deck mounting plane.
bpy.context.view_layer.update()
maxz=max((o.matrix_world@Vector(c)).z for o in collections[group].objects for c in o.bound_box)
factor=5/(maxz-1.2)
for o in collections[group].objects:
    o.location.z=1.2+(o.location.z-1.2)*factor
    o.scale.z*=factor
group='08_Details'
box('Sealed unmanned electronics enclosure',(0,-1.75,1.39),(.68,.88,.36),green,.08)
box('Electronics yellow lid',(0,-1.75,1.6),(.7,.9,.08),yellow,.04)
for x in [-.24,.24]:
    for y in [-2.03,-1.47]:rod('Lid screw',(x,y,1.63),(x,y,1.65),.025,silver)
def label(name,text,loc,size,m,rotation=(0,0,0)):
    cu=bpy.data.curves.new(name,'FONT');cu.body=text;cu.align_x='CENTER';cu.size=size;cu.extrude=.001
    o=bpy.data.objects.new(name,cu);collections[group].objects.link(o);o.location=loc;o.rotation_euler=rotation;cu.materials.append(m);return o
label('Bow rescue lettering','RESCUE',(0,2.77,1.226),.29,white)
label('Deck craft number','USV 07',(0,.7,1.226),.22,yellow)
box('Rescue emblem backing',(0,2.27,1.223),(.43,.43,.015),yellow,.04)
box('Rescue cross horizontal',(0,2.27,1.237),(.32,.1,.013),green,.01)
box('Rescue cross vertical',(0,2.27,1.24),(.1,.32,.013),green,.01)
group='09_Studio'
floor=mat('Studio slate',(.055,.083,.10),0,.72)
box('Studio ground',(0,0,-.24),(200,200,.14),floor,.01)
world=bpy.data.worlds.new('Soft studio world');scene.world=world;world.use_nodes=True;bg=next(n for n in world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.25,.3,.35,1);bg.inputs[1].default_value=.45
def light(name,loc,power,size,color):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size;d.color=color;o=bpy.data.objects.new(name,d);collections[group].objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.5))-o.location).to_track_quat('-Z','Y').to_euler()
light('Large softbox',(3,4,12),1700,8,(1,.92,.78));light('Cool fill',(-7,0,7),1200,7,(.68,.82,1));light('Rim softbox',(1,-8,9),2100,6,(1,1,1))
def camera(name,loc,target,ortho):
    d=bpy.data.cameras.new(name);o=bpy.data.objects.new(name,d);collections[group].objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();d.type='ORTHO';d.ortho_scale=ortho;d.clip_start=.01;return o
hero=camera('Camera · bow three quarter',(11,14,11),(0,-.25,2.6),12.3)
rear=camera('Camera · stern hardware',(-10,-14,9),(0,-.3,2.4),12)
top=camera('Camera · deck layout',(0,0,18),(0,0,0),10.5)
scene.camera=hero;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=1400;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX'
scene['Specification']='Hull 7 x 5 cm; antenna 5 cm above deck; railing 1 cm; 6 seats; 4 yellow lifebuoys; 2 horizontal shafts; perimeter rope + 2 coils per side.'
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D':
            a.spaces.active.clip_start=.01;a.spaces.active.clip_end=1000;a.spaces.active.region_3d.view_distance=14;a.spaces.active.region_3d.view_location=(0,0,2.2);a.spaces.active.region_3d.view_rotation=hero.rotation_euler.to_quaternion();a.spaces.active.shading.type='MATERIAL'
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=OUT+'/01_Unmanned_Rescue_Boat_7x5cm.blend')
result={'file':bpy.data.filepath,'scene':scene.name,'objects':len(scene.objects),'hull_cm':list(hull.dimensions),'seats':6,'lifebuoys':4,'propellers':2,'antenna_height_cm':5,'railing_height_cm':1}
