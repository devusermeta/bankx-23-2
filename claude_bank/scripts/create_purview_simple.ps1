# Create Microsoft Purview Account via REST API
param(
    [string]$PurviewAccountName = "bankx-purview",
    [string]$ResourceGroupName = "rg-multimodaldemo",
    [string]$Location = "eastus",
    [string]$SubscriptionId = "e0783b50-4ca5-4059-83c1-524f39faa624"
)

Write-Host "Creating Microsoft Purview Account: $PurviewAccountName"
Write-Host "Resource Group: $ResourceGroupName"
Write-Host "Location: $Location"

# Get access token
$token = az account get-access-token --query accessToken -o tsv

if (-not $token) {
    Write-Host "Failed to get access token"
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

Write-Host "Sending Purview creation request..."

try {
    $response = Invoke-RestMethod -Uri $url -Method Put -Headers @{"Authorization" = "Bearer $token"; "Content-Type" = "application/json"} -Body $body

    Write-Host "SUCCESS: Purview account creation initiated"
    Write-Host "Name: $($response.name)"
    Write-Host "ID: $($response.id)"
    Write-Host "Provisioning State: $($response.properties.provisioningState)"
    
    if ($response.properties.endpoints) {
        Write-Host "Endpoints:"
        Write-Host "  Catalog: $($response.properties.endpoints.catalog)"
        Write-Host "  Scan: $($response.properties.endpoints.scan)"
    }

    Write-Host "Note: Purview account creation takes 5-10 minutes"

} catch {
    Write-Host "FAILED to create Purview account"
    Write-Host "Error: $($_.Exception.Message)"
    exit 1
}
