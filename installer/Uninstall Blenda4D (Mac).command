#!/bin/bash
# Blenda 4D uninstaller for macOS / Blenda 4D macOS 卸载程序
# Removes the Blenda 4D extension from every Blender 5.2+ found on this Mac.
set -u
echo "==================================================="
echo "  Blenda 4D - uninstaller (macOS) / 卸载程序"
echo "==================================================="
echo
PY='
import bpy, os, shutil
try:
    bpy.ops.preferences.addon_disable(module="bl_ext.user_default.blenda4d")
except Exception:
    pass
bpy.ops.wm.save_userpref()
cfg = bpy.utils.user_resource("CONFIG")
ext = os.path.join(os.path.dirname(cfg), "extensions", "user_default", "blenda4d")
shutil.rmtree(ext, ignore_errors=True)
print("B4D_REMOVED", ext)
'
found=0
shopt -s nullglob
for app in /Applications/Blender*.app "$HOME/Applications/Blender"*.app; do
    bin="$app/Contents/MacOS/Blender"
    [ -x "$bin" ] || continue
    ver_line="$("$bin" --version 2>/dev/null | head -1)"
    ver="$(echo "$ver_line" | sed -E 's/^Blender ([0-9]+\.[0-9]+).*/\1/')"
    major="${ver%%.*}"; minor="${ver##*.}"
    case "$major" in (*[!0-9]*|"") continue;; esac
    case "$minor" in (*[!0-9]*|"") continue;; esac
    dir="$HOME/Library/Application Support/Blender/$major.$minor/extensions/user_default/blenda4d"
    [ -d "$dir" ] || continue
    "$bin" -b --python-expr "$PY" >/dev/null 2>&1
    # Blender's stdout/exit code are not trusted (some builds crash on exit and lose them):
    # success is the extension folder being gone.
    if [ ! -d "$dir" ]; then
        found=$((found+1))
        echo "[OK] $app ($ver_line) - Blenda 4D removed / 已卸载"
    else
        echo "[FAIL] $app ($ver_line) - could not remove / 卸载失败"
    fi
done
echo
if [ "$found" -eq 0 ]; then
    echo "No Blender with Blenda 4D found. / 未找到装有 Blenda 4D 的 Blender。"
else
    echo "Done. Your own Blender layouts, files and other add-ons are untouched."
    echo "完成。你自己的 Blender 布局、文件与其他插件不受影响。"
fi
echo "==================================================="
read -n 1 -s -r -p "Press any key to close / 按任意键关闭..."
echo
