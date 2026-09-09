import bpy
import json
import math
import os
from mathutils import Vector


ROOT_DIR = r"F:\gugugaga\blender"
EXPORT_DIR = os.path.join(ROOT_DIR, "exports")
PREVIEW_DIR = os.path.join(ROOT_DIR, "previews")
BLEND_PATH = os.path.join(ROOT_DIR, "RescueSimulation_Blockout.blend")
MATERIALS = {}


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials,
                       bpy.data.cameras, bpy.data.lights):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def root_object(name, location=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_type = "PLAIN_AXES"
    obj.empty_display_size = 0.04
    obj.location = location
    return obj


def child_empty(name, parent, local_location=(0, 0, 0), rotation=(0, 0, 0)):
    obj = root_object(name)
    obj.parent = parent
    obj.location = local_location
    obj.rotation_euler = rotation
    return obj


def finish_mesh(obj, parent, local_location, bevel=0.0, segments=2):
    obj.name = obj.data.name = obj.name
    obj.parent = parent
    obj.location = local_location
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel > 0:
        modifier = obj.modifiers.new("Structural_Bevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = segments
        modifier.limit_method = "ANGLE"
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    for polygon in obj.data.polygons:
        polygon.use_smooth = False
    obj.select_set(False)
    return obj


def box(name, dimensions, local_location, parent, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    return finish_mesh(obj, parent, local_location, bevel)


def cylinder(name, radius, depth, local_location, parent, vertices=24,
             rotation=(0, 0, 0), bevel=0.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return finish_mesh(obj, parent, local_location, bevel)


def sphere(name, radius, local_location, parent, segments=24, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, radius=radius)
    obj = bpy.context.object
    obj.name = name
    return finish_mesh(obj, parent, local_location, 0.0)


def torus(name, major_radius, minor_radius, local_location, parent,
          rotation=(0, 0, 0), major_segments=32, minor_segments=10):
    bpy.ops.mesh.primitive_torus_add(
        major_radius=major_radius, minor_radius=minor_radius,
        major_segments=major_segments, minor_segments=minor_segments)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = rotation
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return finish_mesh(obj, parent, local_location, 0.0)


def create_material(name, color, metallic=0.0, roughness=0.45):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    principled = mat.node_tree.nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = (*color, 1.0)
        principled.inputs["Metallic"].default_value = metallic
        principled.inputs["Roughness"].default_value = roughness
    MATERIALS[name] = mat
    return mat


def create_game_materials():
    create_material("M_Base_PaintedMetal", (0.075, 0.11, 0.14), 0.55, 0.28)
    create_material("M_Base_Deck", (0.42, 0.47, 0.49), 0.35, 0.42)
    create_material("M_SafetyOrange", (0.95, 0.19, 0.045), 0.15, 0.32)
    create_material("M_Rubber", (0.018, 0.025, 0.030), 0.05, 0.62)
    create_material("M_Glass", (0.035, 0.17, 0.23), 0.15, 0.16)
    create_material("M_BrushedMetal", (0.31, 0.35, 0.38), 0.85, 0.22)
    create_material("M_BoatHull", (0.78, 0.84, 0.86), 0.22, 0.26)
    create_material("M_Suit", (0.035, 0.075, 0.11), 0.05, 0.62)
    create_material("M_Skin", (0.58, 0.31, 0.20), 0.0, 0.58)
    create_material("M_PiBoard", (0.035, 0.30, 0.13), 0.12, 0.42)
    create_material("M_Rope", (0.30, 0.20, 0.10), 0.0, 0.76)


def assign_game_materials():
    for obj in bpy.data.objects:
        if obj.type != "MESH":
            continue
        name = obj.name.lower()
        key = "M_Base_Deck"
        if "person" in name:
            key = "M_SafetyOrange" if "vest" in name else "M_Skin" if any(token in name for token in ("head", "hand")) else "M_Suit"
        elif "raspberrypi_board" in name:
            key = "M_PiBoard"
        elif "raspberrypi" in name:
            key = "M_Rubber" if "enclosure" in name else "M_BrushedMetal"
        elif "camera" in name:
            key = "M_Rope" if "rope" in name else "M_Glass" if "lens" in name else "M_Rubber"
        elif "rescueboat" in name:
            if any(token in name for token in ("windscreen", "window")):
                key = "M_Glass"
            elif any(token in name for token in ("collar", "lifering", "navlight")):
                key = "M_SafetyOrange"
            elif any(token in name for token in ("rail", "mast", "cleat", "engine")):
                key = "M_BrushedMetal"
            elif any(token in name for token in ("seat", "console")):
                key = "M_Rubber"
            else:
                key = "M_BoatHull"
        elif "basestation" in name:
            if any(token in name for token in ("fender", "float")):
                key = "M_Rubber"
            elif any(token in name for token in ("rail", "bollard", "ladder")):
                key = "M_BrushedMetal"
            elif any(token in name for token in ("roof", "stripe")):
                key = "M_SafetyOrange"
            elif any(token in name for token in ("window", "glass")):
                key = "M_Glass"
            elif "cabin" in name:
                key = "M_Base_PaintedMetal"
        obj.data.materials.clear()
        obj.data.materials.append(MATERIALS[key])


def create_hull(parent):
    # Five closed transverse sections give the rescue craft a purposeful,
    # planing-hull silhouette while keeping the blockout lightweight.
    stations = [
        (-0.155, 0.052, 0.040, -0.012),
        (-0.105, 0.068, 0.045, -0.018),
        (0.000, 0.072, 0.048, -0.021),
        (0.105, 0.052, 0.044, -0.014),
        (0.165, 0.010, 0.032, 0.004),
    ]
    verts = []
    for y, half_width, top_z, keel_z in stations:
        verts.extend([
            (-half_width, y, top_z),
            (half_width, y, top_z),
            (-half_width * 0.56, y, keel_z),
            (half_width * 0.56, y, keel_z),
        ])
    faces = []
    for i in range(len(stations) - 1):
        a = i * 4
        b = (i + 1) * 4
        faces.extend([
            (a, b, b + 1, a + 1),            # deck
            (a, a + 2, b + 2, b),            # port side
            (a + 1, b + 1, b + 3, a + 3),    # starboard side
            (a + 2, a + 3, b + 3, b + 2),    # bottom
        ])
    faces.extend([(0, 1, 3, 2), (16, 18, 19, 17)])
    mesh = bpy.data.meshes.new("RescueBoat_Hull_Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new("RescueBoat_Hull", mesh)
    bpy.context.collection.objects.link(obj)
    finish_mesh(obj, parent, (0, 0, 0), bevel=0.004, segments=3)


def create_base_station(location=(0, 0, 0)):
    root = root_object("BaseStation", location)
    box("BaseStation_Platform", (0.62, 0.62, 0.055), (0, 0, 0.0275), root, 0.012)
    box("BaseStation_OperationsCabin", (0.31, 0.23, 0.22), (0, 0.065, 0.165), root, 0.012)
    box("BaseStation_Roof", (0.35, 0.27, 0.028), (0, 0.065, 0.289), root, 0.008)
    box("BaseStation_FrontApron", (0.38, 0.15, 0.035), (0, -0.235, 0.055), root, 0.006)
    for side, x in (("Port", -0.245), ("Starboard", 0.245)):
        box(f"BaseStation_{side}Dock", (0.105, 0.36, 0.035), (x, -0.015, 0.052), root, 0.006)
        box(f"BaseStation_{side}FenderOuter", (0.018, 0.36, 0.075),
            (x + (-0.058 if x < 0 else 0.058), -0.015, 0.075), root, 0.004)
    for x in (-0.285, 0.285):
        for y in (-0.285, 0.285):
            cylinder(f"BaseStation_Float_{x:+.3f}_{y:+.3f}", 0.032, 0.12,
                     (x, y, 0.01), root, 20, rotation=(math.pi / 2, 0, 0), bevel=0.003)
    # Game-readable architectural detail. The overhead camera is intentionally
    # absent: it is a separately suspended world object, not station hardware.
    box("BaseStation_Door", (0.078, 0.012, 0.145), (0, -0.056, 0.155), root, 0.006)
    for index, x in enumerate((-0.092, 0.092), 1):
        box(f"BaseStation_Window_{index}", (0.072, 0.012, 0.078), (x, -0.056, 0.185), root, 0.004)
    for side, x in (("L", -0.305), ("R", 0.305)):
        for y in (-0.22, 0.0, 0.22):
            cylinder(f"BaseStation_RailPost_{side}_{y:+.2f}", 0.006, 0.115,
                     (x, y, 0.125), root, 16, bevel=0.001)
        box(f"BaseStation_RailTop_{side}", (0.012, 0.50, 0.012), (x, 0, 0.182), root, 0.003)
    for index, pos in enumerate(((-0.27, -0.27), (0.27, -0.27), (-0.27, 0.27), (0.27, 0.27)), 1):
        cylinder(f"BaseStation_Bollard_{index}", 0.014, 0.055, (pos[0], pos[1], 0.085), root, 20, bevel=0.002)
    box("BaseStation_RoofVent", (0.095, 0.075, 0.045), (0.09, 0.065, 0.327), root, 0.008)
    box("BaseStation_SafetyStripe", (0.34, 0.014, 0.022), (0, -0.059, 0.075), root, 0.003)
    return root


def create_raspberry_pi(location=(0, 0, 0)):
    root = root_object("RaspberryPi", location)
    box("RaspberryPi_Enclosure", (0.105, 0.075, 0.030), (0, 0, 0), root, 0.006)
    box("RaspberryPi_Board", (0.085, 0.056, 0.004), (0, 0, 0.018), root, 0.002)
    for index, corner in enumerate(((-0.036, -0.022), (0.036, -0.022),
                                    (-0.036, 0.022), (0.036, 0.022)), 1):
        cylinder(f"RaspberryPi_Mount_{index}", 0.003, 0.010,
                 (corner[0], corner[1], 0.018), root, 16)
    box("RaspberryPi_IO_Block", (0.030, 0.060, 0.018), (0.051, 0, 0.006), root, 0.002)
    for index, x in enumerate((-0.020, 0.0, 0.020), 1):
        box(f"RaspberryPi_HeatSink_{index}", (0.012, 0.022, 0.012), (x, 0.004, 0.026), root, 0.001)
    box("RaspberryPi_RibbonConnector", (0.028, 0.012, 0.010), (-0.020, -0.024, 0.024), root, 0.001)
    return root


def create_overhead_camera(location=(0, 0, 0)):
    root = root_object("OverheadCamera", location)
    box("OverheadCamera_Housing", (0.12, 0.09, 0.07), (0, 0, 0), root, 0.012)
    cylinder("OverheadCamera_LensBarrel", 0.027, 0.050, (0, 0, -0.055), root, 32, bevel=0.002)
    cylinder("OverheadCamera_LensGlass_Blockout", 0.022, 0.004, (0, 0, -0.082), root, 32)
    cylinder("OverheadCamera_Shackle", 0.014, 0.020, (0, 0, 0.044), root, 20, bevel=0.002)
    cylinder("OverheadCamera_SuspensionRope", 0.006, 0.052, (0, 0, 0.070), root, 20, bevel=0.001)
    torus("OverheadCamera_RopeEye", 0.014, 0.004, (0, 0, 0.078), root,
          rotation=(math.pi / 2, 0, 0), major_segments=24, minor_segments=8)
    return root


def create_rescue_boat(location=(0, 0, 0)):
    root = root_object("RescueBoat", location)
    create_hull(root)
    box("RescueBoat_DeckInsert", (0.105, 0.175, 0.018), (0, -0.015, 0.050), root, 0.008)
    box("RescueBoat_Cabin", (0.092, 0.082, 0.072), (0, 0.040, 0.095), root, 0.010)
    box("RescueBoat_Windscreen", (0.078, 0.012, 0.046), (0, 0.086, 0.113), root, 0.004)
    box("RescueBoat_ControlConsole", (0.058, 0.040, 0.048), (0, 0.015, 0.086), root, 0.005)
    for index, x in enumerate((-0.034, 0.034), 1):
        box(f"RescueBoat_Seat_{index}", (0.030, 0.042, 0.035), (x, -0.065, 0.080), root, 0.006)
    box("RescueBoat_SternBench", (0.105, 0.030, 0.028), (0, -0.125, 0.070), root, 0.005)
    cylinder("RescueBoat_Engine", 0.028, 0.075, (0, -0.175, 0.025), root, 24,
             rotation=(math.pi / 2, 0, 0), bevel=0.003)
    for side, x in (("Port", -0.073), ("Starboard", 0.073)):
        cylinder(f"RescueBoat_{side}Collar", 0.013, 0.260, (x, -0.010, 0.050), root,
                 20, rotation=(math.pi / 2, 0, 0), bevel=0.002)
    box("RescueBoat_CabinRoof", (0.108, 0.105, 0.014), (0, 0.038, 0.139), root, 0.006)
    for side, x in (("Port", -0.048), ("Starboard", 0.048)):
        box(f"RescueBoat_{side}Window", (0.010, 0.058, 0.038), (x, 0.039, 0.112), root, 0.003)
        box(f"RescueBoat_{side}GrabRail", (0.008, 0.205, 0.008), (x * 1.28, -0.005, 0.092), root, 0.002)
    cylinder("RescueBoat_RadarMast", 0.006, 0.075, (0, 0.025, 0.181), root, 18, bevel=0.001)
    box("RescueBoat_RadarBar", (0.075, 0.014, 0.012), (0, 0.025, 0.220), root, 0.004)
    torus("RescueBoat_LifeRing", 0.024, 0.006, (0, -0.147, 0.105), root,
          rotation=(math.pi / 2, 0, 0), major_segments=28, minor_segments=8)
    for side, x in (("Port", -0.040), ("Starboard", 0.040)):
        cylinder(f"RescueBoat_NavLight_{side}", 0.007, 0.010, (x, 0.078, 0.153), root, 18, bevel=0.001)
    box("RescueBoat_RescueCrate", (0.055, 0.046, 0.033), (-0.034, -0.110, 0.092), root, 0.005)
    return root


def create_person(location=(0, 0, 0)):
    root = root_object("Person", location)
    sphere("Person_Head", 0.018, (0, 0, 0.162), root, 20, 10)
    box("Person_Torso", (0.050, 0.028, 0.070), (0, 0, 0.105), root, 0.009)
    box("Person_LifeVest", (0.056, 0.034, 0.046), (0, -0.004, 0.117), root, 0.007)
    for side, x in (("L", -0.035), ("R", 0.035)):
        arm = child_empty(f"Person_Arm_{side}", root, (x * 0.70, 0, 0.132),
                          (0, math.radians(55 if x < 0 else -55), 0))
        cylinder(f"Person_Arm_{side}_Mesh", 0.009, 0.072, (0, 0, -0.033), arm, 16, bevel=0.001)
        sphere(f"Person_Hand_{side}", 0.011, (0, 0, -0.073), arm, 18, 9)
        cylinder(f"Person_Leg_{side}", 0.010, 0.075, (x * 0.42, 0, 0.043), root, 16,
                 bevel=0.001)
    sphere("Person_Hair", 0.0185, (0, 0.002, 0.168), root, 20, 10)
    box("Person_VestReflectiveBand", (0.060, 0.036, 0.010), (0, -0.005, 0.122), root, 0.003)
    for side, x in (("L", -0.014), ("R", 0.014)):
        box(f"Person_Boot_{side}", (0.024, 0.044, 0.020), (x, -0.006, 0.010), root, 0.005)
    return root


def hierarchy(root):
    result = [root]
    queue = list(root.children)
    while queue:
        obj = queue.pop(0)
        result.append(obj)
        queue.extend(obj.children)
    return result


def export_assembly(root, filename):
    original_location = root.location.copy()
    original_rotation = root.rotation_euler.copy()
    root.location = (0, 0, 0)
    root.rotation_euler = (0, 0, 0)
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    for obj in hierarchy(root):
        obj.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(EXPORT_DIR, filename),
        use_selection=True,
        object_types={"EMPTY", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z",
        axis_up="Y",
        bake_space_transform=False,
        add_leaf_bones=False,
        mesh_smooth_type="FACE",
        use_mesh_modifiers=True,
    )
    root.location = original_location
    root.rotation_euler = original_rotation
    bpy.context.view_layer.update()


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def render_preview():
    scene = bpy.context.scene
    camera_data = bpy.data.cameras.new("PreviewCamera_Data")
    camera = bpy.data.objects.new("PreviewCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (1.12, -1.24, 1.02)
    look_at(camera, (0, 0, 0.27))
    camera_data.lens = 52
    scene.camera = camera
    for engine in ("BLENDER_WORKBENCH_NEXT", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = engine
            break
        except TypeError:
            continue
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.render.resolution_x = 1000
    scene.render.resolution_y = 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.join(PREVIEW_DIR, "RescueSimulation_Blockout.png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    bpy.data.cameras.remove(camera_data)
    scene.camera = None


def main():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    clear_scene()
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.length_unit = "METERS"
    scene.unit_settings.scale_length = 1.0
    create_game_materials()

    base = create_base_station((0, 0.2942, 0))
    pi = create_raspberry_pi((0.105, 0.1992, 0.315))
    # Lens face is approximately 1.000 m above the ground plane.
    camera = create_overhead_camera((0, 0.3942, 1.082))
    boat = create_rescue_boat((0.43, -0.36, 0.045))
    boat.rotation_euler.z = math.radians(-28)
    person = create_person((-0.5308, -0.43, 0))
    assign_game_materials()

    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    export_assembly(base, "BaseStation_Blockout.fbx")
    export_assembly(pi, "RaspberryPi_Blockout.fbx")
    export_assembly(camera, "OverheadCamera_Blockout.fbx")
    export_assembly(boat, "RescueBoat_Blockout.fbx")
    export_assembly(person, "Person_Blockout.fbx")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(EXPORT_DIR, "RescueSimulation_Blockout_All.fbx"),
        use_selection=True,
        object_types={"EMPTY", "MESH"},
        apply_unit_scale=True,
        apply_scale_options="FBX_SCALE_UNITS",
        axis_forward="-Z",
        axis_up="Y",
        add_leaf_bones=False,
        mesh_smooth_type="FACE",
    )
    render_preview()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)

    manifest = {
        "stage": "GameAsset_V2",
        "units": "meters",
        "overall_envelope_m": [1.2, 1.2, 1.2],
        "materials": len(MATERIALS),
        "lights": 0,
        "assemblies": {
            "BaseStation": "BaseStation_Blockout.fbx",
            "RaspberryPi": "RaspberryPi_Blockout.fbx",
            "OverheadCamera": "OverheadCamera_Blockout.fbx",
            "RescueBoat": "RescueBoat_Blockout.fbx",
            "Person": "Person_Blockout.fbx",
        },
        "notes": "Second-stage real-time game asset. PBR material zones, baked bevels and named independent assemblies."
    }
    with open(os.path.join(ROOT_DIR, "blockout_manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
    print("BLOCKOUT_BUILD_COMPLETE", BLEND_PATH)


if __name__ == "__main__":
    main()
