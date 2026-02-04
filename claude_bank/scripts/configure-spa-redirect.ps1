# Configure SPA Redirect URIs for BankX App Registration
# This fixes CORS issues by properly configuring the app as a Single-Page Application

$clientId = "c37e62a7-a62f-4ebf-a7c2-d6a3d318f76b"
$tenantId = "ed6f4727-c993-424d-ad62-91492f3c1f41"

Write-Host "Configuring SPA platform for BankX app..." -ForegroundColor Cyan

# Get current app configuration
Write-Host "Fetching current app configuration..." -ForegroundColor Yellow
$app = az ad app show --id $clientId | ConvertFrom-Json

# Configure SPA platform with redirect URIs
$spaConfig = @{
    spa = @{
        redirectUris = @(
            "http://localhost:8081",
            "http://localhost:8081/"
        )
    }
    web = @{
        implicitGrantSettings = @{
            enableIdTokenIssuance = $true
            enableAccessTokenIssuance = $true
        }
    }
}

$spaJson = $spaConfig | ConvertTo-Json -Depth 10

Write-Host "Updating app registration with SPA configuration..." -ForegroundColor Yellow
az rest --method PATCH `
    --uri "https://graph.microsoft.com/v1.0/applications/$($app.id)" `
    --headers "Content-Type=application/json" `
    --body $spaJson

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ SPA configuration added successfully!" -ForegroundColor Green
    Write-Host "`nConfigured redirect URIs:" -ForegroundColor Cyan
    Write-Host "  - http://localhost:8081" -ForegroundColor White
    Write-Host "  - http://localhost:8081/" -ForegroundColor White
    Write-Host "`nPlease refresh the frontend page and try logging in again." -ForegroundColor Yellow
} else {
    Write-Host "`n❌ Failed to configure SPA settings" -ForegroundColor Red
    Write-Host "Please configure manually in Azure Portal:" -ForegroundColor Yellow
    Write-Host "1. Go to App registrations → BankX-Multi-Agent-App" -ForegroundColor White
    Write-Host "2. Click 'Authentication' → Add platform → Single-page application" -ForegroundColor White
    Write-Host "3. Add redirect URI: http://localhost:8081" -ForegroundColor White
    Write-Host "4. Enable ID tokens and Access tokens" -ForegroundColor White
}
