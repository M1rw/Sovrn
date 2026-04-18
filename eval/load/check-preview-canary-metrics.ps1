param(
    [string]$WebBaseUrl = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_WEB_BASE_URL)) { 'http://localhost:3000' } else { $env:SOVRN_WEB_BASE_URL }),
    [double]$MaxPreviewRenderP95Ms = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_PREVIEW_TARGET_P95_MS)) { 1500 } else { [double]$env:SOVRN_PREVIEW_TARGET_P95_MS }),
    [int]$MinStreamUpdateCount = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_PREVIEW_MIN_STREAM_UPDATES)) { 1 } else { [int]$env:SOVRN_PREVIEW_MIN_STREAM_UPDATES }),
    [int]$MaxStreamReconnectCount = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_PREVIEW_MAX_STREAM_RECONNECTS)) { 10 } else { [int]$env:SOVRN_PREVIEW_MAX_STREAM_RECONNECTS }),
    [int]$MaxRuntimeRestartCount = $(if ([string]::IsNullOrWhiteSpace($env:SOVRN_PREVIEW_MAX_RUNTIME_RESTARTS)) { 10 } else { [int]$env:SOVRN_PREVIEW_MAX_RUNTIME_RESTARTS })
)

$ErrorActionPreference = 'Stop'

$metricsUrl = "{0}/api/v1/telemetry/client-metrics" -f ($WebBaseUrl.TrimEnd('/'))
Write-Host "Checking preview canary metrics at $metricsUrl"

try {
    $snapshot = Invoke-RestMethod -Uri $metricsUrl -Method Get
} catch {
    Write-Error "Failed to fetch telemetry metrics snapshot: $($_.Exception.Message)"
    exit 2
}

$metrics = $snapshot.metrics
if ($null -eq $metrics) {
    Write-Error 'Telemetry snapshot did not include metrics payload.'
    exit 2
}

$render = $metrics.'builder_preview_render_ms'
$streamUpdates = $metrics.'builder_preview_stream_update_count'
$reconnects = $metrics.'builder_preview_stream_reconnect_count'
$restarts = $metrics.'builder_preview_runtime_restart_count'

$failed = $false

if ($null -eq $render) {
    Write-Host '- MISSING metric: builder_preview_render_ms'
    $failed = $true
} else {
    Write-Host ("- builder_preview_render_ms p95: {0} ms" -f $render.p95)
    if ([double]$render.p95 -gt $MaxPreviewRenderP95Ms) {
        Write-Host ("  FAIL: p95 exceeds threshold ({0} ms)" -f $MaxPreviewRenderP95Ms)
        $failed = $true
    }
}

if ($null -eq $streamUpdates) {
    Write-Host '- MISSING metric: builder_preview_stream_update_count'
    $failed = $true
} else {
    Write-Host ("- builder_preview_stream_update_count total: {0}" -f $streamUpdates.sum)
    if ([double]$streamUpdates.sum -lt $MinStreamUpdateCount) {
        Write-Host ("  FAIL: stream updates below minimum ({0})" -f $MinStreamUpdateCount)
        $failed = $true
    }
}

if ($null -eq $reconnects) {
    Write-Host '- MISSING metric: builder_preview_stream_reconnect_count (treated as 0)'
} else {
    Write-Host ("- builder_preview_stream_reconnect_count total: {0}" -f $reconnects.sum)
    if ([double]$reconnects.sum -gt $MaxStreamReconnectCount) {
        Write-Host ("  FAIL: reconnect count exceeds threshold ({0})" -f $MaxStreamReconnectCount)
        $failed = $true
    }
}

if ($null -eq $restarts) {
    Write-Host '- MISSING metric: builder_preview_runtime_restart_count (treated as 0)'
} else {
    Write-Host ("- builder_preview_runtime_restart_count total: {0}" -f $restarts.sum)
    if ([double]$restarts.sum -gt $MaxRuntimeRestartCount) {
        Write-Host ("  FAIL: runtime restart count exceeds threshold ({0})" -f $MaxRuntimeRestartCount)
        $failed = $true
    }
}

if ($failed) {
    Write-Host 'Canary metric checks: FAIL'
    exit 1
}

Write-Host 'Canary metric checks: PASS'
exit 0
