import json, struct
from pathlib import Path

path = Path(r'F:\gugugaga\07enSimulation\rescueboat.glb')
data = path.read_bytes()
magic, version, length = struct.unpack_from('<4sII', data, 0)
offset = 12
chunks = []
while offset < length:
    size, kind = struct.unpack_from('<II', data, offset)
    payload = data[offset + 8:offset + 8 + size]
    chunks.append((kind, payload))
    offset += 8 + size
doc = json.loads(next(payload for kind, payload in chunks if kind == 0x4E4F534A).decode('utf-8').rstrip('\x00 '))
print('GLB', magic, version, length)
print('scene', doc.get('scene'), 'scenes', doc.get('scenes'))
print('nodes', json.dumps(doc.get('nodes', []), ensure_ascii=False, indent=2))
print('meshes', json.dumps(doc.get('meshes', []), ensure_ascii=False, indent=2))
print('accessors', json.dumps(doc.get('accessors', []), ensure_ascii=False, indent=2))
print('materials', json.dumps(doc.get('materials', []), ensure_ascii=False, indent=2))
