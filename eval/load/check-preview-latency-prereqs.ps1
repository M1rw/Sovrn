param(
    [string]$BaseUrl = $env:SOVRN_BASE_URL,
    [int]$TimeoutSec = 5
)

$ErrorActionPreference = 'Stop'

$requiredEnv = @('SOVRN_BASE_URL', 'SOVRN_TOKEN', 'SOVRN_PROJECT_ID')
$missingEnv = @()

Write-Host 'Preview latency benchmark prerequisite check'
Write-Host '------------------------------------------'

foreach ($name in $requiredEnv) {
    $present = Test-Path "Env:$name"
    Write-Host ("{0}: {1}" -f $name, $(if ($present) { 'Present' } else { 'Missing' }))
    if (-not $present) {
        $missingEnv += $name
    }
}

$healthCandidates = @('http://localhost:8000', 'http://localhost')
if (-not [string]::IsNullOrWhiteSpace($BaseUrl)) {
    $healthCandidates = @($BaseUrl.TrimEnd('/')) + $healthCandidates
}

$reachableBaseUrl = $null
Write-Host ''
Write-Host 'Health checks:'
foreach ($candidate in $healthCandidates | Select-Object -Unique) {
    $healthUrl = "$candidate/health"
    try {
        $response = Invoke-WebRequest -Uri $healthUrl -TimeoutSec $TimeoutSec -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host ("OK: {0}" -f $healthUrl)
            if ($null -eq $reachableBaseUrl) {
                $reachableBaseUrl = $candidate
            }
        } else {
            Write-Host ("FAIL: {0} (HTTP {1})" -f $healthUrl, $response.StatusCode)
        }
    } catch {
        Write-Host ("FAIL: {0} ({1})" -f $healthUrl, $_.Exception.Message)
    }
}

Write-Host ''
if ($missingEnv.Count -gt 0) {
    Write-Host ("BLOCKED: missing environment variables: {0}" -f ($missingEnv -join ', '))
    exit 2
}

if ($null -eq $reachableBaseUrl) {
    Write-Host 'BLOCKED: no reachable /health endpoint found for configured or local base URLs.'
    exit 3
}

Write-Host ("READY: prerequisites satisfied. Suggested BaseUrl: {0}" -f $reachableBaseUrl)
exit 0
