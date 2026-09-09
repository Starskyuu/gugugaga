import bpy
import json
from mathutils import Vector


required_roots = ["BaseStation", "RaspberryPi", "OverheadCamera", "RescueBoat", "Person"]
errors = []
report = {"roots": {}, "mesh_count": 0, "vertex_count": 0, "face_count": 0}

if len(bpy.data.materials) < 8:
    errors.append(f"Expected game PBR material zones, found only {len(bpy.data.materials)}")
if bpy.data.lights:
    errors.append(f"Expected no lights, found {len(bpy.data.lights)}")

for name in required_roots:
    root = bpy.data.objects.get(name)
    if root is None:
        errors.append(f"Missing root: {name}")
        continue
    children = list(root.children_recursive)
    meshes = [obj for obj in children if obj.type == "MESH"]
    if not meshes:
        errors.append(f"Root has no mesh children: {name}")
    report["roots"][name] = {"child_count": len(children), "mesh_count": len(meshes)}

for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    report["mesh_count"] += 1
    report["vertex_count"] += len(obj.data.vertices)
    report["face_count"] += len(obj.data.polygons)
    if min(obj.dimensions) <= 0.00001:
        errors.append(f"Zero-thickness mesh: {obj.name} dimensions={tuple(obj.dimensions)}")
    if any(abs(value - 1.0) > 0.0001 for value in obj.scale):
        errors.append(f"Scale not applied: {obj.name} scale={tuple(obj.scale)}")
    if obj.data.validate(verbose=False, clean_customdata=False):
        errors.append(f"Invalid mesh data corrected during validation: {obj.name}")

world_points = []
for obj in bpy.data.objects:
    if obj.type == "MESH":
        world_points.extend([obj.matrix_world @ Vector(corner) for corner in obj.bound_box])
minimum = Vector((min(p.x for p in world_points), min(p.y for p in world_points), min(p.z for p in world_points)))
maximum = Vector((max(p.x for p in world_points), max(p.y for p in world_points), max(p.z for p in world_points)))
dimensions = maximum - minimum
report["bounds_min_m"] = [round(value, 4) for value in minimum]
report["bounds_max_m"] = [round(value, 4) for value in maximum]
report["bounds_dimensions_m"] = [round(value, 4) for value in dimensions]
if any(value > 1.2001 for value in dimensions):
    errors.append(f"Overall bounds exceed 1.2 m envelope: {tuple(dimensions)}")

report["errors"] = errors
print("BLOCKOUT_VALIDATION", json.dumps(report, ensure_ascii=False))
if errors:
    raise RuntimeError("; ".join(errors))
