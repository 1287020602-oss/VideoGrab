$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $ProjectRoot
try {
    $Source = Get-Content "outputs\VideoGrab\app.py" -Raw -Encoding UTF8
    $Version = [regex]::Match($Source, '(?m)^APP_VERSION = "(\d+\.\d+\.\d+)"').Groups[1].Value
    if (-not $Version) { throw "Cannot read product version." }
    $Changes = & git status --porcelain --untracked-files=normal
    if ($LASTEXITCODE -ne 0 -or $Changes) { throw "Commit intentional source changes before packaging. Working tree must be clean." }
    $Expected = Get-Content "work\vendor-sha256.json" -Raw | ConvertFrom-Json
    foreach ($Entry in $Expected.PSObject.Properties) {
        $File = Join-Path $ProjectRoot "outputs\VideoGrab\vendor\$($Entry.Name)"
        if ((Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Entry.Value) { throw "Vendor checksum mismatch: $($Entry.Name)" }
    }
    $ReleaseDir = Join-Path $ProjectRoot "outputs\VideoGrab-release"
    New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
    $Archive = Join-Path $ReleaseDir "VideoGrab-$Version-Source-with-dependencies-x64.zip"
    & git archive --format=zip "--output=$Archive" HEAD
    if ($LASTEXITCODE -ne 0) { throw "Source export failed." }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $Zip = [System.IO.Compression.ZipFile]::Open($Archive, [System.IO.Compression.ZipArchiveMode]::Update)
    try {
        foreach ($Entry in $Expected.PSObject.Properties) {
            $Relative = "outputs/VideoGrab/vendor/$($Entry.Name)"
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($Zip, (Join-Path $ProjectRoot $Relative), $Relative, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
        }
    } finally { $Zip.Dispose() }
    $Artifacts = @("VideoGrab-$Version-Setup-x64.exe", "VideoGrab-$Version-Portable-x64.zip", "VideoGrab-$Version-Source-with-dependencies-x64.zip")
    $Lines = foreach ($Name in $Artifacts) {
        $Hash = Get-FileHash -LiteralPath (Join-Path $ReleaseDir $Name) -Algorithm SHA256
        "$($Hash.Hash.ToLowerInvariant())  $Name"
    }
    [System.IO.File]::WriteAllLines((Join-Path $ReleaseDir "SHA256SUMS.txt"), $Lines, [System.Text.UTF8Encoding]::new($false))
    Write-Output $Archive
} finally { Pop-Location }
