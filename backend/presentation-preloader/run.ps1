# PowerShell script to run preload_presentation_messages.py with proper environment variables

# Set environment variables for Google Cloud and Vertex AI
$env:GOOGLE_CLOUD_PROJECT = "langbridge-presenter"
$env:GOOGLE_CLOUD_LOCATION = "global"
$env:GOOGLE_GENAI_USE_VERTEXAI = "True"

# Optional: Set path to service account key file if you have one
# Uncomment and set the path to your service account JSON key file:
# $env:GOOGLE_APPLICATION_CREDENTIALS = "C:\path\to\your\service-account-key.json"

# Check if PPTX path is provided as argument
if ($args.Count -eq 0) {
    Write-Host "Usage: .\run_preload.ps1 <path-to-pptx> [languages]" -ForegroundColor Yellow
    Write-Host "Example: .\run_preload.ps1 'C:\path\to\presentation.pptx' 'en,zh'" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Default languages: en,zh" -ForegroundColor Gray
    exit 1
}

$pptxPath = $args[0]
$languages = if ($args.Count -gt 1) { $args[1] } else { "en,zh" }

# Verify PPTX file exists
if (-not (Test-Path $pptxPath)) {
    Write-Host "Error: PPTX file not found: $pptxPath" -ForegroundColor Red
    exit 1
}

Write-Host "Starting preload process..." -ForegroundColor Green
Write-Host "PPTX: $pptxPath" -ForegroundColor Cyan
Write-Host "Languages: $languages" -ForegroundColor Cyan
Write-Host "Project: $env:GOOGLE_CLOUD_PROJECT" -ForegroundColor Cyan
Write-Host ""

# Run the preload script
python main.py --pptx $pptxPath --languages $languages

if ($LASTEXITCODE -eq 0) {
    Write-Host "`nPreload completed successfully!" -ForegroundColor Green
} else {
    Write-Host "`nPreload failed with exit code: $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
