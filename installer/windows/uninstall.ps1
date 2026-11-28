# Blenda 4D uninstaller for Windows.
# Removes the Blenda 4D extension from every Blender 5.2+ found on this PC.
$ErrorActionPreference = "Continue"

Write-Host "==================================================="
Write-Host "  Blenda 4D - uninstaller (Windows) / 卸载程序"
Write-Host "==================================================="
Write-Host ""

$candidates = @()
$candidates += Get-ChildItem "$env:ProgramFiles\Blender Foundation\Blender*\blender.exe" -ErrorAction SilentlyContinue
$candidates += Get-ChildItem "${env:ProgramFiles(x86)}\Blender Foundation\Blender*\blender.exe" -ErrorAction SilentlyContinue
$candidates += Get-ChildItem "$env:LOCALAPPDATA\Programs\Blender*\blender.exe" -ErrorAction SilentlyContinue
$candidates += Get-ChildItem "${env:ProgramFiles(x86)}\Steam\steamapps\common\Blender\blender.exe" -ErrorAction SilentlyContinue
$inPath = Get-Command blender.exe -ErrorAction SilentlyContinue
if ($inPath) { $candidates += Get-Item $inPath.Source }

$seen = @{}
$blenders = @()
foreach ($exe in $candidates) {
    $p = $exe.FullName
    if (-not $seen.ContainsKey($p)) { $seen[$p] = $true; $blenders += $p }
}

$py = @"
import bpy, os, shutil
try:
    bpy.ops.preferences.addon_disable(module='bl_ext.user_default.blenda4d')
except Exception:
    pass
bpy.ops.wm.save_userpref()
cfg = bpy.utils.user_resource('CONFIG')
ext = os.path.join(os.path.dirname(cfg), 'extensions', 'user_default', 'blenda4d')
shutil.rmtree(ext, ignore_errors=True)
print('B4D_REMOVED', ext)
"@

$found = 0
foreach ($exe in $blenders) {
    $verLine = (& $exe -b --version 2>$null | Select-Object -First 1)
    $verText = "$verLine"
    if ($verText -notmatch "Blender (\d+)\.(\d+)") { continue }
    $dir = "$env:APPDATA\Blender Foundation\Blender\$($Matches[1]).$($Matches[2])\extensions\user_default\blenda4d"
    if (-not (Test-Path $dir)) { continue }
    & $exe -b --python-expr $py | Out-Null
    # Blender's stdout/exit code are not trusted (some builds crash on exit and lose them):
    # success is the extension folder being gone.
    if (-not (Test-Path $dir)) {
        $found++
        Write-Host "[OK] $exe - Blenda 4D removed / 已卸载"
    } else {
        Write-Host "[FAIL] $exe - could not remove / 卸载失败"
    }
}

Write-Host ""
if ($found -eq 0) {
    Write-Host "No Blender with Blenda 4D found. / 未找到装有 Blenda 4D 的 Blender。"
} else {
    Write-Host "Done. Your own Blender layouts, files and other add-ons are untouched."
    Write-Host "完成。你自己的 Blender 布局、文件与其他插件不受影响。"
}
Write-Host "==================================================="
Read-Host "Press Enter to close / 按回车关闭"
