# Account MCP Server Startup Script
# Run this to start the MCP server on port 8070

Write-Host "Starting Account MCP Server..." -ForegroundColor Green
Write-Host "Port: 8070" -ForegroundColor Cyan
Write-Host "Available tools:" -ForegroundColor Yellow
Write-Host "  - getAccountsByUserName" -ForegroundColor White
Write-Host "  - getAccountDetails" -ForegroundColor White
Write-Host "  - getPaymentMethodDetails" -ForegroundColor White
Write-Host "  - checkLimits" -ForegroundColor White
Write-Host "  - getAccountLimits" -ForegroundColor White
Write-Host ""

# Activate virtual environment if it exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & .venv\Scripts\Activate.ps1
}

# Set environment variables
$env:PORT = "8070"
$env:HOST = "0.0.0.0"
$env:LOG_LEVEL = "INFO"

# Run the server
python main.py
