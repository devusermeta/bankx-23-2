# Quick Power Automate Diagnostics

Write-Host "🚨 POWER AUTOMATE 502 ERROR DIAGNOSTICS" -ForegroundColor Red
Write-Host "=" * 50 -ForegroundColor Red

Write-Host "`n🔍 Checking common causes of 502 Bad Gateway..." -ForegroundColor Yellow

# 1. Check if .env file exists and has required values
Write-Host "`n📋 Step 1: Environment Configuration" -ForegroundColor Cyan
if (Test-Path ".env") {
    Write-Host "   ✅ .env file exists" -ForegroundColor Green
    
    $envContent = Get-Content ".env" | Where-Object { $_ -match "POWER_AUTOMATE_FLOW_URL" }
    if ($envContent) {
        Write-Host "   ✅ POWER_AUTOMATE_FLOW_URL is set" -ForegroundColor Green
    } else {
        Write-Host "   ❌ POWER_AUTOMATE_FLOW_URL is missing" -ForegroundColor Red
    }
} else {
    Write-Host "   ❌ .env file not found" -ForegroundColor Red
}

# 2. Test basic connectivity
Write-Host "`n📋 Step 2: Testing Flow Connectivity" -ForegroundColor Cyan
Write-Host "   Running Python diagnostics..." -ForegroundColor White

try {
    python diagnose_power_automate.py
} catch {
    Write-Host "   ❌ Python diagnostics failed" -ForegroundColor Red
}

# 3. Common fixes
Write-Host "`n📋 Step 3: Common Solutions for 502 Errors" -ForegroundColor Cyan
Write-Host "   The 502 Bad Gateway error typically means:" -ForegroundColor White
Write-Host "   1. 🤖 Copilot Studio bot is not published or accessible" -ForegroundColor Yellow
Write-Host "   2. 📧 Outlook connector authentication expired" -ForegroundColor Yellow  
Write-Host "   3. 📊 Excel connector lost permissions" -ForegroundColor Yellow
Write-Host "   4. ⚡ Power Automate flow is disabled/turned off" -ForegroundColor Yellow

Write-Host "`n🔧 IMMEDIATE ACTIONS TO TRY:" -ForegroundColor Green
Write-Host "   1. Go to https://make.powerautomate.com" -ForegroundColor White
Write-Host "   2. Find your escalation flow" -ForegroundColor White
Write-Host "   3. Check if it's 'On' (toggle switch)" -ForegroundColor White
Write-Host "   4. Click 'Run history' to see error details" -ForegroundColor White
Write-Host "   5. Test each connector individually" -ForegroundColor White

Write-Host "`n🤖 COPILOT STUDIO CHECK:" -ForegroundColor Green  
Write-Host "   1. Go to https://copilotstudio.microsoft.com" -ForegroundColor White
Write-Host "   2. Find your EscalationAgent bot" -ForegroundColor White
Write-Host "   3. Ensure it's Published (not just saved)" -ForegroundColor White
Write-Host "   4. Test the bot manually first" -ForegroundColor White

Write-Host "`n📞 If nothing works:" -ForegroundColor Magenta
Write-Host "   Consider switching to Direct Line API instead of Power Automate" -ForegroundColor White
Write-Host "   (More reliable for production use)" -ForegroundColor White

Write-Host "`n" + "=" * 50 -ForegroundColor Red