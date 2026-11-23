# SPDX-License-Identifier: GPL-3.0-or-later
"""Blenda 4D: a motion-design layout, managers and workflows for Blender, built from Blender's own UI elements."""
import bpy

from . import settings, switch


def _start():
    try:
        on = settings.get().mode
    except (KeyError, AttributeError):
        on = True
    if on and not switch.is_on():
        switch.set_mode(True)
    return None


@bpy.app.handlers.persistent
def _after_load(*_args):
    if switch.is_on():
        from . import build
        window = bpy.context.window_manager.windows[0] if bpy.context.window_manager.windows else None
        if window is not None and window.workspace and window.workspace.name == switch.WORKSPACE:
            bpy.app.timers.register(lambda: build.rebuild(window) and None, first_interval=0.2)


def register():
    from . import keymap, translations
    translations.register()
    keymap.add_preset_path()
    settings.register()
    switch.register()
    try:                                                  # before Blender first draws its splash
        on = settings.get().mode
    except (KeyError, AttributeError):
        on = True
    switch.splash(on)
    if on:                                                # the Blenda 4D key map, chosen before Blender loads one,
        keymap.choose_at_start()                          # so the splash's Keymap shows it too
    if _after_load not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(_after_load)
    bpy.app.timers.register(_start, first_interval=0.5)


def unregister():
    switch.splash(False)
    if _after_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_after_load)
    switch.unregister()
    settings.unregister()
    from . import keymap, translations
    keymap.remove_preset_path()
    translations.unregister()
