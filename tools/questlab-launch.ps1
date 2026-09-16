[CmdletBinding()]
param(
    [string]$Workspace,
    [ValidateRange(1, 65535)]
    [int]$BackendPort = 7331,
    [ValidateRange(1, 65535)]
    [int]$FrontendPort = 5173,
    [switch]$NoBrowser,
    [switch]$MigrateLocalState,
    [switch]$AllowOtherBranch,
    [switch]$AllowStaleCheckout
)

$ErrorActionPreference = 'Stop'
$expectedBranch = 'feature/cloud-sync-desktop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Quote-BashLiteral([string]$Value) {
    # Keep spaces and punctuation in Windows/OneDrive paths safe when the
    # command is passed through bash -lc.
    $apostrophe = [char]39
    $replacement = [string]$apostrophe + [char]92 + [string]$apostrophe + [string]$apostrophe
    return [string]$apostrophe + $Value.Replace([string]$apostrophe, $replacement) + [string]$apostrophe
}

function Require-Path([string]$Path, [string]$Description) {
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Description is missing: $Path`nRun the setup commands in FRIEND_ONBOARDING.md first."
    }
}

Require-Path (Join-Path $repoRoot 'ide/quest.py') 'Quest Lab launcher'
Require-Path (Join-Path $repoRoot '.venv/bin/python') 'WSL Python environment'
Require-Path (Join-Path $repoRoot 'ide/frontend/node_modules') 'frontend dependencies'

$branchOutput = & git -C $repoRoot branch --show-current
$branchExit = $LASTEXITCODE
$branch = if ($branchExit -eq 0) { ([string]$branchOutput).Trim() } else { '' }
if (-not $AllowOtherBranch -and $branch -ne $expectedBranch) {
    throw "Wrong Quest Lab checkout branch '$branch'. Switch to '$expectedBranch' or pass -AllowOtherBranch explicitly."
}

$upstreamRefOutput = if ($branch) { & git -C $repoRoot for-each-ref --format='%(upstream:short)' "refs/heads/$branch" } else { @() }
$upstreamRefExit = $LASTEXITCODE
$upstreamRef = if ($upstreamRefExit -eq 0) { ([string]$upstreamRefOutput).Trim() } else { '' }
if ($upstreamRef -and -not $AllowStaleCheckout) {
    & git -C $repoRoot fetch --quiet origin
    if ($LASTEXITCODE -ne 0) {
        throw "Could not refresh '$upstreamRef'. Re-run with -AllowStaleCheckout only when offline use is intentional."
    }
    $headOutput = & git -C $repoRoot rev-parse --verify --quiet HEAD
    $headExit = $LASTEXITCODE
    $headSha = if ($headExit -eq 0) { ([string]$headOutput).Trim() } else { '' }
    $upstreamOutput = & git -C $repoRoot rev-parse --verify --quiet "refs/remotes/$upstreamRef"
    $upstreamExit = $LASTEXITCODE
    $upstreamSha = if ($upstreamExit -eq 0) { ([string]$upstreamOutput).Trim() } else { '' }
    if (-not $headSha -or -not $upstreamSha) {
        throw "Could not resolve checkout or upstream identity for '$upstreamRef'. Re-run with -AllowStaleCheckout only when offline use is intentional."
    }
    if ($headSha -ne $upstreamSha) {
        throw "Checkout is not at upstream '$upstreamRef'. Run git pull --ff-only origin $expectedBranch or pass -AllowStaleCheckout explicitly."
    }
}

$progressStatus = ([string](& git -C $repoRoot status --short -- progress.json)).Trim()
if ($progressStatus) {
    Write-Warning 'Canonical progress.json has local player-state changes; the launcher will not overwrite or reconcile them.'
}

if (-not $Workspace) {
    $Workspace = $repoRoot
} else {
    $Workspace = (Resolve-Path -LiteralPath $Workspace).Path
}
Require-Path $Workspace 'Quest workspace'

$repoWsl = (& wsl.exe -d Ubuntu -- wslpath -a -- $repoRoot).Trim()
$workspaceWsl = (& wsl.exe -d Ubuntu -- wslpath -a -- $Workspace).Trim()
if (-not $repoWsl -or -not $workspaceWsl) {
    throw 'Could not convert the launcher paths to WSL paths. Confirm that Ubuntu/WSL is installed.'
}

# Run the launcher as a module so Python can resolve the repository's `ide`
# package even when this command is invoked from a mounted Windows checkout.
$command = "cd $(Quote-BashLiteral $repoWsl) && exec env PYTHONPATH=. .venv/bin/python -m ide.quest --workspace $(Quote-BashLiteral $workspaceWsl) --backend-port $BackendPort --frontend-port $FrontendPort"
if ($NoBrowser) { $command += ' --no-browser' }
if ($MigrateLocalState) { $command += ' --use-local-state' }

Write-Host "Quest Lab checkout: $branch"
Write-Host "Canonical state:    $repoWsl/progress.json"
Write-Host "Quest workspace:    $workspaceWsl"
Write-Host "Expected branch:    $expectedBranch"
if ($upstreamRef) { Write-Host "Upstream:           $upstreamRef" }
Write-Host 'PTY mode:            stable (backend reload disabled)'
if ($MigrateLocalState) { Write-Host 'Local custody:       review preview and type MIGRATE_LOCAL_STATE when prompted' }
Write-Host ''

& wsl.exe -d Ubuntu -- bash -lc $command
exit $LASTEXITCODE
