param(
    [ValidateSet('chat', 'generation')]
    [string]$Scenario = 'chat',
    [string]$BaseUrl = 'http://host.docker.internal:8000',
    [string]$Token = ''
)

$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$scriptPath = if ($Scenario -eq 'chat') {
    'eval/load/k6_chat.js'
} else {
    'eval/load/k6_generation_flow.js'
}

$dockerArgs = @(
    'run', '--rm', '-i',
    '-v', "$repoRoot:/work",
    '-w', '/work',
    '-e', "SOVRN_BASE_URL=$BaseUrl"
)

if ($Scenario -eq 'generation') {
    if ([string]::IsNullOrWhiteSpace($Token)) {
        throw 'Generation scenario requires -Token (SOVRN bearer token).'
    }
    $dockerArgs += @('-e', "SOVRN_TOKEN=$Token")
}

$dockerArgs += @('grafana/k6', 'run', $scriptPath)

Write-Host "Running k6 scenario '$Scenario' against $BaseUrl"
& docker @dockerArgs
