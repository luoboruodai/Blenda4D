# Checks that F1-F4 bring each view back where it was left.
#   Blender -b --factory-startup --python tools/tests/views_engine.py
import sys; import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import bpy
from mathutils import Quaternion, Vector
from blenda4d import views, quadview, viewmenus
class RV:
    def __init__(s): s.view_rotation=Quaternion((1,0,0,0)); s.view_location=Vector(); s.view_distance=10.0; s.view_perspective="PERSP"; s.lock_rotation=False
    def as_pointer(s): return id(s)
class Shade: pass
class SP:
    def __init__(s): s.region_3d=RV(); s.shading=Shade(); s.overlay=Shade(); s.lens=50.0; s.lock_camera=False
class Spaces:
    def __init__(s): s.active=SP()
class Area:
    def __init__(s): s.spaces=Spaces(); s.regions=[]
    def as_pointer(s): return 1
    def tag_redraw(s): pass
def axis_view(window, area, corner):
    rv=area.spaces.active.region_3d; rv.view_rotation=quadview.AXIS_ROTATION[corner].copy(); rv.view_perspective="ORTHO"; rv.lock_rotation=True
quadview._axis_view = axis_view
views._start_perspective = lambda w,a: setattr(a.spaces.active.region_3d, "view_perspective", "PERSP")
a=Area(); rv=a.spaces.active.region_3d
fails=[]
def check(ok,msg):
    print(("ok  " if ok else "FAIL"), msg); ok or fails.append(msg)
orbit=Quaternion((0.8,0.4,0.2,0.4)).normalized(); rv.view_rotation=orbit.copy(); rv.view_location=Vector((1,2,3)); rv.view_distance=7.0
views.switch_single(None,a,"TOP")
check(rv.view_perspective=="ORTHO" and rv.lock_rotation, "F2: top, orthographic, locked")
rv.view_location=Vector((5,5,0)); rv.view_distance=3.0
views.switch_single(None,a,"PERSP")
check(rv.view_perspective=="PERSP" and not rv.lock_rotation, "F1: back to perspective")
check(abs(rv.view_rotation.rotation_difference(orbit).angle)<1e-5 and tuple(rv.view_location)==(1,2,3) and rv.view_distance==7.0, "F1: same angle, place and zoom as before")
views.switch_single(None,a,"TOP")
check(tuple(rv.view_location)==(5,5,0) and rv.view_distance==3.0, "F2 again: Top keeps its own pan and zoom")
views.switch_single(None,a,"FRONT"); views.switch_single(None,a,"RIGHT")
check(quadview.corner_of_single(a)=="RIGHT", "F3: right view")
views.switch_single(None,a,"PERSP")
check(abs(rv.view_rotation.rotation_difference(orbit).angle)<1e-5, "F1 after several side views: perspective still as left")
viewmenus._editor_view[1]={"rot":orbit.copy(),"loc":Vector((1,2,3)),"dist":7.0,"persp":"PERSP","lens":50.0}
rv.view_perspective="CAMERA"
views.switch_single(None,a,"PERSP")
check(rv.view_perspective=="PERSP", "F1 while looking through a camera: back to the viewport's own camera")
print("VIEWS", "PASS" if not fails else "FAIL %d" % len(fails))
