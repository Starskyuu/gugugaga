import json, struct
from pathlib import Path

p=Path(r'F:\gugugaga\07enSimulation\RescueSystemModel.glb')
raw=p.read_bytes()
magic,version,total=struct.unpack_from('<4sII',raw,0)
assert magic==b'glTF' and version==2 and total==len(raw)
off=12; doc=None; binary=None
while off<total:
    size,kind=struct.unpack_from('<II',raw,off); payload=raw[off+8:off+8+size]
    if kind==0x4E4F534A: doc=json.loads(payload.decode('utf-8').rstrip('\x00 '))
    if kind==0x004E4942: binary=payload
    off+=8+size
assert doc is not None and binary is not None
assert doc['buffers'][0]['byteLength']==len(binary)
for idx,view in enumerate(doc.get('bufferViews',[])):
    start=view.get('byteOffset',0); end=start+view['byteLength']
    assert 0<=start<=end<=len(binary),(idx,start,end,len(binary))
for idx,acc in enumerate(doc.get('accessors',[])):
    if 'bufferView' in acc: assert 0<=acc['bufferView']<len(doc['bufferViews']),idx
for scene in doc['scenes']:
    for node in scene.get('nodes',[]): assert 0<=node<len(doc['nodes'])
print('VALID GLB 2.0')
print('bytes',len(raw),'nodes',len(doc['nodes']),'meshes',len(doc['meshes']),'materials',len(doc['materials']))
print('scene:',doc['scenes'][doc.get('scene',0)]['name'])
print('root nodes:',[doc['nodes'][i].get('name') for i in doc['scenes'][doc.get('scene',0)]['nodes']])
print('extensions:',doc.get('extensionsUsed',[]))
