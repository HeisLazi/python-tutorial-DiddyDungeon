[CmdletBinding()]
param(
    [ValidateRange(1, 65535)]
    [int]$BackendPort = 7331,
    [ValidateRange(1, 65535)]
    [int]$FrontendPort = 5173,
    [switch]$AllowStaleCheckout,
    [switch]$SkipFrontendSource
)

# Read-only gate for the manual K&M acceptance. This deliberately performs
# only local Git reads and HTTP GETs; it never writes the save, calls Supabase,
# restarts a runtime or touches either PTY.
$ErrorActionPreference = 'Stop'
$expectedBranch = 'feature/cloud-sync-desktop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Fail([string]$Message) {
    throw "K&M preflight failed: $Message"
}

function Get-Json([string]$Uri) {
    try {
        return Invoke-RestMethod -UseBasicParsing -Uri $Uri -Method Get -TimeoutSec 5
    } catch {
        Fail "could not read $Uri ($($_.Exception.Message))"
    }
}

$branchOutput = & git -C $repoRoot branch --show-current 2>$null
$branchExit = $LASTEXITCODE
$branch = if ($branchExit -eq 0) { ([string]$branchOutput).Trim() } else { '' }
if (-not $AllowStaleCheckout -and $branch -ne $expectedBranch) {
    Fail "checkout branch is '$branch'; expected '$expectedBranch'"
}

$headOutput = & git -C $repoRoot rev-parse --verify --quiet HEAD 2>$null
$headExit = $LASTEXITCODE
$headSha = if ($headExit -eq 0) { ([string]$headOutput).Trim() } else { '' }
if (-not $headSha) {
    Fail 'could not resolve checkout HEAD'
}

$upstreamOutput = & git -C $repoRoot rev-parse --verify --quiet "refs/remotes/origin/$expectedBranch" 2>$null
$upstreamExit = $LASTEXITCODE
$upstreamSha = if ($upstreamExit -eq 0) { ([string]$upstreamOutput).Trim() } else { '' }
if (-not $AllowStaleCheckout -and $upstreamSha -and $headSha -ne $upstreamSha) {
    Fail "HEAD $headSha is not the local origin/$expectedBranch $upstreamSha"
}

$runtime = Get-Json "http://127.0.0.1:$BackendPort/api/runtime"
$repoGit = $runtime.repo_git
if ($repoGit -and $repoGit.branch -and $repoGit.branch -ne $expectedBranch) {
    Fail "backend reports repo branch '$($repoGit.branch)'"
}
if (-not $repoGit -or -not $repoGit.head_sha) {
    Fail 'backend runtime health does not expose repo HEAD identity'
}
if (-not $AllowStaleCheckout -and $upstreamSha -and $repoGit.head_sha -ne $upstreamSha) {
    Fail "backend HEAD $($repoGit.head_sha) does not match origin/$expectedBranch $upstreamSha"
}

# The browser talks to /api through Vite's proxy. Compare that identity with
# the direct backend probe so a stale/mismatched frontend cannot be accepted
# merely because its source contains the expected marker strings.
$frontendRuntime = Get-Json "http://127.0.0.1:$FrontendPort/api/runtime"
$frontendRepoGit = $frontendRuntime.repo_git
if (-not $frontendRepoGit -or -not $frontendRepoGit.head_sha) {
    Fail 'frontend /api proxy does not expose repo HEAD identity'
}
if ($frontendRepoGit.branch -and $frontendRepoGit.branch -ne $repoGit.branch) {
    Fail "frontend /api proxy branch '$($frontendRepoGit.branch)' differs from backend '$($repoGit.branch)'"
}
if ($frontendRepoGit.head_sha -ne $repoGit.head_sha) {
    Fail "frontend /api proxy HEAD $($frontendRepoGit.head_sha) differs from backend $($repoGit.head_sha)"
}
if ($frontendRuntime.state_authority.canonical_path -ne $runtime.state_authority.canonical_path -or
    $frontendRuntime.state_authority.legacy_path -ne $runtime.state_authority.legacy_path) {
    Fail 'frontend /api proxy state paths differ from the backend authority'
}

$authority = $runtime.state_authority
if (-not $authority.canonical_authoritative) {
    Fail 'runtime did not mark one canonical state path authoritative'
}
if ($authority.legacy_authoritative) {
    Fail 'runtime marked the legacy/workspace state path authoritative'
}
if (-not $authority.canonical_path -or -not $authority.legacy_path -or $authority.canonical_path -eq $authority.legacy_path) {
    Fail 'runtime did not expose distinct canonical and legacy state paths'
}

$revision = Get-Json "http://127.0.0.1:$BackendPort/api/state/revision"
if ($null -eq $revision.revision) {
    Fail 'state revision probe returned no revision'
}

if (-not $SkipFrontendSource) {
    try {
        $source = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$FrontendPort/src/AppV2.jsx" -TimeoutSec 5).Content
    } catch {
        Fail "could not read the served AppV2 source on port $FrontendPort ($($_.Exception.Message))"
    }
    if ($source -notmatch 'campaignReady' -or $source -notmatch 'data-react-stat' -or $source -notmatch 'top-stats') {
        Fail 'served AppV2 source is stale or missing the current loading/SVG HUD markers'
    }
    if ($source -match '♥\s*\$\{player\.hp') {
        Fail 'served AppV2 source still contains the old emoji stat renderer'
    }
}

Write-Host 'K&M preflight: GREEN'
Write-Host "Checkout:          $branch @ $headSha"
Write-Host "Backend:           127.0.0.1:$BackendPort"
Write-Host "Frontend:          127.0.0.1:$FrontendPort"
Write-Host "Campaign revision: $($revision.revision)"
Write-Host "Canonical state:   $($authority.canonical_path)"
Write-Host "Legacy evidence:   $($authority.legacy_path) (non-authoritative)"
