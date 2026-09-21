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

# Friendly root-level entry point. Keep the guarded launcher in tools/ as the
# source of truth so this shortcut cannot bypass branch, dependency, state or
# stable-PTY checks.
$launcher = Join-Path $PSScriptRoot 'tools/questlab-launch.ps1'
if (-not (Test-Path -LiteralPath $launcher)) {
    throw "Quest Lab launcher is missing: $launcher"
}

$launcherParams = @{
    BackendPort = $BackendPort
    FrontendPort = $FrontendPort
}
if ($Workspace) { $launcherParams.Workspace = $Workspace }
if ($NoBrowser) { $launcherParams.NoBrowser = $true }
if ($MigrateLocalState) { $launcherParams.MigrateLocalState = $true }
if ($AllowOtherBranch) { $launcherParams.AllowOtherBranch = $true }
if ($AllowStaleCheckout) { $launcherParams.AllowStaleCheckout = $true }

& $launcher @launcherParams
exit $LASTEXITCODE
