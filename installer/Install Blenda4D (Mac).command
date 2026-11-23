#!/bin/bash
# Blenda 4D one-click installer for macOS / Blenda 4D macOS 一键安装
# Lets you pick which Blender 5.2+ installs get the extension (default: all of them).
set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
ZIP="$(ls "$ROOT"/payload/blenda4d-*.zip 2>/dev/null | head -1)"
VERSION="$(basename "$ZIP" .zip | sed 's/^blenda4d-//')"

echo "==================================================="
echo "  Blenda 4D $VERSION - one-click installer (macOS)"
echo "  Blenda 4D $VERSION 一键安装程序 (macOS)"
echo "==================================================="
echo

if [ -z "$ZIP" ] || [ ! -f "$ZIP" ]; then
    echo "[ERROR] No payload/blenda4d-*.zip found next to this script."
    echo "[错误] 未找到安装负载 payload/blenda4d-*.zip。"
    read -n 1 -s -r -p "Press any key to close / 按任意键关闭..."
    exit 1
fi

# --- find Blender 5.2+ ------------------------------------------------------------
shopt -s nullglob
APPS=(); VERS=()
for app in /Applications/Blender*.app "$HOME/Applications/Blender"*.app; do
    bin="$app/Contents/MacOS/Blender"
    [ -x "$bin" ] || continue
    ver_line="$("$bin" --version 2>/dev/null | head -1)"
    ver="$(echo "$ver_line" | sed -E 's/^Blender ([0-9]+\.[0-9]+).*/\1/')"
    major="${ver%%.*}"; minor="${ver##*.}"
    case "$major" in (*[!0-9]*|"") continue;; esac
    case "$minor" in (*[!0-9]*|"") continue;; esac
    if [ "$major" -lt 5 ] || { [ "$major" -eq 5 ] && [ "$minor" -lt 2 ]; }; then
        echo "[SKIP] $app ($ver_line) - needs Blender 5.2+ / 需要 Blender 5.2 及以上"
        continue
    fi
    APPS+=("$app"); VERS+=("$major.$minor")
done

if [ "${#APPS[@]}" -eq 0 ]; then
    echo "No Blender 5.2+ found in /Applications."
    echo "未找到 Blender 5.2 或更高版本。请先安装: https://www.blender.org/download/"
    read -n 1 -s -r -p "Press any key to close / 按任意键关闭..."
    exit 1
fi

# --- choose targets -----------------------------------------------------------------
echo "Found ${#APPS[@]} Blender installation(s) / 找到 ${#APPS[@]} 个 Blender:"
for i in "${!APPS[@]}"; do
    printf "  [%d] Blender %s  -  %s\n" "$((i+1))" "${VERS[$i]}" "${APPS[$i]}"
done
echo
TARGETS=()
if [ "${#APPS[@]}" -eq 1 ]; then
    TARGETS=("${!APPS[@]}")          # only one install: nothing to choose
else
    echo "Install into which one(s)? Type numbers separated by spaces, or just press Enter for ALL."
    echo "安装到哪些版本？输入编号（空格分隔），或直接回车 = 全部安装。"
    read -r -p "> " choice || choice=""
    if [ -z "$choice" ]; then
        TARGETS=("${!APPS[@]}")      # Enter, EOF or no terminal: all of them
    else
        for n in $choice; do
            case "$n" in (*[!0-9]*|"") echo "[SKIP] '$n' is not a number / 不是编号";; esac
            [ -n "$n" ] && [ "$n" -ge 1 ] && [ "$n" -le "${#APPS[@]}" ] && TARGETS+=("$((n-1))")
        done
    fi
fi
if [ "${#TARGETS[@]}" -eq 0 ]; then
    echo "Nothing selected. / 未选择任何版本。"
    read -n 1 -s -r -p "Press any key to close / 按任意键关闭..."
    exit 1
fi
echo

# --- install ------------------------------------------------------------------------
ok=0
for i in "${TARGETS[@]}"; do
    app="${APPS[$i]}"; ver="${VERS[$i]}"; bin="$app/Contents/MacOS/Blender"
    echo "[..] Installing into $app (Blender $ver)"
    echo "     正在安装到 $app (Blender $ver)"
    B4D_ZIP="$ZIP" "$bin" -b --python-expr "import bpy, os; bpy.ops.extensions.package_install_files(filepath=os.environ['B4D_ZIP'], repo='user_default', enable_on_install=True, overwrite=True); bpy.ops.wm.save_userpref()" >/dev/null 2>&1
    # Blender's exit code is not trusted (some builds crash on exit after the work is done):
    # success is the installed manifest carrying this package's version.
    if grep -q "version = \"$VERSION\"" "$HOME/Library/Application Support/Blender/$ver/extensions/user_default/blenda4d/blender_manifest.toml" 2>/dev/null; then
        ok=$((ok+1))
        echo "[OK] Blender $ver - Blenda 4D installed and enabled / 已安装并启用"
    else
        echo "[FAIL] Blender $ver - installation failed / 安装失败"
    fi
    echo
done

echo "==================================================="
echo "Done: $ok of ${#TARGETS[@]} selected Blender installation(s) updated."
echo "完成: 所选 ${#TARGETS[@]} 个 Blender 中 $ok 个已装好。"
echo "Restart Blender and it opens in the Blenda 4D layout."
echo "重启 Blender 即自动进入 Blenda 4D 布局。"
echo "==================================================="
read -n 1 -s -r -p "Press any key to close / 按任意键关闭..."
echo
