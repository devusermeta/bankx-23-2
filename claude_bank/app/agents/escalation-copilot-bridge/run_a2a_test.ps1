# BankX Escalation A2A Test Runner
# This script helps you test the A2A → Copilot Studio integration

Write-Host "🎯 BankX Escalation A2A Test Runner" -ForegroundColor Cyan
Write-Host "=" * 50 -ForegroundColor Cyan

Write-Host "`n📋 Prerequisites:" -ForegroundColor Yellow
Write-Host "   1. Escalation Bridge running on port 9006" -ForegroundColor White
Write-Host "   2. Copilot Studio agent published and accessible" -ForegroundColor White
Write-Host "   3. Power Automate flow configured" -ForegroundColor White

Write-Host "`n🔍 Checking Prerequisites..." -ForegroundColor Green

# Check if bridge is running
try {
    $healthCheck = Invoke-RestMethod -Uri "http://localhost:9006/health" -Method GET -TimeoutSec 5
    Write-Host "   ✅ Bridge health check: OK" -ForegroundColor Green
} catch {
    Write-Host "   ❌ Bridge not running. Start with: python main.py" -ForegroundColor Red
    Write-Host "   📍 Navigate to: claude_bank\app\agents\escalation-copilot-bridge" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n🚀 Starting A2A Test..." -ForegroundColor Green

# Run the Python test
try {
    python test_a2a_escalation.py
} catch {
    Write-Host "❌ Test failed. Make sure Python and dependencies are installed." -ForegroundColor Red
    Write-Host "Try: pip install httpx asyncio" -ForegroundColor Yellow
}

Write-Host "`n🎉 Test Complete!" -ForegroundColor Cyan
Write-Host "Check the output above for results." -ForegroundColor White