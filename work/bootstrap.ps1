param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Version = & $Python -c "import sys; print('.'.join(map(str, sys.version_info[:2])))"
if ($LASTEXITCODE -ne 0 -or $Version -ne "3.12") { throw "Use official Python 3.12 x64 with Tcl/Tk; pass -Python with its executable path." }
& $Python -c "import struct, tkinter; assert struct.calcsize('P') == 8"
if ($LASTEXITCODE -ne 0) { throw "Python must be x64 and include tkinter." }
$Venv = Join-Path $ProjectRoot "work\videograb-venv"
if (-not (Test-Path -LiteralPath (Join-Path $Venv "Scripts\python.exe"))) {
    & $Python -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}
$VenvPython = Join-Path $Venv "Scripts\python.exe"
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements-lock.txt")
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
$Expected = Get-Content (Join-Path $PSScriptRoot "vendor-sha256.json") -Raw | ConvertFrom-Json
foreach ($Entry in $Expected.PSObject.Properties) {
    $File = Join-Path $ProjectRoot "outputs\VideoGrab\vendor\$($Entry.Name)"
    if (-not (Test-Path -LiteralPath $File)) { throw "Missing $File. Restore vendor from the private Release source-with-dependencies zip." }
    if ((Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Entry.Value) { throw "Vendor checksum mismatch: $($Entry.Name)" }
}
Write-Output "VideoGrab development environment is ready."
