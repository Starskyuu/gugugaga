import json
import math
import struct
from pathlib import Path

SRC = Path(r'F:\gugugaga\07enSimulation\rescueboat.glb')
OUT = Path(r'F:\gugugaga\07enSimulation\RescueSystemModel.glb')


def read_glb(path):
    raw = path.read_bytes()
    magic, version, total = struct.unpack_from('<4sII', raw, 0)
    if magic != b'glTF' or version != 2:
        raise ValueError('Expected a glTF 2.0 binary file')
    offset = 12
    json_chunk = None
    bin_chunk = b''
    while offset < total:
        size, kind = struct.unpack_from('<II', raw, offset)
        payload = raw[offset + 8:offset + 8 + size]
        if kind == 0x4E4F534A:
            json_chunk = payload
        elif kind == 0x004E4942:
            bin_chunk = payload
        offset += 8 + size
    if json_chunk is None:
        raise ValueError('GLB has no JSON chunk')
    doc = json.loads(json_chunk.decode('utf-8').rstrip('\x00 '))
    return doc, bytearray(bin_chunk)


def vadd(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def vsub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def vmul(a, s): return (a[0] * s, a[1] * s, a[2] * s)
def dot(a, b): return a[0]*b[0] + a[1]*b[1] + a[2]*b[2]
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def norm(a):
    length = math.sqrt(max(dot(a, a), 1e-20))
    return (a[0]/length, a[1]/length, a[2]/length)


class MeshGroup:
    def __init__(self):
        self.p = []
        self.n = []
        self.i = []

    def add_triangles(self, positions, normals, indices):
        base = len(self.p)
        self.p.extend(positions)
        self.n.extend(normals)
        self.i.extend(base + idx for idx in indices)


groups = {name: MeshGroup() for name in ['water', 'concrete', 'steel', 'equipment', 'accent']}


def add_box(group, center, size, yaw=0.0):
    cx, cy, cz = center
    sx, sy, sz = (size[0]/2, size[1]/2, size[2]/2)
    faces = [
        ((1,0,0), [(sx,-sy,-sz),(sx,sy,-sz),(sx,sy,sz),(sx,-sy,sz)]),
        ((-1,0,0), [(-sx,-sy,sz),(-sx,sy,sz),(-sx,sy,-sz),(-sx,-sy,-sz)]),
        ((0,1,0), [(-sx,sy,-sz),(-sx,sy,sz),(sx,sy,sz),(sx,sy,-sz)]),
        ((0,-1,0), [(-sx,-sy,sz),(-sx,-sy,-sz),(sx,-sy,-sz),(sx,-sy,sz)]),
        ((0,0,1), [(sx,-sy,sz),(sx,sy,sz),(-sx,sy,sz),(-sx,-sy,sz)]),
        ((0,0,-1), [(-sx,-sy,-sz),(-sx,sy,-sz),(sx,sy,-sz),(sx,-sy,-sz)]),
    ]
    co, si = math.cos(yaw), math.sin(yaw)
    def rot(v): return (co*v[0] + si*v[2] + cx, v[1] + cy, -si*v[0] + co*v[2] + cz)
    def rotn(v): return (co*v[0] + si*v[2], v[1], -si*v[0] + co*v[2])
    pos, nor, ind = [], [], []
    for normal, corners in faces:
        base = len(pos)
        pos.extend(rot(v) for v in corners)
        nor.extend([rotn(normal)] * 4)
        ind.extend([base,base+1,base+2, base,base+2,base+3])
    groups[group].add_triangles(pos, nor, ind)


def add_cylinder(group, a, b, radius, sides=10):
    axis = vsub(b, a)
    length = math.sqrt(dot(axis, axis))
    if length < 1e-8: return
    w = norm(axis)
    helper = (0,1,0) if abs(w[1]) < 0.9 else (1,0,0)
    u = norm(cross(helper, w))
    v = cross(w, u)
    pos, nor, ind = [], [], []
    for end in (a, b):
        for k in range(sides):
            ang = 2*math.pi*k/sides
            radial = vadd(vmul(u, math.cos(ang)), vmul(v, math.sin(ang)))
            pos.append(vadd(end, vmul(radial, radius)))
            nor.append(radial)
    for k in range(sides):
        q=(k+1)%sides
        ind.extend([k,q,sides+q, k,sides+q,sides+k])
    for end_index, normal in ((0,vmul(w,-1)),(1,w)):
        center_idx=len(pos); center=a if end_index==0 else b
        pos.append(center); nor.append(normal)
        ring=end_index*sides
        for k in range(sides):
            q=(k+1)%sides
            if end_index==0: ind.extend([center_idx,ring+q,ring+k])
            else: ind.extend([center_idx,ring+k,ring+q])
    groups[group].add_triangles(pos,nor,ind)


def add_uv_sphere(group, center, radius, rings=8, sides=12, y_scale=1.0):
    pos,nor,ind=[],[],[]
    for r in range(rings+1):
        phi=math.pi*r/rings
        for k in range(sides):
            theta=2*math.pi*k/sides
            unit=(math.sin(phi)*math.cos(theta), math.cos(phi), math.sin(phi)*math.sin(theta))
            pos.append((center[0]+radius*unit[0],center[1]+radius*y_scale*unit[1],center[2]+radius*unit[2]))
            nor.append(norm((unit[0],unit[1]/max(y_scale,1e-6),unit[2])))
    for r in range(rings):
        for k in range(sides):
            q=(k+1)%sides; a=r*sides+k; b=r*sides+q; c=(r+1)*sides+q; d=(r+1)*sides+k
            ind.extend([a,b,c,a,c,d])
    groups[group].add_triangles(pos,nor,ind)


def add_lattice_tower():
    cx, cz = 4.7, 0.0
    y0, y1 = 0.45, 7.2
    levels = [y0, 2.15, 3.85, 5.55, y1]
    def half_at(y):
        t=(y-y0)/(y1-y0)
        return 0.78*(1-t)+0.28*t
    corners=[(-1,-1),(-1,1),(1,1),(1,-1)]
    points={}
    for li,y in enumerate(levels):
        h=half_at(y)
        for ci,(sx,sz) in enumerate(corners): points[(li,ci)]=(cx+sx*h,y,cz+sz*h)
    for ci in range(4): add_cylinder('steel',points[(0,ci)],points[(len(levels)-1,ci)],0.075,8)
    for li in range(len(levels)):
        for ci in range(4): add_cylinder('steel',points[(li,ci)],points[(li,(ci+1)%4)],0.045,8)
    for li in range(len(levels)-1):
        for ci in range(4):
            # One diagonal per side, alternating direction by level.
            start=points[(li,ci)] if li%2==0 else points[(li,(ci+1)%4)]
            end=points[(li+1,(ci+1)%4)] if li%2==0 else points[(li+1,ci)]
            add_cylinder('steel',start,end,0.035,8)
    add_cylinder('steel',(cx,y1,cz),(cx,9.0,cz),0.11,12)
    add_uv_sphere('equipment',(cx,9.18,cz),0.23,8,14,0.55)
    # Three sector panel antennas around the mast.
    add_box('equipment',(cx+0.34,8.15,cz),(0.10,0.85,0.32),0)
    add_box('equipment',(cx-0.17,8.15,cz+0.30),(0.10,0.85,0.32),2.10)
    add_box('equipment',(cx-0.17,8.15,cz-0.30),(0.10,0.85,0.32),-2.10)
    # A compact camera/sensor head facing the water.
    add_box('accent',(cx-0.55,7.45,cz),(0.42,0.28,0.30),0)
    add_cylinder('steel',(cx-0.82,7.45,cz),(cx-0.55,7.45,cz),0.09,12)


def add_environment():
    # Water and shore are thin solids to remain visible from oblique views.
    add_box('water',(-5.0,-0.12,0.0),(12.0,0.20,14.0))
    add_box('concrete',(4.5,-0.10,0.0),(7.0,0.20,14.0))
    add_box('concrete',(4.7,0.18,0.0),(2.8,0.36,2.8))
    # Anchor plinths below the four tower legs.
    for dx in (-0.78,0.78):
        for dz in (-0.78,0.78): add_box('concrete',(4.7+dx,0.43,dz),(0.42,0.50,0.42))
    # Weatherproof equipment cabinet with a raised curb.
    add_box('concrete',(6.45,0.30,0.0),(1.35,0.18,1.15))
    add_box('equipment',(6.45,1.02,0.0),(0.92,1.25,0.70))
    add_box('accent',(5.96,1.10,0.0),(0.035,0.24,0.22))
    add_lattice_tower()


def align4(blob):
    while len(blob)%4: blob.append(0)


def append_view(doc, binary, payload, target=None):
    align4(binary); offset=len(binary); binary.extend(payload)
    view={'buffer':0,'byteOffset':offset,'byteLength':len(payload)}
    if target: view['target']=target
    doc.setdefault('bufferViews',[]).append(view)
    return len(doc['bufferViews'])-1


def append_accessor(doc, view, component, count, kind, minimum=None, maximum=None):
    acc={'bufferView':view,'byteOffset':0,'componentType':component,'count':count,'type':kind}
    if minimum is not None: acc['min']=minimum
    if maximum is not None: acc['max']=maximum
    doc.setdefault('accessors',[]).append(acc)
    return len(doc['accessors'])-1


def material(name, color, metallic=0.0, roughness=0.8):
    return {'name':name,'pbrMetallicRoughness':{'baseColorFactor':color,'metallicFactor':metallic,'roughnessFactor':roughness}}


def pack_glb(doc, binary, out_path):
    align4(binary)
    doc['buffers'][0]['byteLength']=len(binary)
    raw=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode('utf-8')
    while len(raw)%4: raw+=b' '
    total=12+8+len(raw)+8+len(binary)
    with out_path.open('wb') as f:
        f.write(struct.pack('<4sII',b'glTF',2,total))
        f.write(struct.pack('<II',len(raw),0x4E4F534A)); f.write(raw)
        f.write(struct.pack('<II',len(binary),0x004E4942)); f.write(binary)


def main():
    doc,binary=read_glb(SRC)
    doc.setdefault('asset',{})['generator']='Codex rescue-system model builder; boat mesh retained from rescueboat.glb'
    # Reference boat: scale the SolidWorks-exported geometry to a practical rescue-boat envelope.
    boat_node=doc['nodes'][1]
    boat_node.pop('matrix',None)
    boat_node['name']='RescueBoat_reference'
    boat_node['translation']=[-4.0,0.85,0.0]
    boat_node['scale']=[80.0,80.0,80.0]
    doc['materials'][0]=material('Safety orange boat',[0.92,0.26,0.08,1.0],0.0,0.72)
    # Remove the exported viewpoint; the deliverable is a clean model scene.
    doc['scenes'][0]['nodes']=[1]
    add_environment()
    mat_map={
        'water':len(doc['materials']),
        'concrete':len(doc['materials'])+1,
        'steel':len(doc['materials'])+2,
        'equipment':len(doc['materials'])+3,
        'accent':len(doc['materials'])+4,
    }
    doc['materials'].extend([
        material('Muted water',[0.12,0.38,0.56,1.0],0.0,0.55),
        material('Concrete',[0.58,0.61,0.64,1.0],0.0,0.95),
        material('Structural steel',[0.12,0.15,0.18,1.0],0.72,0.40),
        material('Equipment housing',[0.82,0.84,0.85,1.0],0.22,0.55),
        material('Safety accent',[0.92,0.26,0.08,1.0],0.05,0.60),
    ])
    primitives=[]
    for name,g in groups.items():
        if not g.i: continue
        flatp=[x for v in g.p for x in v]; flatn=[x for v in g.n for x in v]
        pbytes=struct.pack('<%sf'%len(flatp),*flatp); nbytes=struct.pack('<%sf'%len(flatn),*flatn); ibytes=struct.pack('<%sI'%len(g.i),*g.i)
        pv=append_view(doc,binary,pbytes,34962); nv=append_view(doc,binary,nbytes,34962); iv=append_view(doc,binary,ibytes,34963)
        mins=[min(v[k] for v in g.p) for k in range(3)]; maxs=[max(v[k] for v in g.p) for k in range(3)]
        pa=append_accessor(doc,pv,5126,len(g.p),'VEC3',mins,maxs); na=append_accessor(doc,nv,5126,len(g.n),'VEC3'); ia=append_accessor(doc,iv,5125,len(g.i),'SCALAR',[min(g.i)],[max(g.i)])
        primitives.append({'attributes':{'POSITION':pa,'NORMAL':na},'indices':ia,'mode':4,'material':mat_map[name]})
    doc.setdefault('meshes',[]).append({'name':'BaseStation_Shore_Environment','primitives':primitives})
    mesh_idx=len(doc['meshes'])-1
    doc.setdefault('nodes',[]).append({'name':'Physically_based_base_station','mesh':mesh_idx})
    doc['scenes'][0]['nodes'].append(len(doc['nodes'])-1)
    doc['scenes'][0]['name']='Rescue boat and shore base station'
    doc['scene']=0
    pack_glb(doc,binary,OUT)
    print(f'Wrote {OUT} ({OUT.stat().st_size} bytes)')
    print('Generated vertices:',sum(len(g.p) for g in groups.values()))
    print('Generated triangles:',sum(len(g.i)//3 for g in groups.values()))


if __name__=='__main__': main()
