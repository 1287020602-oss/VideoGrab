$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $ProjectRoot "work\videograb-venv\Scripts\python.exe"
$Spec = Join-Path $ProjectRoot "work\VideoGrab.spec"
$BuildDir = Join-Path $ProjectRoot "work\release-build"
$DistDir = Join-Path $ProjectRoot "work\release-dist"
$ReleaseDir = Join-Path $ProjectRoot "outputs\VideoGrab-release"
$SourceText = Get-Content (Join-Path $ProjectRoot "outputs\VideoGrab\app.py") -Raw -Encoding UTF8
$Version = [regex]::Match($SourceText, '(?m)^APP_VERSION = "(\d+\.\d+\.\d+)"').Groups[1].Value
if (-not $Version) { throw "Cannot read product version." }
$PortableZip = Join-Path $ReleaseDir "VideoGrab-$Version-Portable-x64.zip"
$Checksums = Join-Path $ReleaseDir "SHA256SUMS.txt"
$InstallerScript = Join-Path $ProjectRoot "work\VideoGrab.iss"
$ChineseLanguage = Join-Path $ProjectRoot "work\ChineseSimplified.isl"

foreach ($Path in @($Python, $Spec, $InstallerScript, $ChineseLanguage)) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Required build input is missing: $Path"
    }
}

$MobileVersion = [regex]::Match((Get-Content (Join-Path $ProjectRoot "outputs\VideoGrab\mobile\server.py") -Raw), '(?m)^APP_VERSION = "([^"]+)"').Groups[1].Value
$InstallerVersion = [regex]::Match((Get-Content $InstallerScript -Raw), '#define MyAppVersion "([^"]+)"').Groups[1].Value
if ($MobileVersion -ne $Version -or $InstallerVersion -ne $Version) { throw "Desktop, mobile and installer versions must match." }
& $Python (Join-Path $ProjectRoot "work\test_videograb.py")
if ($LASTEXITCODE -ne 0) { throw "Core tests failed." }

foreach ($Target in @($BuildDir, $DistDir)) {
    $FullTarget = [System.IO.Path]::GetFullPath($Target)
    $AllowedParent = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "work")) + [System.IO.Path]::DirectorySeparatorChar
    if (-not $FullTarget.StartsWith($AllowedParent, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean a path outside the project: $FullTarget"
    }
    if (Test-Path -LiteralPath $FullTarget) {
        Remove-Item -LiteralPath $FullTarget -Recurse -Force
    }
}

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null

& $Python -m PyInstaller --noconfirm --clean --distpath $DistDir --workpath $BuildDir $Spec
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed with exit code $LASTEXITCODE"
}

if (Test-Path -LiteralPath $PortableZip) {
    Remove-Item -LiteralPath $PortableZip -Force
}
Compress-Archive -LiteralPath (Join-Path $DistDir "VideoGrab") -DestinationPath $PortableZip -CompressionLevel Optimal

$InnoCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe")
)
$ISCC = $InnoCandidates | Where-Object { $_ -and (Test-Path -LiteralPath $_) } | Select-Object -First 1
if (-not $ISCC) {
    throw "Inno Setup compiler was not found. Install JRSoftware.InnoSetup first."
}

& $ISCC $InstallerScript
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup build failed with exit code $LASTEXITCODE"
}

$Setup = Join-Path $ReleaseDir "VideoGrab-$Version-Setup-x64.exe"
if (-not (Test-Path -LiteralPath $Setup)) {
    throw "Installer output was not created: $Setup"
}

$HashLines = foreach ($Artifact in @($Setup, $PortableZip)) {
    $Hash = Get-FileHash -Algorithm SHA256 -LiteralPath $Artifact
    "$($Hash.Hash.ToLowerInvariant())  $([System.IO.Path]::GetFileName($Artifact))"
}
[System.IO.File]::WriteAllLines($Checksums, $HashLines, [System.Text.UTF8Encoding]::new($false))

Write-Output "Release build complete:"
Write-Output $Setup
Write-Output $PortableZip
Write-Output $Checksums
