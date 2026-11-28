# Blenda 4D one-click installer for Windows.
# Lets you pick which Blender 5.2+ installs get the extension (default: all of them).
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $PSScriptRoot
$zip = Get-ChildItem (Join-Path $root "payload\blenda4d-*.zip") -ErrorAction SilentlyContinue | Select-Object -First 1
$version = if ($zip) { $zip.BaseName -replace "^blenda4d-", "" } else { "" }

Write-Host "==================================================="
Write-Host "  Blenda 4D $version - one-click installer (Windows)"
Write-Host "  Blenda 4D $version 一键安装程序 (Windows)"
Write-Host "==================================================="
Write-Host ""

if (-not $zip) {
    Write-Host "[ERROR] No payload\blenda4d-*.zip found next to this script."
    Write-Host "[错误] 未找到安装负载 payload\blenda4d-*.zip。"
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

$apps = @(); $vers = @()
foreach ($exe in $blenders) {
    $verLine = (& $exe -b --version 2>$null | Select-Object -First 1)
    $verText = "$verLine"
    if ($verText -notmatch "Blender (\d+)\.(\d+)") { continue }
    $major = [int]$Matches[1]; $minor = [int]$Matches[2]
    if ($major -lt 5 -or ($major -eq 5 -and $minor -lt 2)) {
        Write-Host "[SKIP] $exe - needs Blender 5.2+ / 需要 Blender 5.2 及以上"
        continue
    }
    $apps += $exe; $vers += "$major.$minor"
}

if ($apps.Count -eq 0) {
    Write-Host "No Blender 5.2+ found. Install it from https://www.blender.org/download/"
    Write-Host "未找到 Blender 5.2 或更高版本。请先安装: https://www.blender.org/download/"
    Write-Host "(The Microsoft Store build is not supported / 应用商店版不受支持)"
    Read-Host "Press Enter to close / 按回车关闭"
    exit 1
}

# --- choose targets -----------------------------------------------------------------
Write-Host "Found $($apps.Count) Blender installation(s) / 找到 $($apps.Count) 个 Blender:"
for ($i = 0; $i -lt $apps.Count; $i++) {
    Write-Host ("  [{0}] Blender {1}  -  {2}" -f ($i + 1), $vers[$i], $apps[$i])
}
Write-Host ""

$targets = @()
if ($apps.Count -eq 1) {
    $targets = 0..($apps.Count - 1)
} else {
    Write-Host "Install into which one(s)? Type numbers separated by spaces, or just press Enter for ALL."
    Write-Host "安装到哪些版本？输入编号（空格分隔），或直接回车 = 全部安装。"
    $choice = Read-Host ">"
    if ([string]::IsNullOrWhiteSpace($choice)) {
        $targets = 0..($apps.Count - 1)
    } else {
        foreach ($n in ($choice -split "\s+")) {
            $num = 0
            if ([int]::TryParse($n, [ref]$num) -and $num -ge 1 -and $num -le $apps.Count) {
                $targets += ($num - 1)
            } else {
                Write-Host "[SKIP] '$n' is not a valid number / 无效编号"
            }
        }
    }
}
if ($targets.Count -eq 0) {
    Write-Host "Nothing selected. / 未选择任何版本。"
    Read-Host "Press Enter to close / 按回车关闭"
    exit 1
}
Write-Host ""

# --- install ------------------------------------------------------------------------
$env:B4D_ZIP = $zip.FullName
$expr = "import bpy, os; bpy.ops.extensions.package_install_files(filepath=os.environ['B4D_ZIP'], repo='user_default', enable_on_install=True, overwrite=True); bpy.ops.wm.save_userpref()"
$ok = 0
foreach ($i in $targets) {
    $exe = $apps[$i]; $ver = $vers[$i]
    Write-Host "[..] Installing into $exe (Blender $ver)"
    Write-Host "     正在安装 / installing..."
    & $exe -b --python-expr $expr | Out-Null
    # Blender's exit code is not trusted (some builds crash on exit after the work is done):
    # success is the installed manifest carrying this package's version.
    $marker = "$env:APPDATA\Blender Foundation\Blender\$ver\extensions\user_default\blenda4d\blender_manifest.toml"
    $installed = (Test-Path $marker) -and ((Get-Content $marker -Raw) -match ('version = "' + [regex]::Escape($version) + '"'))
    if ($installed) {
        $ok++
        Write-Host "[OK] Blender $ver - Blenda 4D installed and enabled / 已安装并启用"
    } else {
        Write-Host "[FAIL] Blender $ver - installation failed / 安装失败"
    }
    Write-Host ""
}

Write-Host "==================================================="
Write-Host "Done: $ok of $($targets.Count) selected Blender installation(s) updated."
Write-Host "完成: 所选 $($targets.Count) 个 Blender 中 $ok 个已装好。"
Write-Host "Restart Blender and it opens in the Blenda 4D layout."
Write-Host "重启 Blender 即自动进入 Blenda 4D 布局。"
Write-Host "==================================================="
Read-Host "Press Enter to close / 按回车关闭"
