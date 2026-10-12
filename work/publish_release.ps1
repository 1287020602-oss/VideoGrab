param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$')][string]$Repository,
    [switch]$SkipBuild
)
$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$GhCommand = Get-Command gh -ErrorAction SilentlyContinue
$Gh = if ($GhCommand) { $GhCommand.Source } else { Join-Path $PSScriptRoot "github-cli\bin\gh.exe" }
if (-not (Test-Path -LiteralPath $Gh)) { throw "Install official GitHub CLI and run gh auth login first." }
function Invoke-Gh {
    $Arguments = $args
    $Result = & $Gh @Arguments
    if ($LASTEXITCODE -ne 0) { throw "GitHub command failed: $($Arguments[0])" }
    return $Result
}
function Invoke-Git {
    $Arguments = $args
    $Result = & git @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Git command failed: $($Arguments[0])" }
    return $Result
}
Push-Location $ProjectRoot
try {
    $Info = (Invoke-Gh @('repo', 'view', $Repository, '--json', 'nameWithOwner,visibility,url')) | ConvertFrom-Json
    if ($Info.visibility -ne 'PRIVATE') { throw "Refusing upload: repository is not private." }
    $Origin = Invoke-Git @('remote', 'get-url', 'origin')
    if ($Origin -notin @("https://github.com/$Repository.git", "https://github.com/$Repository", "git@github.com:$Repository.git")) { throw "origin does not match the selected repository." }
    if (Invoke-Git @('status', '--porcelain', '--untracked-files=normal')) { throw "Commit related source changes before publishing." }
    $Source = Get-Content "outputs\VideoGrab\app.py" -Raw -Encoding UTF8
    $Version = [regex]::Match($Source, '(?m)^APP_VERSION = "(\d+\.\d+\.\d+)"').Groups[1].Value
    if (-not $Version) { throw "Cannot read product version." }
    $Tag = "v$Version"
    $Branch = Invoke-Git @('symbolic-ref', '--short', 'HEAD')
    if (-not $Branch) { throw "Publish from a named branch." }
    if (-not $SkipBuild) { & (Join-Path $PSScriptRoot 'build_release.ps1') }
    & (Join-Path $PSScriptRoot 'package_backup.ps1') | Out-Host
    $ReleaseDir = Join-Path $ProjectRoot 'outputs\VideoGrab-release'
    $Names = @("VideoGrab-$Version-Setup-x64.exe", "VideoGrab-$Version-Portable-x64.zip", "VideoGrab-$Version-Source-with-dependencies-x64.zip", 'SHA256SUMS.txt')
    foreach ($Name in $Names) { if (-not (Test-Path -LiteralPath (Join-Path $ReleaseDir $Name))) { throw "Missing release artifact: $Name" } }
    $ExistingTag = Invoke-Git @('tag', '--list', $Tag)
    if ($ExistingTag) {
        if ((Invoke-Git @('rev-list', '-n', '1', $Tag)) -ne (Invoke-Git @('rev-parse', 'HEAD'))) { throw "Version tag already points at another commit. Increase version." }
    } else { Invoke-Git @('tag', '-a', $Tag, '-m', "VideoGrab $Version") | Out-Host }
    Invoke-Git @('push', 'origin', "HEAD:refs/heads/$Branch") | Out-Host
    Invoke-Git @('push', 'origin', "refs/tags/$Tag") | Out-Host
    $Published = & $Gh release view $Tag --repo $Repository --json isDraft 2>$null
    if ($LASTEXITCODE -eq 0) {
        if (-not ($Published | ConvertFrom-Json).isDraft) { throw "Release is already published. Increase version instead of replacing a release." }
    } else {
        Invoke-Gh @('release', 'create', $Tag, '--repo', $Repository, '--verify-tag', '--draft', '--title', "VideoGrab $Version", '--notes', 'Private backup: Windows x64 installer, portable app, full source with pinned vendor dependencies, and SHA256 checksums. Personal data and credentials are excluded. See README.md for restore/build instructions.') | Out-Host
    }
    # Resume interrupted draft uploads only when existing bytes match the local artifact.
    $Remote = (Invoke-Gh @('api', "repos/$Repository/releases/tags/$Tag")) | ConvertFrom-Json
    foreach ($Name in $Names) {
        $Asset = @($Remote.assets | Where-Object name -EQ $Name)
        $File = Join-Path $ReleaseDir $Name
        $Digest = 'sha256:' + (Get-FileHash -LiteralPath $File -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($Asset.Count) {
            if ($Asset[0].digest -ne $Digest) { throw "Draft contains conflicting artifact: $Name. Not overwriting." }
        } else { Invoke-Gh @('release', 'upload', $Tag, $File, '--repo', $Repository) | Out-Host }
    }
    $Remote = (Invoke-Gh @('api', "repos/$Repository/releases/tags/$Tag")) | ConvertFrom-Json
    foreach ($Name in $Names) {
        $Asset = @($Remote.assets | Where-Object name -EQ $Name)
        $File = Get-Item -LiteralPath (Join-Path $ReleaseDir $Name)
        $Digest = 'sha256:' + (Get-FileHash -LiteralPath $File.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($Asset.Count -ne 1 -or $Asset[0].size -ne $File.Length -or $Asset[0].digest -ne $Digest) { throw "Remote artifact verification failed: $Name. Release remains draft." }
    }
    Invoke-Gh @('release', 'edit', $Tag, '--repo', $Repository, '--draft=false', '--latest') | Out-Host
    Invoke-Gh @('release', 'view', $Tag, '--repo', $Repository, '--json', 'url,isDraft')
} finally { Pop-Location }
