param(
    [string]$BaseUrl = $env:SOVRN_BASE_URL,
    [string]$Token = $env:SOVRN_TOKEN,
    [string]$ProjectId = $env:SOVRN_PROJECT_ID,
    [string]$GenerationId = $env:SOVRN_GENERATION_ID,
    [string]$Entrypoint = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_ENTRYPOINT)) { 'index.html' } else { $env:SOVRN_ENTRYPOINT }),
    [int]$Iterations = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_PREVIEW_BENCH_ITERATIONS)) { 30 } else { [int]$env:SOVRN_PREVIEW_BENCH_ITERATIONS }),
    [int]$Warmup = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_PREVIEW_BENCH_WARMUP)) { 3 } else { [int]$env:SOVRN_PREVIEW_BENCH_WARMUP }),
    [int]$PollIntervalMs = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_PREVIEW_BENCH_POLL_MS)) { 250 } else { [int]$env:SOVRN_PREVIEW_BENCH_POLL_MS }),
    [int]$StreamTimeoutMs = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_PREVIEW_BENCH_STREAM_TIMEOUT_MS)) { 6000 } else { [int]$env:SOVRN_PREVIEW_BENCH_STREAM_TIMEOUT_MS }),
    [int]$RequestTimeoutMs = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_PREVIEW_BENCH_REQUEST_TIMEOUT_MS)) { 15000 } else { [int]$env:SOVRN_PREVIEW_BENCH_REQUEST_TIMEOUT_MS }),
    [double]$TargetP95Ms = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_PREVIEW_TARGET_P95_MS)) { 1500 } else { [double]$env:SOVRN_PREVIEW_TARGET_P95_MS }),
    [string]$OutputPath = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_PREVIEW_BENCH_OUTPUT)) { 'eval/load/phase2_preview_latency_report.json' } else { $env:SOVRN_PREVIEW_BENCH_OUTPUT }),
    [string]$PythonCommand = 'py',
    [string]$PythonSelector = '-3.11'
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    throw 'Missing -BaseUrl or SOVRN_BASE_URL.'
}
if ([string]::IsNullOrWhiteSpace($Token)) {
    throw 'Missing -Token or SOVRN_TOKEN.'
}
if ([string]::IsNullOrWhiteSpace($ProjectId)) {
    throw 'Missing -ProjectId or SOVRN_PROJECT_ID.'
}

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$reportPath = Join-Path $repoRoot $OutputPath

$scriptArgs = @(
    'eval/load/preview_latency_benchmark.py',
    '--base-url', $BaseUrl,
    '--token', $Token,
    '--project-id', $ProjectId,
    '--entrypoint', $Entrypoint,
    '--iterations', $Iterations,
    '--warmup', $Warmup,
    '--poll-interval-ms', $PollIntervalMs,
    '--stream-timeout-ms', $StreamTimeoutMs,
    '--request-timeout-ms', $RequestTimeoutMs,
    '--target-p95-ms', $TargetP95Ms,
    '--output', $OutputPath
)

if (-not [string]::IsNullOrWhiteSpace($GenerationId)) {
    $scriptArgs += @('--generation-id', $GenerationId)
}

Write-Host "Running preview latency benchmark against $BaseUrl"
Write-Host "Project: $ProjectId"
Write-Host "Output: $OutputPath"

Push-Location -LiteralPath $repoRoot
try {
    & $PythonCommand $PythonSelector @scriptArgs
    if ($LASTEXITCODE -ne 0) {
        throw "Benchmark process exited with code $LASTEXITCODE"
    }
} finally {
    Pop-Location
}

if (-not (Test-Path -LiteralPath $reportPath)) {
    throw "Expected report file not found: $reportPath"
}

$report = Get-Content -LiteralPath $reportPath -Raw | ConvertFrom-Json
if ($null -eq $report.summary) {
    throw "Report summary missing in: $reportPath"
}

Write-Host ''
Write-Host 'Parsed Summary'
Write-Host "- successful: $($report.summary.successful)/$($report.summary.count)"
Write-Host "- p50 total: $([double]$report.summary.p50_total_ms) ms"
Write-Host "- p95 total: $([double]$report.summary.p95_total_ms) ms"
Write-Host "- p99 total: $([double]$report.summary.p99_total_ms) ms"
Write-Host "- p95 stream first update: $([double]$report.summary.p95_stream_first_update_ms) ms"
Write-Host "- gate passed: $($report.passed)"

