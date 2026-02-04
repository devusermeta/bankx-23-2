# Create Microsoft Purview Account via REST API
# This script creates a Purview account when the CLI extension has dependency issues

param(
    [string]$PurviewAccountName = "bankx-purview",
    [string]$ResourceGroupName = "rg-multimodaldemo",
    [string]$Location = "eastus",
    [string]$SubscriptionId = "e0783b50-4ca5-4059-83c1-524f39faa624"
)

Write-Host "🚀 Creating Microsoft Purview Account: $PurviewAccountName" -ForegroundColor Cyan
Write-Host "   Resource Group: $ResourceGroupName" -ForegroundColor Gray
Write-Host "   Location: $Location" -ForegroundColor Gray

# Get access token
Write-Host "`n📋 Getting Azure access token..." -ForegroundColor Yellow
$token = az account get-access-token --query accessToken -o tsv

if (-not $token) {
    Write-Host "❌ Failed to get access token. Please run 'az login' first." -ForegroundColor Red
    exit 1
}

# Construct API URL
$apiVersion = "2021-07-01"
$url = "https://management.azure.com/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Purview/accounts/$PurviewAccountName?api-version=$apiVersion"

# Construct request body
$body = @{
    location = $Location
    sku = @{
        name = "Standard"
        capacity = 1
    }
    identity = @{
        type = "SystemAssigned"
    }
    properties = @{
        publicNetworkAccess = "Enabled"
        managedResourceGroupName = "managed-rg-purview-$PurviewAccountName"
    }
} | ConvertTo-Json -Depth 10

Write-Host "📤 Sending Purview creation request..." -ForegroundColor Yellow
Write-Host "   URL: $url" -ForegroundColor Gray

try {
    $response = Invoke-RestMethod `
        -Uri $url `
        -Method Put `
        -Headers @{
            "Authorization" = "Bearer $token"
            "Content-Type" = "application/json"
        } `
        -Body $body

    Write-Host "`n✅ Purview account creation initiated successfully!" -ForegroundColor Green
    Write-Host "   Name: $($response.name)" -ForegroundColor Gray
    Write-Host "   ID: $($response.id)" -ForegroundColor Gray
    Write-Host "   Provisioning State: $($response.properties.provisioningState)" -ForegroundColor Gray
    
    if ($response.properties.endpoints) {
        Write-Host "`n📍 Endpoints:" -ForegroundColor Cyan
        Write-Host "   Catalog: $($response.properties.endpoints.catalog)" -ForegroundColor Gray
        Write-Host "   Scan: $($response.properties.endpoints.scan)" -ForegroundColor Gray
        Write-Host "   Guardian: $($response.properties.endpoints.guardian)" -ForegroundColor Gray
    }

    Write-Host "`n⏳ Note: Purview account creation takes 5-10 minutes to complete." -ForegroundColor Yellow
    Write-Host "   Monitor status with Azure portal or wait for completion" -ForegroundColor Gray

    # Return the response for further processing
    return $response

} catch {
    Write-Host ""
    Write-Host "Failed to create Purview account!" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $reader.BaseStream.Position = 0
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response: $responseBody" -ForegroundColor Red
    }
    
    exit 1
}
