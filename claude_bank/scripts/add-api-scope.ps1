# Add API Scope to BankX App Registration
# This script adds a custom scope "BankX.Access" to allow frontend to access backend API

$clientId = "c37e62a7-a62f-4ebf-a7c2-d6a3d318f76b"
$tenantId = "ed6f4727-c993-424d-ad62-91492f3c1f41"

Write-Host "Adding API scope to BankX app registration..." -ForegroundColor Cyan

# Generate a new GUID for the scope
$scopeId = [guid]::NewGuid().ToString()

# Create the oauth2PermissionScopes JSON
$oauth2Permissions = @{
    oauth2PermissionScopes = @(
        @{
            adminConsentDescription = "Allows the application to access BankX banking services on behalf of the signed-in user"
            adminConsentDisplayName = "Access BankX API"
            id = $scopeId
            isEnabled = $true
            type = "User"
            userConsentDescription = "Allows the app to access your BankX banking information"
            userConsentDisplayName = "Access your BankX account"
            value = "BankX.Access"
        }
    )
} | ConvertTo-Json -Depth 10

Write-Host "Scope ID: $scopeId" -ForegroundColor Yellow

# Update the app with the new scope
Write-Host "`nUpdating app registration with API scope..." -ForegroundColor Cyan
az ad app update --id $clientId --set "api=$oauth2Permissions"

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ API scope added successfully!" -ForegroundColor Green
    Write-Host "`nAPI Scope Details:" -ForegroundColor Cyan
    Write-Host "  Scope Value: BankX.Access" -ForegroundColor White
    Write-Host "  Full Scope: api://$clientId/BankX.Access" -ForegroundColor White
    Write-Host "  Scope ID: $scopeId" -ForegroundColor White
    
    Write-Host "`nNext steps:" -ForegroundColor Yellow
    Write-Host "1. Update frontend to request scope: api://$clientId/BankX.Access"
    Write-Host "2. Update backend to validate this scope in JWT tokens"
    Write-Host "3. Restart both frontend and backend services"
} else {
    Write-Host "`n❌ Failed to add API scope" -ForegroundColor Red
}
