# SPDX-License-Identifier: GPL-3.0-or-later
"""Render Settings: a floating window drawn with Blender's own lists, fields and menus.

Left: the Renderer dropdown, the list of sections (Output, Save, Multi-Pass, Anti-Aliasing, Options, Material
Override, and the renderer's own sections), then the scene's saved render settings and a "Render Setting..." menu.
Right: the page of the section picked in the list, with its title on top.

A scene keeps any number of named render settings; one is active and the scene shows its values. Picking another
setting stores what the scene shows into the one that was active, then puts the picked one's values on the scene.
Saving the file stores the active one first, so reopening and switching never writes old values back.

Frame Range, Frame Rate and Save act when rendering through blenda4d.render (Render menu): the scene's frame range
and rate are set for the render and put back when it ends or is cancelled.

Opened from the viewport's "Render Settings" tab and Render > Render Settings...; the window is a Properties editor
on its Tool tab with the RENDER role (see roles.py)."""
import json

import bpy

from . import roles

ROLE = "RENDER"
DEFAULT_NAME = "Render Setting"

# --- tables ------------------------------------------------------------------------------------------------------
PRESETS = (("CUSTOM", "Custom", 0, 0), ("HD720", "1280 x 720 (HD)", 1280, 720), ("HD1080", "1920 x 1080 (Full HD)", 1920, 1080),
           ("UHD", "3840 x 2160 (4K UHD)", 3840, 2160), ("DCI2K", "2048 x 1080 (2K)", 2048, 1080),
           ("DCI4K", "4096 x 2160 (4K)", 4096, 2160), ("SQ1080", "1080 x 1080 (Square)", 1080, 1080),
           ("VERT1080", "1080 x 1920 (Vertical)", 1080, 1920), ("SOCIAL", "1080 x 1350 (Portrait 4:5)", 1080, 1350),
           ("VGA", "640 x 480", 640, 480), ("SD", "720 x 576 (SD)", 720, 576))
SIZE_UNITS = (("PX", "Pixels", "Width and height in pixels"), ("CM", "cm", "As a print size in centimetres"),
              ("MM", "mm", "As a print size in millimetres"), ("IN", "Inches", "As a print size in inches"),
              ("PT", "Points", "As a print size in points (72 to the inch)"),
              ("PC", "Picas", "As a print size in picas (6 to the inch)"))
PER_INCH = {"CM": 2.54, "MM": 25.4, "IN": 1.0, "PT": 72.0, "PC": 6.0}
DPI_UNITS = (("IN", "Pixels/Inch (DPI)", "Resolution in pixels per inch"), ("CM", "Pixels/cm", "Resolution in pixels per centimetre"))
FILM = (("CUSTOM", "Custom", 0.0), ("SQUARE", "Square (1:1)", 1.0), ("STD", "Standard (4:3)", 4 / 3),
        ("HDTV", "HDTV (16:9)", 16 / 9), ("PHOTO", "Photo (3:2)", 1.5), ("PORTRAIT", "Portrait (4:5)", 0.8),
        ("VERT", "Vertical (9:16)", 9 / 16), ("WIDE", "Widescreen (1.85:1)", 1.85), ("SCOPE", "Scope (2.39:1)", 2.39))
PIXEL = (("CUSTOM", "Custom", 0.0), ("SQUARE", "Square", 1.0), ("ANA133", "Anamorphic (1.333)", 4 / 3),
         ("ANA2", "Anamorphic (2.0)", 2.0))
FRAME_RANGES = (("MANUAL", "Manual", "Render the frames from From to To"),
                ("CURRENT", "Current Frame", "Render only the frame the timeline is on"),
                ("ALL", "All Frames", "Render the scene's whole frame range"),
                ("PREVIEW", "Preview Range", "Render the timeline's preview range"))
PASSES = (("pass_z", "use_pass_z", "Depth"), ("pass_mist", "use_pass_mist", "Mist"), ("pass_normal", "use_pass_normal", "Normal"),
          ("pass_ao", "use_pass_ambient_occlusion", "Ambient Occlusion"), ("pass_diffuse", "use_pass_diffuse_color", "Diffuse Color"),
          ("pass_glossy", "use_pass_glossy_color", "Glossy Color"), ("pass_emit", "use_pass_emit", "Emission"),
          ("pass_env", "use_pass_environment", "Environment"), ("pass_object", "use_pass_object_index", "Object Index"),
          ("pass_material", "use_pass_material_index", "Material Index"))
# (key, title, switch) of every section; switch = (owner kind, attribute) of the checkbox beside its list row
PAGES = (("OUTPUT", "Output", None), ("SAVE", "Save", ("rs", "save")), ("MULTIPASS", "Multi-Pass", ("rs", "multipass")),
         ("AA", "Anti-Aliasing", None), ("OPTIONS", "Options", None), ("OVERRIDE", "Material Override", ("rs", "material_override")),
         ("ENGINE", "Renderer", None))
# the last page is the renderer's own, listed under its name
ENGINE_NAMES = {"BLENDER_EEVEE": "EEVEE", "BLENDER_EEVEE_NEXT": "EEVEE", "CYCLES": "Cycles", "BLENDER_WORKBENCH": "Workbench"}

# What a render setting stores: (owner, attribute). Owners are resolved by _owner().
TRACK = (
    ("render", "engine"),
    ("render", "resolution_x"), ("render", "resolution_y"), ("render", "resolution_percentage"),
    ("render", "pixel_aspect_x"), ("render", "pixel_aspect_y"), ("render", "fps"), ("render", "fps_base"),
    ("render", "use_border"), ("render", "use_crop_to_border"), ("render", "border_min_x"), ("render", "border_max_x"),
    ("render", "border_min_y"), ("render", "border_max_y"),
    ("rs", "lock_ratio"), ("rs", "dpi"), ("rs", "dpi_unit"), ("rs", "size_unit"), ("rs", "use_scene_fps"), ("rs", "fps"),
    ("rs", "frame_range"), ("rs", "frame_from"), ("rs", "frame_to"), ("rs", "frame_step"), ("rs", "annotations"),
    ("rs", "save"),
    ("render", "filepath"), ("render", "use_file_extension"), ("render", "use_overwrite"), ("render", "use_placeholder"),
    ("image", "file_format"), ("image", "color_mode"), ("image", "color_depth"), ("image", "quality"),
    ("image", "compression"), ("render", "film_transparent"),
    ("rs", "multipass"), *(("rs", p[0]) for p in PASSES),
    ("rs", "material_override"), ("rs", "override_material"),
    ("eevee", "taa_render_samples"), ("eevee", "taa_samples"), ("render", "filter_size"),
    ("cycles", "samples"), ("cycles", "preview_samples"), ("cycles", "use_adaptive_sampling"),
    ("cycles", "adaptive_threshold"), ("cycles", "adaptive_min_samples"), ("cycles", "time_limit"),
    ("cycles", "use_denoising"), ("cycles", "denoiser"), ("cycles", "use_preview_denoising"),
    ("cycles", "pixel_filter_type"), ("cycles", "filter_width"),
    ("display", "render_aa"), ("display", "viewport_aa"),
    ("render", "use_simplify"), ("render", "simplify_subdivision_render"), ("render", "simplify_child_particles_render"),
    ("render", "threads_mode"), ("render", "threads"), ("render", "use_persistent_data"), ("render", "dither_intensity"),
    ("render", "use_compositing"),
    ("render", "use_motion_blur"), ("render", "motion_blur_position"), ("render", "motion_blur_shutter"),
    ("cycles", "rolling_shutter_type"), ("cycles", "rolling_shutter_duration"),
    ("eevee", "motion_blur_steps"), ("eevee", "motion_blur_max"), ("eevee", "motion_blur_depth_scale"),
    ("display_device", "display_device"), ("view", "view_transform"), ("view", "look"), ("view", "exposure"),
    ("view", "gamma"),
    ("cycles", "max_bounces"), ("cycles", "diffuse_bounces"), ("cycles", "glossy_bounces"),
    ("cycles", "transmission_bounces"), ("cycles", "volume_bounces"), ("cycles", "transparent_max_bounces"),
    ("cycles", "sample_clamp_direct"), ("cycles", "sample_clamp_indirect"), ("cycles", "blur_glossy"),
    ("cycles", "caustics_reflective"), ("cycles", "caustics_refractive"),
    ("eevee", "volumetric_tile_size"), ("eevee", "volumetric_samples"), ("eevee", "volumetric_sample_distribution"),
    ("eevee", "volumetric_start"), ("eevee", "volumetric_end"), ("eevee", "use_volumetric_shadows"),
    ("eevee", "volumetric_shadow_samples"),
    ("cycles", "device"), ("cycles", "preview_adaptive_threshold"), ("cycles", "use_fast_gi"),
    ("cycles", "preview_dicing_rate"), ("cycles", "dicing_rate"), ("cycles", "max_subdivisions"),
    ("cycles", "film_exposure"), ("cycles", "film_transparent_glass"), ("cycles", "tile_size"),
    ("cycles", "texture_limit_render"), ("render", "preview_pixel_size"),
    ("eevee", "use_shadows"), ("eevee", "shadow_ray_count"), ("eevee", "shadow_step_count"),
    ("eevee", "use_raytracing"), ("eevee", "use_fast_gi"),
    ("display.shading", "light"), ("display.shading", "color_type"), ("display.shading", "show_backface_culling"),
    ("display.shading", "show_xray"), ("display.shading", "show_shadows"), ("display.shading", "show_cavity"),
    ("display.shading", "show_object_outline"), ("display.shading", "show_specular_highlight"),
    # the renderer's Advanced settings
    ("cycles", "use_preview_adaptive_sampling"), ("cycles", "preview_adaptive_min_samples"),
    ("cycles", "preview_denoiser"), ("cycles", "preview_denoising_input_passes"),
    ("cycles", "preview_denoising_prefilter"), ("cycles", "preview_denoising_quality"),
    ("cycles", "preview_denoising_start_sample"), ("cycles", "preview_denoising_use_gpu"),
    ("cycles", "denoising_input_passes"), ("cycles", "denoising_prefilter"), ("cycles", "denoising_quality"),
    ("cycles", "denoising_use_gpu"), ("cycles", "use_guiding"), ("cycles", "guiding_training_samples"),
    ("cycles", "use_surface_guiding"), ("cycles", "use_volume_guiding"), ("cycles", "use_light_tree"),
    ("cycles", "light_sampling_threshold"), ("cycles", "sampling_pattern"), ("cycles", "seed"),
    ("cycles", "use_animated_seed"), ("cycles", "scrambling_distance"), ("cycles", "auto_scrambling_distance"),
    ("cycles", "preview_scrambling_distance"), ("cycles", "min_light_bounces"), ("cycles", "min_transparent_bounces"),
    ("cycles", "use_layer_samples"), ("cycles", "use_pixel_jitter"), ("cycles", "use_sample_subset"),
    ("cycles", "sample_offset"), ("cycles", "sample_subset_length"), ("cycles", "fast_gi_method"),
    ("cycles", "ao_bounces"), ("cycles", "ao_bounces_render"), ("cycles", "offscreen_dicing_scale"),
    ("cycles", "volume_step_rate"), ("cycles", "volume_preview_step_rate"), ("cycles", "volume_max_steps"),
    ("cycles", "volume_biased"), ("cycles", "film_transparent_roughness"), ("cycles", "texture_limit"),
    ("cycles", "use_camera_cull"), ("cycles", "use_distance_cull"), ("cycles", "camera_cull_margin"),
    ("cycles", "distance_cull_margin"), ("cycles", "debug_use_spatial_splits"), ("cycles", "debug_use_hair_bvh"),
    ("cycles", "debug_use_compact_bvh"), ("cycles", "debug_bvh_time_steps"), ("render", "simplify_subdivision"),
    ("render", "simplify_child_particles"), ("render", "simplify_volumes"), ("render", "use_simplify_normals"),
    ("cycles_curves", "shape"), ("cycles_curves", "subdivisions"),
)
# set before the rest: which values are allowed later depends on these
FIRST = (("render", "engine"), ("display_device", "display_device"), ("view", "view_transform"),
         ("image", "file_format"), ("image", "color_mode"), ("image", "color_depth"))
# a new setting keeps the scene's own values for these (a new setting must not send renders somewhere else, and
# Blender's built-in defaults for colour management do not match what a new file uses)
KEEP_ON_NEW = {"render.filepath", "display_device.display_device", "view.view_transform", "view.look"}
# a new setting starts from these where Blender's own default is not the usual starting point
NEW_VALUES = {"render.resolution_x": 1280, "render.resolution_y": 720}


def _owner(scene, kind):
    if kind == "render":
        return scene.render
    if kind == "image":
        return scene.render.image_settings
    if kind == "view":
        return scene.view_settings
    if kind == "display_device":
        return scene.display_settings
    if kind == "display":
        return scene.display
    if kind == "rs":
        return scene.b4d_render
    if kind == "display.shading":
        return scene.display.shading
    return getattr(scene, kind, None)          # "cycles" only exists while the Cycles add-on is on


def capture(scene):
    """The scene's current render values, as plain JSON-ready values."""
    out = {}
    for kind, attr in TRACK:
        own = _owner(scene, kind)
        if own is None or not hasattr(own, attr):
            continue
        v = getattr(own, attr)
        if isinstance(v, bpy.types.ID):
            v = v.name
        elif v is None:
            v = ""
        out[f"{kind}.{attr}"] = round(v, 6) if isinstance(v, float) else v
    return out


def apply_values(scene, values):
    """Put stored values on the scene; a value the scene no longer accepts is skipped."""
    first = [f"{k}.{a}" for k, a in FIRST]
    for key in first + [k for k in values if k not in first]:
        if key not in values:
            continue
        kind, attr = key.rsplit(".", 1)
        own = _owner(scene, kind)
        if own is None or not hasattr(own, attr):
            continue
        v = values[key]
        if key == "rs.override_material":
            v = bpy.data.materials.get(v) if v else None
        try:
            if getattr(own, attr) != v:
                setattr(own, attr, v)
        except (TypeError, ValueError, AttributeError):
            pass


def defaults(scene):
    """Blender's built-in default for every tracked value (used by New)."""
    out = {}
    for kind, attr in TRACK:
        own = _owner(scene, kind)
        key = f"{kind}.{attr}"
        if own is None or not hasattr(own, attr):
            continue
        if key in KEEP_ON_NEW:
            out[key] = getattr(own, attr)
            continue
        if key in NEW_VALUES:
            out[key] = NEW_VALUES[key]
            continue
        prop = own.bl_rna.properties[attr]
        if prop.type == "POINTER":
            out[key] = ""
            continue
        d = getattr(prop, "default", None)
        if prop.type == "ENUM" and d not in {i.identifier for i in prop.enum_items}:
            d = getattr(own, attr)
        out[key] = d if d is not None else getattr(own, attr)
    return out


# --- values the Output page shows (they read and write the real render data) -------------------------------------
def _sc(p):
    return p.id_data


def _ratio(rd):
    return rd.resolution_x / max(1, rd.resolution_y)


def _w_set(self, v):
    rd = _sc(self).render
    r = _ratio(rd)
    rd.resolution_x = max(4, v)
    if self.lock_ratio:
        rd.resolution_y = max(4, round(rd.resolution_x / r))


def _h_set(self, v):
    rd = _sc(self).render
    r = _ratio(rd)
    rd.resolution_y = max(4, v)
    if self.lock_ratio:
        rd.resolution_x = max(4, round(rd.resolution_y * r))


def _per_unit(self):
    return self.dpi / PER_INCH[self.size_unit] if self.size_unit != "PX" else 1.0


def _preset_get(self):
    rd = _sc(self).render
    return next((i for i, row in enumerate(PRESETS) if i and (row[2], row[3]) == (rd.resolution_x, rd.resolution_y)), 0)


def _preset_set(self, i):
    if i:
        rd = _sc(self).render
        rd.resolution_x, rd.resolution_y = PRESETS[i][2], PRESETS[i][3]


def _table_get(table, value):
    return next((i for i, row in enumerate(table) if i and abs(row[2] - value) < 0.002), 0)


def _film_get(self):
    return _ratio(_sc(self).render)


def _film_set(self, v):
    rd = _sc(self).render
    rd.resolution_y = max(4, round(rd.resolution_x / max(0.001, v)))


def _pix_get(self):
    rd = _sc(self).render
    return rd.pixel_aspect_x / max(1e-6, rd.pixel_aspect_y)


def _pix_set(self, v):
    rd = _sc(self).render
    rd.pixel_aspect_x, rd.pixel_aspect_y = max(1.0, v), max(1.0, 1.0 / max(1e-6, v))


def _border(attr, flip, wide):
    def get(self):
        rd = _sc(self).render
        size = rd.resolution_x if wide else rd.resolution_y
        v = getattr(rd, attr)
        return round((1 - v if flip else v) * size)

    def set_(self, v):
        rd = _sc(self).render
        size = rd.resolution_x if wide else rd.resolution_y
        f = max(0.0, min(1.0, v / max(1, size)))
        setattr(rd, attr, 1 - f if flip else f)
    return get, set_


def _dpi_changed(self, _context):
    rd = _sc(self).render
    rd.ppm_base, rd.ppm_factor = 0.0254, self.dpi        # pixels per inch, written into saved images


def _dpi_v_get(self):
    return self.dpi / 2.54 if self.dpi_unit == "CM" else self.dpi


def _dpi_v_set(self, v):
    self.dpi = v * 2.54 if self.dpi_unit == "CM" else v


def frame_span(scene):
    """(first, last, step) the Frame Range setting renders."""
    p = scene.b4d_render
    if p.frame_range == "ALL":
        return scene.frame_start, scene.frame_end, scene.frame_step
    if p.frame_range == "PREVIEW" and scene.use_preview_range:
        return scene.frame_preview_start, scene.frame_preview_end, scene.frame_step
    if p.frame_range == "PREVIEW":
        return scene.frame_start, scene.frame_end, scene.frame_step
    if p.frame_range == "MANUAL":
        return p.frame_from, max(p.frame_from, p.frame_to), p.frame_step
    return scene.frame_current, scene.frame_current, 1


def _span_get(index):
    def get(self):
        return frame_span(_sc(self))[index]
    return get


def _span_set(attr):
    def set_(self, v):                     # typing a frame switches Frame Range to Manual
        first, last, step = frame_span(_sc(self))
        self.frame_from, self.frame_to, self.frame_step = first, last, step
        setattr(self, attr, v)
        self.frame_range = "MANUAL"
    return set_


def _passes_changed(self, _context):
    """Multi-Pass on: the passes ticked on its page are rendered. Off: only the combined image."""
    for vl in _sc(self).view_layers:
        for prop, attr, _label in PASSES:
            if hasattr(vl, attr):
                setattr(vl, attr, self.multipass and getattr(self, prop))


def _override_changed(self, _context):
    mat = self.override_material if self.material_override else None
    for vl in _sc(self).view_layers:
        if vl.material_override != mat:
            vl.material_override = mat


PASS_TIPS = {"Depth": "How far each pixel is from the camera", "Mist": "A fog-like fade with distance",
             "Normal": "Which way each surface faces", "Ambient Occlusion": "Soft shadowing in corners and creases",
             "Diffuse Color": "The plain surface colours without lighting", "Glossy Color": "The colour of reflections",
             "Emission": "Light given off by glowing surfaces", "Environment": "The background and sky alone",
             "Object Index": "A number per object, for picking objects out later",
             "Material Index": "A number per material, for picking materials out later"}


def _pass(name):
    return bpy.props.BoolProperty(name=name, default=False, update=_passes_changed,
                                  description=f"{name} pass: {PASS_TIPS.get(name, name)} (saved as its own image layer)")


class BLENDA4D_RenderProps(bpy.types.PropertyGroup):
    pass_z: _pass("Depth")
    pass_mist: _pass("Mist")
    pass_normal: _pass("Normal")
    pass_ao: _pass("Ambient Occlusion")
    pass_diffuse: _pass("Diffuse Color")
    pass_glossy: _pass("Glossy Color")
    pass_emit: _pass("Emission")
    pass_env: _pass("Environment")
    pass_object: _pass("Object Index")
    pass_material: _pass("Material Index")
    save: bpy.props.BoolProperty(name="Save", default=True,
                                 description="Write still renders to the file below (animations are always written)")
    multipass: bpy.props.BoolProperty(name="Multi-Pass", default=False, update=_passes_changed,
                                      description="Render the extra image passes ticked on the Multi-Pass page")
    material_override: bpy.props.BoolProperty(name="Material Override", default=False, update=_override_changed,
                                              description="Render every object with one material")
    override_material: bpy.props.PointerProperty(description='The material every object renders with while Material Override is on', type=bpy.types.Material, name="Material", update=_override_changed)
    lock_ratio: bpy.props.BoolProperty(name="Lock Ratio", default=False,
                                       description="Changing the width or height keeps the picture's proportions")
    dpi: bpy.props.FloatProperty(description='Pixels per inch or per cm saved in the image; sets its print size', name="Resolution", default=72.0, min=1.0, update=_dpi_changed)
    dpi_unit: bpy.props.EnumProperty(description='Measure the resolution per inch or per centimetre', name="Resolution Unit", items=DPI_UNITS, default="IN")
    size_unit: bpy.props.EnumProperty(name="Size Unit", items=SIZE_UNITS, default="PX",
                                      description="Show the width and height in pixels or as a print size at this resolution")
    use_scene_fps: bpy.props.BoolProperty(name="Use Scene Frame Rate", default=True,
                                            description="Render at the scene's frame rate; off, render at the rate below")
    fps: bpy.props.IntProperty(description="Frames per second for this render when the scene's own rate is not used", name="Frame Rate", default=30, min=1, max=1000)
    frame_range: bpy.props.EnumProperty(description='Which frames are rendered', name="Frame Range", items=FRAME_RANGES, default="CURRENT")
    frame_from: bpy.props.IntProperty(description='The first frame rendered when the range is Manual', name="From", default=0)
    frame_to: bpy.props.IntProperty(description='The last frame rendered when the range is Manual', name="To", default=0)
    frame_step: bpy.props.IntProperty(description='Render every nth frame', name="Frame Step", default=1, min=1)
    annotations: bpy.props.StringProperty(name="Annotations", default="", description="A note kept with this render setting")
    show_region: bpy.props.BoolProperty(name="Region Borders", default=False, description="Show the region's borders")
    # the fields the Output page shows
    v_preset: bpy.props.EnumProperty(description='A common image size; picking one sets the width and height', name="Preset", items=[(r[0], r[1], "Size set by hand" if r[0] == "CUSTOM" else f"Set the image to {r[1]}") for r in PRESETS], get=_preset_get, set=_preset_set)
    v_width: bpy.props.IntProperty(description='The image width in pixels', name="Width", min=4, soft_max=16384, subtype="PIXEL",
                                   get=lambda s: _sc(s).render.resolution_x, set=_w_set)
    v_height: bpy.props.IntProperty(description='The image height in pixels', name="Height", min=4, soft_max=16384, subtype="PIXEL",
                                    get=lambda s: _sc(s).render.resolution_y, set=_h_set)
    v_phys_w: bpy.props.FloatProperty(description='The image width as a print size at the resolution below', name="Width", precision=2, min=0.0, get=lambda s: _sc(s).render.resolution_x / _per_unit(s),
                                      set=lambda s, v: _w_set(s, round(v * _per_unit(s))))
    v_phys_h: bpy.props.FloatProperty(description='The image height as a print size at the resolution below', name="Height", precision=2, min=0.0, get=lambda s: _sc(s).render.resolution_y / _per_unit(s),
                                      set=lambda s, v: _h_set(s, round(v * _per_unit(s))))
    v_dpi: bpy.props.FloatProperty(name="Resolution", precision=0, min=1.0, get=_dpi_v_get, set=_dpi_v_set,
                                   description="Pixels per inch or per cm, saved into the images; sets the print size")
    v_film: bpy.props.FloatProperty(name="Film Aspect", precision=4, min=0.001, max=1000.0, get=_film_get, set=_film_set,
                                    description="Width divided by height; changing it changes the height")
    v_film_p: bpy.props.EnumProperty(description='A common image shape; picking one sets the height from the width', name="Film Aspect Preset", items=[(r[0], r[1], "Shape set by hand" if r[0] == "CUSTOM" else f"Make the image {r[1]}") for r in FILM],
                                     get=lambda s: _table_get(FILM, _film_get(s)), set=lambda s, i: i and _film_set(s, FILM[i][2]))
    v_pix: bpy.props.FloatProperty(name="Pixel Aspect", precision=3, min=0.001, max=1000.0, get=_pix_get, set=_pix_set,
                                   description="Shape of one pixel: 1 is square, above 1 is wider than tall")
    v_pix_p: bpy.props.EnumProperty(description='A common pixel shape: square, or stretched for anamorphic film', name="Pixel Aspect Preset", items=[(r[0], r[1], "Pixel shape set by hand" if r[0] == "CUSTOM" else f"{r[1]} pixels") for r in PIXEL],
                                    get=lambda s: _table_get(PIXEL, _pix_get(s)), set=lambda s, i: i and _pix_set(s, PIXEL[i][2]))
    v_left: bpy.props.IntProperty(description='Pixels from the left edge where the render region starts', name="Left Border", min=0, get=_border("border_min_x", False, True)[0], set=_border("border_min_x", False, True)[1])
    v_right: bpy.props.IntProperty(description='Pixels from the right edge where the render region ends', name="Right Border", min=0, get=_border("border_max_x", True, True)[0], set=_border("border_max_x", True, True)[1])
    v_top: bpy.props.IntProperty(description='Pixels from the top edge where the render region starts', name="Top Border", min=0, get=_border("border_max_y", True, False)[0], set=_border("border_max_y", True, False)[1])
    v_bottom: bpy.props.IntProperty(description='Pixels from the bottom edge where the render region ends', name="Bottom Border", min=0, get=_border("border_min_y", False, False)[0], set=_border("border_min_y", False, False)[1])
    v_from: bpy.props.IntProperty(description='The first frame rendered', name="From", get=_span_get(0), set=_span_set("frame_from"))
    v_to: bpy.props.IntProperty(description='The last frame rendered', name="To", get=_span_get(1), set=_span_set("frame_to"))
    v_step: bpy.props.IntProperty(description='Render every nth frame', name="Frame Step", min=1, get=_span_get(2), set=_span_set("frame_step"))


# --- the list of render settings -------------------------------------------------------------------------------
def sets(scene):
    return scene.b4d_rsets


def commit(scene):
    """Store what the scene shows into the active render setting."""
    i = scene.b4d_rs_loaded
    if 0 <= i < len(sets(scene)):
        sets(scene)[i].values = json.dumps(capture(scene))


def load(scene, index):
    scene.b4d_rs_loaded = index
    apply_values(scene, json.loads(sets(scene)[index].values or "{}"))


def ensure(scene):
    """The first render setting takes over the scene as it stands."""
    if len(sets(scene)):
        return
    r = sets(scene).add()
    r.name = DEFAULT_NAME
    scene.b4d_rs_loaded = 0
    _set_index(scene, 0)
    commit(scene)


def _unique(scene, base):
    names = {r.name for r in sets(scene)}
    if base not in names:
        return base
    i = 1
    while f"{base}.{i:03d}" in names:
        i += 1
    return f"{base}.{i:03d}"


_quiet = [False]


def _set_index(scene, index):
    """Move the list's highlight without the update below running."""
    _quiet[0] = True
    try:
        scene.b4d_rs_index = index
    finally:
        _quiet[0] = False


def _picked(scene, _context):
    """List selection changed: the picked setting becomes the active one."""
    if _quiet[0]:
        return
    i = scene.b4d_rs_index
    if not (0 <= i < len(sets(scene))) or i == scene.b4d_rs_loaded:
        return
    commit(scene)
    load(scene, i)


def _select(scene, index):
    """Make index active without storing the scene into it first (it already holds its own values)."""
    _set_index(scene, index)
    load(scene, index)


class BLENDA4D_RenderSet(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name", default=DEFAULT_NAME)
    values: bpy.props.StringProperty(description='The values this render setting keeps', default="{}")


class BLENDA4D_RenderPage(bpy.types.PropertyGroup):
    key: bpy.props.StringProperty(description='Which page or item this row stands for', )


class BLENDA4D_UL_render_sets(bpy.types.UIList):
    bl_idname = "BLENDA4D_UL_render_sets"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0, flt_flag=0):
        layout.prop(item, "name", text="", emboss=False, icon="RENDER_STILL")


def page_shown(scene, key):
    return True


def page_title(scene, key):
    if key == "ENGINE":
        e = scene.render.engine
        return ENGINE_NAMES.get(e, e.replace("_", " ").title())
    return next(p[1] for p in PAGES if p[0] == key)


def _switch_owner(scene, switch):
    return scene.b4d_render if switch[0] == "rs" else scene.render


class BLENDA4D_UL_render_pages(bpy.types.UIList):
    bl_idname = "BLENDA4D_UL_render_pages"

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index=0, flt_flag=0):
        page = next((p for p in PAGES if p[0] == item.key), None)
        if page is None:
            return
        row = layout.row(align=True)
        if page[2]:
            row.prop(_switch_owner(context.scene, page[2]), page[2][1], text="")
        else:
            row.label(text="", icon="BLANK1")
        row.label(text=page_title(context.scene, page[0]))

    def filter_items(self, context, data, propname):
        items = getattr(data, propname)
        flags = [self.bitflag_filter_item if page_shown(context.scene, it.key) else 0 for it in items]
        return flags, []


def ensure_pages(wm):
    pages = wm.b4d_rs_pages
    if [p.key for p in pages] == [p[0] for p in PAGES]:
        return
    pages.clear()
    for key, _title, _switch in PAGES:
        pages.add().key = key


def current_page(context):
    wm = context.window_manager
    i = wm.b4d_rs_page
    key = wm.b4d_rs_pages[i].key if 0 <= i < len(wm.b4d_rs_pages) else "OUTPUT"
    return key if page_shown(context.scene, key) else "OUTPUT"


# --- operators ---------------------------------------------------------------------------------------------------
class BLENDA4D_OT_rs_add(bpy.types.Operator):
    bl_idname = "blenda4d.rs_add"
    bl_label = "New"
    bl_description = "Add a render setting with default values and make it the active one"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        ensure(scene)
        commit(scene)
        r = sets(scene).add()
        r.name = _unique(scene, DEFAULT_NAME)
        r.values = json.dumps(defaults(scene))
        _select(scene, len(sets(scene)) - 1)
        return {"FINISHED"}


class BLENDA4D_OT_rs_duplicate(bpy.types.Operator):
    bl_idname = "blenda4d.rs_duplicate"
    bl_label = "Duplicate"
    bl_description = "Copy the active render setting and make the copy the active one"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scene = context.scene
        ensure(scene)
        commit(scene)
        src = sets(scene)[scene.b4d_rs_loaded]
        r = sets(scene).add()
        r.name = _unique(scene, src.name)
        r.values = src.values
        sets(scene).move(len(sets(scene)) - 1, scene.b4d_rs_loaded + 1)
        _select(scene, scene.b4d_rs_loaded + 1)
        return {"FINISHED"}


class BLENDA4D_OT_rs_remove(bpy.types.Operator):
    bl_idname = "blenda4d.rs_remove"
    bl_label = "Delete"
    bl_description = "Delete the active render setting; the one above it becomes active"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return len(sets(context.scene)) > 1

    def execute(self, context):
        scene = context.scene
        i = scene.b4d_rs_loaded
        sets(scene).remove(i)
        _select(scene, max(0, min(i - 1, len(sets(scene)) - 1)))
        return {"FINISHED"}


class BLENDA4D_OT_rs_move(bpy.types.Operator):
    bl_idname = "blenda4d.rs_move"
    bl_label = "Move"
    bl_description = "Move the active render setting up or down the list"
    bl_options = {"REGISTER", "UNDO"}
    step: bpy.props.IntProperty(default=-1)

    @classmethod
    def description(cls, context, props):
        return "Move the active render setting up the list" if props.step < 0 else "Move the active render setting down the list"

    def execute(self, context):
        scene = context.scene
        i = scene.b4d_rs_loaded
        j = i + self.step
        if not (0 <= i < len(sets(scene)) and 0 <= j < len(sets(scene))):
            return {"CANCELLED"}
        sets(scene).move(i, j)
        scene.b4d_rs_loaded = j
        _set_index(scene, j)
        return {"FINISHED"}


class BLENDA4D_OT_rs_rename(bpy.types.Operator):
    bl_idname = "blenda4d.rs_rename"
    bl_label = "Rename Render Setting"
    bl_description = "Give the active render setting a new name"
    bl_options = {"REGISTER", "UNDO"}
    name: bpy.props.StringProperty(name="Name")

    @classmethod
    def poll(cls, context):
        return len(sets(context.scene)) > 0

    def invoke(self, context, event):
        self.name = sets(context.scene)[context.scene.b4d_rs_loaded].name
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        sets(context.scene)[context.scene.b4d_rs_loaded].name = self.name or DEFAULT_NAME
        return {"FINISHED"}


class BLENDA4D_MT_render_setting(bpy.types.Menu):
    bl_idname = "BLENDA4D_MT_render_setting"
    bl_label = "Render Setting"
    bl_description = "Add, copy, rename and remove render settings"

    def draw(self, context):
        lay = self.layout
        lay.operator("blenda4d.rs_add", icon="ADD")
        lay.operator("blenda4d.rs_duplicate", icon="DUPLICATE")
        lay.operator("blenda4d.rs_remove", icon="REMOVE")
        lay.separator()
        lay.operator("blenda4d.rs_rename", text="Rename...", icon="GREASEPENCIL")
        lay.operator("blenda4d.rs_move", text="Move Up", icon="TRIA_UP").step = -1
        lay.operator("blenda4d.rs_move", text="Move Down", icon="TRIA_DOWN").step = 1


# --- rendering with the setting's frame range, frame rate and Save ----------------------------------------------
_stash = {}


@bpy.app.handlers.persistent
def _restore(*_args):
    """Put back the frame range and rate prepare() changed for a render."""
    scene = _stash.pop("scene", None)
    values = _stash.pop("values", {})
    _stash.clear()
    if scene is None:
        return
    try:
        scene.frame_start, scene.frame_end = values["frame_start"], values["frame_end"]
        if scene.frame_start != values["frame_start"]:       # Blender keeps start <= end: set again in the other order
            scene.frame_start = values["frame_start"]
        scene.frame_step = values["frame_step"]
        scene.render.fps, scene.render.fps_base = values["fps"], values["fps_base"]
    except (ReferenceError, KeyError):
        pass


def prepare(scene, animation):
    """Set the scene's frame range and rate for a render; _restore() puts them back."""
    _restore()
    p = scene.b4d_render
    keep = {"frame_start": scene.frame_start, "frame_end": scene.frame_end, "frame_step": scene.frame_step,
            "fps": scene.render.fps, "fps_base": scene.render.fps_base}
    _stash.update(scene=scene, values=keep)
    if animation:
        first, last, step = frame_span(scene)
        if first > scene.frame_end:          # Blender keeps start <= end: move the end first
            scene.frame_end = last
            scene.frame_start = first
        else:
            scene.frame_start = first
            scene.frame_end = last
        scene.frame_step = step
    if not p.use_scene_fps:
        scene.render.fps, scene.render.fps_base = p.fps, 1.0


def _has_simulation(tree, seen=None):
    seen = set() if seen is None else seen
    if tree is None or tree.name in seen:
        return False
    seen.add(tree.name)
    for n in tree.nodes:
        if n.bl_idname == "GeometryNodeSimulationOutput":
            return True
        if getattr(n, "node_tree", None) is not None and _has_simulation(n.node_tree, seen):
            return True
    return False


def prime_simulations(scene, last):
    """A render only sees a simulation (Delay, Tracer, MoInstance and other effects that remember earlier frames) as
    far as the timeline has been played: rendered cold, Delay froze the clones where they started. So before a render
    the frames from the start up to the last one rendered are stepped through once, in order, which fills the cache."""
    if not any(m.type == "NODES" and _has_simulation(m.node_group) for o in scene.objects for m in o.modifiers):
        return
    now = scene.frame_current
    for f in range(scene.frame_start, last + 1):
        scene.frame_set(f)
    scene.frame_set(now)


class BLENDA4D_OT_render(bpy.types.Operator):
    bl_idname = "blenda4d.render"
    bl_label = "Render"
    bl_description = "Render with the active render setting: its frame range, frame rate and Save switch"
    animation: bpy.props.BoolProperty(default=False)

    def execute(self, context):
        scene = context.scene
        if bpy.app.is_job_running("RENDER"):
            self.report({"INFO"}, "A render is running")
            return {"CANCELLED"}
        prepare(scene, self.animation)
        prime_simulations(scene, scene.frame_end if self.animation else scene.frame_current)
        keep = scene.b4d_render.save or self.animation       # animations are always written
        from . import viewer
        if not bpy.app.background:
            first, last = (scene.frame_start, scene.frame_end) if self.animation else (scene.frame_current,) * 2
            viewer.begin(scene, first, last, keep)
        try:
            res = bpy.ops.render.render("EXEC_DEFAULT" if bpy.app.background else "INVOKE_DEFAULT",
                                        animation=self.animation, write_still=not self.animation and (keep or not bpy.app.background))
        except RuntimeError as ex:
            viewer.failed()
            _restore()
            self.report({"ERROR"}, str(ex))
            return {"CANCELLED"}
        if bpy.app.background or "RUNNING_MODAL" not in res:   # finished (or never started): put the scene back now
            _restore()
        return {"FINISHED"}


# --- the window ------------------------------------------------------------------------------------------------
def _window_with_role(context):
    for w in context.window_manager.windows:
        if any(roles.role(a) == ROLE for a in w.screen.areas):
            return w
    return None


class BLENDA4D_OT_render_settings(bpy.types.Operator):
    bl_idname = "blenda4d.render_settings"
    bl_label = "Render Settings"
    bl_description = "Open the Render Settings window: saved render settings and their values"

    def execute(self, context):
        ensure(context.scene)
        wm = context.window_manager
        ensure_pages(wm)
        if roles.areas(context.screen, "PV_TOP") and roles.areas(context.screen, "OBJECTS"):      # the Render Viewer is there
            from . import build, viewer
            if build.busy():
                return {"CANCELLED"}
            win = context.window
            build.run_steps(viewer.leave_steps(win), done=lambda: dock(win))
            return {"FINISHED"}
        if roles.areas(context.screen, "OBJECTS"):           # Blenda's layout: in the viewport's place, under its tabs
            return {"FINISHED"} if dock(context.window) else {"CANCELLED"}
        old = _window_with_role(context)
        if old is not None:                      # Blender cannot bring a window to the front: open it again
            with context.temp_override(window=old):
                bpy.ops.wm.window_close()
        before = {w.as_pointer() for w in wm.windows}
        bpy.ops.screen.drivers_editor_show("INVOKE_DEFAULT")       # Blender's way to open a small floating window
        win = next((w for w in wm.windows if w.as_pointer() not in before), None)
        if win is None:
            return {"CANCELLED"}
        area = win.screen.areas[0]
        area.type = "PROPERTIES"
        roles.set_role(area, ROLE)

        def finish():
            if not roles.alive(area):
                return None
            try:
                roles.hide_nav(area, win)
                area.tag_redraw()
            except (ReferenceError, RuntimeError):
                pass
            return None
        bpy.app.timers.register(finish, first_interval=0.05)
        return {"FINISHED"}


def dock(window):
    """Show Render Settings where the viewport is (the viewport tab row's middle tab). The area keeps its 3D view,
    which comes back as it was when View is picked (show_view)."""
    screen = window.screen
    if roles.areas(screen, ROLE):
        return True
    views = [a for a in screen.areas if a.type == "VIEW_3D"]
    if not views:
        return False
    area = max(views, key=lambda a: a.width * a.height)
    area.type = "PROPERTIES"
    tries = [0]

    def finish():
        if not roles.alive(area):
            return None
        try:
            if not roles.set_role(area, ROLE) and tries[0] < 20:
                tries[0] += 1
                return 0.02
            _header(area)
            roles.hide_nav(area, window)
            for a in screen.areas:
                a.tag_redraw()
        except (ReferenceError, RuntimeError):
            pass
        return None
    if roles.set_role(area, ROLE):
        _header(area)
        roles.hide_nav(area, window)
    else:
        bpy.app.timers.register(finish, first_interval=0.02)
    for a in screen.areas:
        a.tag_redraw()
    return True


def _header(area):
    """The docked page keeps a header, at the top as the viewport's is, for the tab row (bars.properties_header)."""
    space = area.spaces.active
    space.show_region_header = True
    for region in area.regions:
        if region.type == "HEADER" and region.alignment != "TOP":
            try:
                with bpy.context.temp_override(area=area, region=region):
                    bpy.ops.screen.region_flip()
            except RuntimeError:
                pass


def show_view(screen):
    """Put the viewport back where Render Settings is shown."""
    for a in roles.areas(screen, ROLE):
        a.type = "VIEW_3D"
    for a in screen.areas:
        a.tag_redraw()


class BLENDA4D_OT_view_tab(bpy.types.Operator):
    bl_idname = "blenda4d.view_tab"
    bl_label = "View"
    bl_description = "Show the viewport"

    def execute(self, context):
        show_view(context.screen)
        if roles.areas(context.screen, "PV_TOP"):
            from . import build, viewer
            if build.busy():
                return {"CANCELLED"}
            build.run_steps(viewer.leave_steps(context.window))
        return {"FINISHED"}


def _close_windows():
    wm = bpy.context.window_manager
    if wm is None:
        return
    for w in list(wm.windows):
        if any(roles.role(a) == ROLE for a in w.screen.areas):
            try:
                with bpy.context.temp_override(window=w):
                    bpy.ops.wm.window_close()
            except (RuntimeError, ReferenceError):
                pass


# --- pages -------------------------------------------------------------------------------------------------------
LABEL_F = 0.27         # the label column: a quarter of the page, as in the reference layout
FIELD_F = 0.2          # a number field's share of the rest; a menu's and a text field's (fields stay short)
MENU_F = 0.49


_geo = {"page": 800.0}   # the page's width in pixels, set as the page is drawn


def _s():
    return bpy.context.preferences.system.ui_scale


def _label_f():
    """The label column: a quarter of the page, never narrower than a long label."""
    return min(0.45, max(LABEL_F, 150 * _s() / max(_geo["page"], 1)))


def _right_px():
    return _geo["page"] * (1 - _label_f())


def _field_f():
    """A number field's share of the rest: short, never too short to show its number."""
    return min(1.0, max(FIELD_F, 80 * _s() / max(_right_px(), 1)))


def _menu_f():
    return min(1.0, max(MENU_F, 170 * _s() / max(_right_px(), 1)))


class PageCol:
    """A page's column: every prop() becomes one row of label (right-aligned, in the label column) and a short field,
    a checkbox without text where the fields start. Anything else goes straight to Blender's layout."""

    def __init__(self, layout):
        self._layout = layout
        self.active = True

    def __getattr__(self, name):
        return getattr(self._layout, name)

    def column(self, **kw):
        kw.pop("heading", None)
        sub = PageCol(self._layout.column(**kw))
        sub.active = self.active
        return sub

    def row(self, **kw):
        sub = PageCol(self._layout.column())
        sub.active = self.active
        return sub

    def prop(self, owner, attr, text=None, expand=False, **kw):
        rna = owner.bl_rna.properties[attr]
        split = self._layout.split(factor=_label_f())
        split.active = self.active
        lab = split.row()
        lab.alignment = "RIGHT"
        lab.label(text=rna.name if text is None else text)
        right = split.row(align=True)
        if expand:
            right.prop(owner, attr, expand=True, **kw)
        elif rna.type == "BOOLEAN" and not getattr(rna, "is_array", False):
            right.prop(owner, attr, text="", **kw)
        else:
            f = _menu_f() if rna.type in ("ENUM", "POINTER", "STRING") else _field_f()
            sub = right.split(factor=f, align=True)
            sub.prop(owner, attr, text="", **kw)
            sub.label(text="")


def _label_col(col, label, active=True):
    split = col.split(factor=_label_f())
    split.active = active
    lab = split.row()
    lab.alignment = "RIGHT"
    lab.label(text=label)
    return split


def _info(col, label, text):
    """A read-only line: label in the label column, text where the fields are."""
    _label_col(col, label).label(text=text)


def _field(col, label, owner, attr, menu=None, wide=False, active=True):
    """Label on the left, a short value field, and an optional dropdown beside it (Width + unit)."""
    right = _label_col(col, label, active)
    if owner.bl_rna.properties[attr].type == "BOOLEAN":
        right.prop(owner, attr, text="")
        return
    if wide:
        sub = right.split(factor=_menu_f())
        sub.prop(owner, attr, text="")
        sub.label(text="")
        return
    if menu and _geo.get("narrow"):                   # a narrow page: the unit menu on a row of its own
        sub = right.split(factor=_field_f())
        sub.prop(owner, attr, text="")
        sub.label(text="")
        _field(col, menu[0].bl_rna.properties[menu[1]].name, menu[0], menu[1], wide=True, active=active)
        return
    pair = right.split(factor=_field_f())
    pair.prop(owner, attr, text="")
    rest_px = _right_px() * (1 - _field_f())                 # the unit menu: never too narrow to show its unit
    rest = pair.split(factor=min(1.0, max(0.45, 110 * _s() / max(rest_px, 1))))
    if menu:
        rest.prop(menu[0], menu[1], text="")
    else:
        rest.label(text="")
    rest.label(text="")


def _rows(col, owner, attrs):
    for attr, text in attrs:
        if owner is not None and hasattr(owner, attr):
            col.prop(owner, attr, text=text)


def draw_output(col, scene):
    rd, p = scene.render, scene.b4d_render
    _field(col, "Preset", p, "v_preset", wide=True)
    px = p.size_unit == "PX"
    _field(col, "Width", p, "v_width" if px else "v_phys_w", menu=(p, "size_unit"))
    _field(col, "Height", p, "v_height" if px else "v_phys_h")
    _field(col, "Lock Ratio", p, "lock_ratio")
    _field(col, "Resolution", p, "v_dpi", menu=(p, "dpi_unit"))
    w = rd.resolution_x * rd.resolution_percentage // 100
    h = rd.resolution_y * rd.resolution_percentage // 100
    _info(col, "Image Resolution:", f"{w} x {h} Pixel")
    _field(col, "Render Scale", rd, "resolution_percentage")
    split = col.split(factor=_label_f())
    lab = split.row()
    lab.alignment = "RIGHT"
    lab.prop(p, "show_region", text="", icon="DOWNARROW_HLT" if p.show_region else "RIGHTARROW", emboss=False)
    lab.label(text="Render Region")
    split.prop(rd, "use_border", text="")
    if p.show_region:
        _field(col, "Crop to Region", rd, "use_crop_to_border", active=rd.use_border)
        for attr, label in (("v_left", "Left Border"), ("v_top", "Top Border"), ("v_right", "Right Border"),
                            ("v_bottom", "Bottom Border")):
            _field(col, label, p, attr, active=rd.use_border)
    col.separator(type="LINE")
    _field(col, "Film Aspect", p, "v_film", menu=(p, "v_film_p"))
    _field(col, "Pixel Aspect", p, "v_pix", menu=(p, "v_pix_p"))
    _field(col, "Use Scene Frame Rate", p, "use_scene_fps")
    _field(col, "Frame Rate", rd if p.use_scene_fps else p, "fps", active=not p.use_scene_fps)
    col.separator(type="LINE")
    _field(col, "Frame Range", p, "frame_range", wide=True)
    manual = p.frame_range == "MANUAL"
    _field(col, "From", p, "v_from", active=manual)
    _field(col, "To", p, "v_to", active=manual)
    _field(col, "Frame Step", p, "v_step", active=manual)
    first, last, step = frame_span(scene)
    n = max(0, (last - first) // max(1, step) + 1)
    _info(col, "Frames:", f"{n} frames (from {first} to {last})")
    col.separator(type="LINE")
    _field(col, "Annotations", p, "annotations", wide=True)


def _group(col, text):
    """A group heading on a page (Sampling, Light Paths ...)."""
    col.separator(factor=0.3)
    col.label(text=text)


def _auto(col, owner, attr, label, active=True):
    """One row for one of Blender's settings, left out when this Blender has no such setting."""
    if owner is None or not hasattr(owner, attr):
        return
    row = col.row()
    row.active = active
    row.prop(owner, attr, text=label)


def draw_save(col, scene):
    rd = scene.render
    img = rd.image_settings
    _group(col, "Regular Image")
    col.prop(scene.b4d_render, "save", text="Save")
    col.prop(rd, "filepath", text="File")
    col.prop(img, "file_format", text="Format")
    if len(img.bl_rna.properties["color_depth"].enum_items) > 1:
        col.row().prop(img, "color_depth", text="Depth", expand=True)
    col.row().prop(img, "color_mode", text="Color Mode", expand=True)
    if img.file_format in {"JPEG", "WEBP", "AVIF", "JPEG2000"}:
        col.prop(img, "quality", text="Quality")
    elif img.file_format == "PNG":
        col.prop(img, "compression", text="Compression")
    col.prop(scene.view_settings, "view_transform", text="Image Color Profile")
    col.prop(rd, "film_transparent", text="Alpha Channel")
    col.prop(rd, "use_compositing", text="Compositing")
    _group(col, "Files")
    col.prop(rd, "use_file_extension", text="File Extensions")
    col.prop(rd, "use_overwrite", text="Overwrite Existing Files")
    col.prop(rd, "use_placeholder", text="Placeholders")


def draw_multipass(col, scene):
    p = scene.b4d_render
    _group(col, "Multi-Pass Image")
    col.prop(p, "multipass")
    sub = col.column(heading="Passes")
    sub.active = p.multipass
    for prop, _attr, label in PASSES:
        sub.prop(p, prop, text=label)
    _info(col, "Always:", "Combined (the finished image)")


def draw_samples(col, scene):
    e = scene.render.engine
    cy = getattr(scene, "cycles", None)
    if e == "CYCLES" and cy is not None:
        col.prop(cy, "samples", text="Max Samples")
        col.prop(cy, "use_adaptive_sampling", text="Adaptive Sampling")
        _auto(col, cy, "adaptive_threshold", "Noise Threshold", cy.use_adaptive_sampling)
        col.prop(cy, "use_denoising", text="Denoise")
        _auto(col, cy, "pixel_filter_type", "Pixel Filter")
        _auto(col, cy, "filter_width", "Filter Width")
    elif e == "BLENDER_WORKBENCH":
        col.prop(scene.display, "render_aa", text="Anti-Aliasing")
        col.prop(scene.display, "viewport_aa", text="Viewport")
    else:
        col.prop(scene.eevee, "taa_render_samples", text="Samples")
        col.prop(scene.render, "filter_size", text="Filter Size")


def draw_options(col, scene):
    rd = scene.render
    cy = getattr(scene, "cycles", None)
    if rd.engine != "BLENDER_WORKBENCH":
        col.prop(rd, "use_motion_blur", text="Motion Blur")
        _auto(col, rd, "motion_blur_shutter", "Shutter", rd.use_motion_blur)
        _auto(col, rd, "motion_blur_position", "Shutter Position", rd.use_motion_blur)
        col.separator(type="LINE")
    col.prop(rd, "use_simplify", text="Simplify")
    _auto(col, rd, "simplify_subdivision_render", "Subdivision Level", rd.use_simplify)
    _auto(col, rd, "simplify_child_particles_render", "Child Particles", rd.use_simplify)
    if rd.engine == "CYCLES":
        _auto(col, cy, "texture_limit_render", "Texture Limit", rd.use_simplify)
    col.separator(type="LINE")
    col.prop(rd, "threads_mode", text="Threads")
    _auto(col, rd, "threads", "Thread Count", rd.threads_mode == "FIXED")
    col.prop(rd, "use_persistent_data", text="Persistent Data")
    col.prop(rd, "dither_intensity", text="Dither")
    if rd.engine == "CYCLES" and cy is not None:
        _auto(col, cy, "device", "Device")
        _auto(col, cy, "max_bounces", "Light Paths")


def draw_override(col, scene):
    p = scene.b4d_render
    col.prop(p, "material_override")
    sub = col.column()
    sub.active = p.material_override
    sub.prop(p, "override_material", text="Custom Material")


ENGINE_DRAW = {}             # engine id -> fn(col, scene): its page in Render Settings


def draw_engine(col, scene):
    """The renderer's own page: what artists change every day in plain sight; for Cycles, the rest of its settings
    under Advanced, closed until opened."""
    e = scene.render.engine
    cy = getattr(scene, "cycles", None)
    if e in ENGINE_DRAW:                                   # a renderer from another module
        ENGINE_DRAW[e](col, scene)
    elif e == "CYCLES" and cy is not None:
        _draw_cycles(col, scene, cy)
    elif e == "BLENDER_WORKBENCH":
        wb = scene.display.shading
        _group(col, "Lighting")
        col.prop(wb, "light", text="Lighting")
        col.prop(wb, "color_type", text="Color")
        col.prop(scene.display, "render_aa", text="Anti-Aliasing")
        _group(col, "Options")
        for attr, label in (("show_backface_culling", "Backface Culling"), ("show_xray", "X-Ray"), ("show_shadows", "Shadow"),
                            ("show_cavity", "Cavity"), ("show_object_outline", "Outline"),
                            ("show_specular_highlight", "Specular Highlights")):
            _auto(col, wb, attr, label)
    else:
        ee = scene.eevee
        _group(col, "Sampling")
        _auto(col, ee, "taa_render_samples", "Render Samples")
        _auto(col, ee, "taa_samples", "Viewport Samples")
        _group(col, "Shadows and Lighting")
        _auto(col, ee, "use_shadows", "Shadows")
        _auto(col, ee, "shadow_ray_count", "Shadow Rays")
        _auto(col, ee, "shadow_step_count", "Shadow Steps")
        _auto(col, ee, "use_raytracing", "Raytracing")
        _auto(col, ee, "use_fast_gi", "Fast GI")
        _group(col, "Volumes")
        for attr, label in (("volumetric_tile_size", "Resolution"), ("volumetric_samples", "Steps"),
                            ("volumetric_sample_distribution", "Distribution"), ("volumetric_start", "Start"),
                            ("volumetric_end", "End"), ("use_volumetric_shadows", "Volume Shadows")):
            _auto(col, ee, attr, label)
        _auto(col, ee, "volumetric_shadow_samples", "Shadow Steps", getattr(ee, "use_volumetric_shadows", True))
        _group(col, "Motion Blur")
        _auto(col, ee, "motion_blur_steps", "Steps", scene.render.use_motion_blur)
        _auto(col, ee, "motion_blur_max", "Max Blur", scene.render.use_motion_blur)
        _group(col, "Film")
        col.prop(scene.render, "filter_size", text="Filter Size")
        col.prop(scene.render, "film_transparent", text="Transparent")
    _group(col, "Color Management")
    col.prop(scene.display_settings, "display_device", text="Display")
    col.prop(scene.view_settings, "view_transform", text="View")
    col.prop(scene.view_settings, "look", text="Look")
    col.prop(scene.view_settings, "exposure", text="Exposure")
    col.prop(scene.view_settings, "gamma", text="Gamma")


def _draw_cycles(col, scene, cy):
    rd = scene.render
    _group(col, "Sampling")
    for attr, label, on in (("device", "Device", True), ("samples", "Render Samples", True),
                            ("preview_samples", "Viewport Samples", True), ("use_adaptive_sampling", "Adaptive Sampling", True),
                            ("adaptive_threshold", "Noise Threshold", cy.use_adaptive_sampling),
                            ("adaptive_min_samples", "Min Samples", cy.use_adaptive_sampling),
                            ("preview_adaptive_threshold", "Viewport Noise Threshold", True), ("time_limit", "Time Limit", True),
                            ("use_denoising", "Denoise", True), ("denoiser", "Denoiser", cy.use_denoising),
                            ("use_preview_denoising", "Viewport Denoise", True)):
        _auto(col, cy, attr, label, on)
    _group(col, "Light Paths")
    for attr, label in (("max_bounces", "Max Bounces"), ("diffuse_bounces", "Diffuse"), ("glossy_bounces", "Glossy"),
                        ("transmission_bounces", "Transmission"), ("volume_bounces", "Volume"),
                        ("transparent_max_bounces", "Transparent"), ("caustics_reflective", "Caustics Reflective"),
                        ("caustics_refractive", "Caustics Refractive"), ("blur_glossy", "Filter Glossy"),
                        ("sample_clamp_direct", "Clamp Direct"), ("sample_clamp_indirect", "Clamp Indirect"),
                        ("use_fast_gi", "Fast GI Approximation")):
        _auto(col, cy, attr, label)
    _group(col, "Subdivision")
    _auto(col, cy, "preview_dicing_rate", "Viewport Dicing Rate")
    _auto(col, cy, "dicing_rate", "Render Dicing Rate")
    _auto(col, cy, "max_subdivisions", "Max Subdivisions")
    _group(col, "Film")
    _auto(col, cy, "film_exposure", "Exposure")
    col.prop(rd, "film_transparent", text="Transparent")
    _auto(col, cy, "film_transparent_glass", "Transparent Glass", rd.film_transparent)
    _auto(col, cy, "pixel_filter_type", "Pixel Filter")
    _auto(col, cy, "filter_width", "Filter Width")
    _group(col, "Performance")
    col.prop(rd, "use_persistent_data", text="Persistent Data")
    col.prop(rd, "threads_mode", text="Threads")
    _auto(col, cy, "tile_size", "Tile Size")
    _auto(col, rd, "preview_pixel_size", "Viewport Pixel Size")
    wm = bpy.context.window_manager
    col.separator()
    row = col._layout.row()
    row.alignment = "LEFT"
    row.prop(wm, "b4d_rs_advanced", text="Advanced", emboss=False,
             icon="DOWNARROW_HLT" if wm.b4d_rs_advanced else "RIGHTARROW")
    if not wm.b4d_rs_advanced:
        return
    on = cy.use_preview_denoising
    _group(col, "Viewport Sampling")
    _auto(col, cy, "use_preview_adaptive_sampling", "Adaptive Sampling")
    _auto(col, cy, "preview_adaptive_min_samples", "Min Samples", getattr(cy, "use_preview_adaptive_sampling", True))
    for attr, label in (("preview_denoiser", "Denoiser"), ("preview_denoising_input_passes", "Passes"),
                        ("preview_denoising_prefilter", "Prefilter"), ("preview_denoising_quality", "Quality"),
                        ("preview_denoising_start_sample", "Start Sample"), ("preview_denoising_use_gpu", "Use GPU")):
        _auto(col, cy, attr, label, on)
    on = cy.use_denoising
    _group(col, "Render Denoising")
    for attr, label in (("denoising_input_passes", "Passes"), ("denoising_prefilter", "Prefilter"),
                        ("denoising_quality", "Quality"), ("denoising_use_gpu", "Use GPU")):
        _auto(col, cy, attr, label, on)
    _group(col, "Path Guiding")
    _auto(col, cy, "use_guiding", "Path Guiding")
    on = getattr(cy, "use_guiding", False)
    for attr, label in (("guiding_training_samples", "Training Samples"), ("use_surface_guiding", "Surface Guiding"),
                        ("use_volume_guiding", "Volume Guiding")):
        _auto(col, cy, attr, label, on)
    _group(col, "Lights")
    _auto(col, cy, "use_light_tree", "Light Tree")
    _auto(col, cy, "light_sampling_threshold", "Light Threshold")
    _group(col, "Sampling Pattern")
    for attr, label in (("sampling_pattern", "Pattern"), ("seed", "Seed"), ("use_animated_seed", "Animated Seed"),
                        ("scrambling_distance", "Scrambling Distance"), ("auto_scrambling_distance", "Automatic Scrambling"),
                        ("preview_scrambling_distance", "Viewport Scrambling"), ("min_light_bounces", "Min Light Bounces"),
                        ("min_transparent_bounces", "Min Transparent Bounces"), ("use_layer_samples", "Layer Samples"),
                        ("use_pixel_jitter", "Pixel Jitter"), ("use_sample_subset", "Sample Subset")):
        _auto(col, cy, attr, label)
    on = getattr(cy, "use_sample_subset", False)
    _auto(col, cy, "sample_offset", "Subset Offset", on)
    _auto(col, cy, "sample_subset_length", "Subset Length", on)
    _group(col, "Fast GI")
    on = getattr(cy, "use_fast_gi", False)
    _auto(col, cy, "fast_gi_method", "Method", on)
    _auto(col, cy, "ao_bounces", "Viewport Bounces", on)
    _auto(col, cy, "ao_bounces_render", "Render Bounces", on)
    world = scene.world.light_settings if scene.world is not None else None
    _auto(col, world, "ao_factor", "AO Factor", on)
    _auto(col, world, "distance", "AO Distance", on)
    _group(col, "Subdivision")
    _auto(col, cy, "offscreen_dicing_scale", "Offscreen Scale")
    _auto(col, cy, "dicing_camera", "Dicing Camera")
    _group(col, "Volumes")
    for attr, label in (("volume_step_rate", "Step Rate Render"), ("volume_preview_step_rate", "Step Rate Viewport"),
                        ("volume_max_steps", "Max Steps"), ("volume_biased", "Biased")):
        _auto(col, cy, attr, label)
    curves = getattr(scene, "cycles_curves", None)
    _group(col, "Hair Curves")
    _auto(col, curves, "shape", "Shape")
    _auto(col, curves, "subdivisions", "Curve Subdivisions")
    _group(col, "Film")
    _auto(col, cy, "film_transparent_roughness", "Roughness Threshold",
          rd.film_transparent and getattr(cy, "film_transparent_glass", False))
    on = rd.use_motion_blur
    _group(col, "Motion Blur")
    col.prop(rd, "use_motion_blur", text="Motion Blur")
    _auto(col, rd, "motion_blur_shutter", "Shutter", on)
    _auto(col, rd, "motion_blur_position", "Shutter Position", on)
    _auto(col, cy, "rolling_shutter_type", "Rolling Shutter", on)
    _auto(col, cy, "rolling_shutter_duration", "Rolling Shutter Duration", on)
    on = rd.use_simplify
    _group(col, "Simplify")
    for owner, attr, label in ((rd, "simplify_subdivision", "Viewport Subdivision"),
                               (rd, "simplify_child_particles", "Viewport Child Particles"),
                               (rd, "simplify_child_particles_render", "Render Child Particles"),
                               (cy, "texture_limit", "Viewport Texture Limit"), (rd, "simplify_volumes", "Volume Resolution"),
                               (rd, "use_simplify_normals", "Normals"), (cy, "use_camera_cull", "Camera Culling"),
                               (cy, "use_distance_cull", "Distance Culling")):
        _auto(col, owner, attr, label, on)
    _auto(col, cy, "camera_cull_margin", "Camera Cull Margin", on and getattr(cy, "use_camera_cull", False))
    _auto(col, cy, "distance_cull_margin", "Cull Distance", on and getattr(cy, "use_distance_cull", False))
    _group(col, "Threads and Memory")
    _auto(col, rd, "threads", "Thread Count", rd.threads_mode == "FIXED")
    _auto(col, rd, "use_texture_cache", "Texture Cache")
    _auto(col, rd, "use_auto_generate_texture_cache", "Generate Cache Files")
    _group(col, "Acceleration Structure")
    for attr, label in (("debug_use_spatial_splits", "Spatial Splits"), ("debug_use_hair_bvh", "Hair BVH"),
                        ("debug_use_compact_bvh", "Compact BVH"), ("debug_bvh_time_steps", "Motion Steps")):
        _auto(col, cy, attr, label)
    bake = rd.bake
    _group(col, "Bake")
    _auto(col, cy, "bake_type", "Bake Type")
    for attr, label in (("view_from", "View From"), ("use_selected_to_active", "Selected to Active"), ("use_cage", "Cage"),
                        ("cage_object", "Cage Object"), ("cage_extrusion", "Extrusion"), ("max_ray_distance", "Max Ray Distance"),
                        ("target", "Target"), ("use_clear", "Clear Image"), ("margin_type", "Margin Type"), ("margin", "Margin"),
                        ("use_pass_direct", "Direct"), ("use_pass_indirect", "Indirect"), ("use_pass_color", "Color"),
                        ("use_pass_diffuse", "Diffuse"), ("use_pass_glossy", "Glossy"), ("use_pass_transmission", "Transmission"),
                        ("use_pass_emit", "Emit"), ("normal_space", "Normal Space"), ("normal_r", "Swizzle R"),
                        ("normal_g", "Swizzle G"), ("normal_b", "Swizzle B"), ("displacement_space", "Displacement Space"),
                        ("use_lores_mesh", "Low Resolution Mesh"), ("use_multires", "Multires")):
        _auto(col, bake, attr, label)
    col.operator("object.bake", text="Bake")


PAGE_DRAW = {"OUTPUT": draw_output, "SAVE": draw_save, "MULTIPASS": draw_multipass, "AA": draw_samples,
             "OPTIONS": draw_options, "OVERRIDE": draw_override, "ENGINE": draw_engine}


class BLENDA4D_MT_rs_multipass(bpy.types.Menu):
    bl_idname = "BLENDA4D_MT_rs_multipass"
    bl_label = "Multi-Pass"
    bl_description = "Switch extra image passes on or off"

    def draw(self, context):
        p = context.scene.b4d_render
        self.layout.prop(p, "multipass")
        self.layout.separator()
        for prop, _attr, label in PASSES:
            self.layout.prop(p, prop, text=label)


def draw_page(layout, context):
    scene, wm = context.scene, context.window_manager
    width = context.region.width - 2 * 8 * _s()
    if width < 760 * _s():                       # a narrow area: the lists go above the page instead of beside it
        left, right = layout.column(), None
        _geo["page"], _geo["narrow"] = width, True
    else:
        split = layout.split(factor=0.3)
        left, right = split.column(), False
        _geo["page"], _geo["narrow"] = width * 0.7, False
    top = left.row()
    top.use_property_split = True
    top.use_property_decorate = False
    top.prop(scene.render, "engine", text="Renderer")
    if len(wm.b4d_rs_pages):
        left.template_list(BLENDA4D_UL_render_pages.bl_idname, "", wm, "b4d_rs_pages", wm, "b4d_rs_page", rows=len(PAGES))  # noqa
    row = left.row(align=True)                   # under the page list, as in the reference layout
    sub = row.row(align=True)
    sub.enabled = False                          # Blender has no render effects list to add from
    sub.operator("blenda4d.noop", text="Effect...")
    row.menu(BLENDA4D_MT_rs_multipass.bl_idname, text="Multi-Pass...")
    left.separator(factor=2.0)
    if len(sets(scene)):
        left.template_list(BLENDA4D_UL_render_sets.bl_idname, "", scene, "b4d_rsets", scene, "b4d_rs_index", rows=4)
    else:
        left.operator("blenda4d.rs_add", text="New Render Setting", icon="ADD")
    left.menu(BLENDA4D_MT_render_setting.bl_idname, text="Render Setting...")
    if right is None:
        layout.separator(type="LINE")
        right = layout.column()
    else:
        right = split.column()
    key = current_page(context)
    right.label(text=page_title(scene, key))
    PAGE_DRAW[key](PageCol(right.column()), scene)


class BLENDA4D_PT_render_settings(roles.RolePanel, bpy.types.Panel):
    bl_label = "Render Settings"
    role = ROLE

    def draw(self, context):
        draw_page(self.layout, context)


# --- saving: the active setting keeps what the scene shows -----------------------------------------------------
@bpy.app.handlers.persistent
def _commit_on_save(*_args):
    for scene in bpy.data.scenes:
        try:
            if len(sets(scene)):
                commit(scene)
        except Exception as ex:                  # never stop a save
            print("Blenda 4D: render setting not stored:", ex)


CLASSES = (BLENDA4D_MT_rs_multipass, BLENDA4D_RenderProps, BLENDA4D_RenderSet, BLENDA4D_RenderPage, BLENDA4D_UL_render_sets,
           BLENDA4D_UL_render_pages, BLENDA4D_OT_rs_add, BLENDA4D_OT_rs_duplicate, BLENDA4D_OT_rs_remove,
           BLENDA4D_OT_rs_move, BLENDA4D_OT_rs_rename, BLENDA4D_MT_render_setting, BLENDA4D_OT_render,
           BLENDA4D_OT_render_settings, BLENDA4D_OT_view_tab, BLENDA4D_PT_render_settings)
HANDLERS = (("save_pre", _commit_on_save), ("render_complete", _restore), ("render_cancel", _restore))


def _fill_pages():
    try:
        ensure_pages(bpy.context.window_manager)
    except AttributeError:
        return 0.2
    return None


def register():
    roles.ROLE_FLAGS[ROLE] = "show_properties_render"
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    S = bpy.types.Scene
    S.b4d_render = bpy.props.PointerProperty(description="This scene's render settings as Render Settings shows them", type=BLENDA4D_RenderProps)
    S.b4d_rsets = bpy.props.CollectionProperty(description='The saved render settings of this scene', type=BLENDA4D_RenderSet)
    S.b4d_rs_index = bpy.props.IntProperty(description='The render setting in use', name="Render Setting", default=0, update=_picked)
    S.b4d_rs_loaded = bpy.props.IntProperty(description='Which saved render setting the scene shows (kept so switching never writes old values back)', default=0)
    WM = bpy.types.WindowManager
    WM.b4d_rs_pages = bpy.props.CollectionProperty(description='The pages of Render Settings', type=BLENDA4D_RenderPage)
    WM.b4d_rs_page = bpy.props.IntProperty(description='The page of Render Settings that is shown', name="Section", default=0)
    WM.b4d_rs_advanced = bpy.props.BoolProperty(name="Advanced", default=False,
                                                description="Show the rest of the renderer's settings")
    for name, fn in HANDLERS:
        if fn not in getattr(bpy.app.handlers, name):
            getattr(bpy.app.handlers, name).append(fn)
    bpy.app.timers.register(_fill_pages, first_interval=0.0)


def unregister():
    try:
        for w in bpy.context.window_manager.windows:
            show_view(w.screen)
    except Exception as ex:
        print("Blenda 4D: viewport not put back:", ex)
    try:
        _close_windows()
    except Exception as ex:
        print("Blenda 4D: render settings window not closed:", ex)
    _restore()
    for name, fn in HANDLERS:
        if fn in getattr(bpy.app.handlers, name):
            getattr(bpy.app.handlers, name).remove(fn)
    if bpy.app.timers.is_registered(_fill_pages):
        bpy.app.timers.unregister(_fill_pages)
    for T, names in ((bpy.types.WindowManager, ("b4d_rs_advanced", "b4d_rs_page", "b4d_rs_pages")),
                     (bpy.types.Scene, ("b4d_rs_loaded", "b4d_rs_index", "b4d_rsets", "b4d_render"))):
        for name in names:
            if hasattr(T, name):
                delattr(T, name)
    for cls in reversed(CLASSES):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    roles.ROLE_FLAGS.pop(ROLE, None)
