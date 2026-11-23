# Headless test of the Render Settings engine (no UI):
#   BLENDER_USER_CONFIG=<scratch> Blender -b --factory-startup --python tools/tests/render_settings_engine.py -- <scratch dir>
import json
import os
import sys

import bpy

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "/tmp"

from blenda4d import render_settings as rs  # noqa: E402

rs.register()
scene = bpy.context.scene
fails = []


def check(ok, what):
    print(("PASS " if ok else "FAIL ") + what, flush=True)
    if not ok:
        fails.append(what)


# 1. the first setting takes over the scene
rs.ensure(scene)
check(len(scene.b4d_rsets) == 1 and scene.b4d_rs_loaded == 0, "first setting made")
first = json.loads(scene.b4d_rsets[0].values)
check(first.get("render.resolution_x") == scene.render.resolution_x, "first setting holds the scene's width")
missing = [f"{k}.{a}" for k, a in rs.TRACK if f"{k}.{a}" not in first]
check(not missing, "every tracked value captured (missing: %s)" % missing)

# 2. every tracked value can be changed and is put back by applying the stored setting
NEW = {"render.engine": "CYCLES", "image.file_format": "JPEG", "image.color_mode": "RGB", "render.filepath": "//out/",
       "display_device.display_device": None, "view.view_transform": "Standard", "view.look": None,
       "cycles.denoiser": None, "cycles.pixel_filter_type": "GAUSSIAN", "cycles.rolling_shutter_type": "TOP",
       "eevee.volumetric_tile_size": "2", "display.render_aa": "32", "display.viewport_aa": "OFF",
       "image.color_depth": None, "rs.override_material": None, "rs.frame_range": "MANUAL"}
changed = {}
for key, val in first.items():
    kind, attr = key.rsplit(".", 1)
    own = rs._owner(scene, kind)
    if key in NEW:
        v = NEW[key]
        if v is None:
            continue
    elif isinstance(val, bool):
        v = not val
    elif isinstance(val, int):
        p = own.bl_rna.properties[attr]
        v = val + 1 if val + 1 <= p.hard_max else val - 1
    elif isinstance(val, float):
        p = own.bl_rna.properties[attr]
        v = round(val + 0.01, 6) if val + 0.01 <= p.hard_max else round(val - 0.01, 6)
    elif isinstance(val, str):
        p = own.bl_rna.properties[attr]
        if p.type == "ENUM":
            others = [i.identifier for i in p.enum_items if i.identifier != val]
            if not others:
                continue
            v = others[0]
        else:
            v = val + "x"
    try:
        setattr(own, attr, v)
    except (TypeError, ValueError) as ex:
        check(False, f"set {key} to {v!r}: {ex}")
        continue
    changed[key] = getattr(own, attr)
check(len(changed) >= len(first) - 8, "changed %d of %d values" % (len(changed), len(first)))

# store the changed scene as setting B (duplicate), go back to A, and check A restored everything
rs.commit(scene)                    # A now = changed values; make B a copy, then put A back to the first values
bpy.ops.blenda4d.rs_duplicate()
check(len(scene.b4d_rsets) == 2 and scene.b4d_rs_loaded == 1, "duplicate made and active")
scene.b4d_rsets[0].values = json.dumps(first)
scene.b4d_rs_index = 0              # pick A in the list: B stores the scene, A's values go on the scene
now = rs.capture(scene)
wrong = [k for k in first if k in now and now[k] != first[k]]
check(not wrong, "picking A put back every value (wrong: %s)" % wrong)
scene.b4d_rs_index = 1
now = rs.capture(scene)
wrong = [k for k in changed if now.get(k) != (round(changed[k], 6) if isinstance(changed[k], float) else changed[k])]
check(not wrong, "picking B put back every changed value (wrong: %s)" % wrong)

# 3. Add makes a default setting, Delete removes the active one, Move reorders
bpy.ops.blenda4d.rs_add()
check(len(scene.b4d_rsets) == 3 and scene.b4d_rs_loaded == 2, "add made a third, active")
check(scene.render.engine == "BLENDER_EEVEE" and scene.render.filepath == "//out/", "added setting: default engine, file path kept")
bpy.ops.blenda4d.rs_move(step=-1)
check(scene.b4d_rs_loaded == 1 and scene.b4d_rsets[1].name.startswith("Render Setting."), "move up")
bpy.ops.blenda4d.rs_remove()
check(len(scene.b4d_rsets) == 2 and scene.b4d_rs_loaded == 0 and scene.b4d_rs_index == 0, "delete: the one above is active %s" % ((len(scene.b4d_rsets), scene.b4d_rs_loaded, scene.b4d_rs_index),))
check(scene.render.engine == first["render.engine"], "after delete the scene shows the active setting")

# 4. save stores the active setting; reload keeps the values (PLAN 3.6)
scene.render.resolution_x = 777
path = os.path.join(OUT, "rs_save.blend")
bpy.ops.wm.save_as_mainfile(filepath=path)
check(json.loads(scene.b4d_rsets[0].values)["render.resolution_x"] == 777, "save stored the scene into the active setting")
bpy.ops.wm.open_mainfile(filepath=path)
scene = bpy.context.scene
check(scene.render.resolution_x == 777 and scene.b4d_rs_loaded == 0, "reopened file keeps the values")
scene.b4d_rs_index = 1
scene.b4d_rs_index = 0
check(scene.render.resolution_x == 777, "switching away and back after reopen does not bring old values back")

# 5. the Output page's fields write the real render values
p = scene.b4d_render
scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
p.lock_ratio = True
p.v_width = 960
check((scene.render.resolution_x, scene.render.resolution_y) == (960, 540), "Lock Ratio keeps the proportions")
p.lock_ratio = False
p.v_preset = "SQ1080"
check((scene.render.resolution_x, scene.render.resolution_y) == (1080, 1080), "preset sets width and height")
check(p.v_preset == "SQ1080", "preset shows the matching entry")
p.v_film_p = "HDTV"
check(scene.render.resolution_y == 608, "film aspect preset changes the height (%d)" % scene.render.resolution_y)
p.dpi = 300
check(abs(scene.render.ppm_factor - 300) < 1e-3, "resolution goes into the image's pixels per inch")
p.size_unit = "IN"
check(abs(p.v_phys_w - 1080 / 300) < 0.01, "print size in inches")
p.size_unit = "PX"
p.v_pix_p = "ANA2"
check(abs(p.v_pix - 2.0) < 0.01, "pixel aspect preset")
p.multipass, p.pass_z = True, True
check(scene.view_layers[0].use_pass_z, "Multi-Pass on renders the ticked passes")
p.multipass = False
check(not scene.view_layers[0].use_pass_z, "Multi-Pass off leaves only the combined image")
mat = bpy.data.materials.new("Clay")
p.override_material, p.material_override = mat, True
check(scene.view_layers[0].material_override == mat, "Material Override sets the view layer's material")
p.material_override = False
check(scene.view_layers[0].material_override is None, "Material Override off clears it")
p.v_from = 3
check(p.frame_range == "MANUAL" and p.frame_from == 3, "typing From switches Frame Range to Manual")

# 6. rendering uses the Frame Range, frame rate and Save; the scene's own range comes back afterwards
import os as _os
outd = _os.path.join(OUT, "frames")
_os.makedirs(outd, exist_ok=True)
for f in _os.listdir(outd):
    _os.remove(_os.path.join(outd, f))
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = 32
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.frame_start, scene.frame_end, scene.frame_current = 1, 20, 7
scene.render.filepath = _os.path.join(outd, "cur_")
p.frame_range = "CURRENT"
bpy.ops.blenda4d.render(animation=True)
files = sorted(_os.listdir(outd))
check(files == ["cur_0007.png"], "Current Frame renders only frame 7 (%s)" % files)
check((scene.frame_start, scene.frame_end) == (1, 20), "scene range put back after the render")
scene.render.filepath = _os.path.join(outd, "man_")
p.frame_range, p.frame_from, p.frame_to, p.frame_step = "MANUAL", 3, 7, 2
p.use_scene_fps, p.fps = False, 12
bpy.ops.blenda4d.render(animation=True)
files = sorted(f for f in _os.listdir(outd) if f.startswith("man_"))
check(files == ["man_0003.png", "man_0005.png", "man_0007.png"], "Manual 3 to 7 step 2 (%s)" % files)
check(scene.render.fps == 24 and scene.frame_step == 1, "frame rate and step put back")
scene.render.filepath = _os.path.join(outd, "still_")
p.save = True
bpy.ops.blenda4d.render(animation=False)
check(any(f.startswith("still_") for f in _os.listdir(outd)), "Save on writes a still render")
scene.render.filepath = _os.path.join(outd, "nosave_")
p.save = False
bpy.ops.blenda4d.render(animation=False)
check(not any(f.startswith("nosave_") for f in _os.listdir(outd)), "Save off writes no still")

print("RESULT", "FAIL %d" % len(fails) if fails else "ALL PASS", flush=True)
rs.unregister()
