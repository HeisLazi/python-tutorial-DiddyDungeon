[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path (Get-Location) 'questlab-bundles'),
    [switch]$KeepStaging,
    [string[]]$IgnoreUntrackedPath = @()
)

$ErrorActionPreference = 'Stop'
$expectedBranch = 'feature/cloud-sync-desktop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Require-Command([string]$Name) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Quest Lab packaging requires '$Name' on PATH."
    }
}

Require-Command 'git'
Require-Command 'tar'
Require-Command 'Compress-Archive'

$branch = (& git -C $repoRoot branch --show-current).Trim()
if ($branch -ne $expectedBranch) {
    throw "Wrong Quest Lab checkout branch '$branch'. Switch to '$expectedBranch' before packaging."
}

# Keep non-ASCII user-owned path names readable so an exact ignore path can be
# compared without decoding Git's quoted octal representation.
$dirty = @(& git -c core.quotePath=false -C $repoRoot status --porcelain=v1)
$ignoredUntracked = @{}
foreach ($candidate in $IgnoreUntrackedPath) {
    if ([string]::IsNullOrWhiteSpace($candidate)) {
        throw 'IgnoreUntrackedPath cannot be empty.'
    }
    $candidatePath = [System.IO.Path]::GetFullPath((Join-Path $repoRoot $candidate))
    $repoPrefix = $repoRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar, [System.IO.Path]::AltDirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
    if ($candidatePath -eq $repoRoot -or -not $candidatePath.StartsWith($repoPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "IgnoreUntrackedPath must stay inside the repository: $candidate"
    }
    if (-not (Test-Path -LiteralPath $candidatePath)) {
        throw "IgnoreUntrackedPath does not exist: $candidate"
    }
    $relativeCandidate = [System.IO.Path]::GetRelativePath($repoRoot, $candidatePath).Replace('\', '/')
    $trackedCandidate = @(& git -C $repoRoot ls-files --error-unmatch -- $relativeCandidate 2>$null)
    if ($LASTEXITCODE -eq 0 -and $trackedCandidate.Count -gt 0) {
        throw "IgnoreUntrackedPath must be untracked: $candidate"
    }
    $ignoredUntracked[$relativeCandidate] = $true
}
$unexpected = @($dirty | Where-Object {
    # These are player/workspace files, not committed distribution source.
    # They must never enter the bundle, but their presence must not prevent a
    # friend package from being built.
    $statusLine = $_
    $normalizedStatus = if ($statusLine) { $statusLine.Replace('\', '/') } else { '' }
    $explicitlyIgnored = @($ignoredUntracked.Keys | Where-Object { $normalizedStatus.Contains($_) }).Count -gt 0
    $statusLine -and -not $explicitlyIgnored -and $statusLine -notmatch '(^|\s)(progress\.json|tutor\.py|dungeon\.py)$' -and $statusLine -notmatch '^\?\? notes(?:/|\\)'
})
if ($unexpected.Count -gt 0) {
    throw "Refusing to package a checkout with uncommitted source changes:`n$($unexpected -join "`n")"
}

$head = (& git -C $repoRoot rev-parse HEAD).Trim()
$shortHead = (& git -C $repoRoot rev-parse --short HEAD).Trim()
$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $outputRoot -Force | Out-Null
$bundleName = "QuestLab-$shortHead"
$bundleDirectory = Join-Path $outputRoot $bundleName
if (Test-Path -LiteralPath $bundleDirectory) {
    throw "Bundle already exists: $bundleDirectory. Choose another output directory."
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("questlab-package-" + [guid]::NewGuid().ToString('N'))
$archive = Join-Path $tempRoot 'source.tar'
$staging = Join-Path $tempRoot 'staging'
New-Item -ItemType Directory -Path $staging -Force | Out-Null

try {
    # Archive HEAD, never the working tree: uncommitted progress.json,
    # untracked tutor.py/dungeon.py and student notes can therefore never leak
    # into a friend bundle.
    & git -C $repoRoot archive --format=tar --output=$archive HEAD
    if ($LASTEXITCODE -ne 0) { throw 'git archive failed.' }
    & tar -xf $archive -C $staging
    if ($LASTEXITCODE -ne 0) { throw 'tar extraction failed.' }

    # A tracked starter progress.json is still player-state data. Remove all
    # player-owned save/notebook paths from the staging tree before the friend
    # bundle is copied or zipped; git archive alone cannot distinguish a
    # committed baseline save from source. The live checkout and its save are
    # never touched here.
    $protectedPackagePaths = @('progress.json', 'tutor.py', 'dungeon.py', 'notes')
    foreach ($relativePath in $protectedPackagePaths) {
        $protectedPath = Join-Path $staging $relativePath
        if (Test-Path -LiteralPath $protectedPath) {
            Remove-Item -LiteralPath $protectedPath -Recurse -Force
        }
    }
    $leakedProtectedPath = @($protectedPackagePaths | Where-Object { Test-Path -LiteralPath (Join-Path $staging $_) })
    if ($leakedProtectedPath.Count -gt 0) {
        throw "Refusing to package player-owned paths: $($leakedProtectedPath -join ', ')"
    }

    $manifest = @(
        'Quest Lab local-first bundle',
        "Branch: $expectedBranch",
        "Source HEAD: $head",
        '',
        'This bundle contains committed source only.',
        'Player state, tutor.py, dungeon.py and notes are local to the checkout and are never copied between devices.',
        'Follow FRIEND_ONBOARDING.md for WSL setup and the guarded launcher.',
        'Do not reuse node_modules from another operating system; run npm ci inside WSL.'
    ) -join [Environment]::NewLine
    Set-Content -LiteralPath (Join-Path $staging 'QUESTLAB_BUNDLE.txt') -Value $manifest -Encoding UTF8

    # Keep the archive self-contained but omit platform-specific dependency
    # trees and local caches; the onboarding flow installs them on the target.
    New-Item -ItemType Directory -Path $bundleDirectory -Force | Out-Null
    Copy-Item -Path (Join-Path $staging '*') -Destination $bundleDirectory -Recurse -Force
    $zipPath = Join-Path $outputRoot "$bundleName.zip"
    Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $zipPath -CompressionLevel Optimal

    Write-Host "Quest Lab bundle created: $bundleDirectory"
    Write-Host "Quest Lab zip created:     $zipPath"
    Write-Host "Source HEAD:               $head"
}
finally {
    if (-not $KeepStaging -and (Test-Path -LiteralPath $tempRoot)) {
        [System.IO.Directory]::Delete($tempRoot, $true)
    } elseif ($KeepStaging) {
        Write-Host "Staging retained:           $tempRoot"
    }
}
