param([Parameter(Mandatory = $true)][string]$RequestPath, [Parameter(Mandatory = $true)][string]$ResultPath)
$ErrorActionPreference = 'Stop'
$requestId = ''
$success = $false
$environment = @{}
function Write-AtomicJson([string]$Path, $Value) {
    $temporaryPath = $Path + '.new-' + [guid]::NewGuid().ToString('N')
    [IO.File]::WriteAllText($temporaryPath, ($Value | ConvertTo-Json -Depth 12 -Compress), (New-Object Text.UTF8Encoding($false)))
    try {
        if (Test-Path -LiteralPath $Path) { [IO.File]::Replace($temporaryPath, $Path, [NullString]::Value) }
        else { [IO.File]::Move($temporaryPath, $Path) }
    }
    finally { if (Test-Path -LiteralPath $temporaryPath) { Remove-Item -LiteralPath $temporaryPath -Force } }
}
try {
    if ((Get-Item -LiteralPath $RequestPath).Length -gt 1048576) { throw 'Helper request is too large.' }
    $request = Get-Content -LiteralPath $RequestPath -Raw | ConvertFrom-Json
    $requestId = [string]$request.requestId
    if ($request.protocol -ne 'evejs_launcher_mod_v1') { throw 'Unsupported helper protocol.' }
    $action = [string]$request.action
    if ($action -in @('install', 'prepare_profile')) {
        $handshakePath = Join-Path ([string]$request.runtime.evejsRoot) 'server/src/network/tcp/handshake.js'
        $source = [IO.File]::ReadAllText($handshakePath).Replace("`r`n", "`n")
        $sha256 = [Security.Cryptography.SHA256]::Create()
        try { $hash = ([BitConverter]::ToString($sha256.ComputeHash([Text.Encoding]::UTF8.GetBytes($source)))).Replace('-', '').ToLowerInvariant() }
        finally { $sha256.Dispose() }
        if ($hash -ne '4fc3c37ec83c443c1497a3daba57d7157d05bbe55af3be2d5545b6162398ebc9') { throw 'The installed EveJS login source is not compatible with this mod.' }
        foreach ($name in @('client-ui.py', 'controller.py', 'controller-devices.py', 'controller-feedback.py', 'controller-settings.py', 'preferences.json', 'assets/controller-settings.png', 'runtime/SDL3.dll', 'runtime/SDL-LICENSE.txt')) {
            if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot $name) -PathType Leaf)) { throw "Missing runtime file: $name" }
        }
        if ($action -eq 'install') { Write-AtomicJson (Join-Path $PSScriptRoot 'activation.json') @{ enabled = $true } }
        $environment['CONTROLLER_MOD_DIRECTORY'] = $PSScriptRoot
        $message = 'Controller support will run inside the EVE client at login. Restart the game server when requested.'
    }
    elseif ($action -in @('prepare_disable', 'prepare_remove', 'recover')) {
        Write-AtomicJson (Join-Path $PSScriptRoot 'activation.json') @{ enabled = $false }
        $message = 'Controller support disabled. Restart the game server when requested.'
    }
    else { throw 'Unsupported helper action.' }
    $success = $true
}
catch { $message = $_.Exception.Message }
$state = if ($success) { 'ready' } else { 'failed' }
Write-AtomicJson $ResultPath @{
    protocol = 'evejs_launcher_mod_v1'; requestId = $requestId; success = $success; state = $state
    message = $message; restartRequired = @(); contributions = @(); environment = $environment; arguments = @()
}
if (-not $success) { exit 1 }
