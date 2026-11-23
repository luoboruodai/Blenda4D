#!/bin/bash
# Blenda 4D one-click installer for macOS / Blenda 4D macOS 一键安装
# Installs the Blenda 4D extension into every Blender 5.2+ found on this Mac.
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
ZIP="$ROOT/payload/blenda4d-0.1.27.zip"

echo "==================================================="
echo "  Blenda 4D 0.1.27 - one-click installer (macOS)"
echo "  Blenda 4D 0.1.27 一键安装程序 (macOS)"
echo "==================================================="
echo

if [ ! -f "$ZIP" ]; then
    echo "[ERROR] Payload not found: $ZIP"
    echo "[错误] 未找到安装负载: $ZIP"
    read -n 1 -s -r -p "Press any key to close / 按任意键关闭..."
    exit 1
fi

found=0
ok=0
shopt -s nullglob
for app in /Applications/Blender*.app "$HOME/Applications/Blender"*.app; do
    bin="$app/Contents/MacOS/Blender"
    [ -x "$bin" ] || continue
    ver_line="$("$bin" --version 2>/dev/null | head -1)"
    ver="$(echo "$ver_line" | sed -E 's/^Blender ([0-9]+\.[0-9]+).*/\1/')"
    major="${ver%%.*}"; minor="${ver##*.}"
    case "$major" in (*[!0-9]*|"") continue;; esac
    case "$minor" in (*[!0-9]*|"") continue;; esac
    if [ "$major" -lt 5 ] || { [ "$major" -eq 5 ] && [ "$minor" -lt 2 ]; }; then
        echo "[SKIP] $app ($ver_line) - Blenda 4D needs Blender 5.2 or newer / 需要 Blender 5.2 及以上"
        continue
    fi
    found=$((found+1))
    echo "[..] Installing into $app ($ver_line)"
    echo "     正在安装到 $app ($ver_line)"
    B4D_ZIP="$ZIP" "$bin" -b --python-expr "import bpy, os; bpy.ops.extensions.package_install_files(filepath=os.environ['B4D_ZIP'], repo='user_default', enable_on_install=True, overwrite=True); bpy.ops.wm.save_userpref()" >/dev/null 2>&1
    # Blender's exit code is not trusted (some builds crash on exit after the work is done):
    # success is the installed manifest carrying this package's version.
    if grep -q 'version = "0.1.27"' "$HOME/Library/Application Support/Blender/$major.$minor/extensions/user_default/blenda4d/blender_manifest.toml" 2>/dev/null; then
        ok=$((ok+1))
        echo "[OK] Blender $ver - Blenda 4D installed and enabled / 已安装并启用"
    else
        echo "[FAIL] Blender $ver - installation failed, see above / 安装失败"
    fi
    echo
done

echo "==================================================="
if [ "$found" -eq 0 ]; then
    echo "No Blender 5.2+ found in /Applications."
    echo "未在 /Applications 中找到 Blender 5.2 或更高版本。"
    echo "Install Blender first from https://www.blender.org/download/"
else
    echo "Done: $ok of $found Blender installation(s) updated."
    echo "完成: $found 个 Blender 中 $ok 个已装好。"
    echo "Restart Blender and it opens in the Blenda 4D layout."
    echo "重启 Blender 即自动进入 Blenda 4D 布局。"
fi
echo "==================================================="
read -n 1 -s -r -p "Press any key to close / 按任意键关闭..."
echo
