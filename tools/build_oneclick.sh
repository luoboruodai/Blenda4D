#!/bin/bash
# Build the universal one-click installer zip (Windows + macOS) from this checkout.
#   tools/build_oneclick.sh /path/to/Blender [output-dir]
# Builds the extension with Blender's own extension builder, stages installer/ +
# payload, and zips the package. The zip is a build artifact: do not commit it.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BLENDER="${1:?usage: tools/build_oneclick.sh /path/to/Blender [output-dir]}"
OUT="${2:-$ROOT/dist}"
VERSION="$(sed -n 's/^version = "\(.*\)"/\1/p' "$ROOT/blenda4d/blender_manifest.toml")"
NAME="Blenda4D-$VERSION-OneClick-WinMac"
STAGE="$(mktemp -d)/$NAME"

mkdir -p "$OUT"
"$BLENDER" -b --factory-startup --command extension build --source-dir "$ROOT/blenda4d" --output-dir "$OUT"

mkdir -p "$STAGE/payload" "$STAGE/windows"
cp "$ROOT/installer/Install Blenda4D (Mac).command" "$STAGE/"
cp "$ROOT/installer/Uninstall Blenda4D (Mac).command" "$STAGE/"
cp "$ROOT/installer/Install Blenda4D (Windows).bat" "$STAGE/"
cp "$ROOT/installer/Uninstall Blenda4D (Windows).bat" "$STAGE/"
cp "$ROOT/installer/README.txt" "$STAGE/"
cp "$ROOT/installer/windows/install.ps1" "$ROOT/installer/windows/uninstall.ps1" "$STAGE/windows/"
cp "$OUT/blenda4d-$VERSION.zip" "$STAGE/payload/"
chmod +x "$STAGE"/*.command

cd "$(dirname "$STAGE")"
rm -f "$OUT/$NAME.zip"
COPYFILE_DISABLE=1 zip -r -X -q "$OUT/$NAME.zip" "$NAME"
shasum -a 256 "$OUT/$NAME.zip"
echo "built: $OUT/$NAME.zip"
