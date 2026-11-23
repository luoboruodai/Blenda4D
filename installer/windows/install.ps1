# Blenda 4D one-click installer for Windows.
# Installs the Blenda 4D extension into every Blender 5.2+ found on this PC.
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$zip = Join-Path $root "payload\blenda4d-0.1.27.zip"

Write-Host "==================================================="
Write-Host "  Blenda 4D 0.1.27 - one-click installer (Windows)"
Write-Host "  Blenda 4D 0.1.27 一键安装程序 (Windows)"
Write-Host "==================================================="
Write-Host ""

if (-not (Test-Path $zip)) {
    Write-Host "[ERROR] Payload not found: $zip"
    Write-Host "[错误] 未找到安装负载: $zip"
    Read-Host "Press Enter to close / 按回车关闭"
    exit 1
}

# --- find blender.exe -------------------------------------------------------------
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

if ($blenders.Count -eq 0) {
    Write-Host "No Blender found. Install Blender 5.2+ from https://www.blender.org/download/"
    Write-Host "未找到 Blender。请先从 https://www.blender.org/download/ 安装 Blender 5.2 或更高版本。"
    Write-Host "(Microsoft Store 版 Blender 不在支持范围内 / The Microsoft Store build is not supported.)"
    Read-Host "Press Enter to close / 按回车关闭"
    exit 1
}

$env:B4D_ZIP = $zip
$ok = 0
$total = 0
foreach ($exe in $blenders) {
    $verLine = (& $exe -b --version 2>$null | Select-Object -First 1)
    $verText = "$verLine"
    if ($verText -notmatch "Blender (\d+)\.(\d+)") {
        Write-Host "[SKIP] $exe (could not read version)"
        continue
    }
    $major = [int]$Matches[1]; $minor = [int]$Matches[2]
    if ($major -lt 5 -or ($major -eq 5 -and $minor -lt 2)) {
        Write-Host "[SKIP] $exe - Blenda 4D needs Blender 5.2 or newer / 需要 Blender 5.2 及以上"
        continue
    }
    $total++
    Write-Host "[..] Installing into $exe (Blender $major.$minor)"
    Write-Host "     正在安装 / installing..."
    $expr = "import bpy, os; bpy.ops.extensions.package_install_files(filepath=os.environ['B4D_ZIP'], repo='user_default', enable_on_install=True, overwrite=True); bpy.ops.wm.save_userpref()"
    & $exe -b --python-expr $expr | Out-Null
    # Blender's exit code is not trusted (some builds crash on exit after the work is done):
    # success is the installed manifest carrying this package's version.
    $marker = "$env:APPDATA\Blender Foundation\Blender\$major.$minor\extensions\user_default\blenda4d\blender_manifest.toml"
    $installed = (Test-Path $marker) -and ((Get-Content $marker -Raw) -match 'version = "0\.1\.27"')
    if ($installed) {
        $ok++
        Write-Host "[OK] Blender $major.$minor - Blenda 4D installed and enabled / 已安装并启用"
    } else {
        Write-Host "[FAIL] Blender $major.$minor - installation failed / 安装失败"
    }
    Write-Host ""
}

Write-Host "==================================================="
Write-Host "Done: $ok of $total Blender installation(s) updated."
Write-Host "完成: $total 个 Blender 中 $ok 个已装好。"
Write-Host "Restart Blender and it opens in the Blenda 4D layout."
Write-Host "重启 Blender 即自动进入 Blenda 4D 布局。"
Write-Host "==================================================="
Read-Host "Press Enter to close / 按回车关闭"
