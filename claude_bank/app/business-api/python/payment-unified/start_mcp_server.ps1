# Start Payment Unified MCP Server
# Sets up environment and starts the server

$ErrorActionPreference = "Stop"

Write-Host "🚀 Starting Payment Unified MCP Server..." -ForegroundColor Cyan

# Navigate to claude_bank root
$CLAUDE_BANK_ROOT = "d:\Metakaal\Updated_BankX\claude_bank"
Set-Location $CLAUDE_BANK_ROOT

# Set PYTHONPATH to include claude_bank root
$env:PYTHONPATH = $CLAUDE_BANK_ROOT

# Check if .env exists in payment-unified folder
$ENV_FILE = Join-Path $CLAUDE_BANK_ROOT "app\business-api\python\payment-unified\.env"
if (-not (Test-Path $ENV_FILE)) {
    Write-Host "⚠️  No .env file found. Using default configuration." -ForegroundColor Yellow
}

# Run the server as a module from claude_bank root
Write-Host "✅ PYTHONPATH set to: $env:PYTHONPATH" -ForegroundColor Green
Write-Host "✅ Starting server on port 8076..." -ForegroundColor Green

python -m app.business-api.python.payment-unified.main

