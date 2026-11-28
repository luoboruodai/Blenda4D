# Headless test of the Sky object (blenda4d/sky.py):
#   BLENDER_USER_CONFIG=<scratch> Blender -b --factory-startup --python tools/tests/sky_engine.py -- <scratch folder>
# Renders the sky through a panoramic camera (Cycles, tiny) and checks that every page row changes the picture, that
# the dots and the check take the sky out of the render, and that deleting the Sky gives the scene its old World back.
import math
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp"
import blenda4d  # noqa: E402
from blenda4d import kinds, switch  # noqa: E402

switch._register_mode()
from blenda4d import sky  # noqa: E402

fails = []


def check(ok, what):
    print(("PASS " if ok else "FAIL ") + what, flush=True)
    if not ok:
        fails.append(what)


scene = bpy.context.scene
for ob in list(bpy.data.objects):
    bpy.data.objects.remove(ob)
scene.render.engine = "CYCLES"
scene.cycles.samples = 1
scene.cycles.use_denoising = False
scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = 64, 32, 100
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
cam.data.type = "PANO"
cam.data.panorama_type = "EQUIRECTANGULAR"
cam.rotation_euler = (math.pi / 2, 0, 0)
scene.collection.objects.link(cam)
scene.camera = cam
first_world = scene.world


def pixels():
    path = os.path.join(OUT, "sky_test.exr")
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(path, check_existing=False)
    px = list(img.pixels)
    bpy.data.images.remove(img)
    return px


def diff(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def make_hdri():
    img = bpy.data.images.new("TestHDRI", 64, 32, float_buffer=True)
    px = []
    for y in range(32):
        for x in range(64):
            px += [x / 64.0 * 4.0, y / 32.0, 0.3 + 0.5 * ((x // 8) % 2), 1.0]
    img.pixels = px
    img.filepath_raw = os.path.join(OUT, "test_hdri.exr")
    img.file_format = "OPEN_EXR"
    img.save()
    return img


# --- create -------------------------------------------------------------------------------------------------------
check(kinds.kind_of(None) is None and "sky" in kinds.KINDS and "physical_sky" in kinds.KINDS, "kinds registered")
from blenda4d import bars  # noqa: E402
env = [m[0] for m in bars.GROUPS["environment"]]
check(env[:3] == ["Sky", "Physical Sky", "Floor"], f"environment group {env}")
check(all(m[2] == "blenda4d.add_kind" for m in bars.GROUPS["environment"][:3]), "environment buttons wired")
check([e[0] for e in kinds.menu_items("Create")][-3:] == ["Sky", "Physical Sky", "Floor"], "Create menu items")

bpy.ops.blenda4d.add_kind(kind="sky")
ob = bpy.context.view_layer.objects.active
check(sky.is_sky(ob) and kinds.kind_of(ob) == "sky", "Sky object made and active")
check(len(ob.data.vertices) == 0, "Sky has no geometry")
check(scene.world == scene.b4d_sky_world and scene.b4d_sky_prev_world is None, "Sky took over the World (no old World kept, 0.1.5x)")
scene.b4d_sky_intensity = 1.0
outs = [n for n in scene.world.node_tree.nodes if n.type == "OUTPUT_WORLD"]
check(len(outs) == 1 and outs[0].inputs[0].is_linked and len(scene.world.node_tree.nodes) == 2, "the Sky's World: one output, its own nodes only")
bpy.ops.blenda4d.add_kind(kind="sky")
check(sum(sky.is_sky(o) for o in scene.objects) == 1, "one Sky per scene")

base = pixels()
scene.b4d_sky_color = (0.2, 0.4, 0.8)
p = pixels()
check(diff(base, p) > 0.05 and abs(p[0] - 0.2) < 0.02, f"Sky Color shows ({p[0]:.3f})")
base = p
scene.b4d_sky_intensity = 2.0
p = pixels()
check(abs(p[0] - 0.4) < 0.03, f"Intensity scales ({p[0]:.3f})")
scene.b4d_sky_intensity = 1.0

hdri = make_hdri()
base = pixels()
scene.b4d_sky_image = hdri
p_img = pixels()
check(diff(base, p_img) > 0.1, "HDRI shows")
for attr, value in (("b4d_sky_rotation", math.radians(90)), ("b4d_sky_contrast", 60.0), ("b4d_sky_saturation", 20.0)):
    old = getattr(scene, attr)
    setattr(scene, attr, value)
    p = pixels()
    check(diff(p_img, p) > 0.02, f"{attr} changes the picture")
    setattr(scene, attr, old)
check(not any(n.name.startswith("Blenda Grade") or n.name == "Blenda Saturation" for n in scene.world.node_tree.nodes),
      "grade nodes go when at rest")
scene.b4d_sky_hide_camera = True
p = pixels()
check(abs(p[0] - 0.2) < 0.02 and abs(p[2] - 0.8) < 0.03, "Hide from Camera: camera sees the Sky Color")
scene.b4d_sky_hide_camera = False

# --- dots and check -----------------------------------------------------------------------------------------------
ob.hide_render = True
p = pixels()
check(abs(p[0] - sky.GREY[0]) < 0.01, "render dot off: render sees grey")
check(scene.world.node_tree.nodes.get("Blenda Render Grey") is None, "render grey taken out after the render")
ob.hide_render = False
check(diff(pixels(), p_img) < 1e-4, "render dot on again: HDRI back")
ob.b4d_enabled = False
p = pixels()
check(abs(p[0] - sky.GREY[0]) < 0.01, "check off: render sees grey")
sky.sync(scene)
check(scene.get("b4d_sky_views") == 0, "check off: views told to hide the sky")
ob.b4d_enabled = True
sky.sync(scene)
check(scene.get("b4d_sky_views") == 1, "check on: views show the sky")

# --- Physical Sky ---------------------------------------------------------------------------------------------------
bpy.ops.blenda4d.add_kind(kind="physical_sky")
check(sum(sky.is_sky(o) for o in scene.objects) == 1 and scene.b4d_sky_image is None, "Physical Sky reuses the Sky, HDRI gives way")
sun = sky.physical_node(scene)
check(sun is not None and sun.outputs[0].is_linked, "sun-and-atmosphere node drives the sky")
p_sun = pixels()
check(diff(p_sun, p_img) > 0.05, "Physical Sky shows")
tests = (("sun_elevation", math.radians(5)), ("sun_rotation", math.radians(120)), ("sun_size", math.radians(20)),
         ("sun_intensity", 5.0), ("altitude", 20000.0), ("air_density", 8.0), ("aerosol_density", 8.0),
         ("ozone_density", 10.0), ("sun_disc", False))
for attr, value in tests:
    if attr == "sun_intensity":          # the sun's own rows need a sun big enough to land on a 64 x 32 picture
        sun.sun_size = math.radians(20)
        p_sun = pixels()
    old = getattr(sun, attr)
    setattr(sun, attr, value)
    p = pixels()
    check(diff(p_sun, p) > 1e-3, f"{attr} changes the picture ({diff(p_sun, p):.4f})")
    setattr(sun, attr, old)
scene.b4d_sky_intensity = 0.5
check(sun.outputs[0].is_linked and diff(pixels(), p_sun) > 1e-3, "Intensity on a Physical Sky keeps it plugged in")
scene.b4d_sky_hide_camera = True
p = pixels()
check(abs(p[0] - 0.2) < 0.02, "Hide from Camera works on the Physical Sky")
scene.b4d_sky_hide_camera = False
scene.b4d_sky_image = hdri
check(not sun.outputs[0].is_linked, "an HDRI takes over from the Physical Sky")
scene.b4d_sky_image = None
check(sky.physical_node(scene).outputs[0].is_linked, "HDRI cleared: the Physical Sky is back")

# --- delete -------------------------------------------------------------------------------------------------------
sky_world = scene.b4d_sky_world.name
bpy.data.objects.remove(ob)
sky.sync(scene)
check(scene.world != first_world and scene.world.name == "No Sky", "deleting the Sky leaves plain medium grey (0.1.5x)")
check(sky_world not in bpy.data.worlds, "the Sky's World is removed")
check(scene.b4d_sky_image is None and scene.get("b4d_sky_views") == -1, "settings and views back to defaults")
bpy.ops.blenda4d.add_kind(kind="sky")
check(tuple(round(c, 3) for c in scene.b4d_sky_color) == sky.GREY, f"a new Sky starts from the defaults {tuple(scene.b4d_sky_color)} {list(scene.keys())}")
bpy.data.objects.remove(bpy.context.view_layer.objects.active)
sky.sync(scene)

# a World set some other way (a dropped HDRI) while a Sky is there: the Sky takes its picture
bpy.ops.blenda4d.add_kind(kind="sky")
dropped = bpy.data.worlds.new("Dropped")
dropped.use_nodes = True
e = dropped.node_tree.nodes.new("ShaderNodeTexEnvironment")
e.image = hdri
dropped.node_tree.links.new(e.outputs[0], dropped.node_tree.nodes["Background"].inputs["Color"])
scene.world = dropped
sky.sync(scene)
check(scene.world == scene.b4d_sky_world and scene.b4d_sky_image == hdri, "a dropped HDRI World becomes the Sky's HDRI")

# --- Floor --------------------------------------------------------------------------------------------------------
bpy.ops.blenda4d.add_kind(kind="floor")
fl = bpy.context.view_layer.objects.active
check(kinds.kind_of(fl) == "floor" and len(fl.data.polygons) == 1 and abs(fl.dimensions.x - sky.FLOOR_SIZE) < 1e-3,
      f"Floor: one {fl.dimensions.x:.0f} m polygon")

print("SKY TEST", "FAILED: " + "; ".join(fails) if fails else "ALL PASSED", flush=True)
