[CmdletBinding()]
param(
    [string]$Workspace,
    [ValidateRange(1, 65535)]
    [int]$BackendPort = 7331,
    [ValidateRange(1, 65535)]
    [int]$FrontendPort = 5173,
    [switch]$NoBrowser,
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

$branch = (& git -C $repoRoot branch --show-current).Trim()
if (-not $AllowOtherBranch -and $branch -ne $expectedBranch) {
    throw "Wrong Quest Lab checkout branch '$branch'. Switch to '$expectedBranch' or pass -AllowOtherBranch explicitly."
}

$upstreamRef = (& git -C $repoRoot rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null).Trim()
if ($upstreamRef -and -not $AllowStaleCheckout) {
    & git -C $repoRoot fetch --quiet origin
    if ($LASTEXITCODE -ne 0) {
        throw "Could not refresh '$upstreamRef'. Re-run with -AllowStaleCheckout only when offline use is intentional."
    }
    $headSha = (& git -C $repoRoot rev-parse HEAD).Trim()
    $upstreamSha = (& git -C $repoRoot rev-parse '@{u}').Trim()
    if ($headSha -ne $upstreamSha) {
        throw "Checkout is not at upstream '$upstreamRef'. Run git pull --ff-only origin $expectedBranch or pass -AllowStaleCheckout explicitly."
    }
}

$progressStatus = (& git -C $repoRoot status --short -- progress.json).Trim()
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

$command = "cd $(Quote-BashLiteral $repoWsl) && exec .venv/bin/python ide/quest.py --workspace $(Quote-BashLiteral $workspaceWsl) --backend-port $BackendPort --frontend-port $FrontendPort"
if ($NoBrowser) { $command += ' --no-browser' }

Write-Host "Quest Lab checkout: $branch"
Write-Host "Canonical state:    $repoWsl/progress.json"
Write-Host "Quest workspace:    $workspaceWsl"
Write-Host "Expected branch:    $expectedBranch"
if ($upstreamRef) { Write-Host "Upstream:           $upstreamRef" }
Write-Host 'PTY mode:            stable (backend reload disabled)'
Write-Host ''

& wsl.exe -d Ubuntu -- bash -lc $command
exit $LASTEXITCODE
