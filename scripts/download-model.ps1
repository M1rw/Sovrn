# Download and prepare the Llama 3.2 11B model for SOVRN
# Run this script with PowerShell

param(
    [string]$ModelDir = ".\models",
    [string]$Quantization = "Q4_K_M"
)

$ErrorActionPreference = "Stop"

Write-Host "🚀 SOVRN Model Downloader" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan
Write-Host ""

# Create models directory
New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null
Push-Location $ModelDir

Write-Host "📁 Model directory: $(Get-Location)" -ForegroundColor Yellow
Write-Host "📦 Model: llama-3.2-11b-vision-instruct" -ForegroundColor Yellow
Write-Host "🔧 Quantization: $Quantization" -ForegroundColor Yellow
Write-Host ""

# Check if huggingface-cli is available
try {
    $null = Get-Command huggingface-cli -ErrorAction Stop
} catch {
    Write-Host "⚠️  huggingface-cli not found. Installing..." -ForegroundColor Yellow
    pip install huggingface_hub[cli]
}

# Download the quantized GGUF model
Write-Host "📥 Downloading model..." -ForegroundColor Green
Write-Host "   This may take a while depending on your connection speed." -ForegroundColor Gray
Write-Host ""

$ModelFile = "llama-3.2-11b-vision-instruct.$Quantization.gguf"
$HuggingFaceRepo = "bartowski/Llama-3.2-11B-Vision-Instruct-GGUF"

if (Test-Path $ModelFile) {
    Write-Host "✅ Model already exists: $ModelFile" -ForegroundColor Green
} else {
    huggingface-cli download $HuggingFaceRepo $ModelFile --local-dir . --local-dir-use-symlinks False
    Write-Host "✅ Model downloaded successfully!" -ForegroundColor Green
}

# Verify the model file
if (Test-Path $ModelFile) {
    $ModelSize = (Get-Item $ModelFile).Length / 1GB
    Write-Host ""
    Write-Host "📊 Model Info:" -ForegroundColor Cyan
    Write-Host "   File: $ModelFile"
    Write-Host "   Size: $([math]::Round($ModelSize, 2)) GB"
} else {
    Write-Host "❌ Error: Model file not found after download" -ForegroundColor Red
    Pop-Location
    exit 1
}

Pop-Location

Write-Host ""
Write-Host "✨ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the inference server, run:" -ForegroundColor Cyan
Write-Host "   docker compose up infer" -ForegroundColor White
Write-Host ""
Write-Host "Or with llama.cpp directly:" -ForegroundColor Cyan
Write-Host "   llama-server -m models\$ModelFile --host 0.0.0.0 --port 8080" -ForegroundColor White
Write-Host ""
