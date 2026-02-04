# Create Microsoft Purview Account via REST API with detailed error handling
param(
    [string]$PurviewAccountName = "bankx-purview",
    [string]$ResourceGroupName = "rg-multimodaldemo",
    [string]$Location = "eastus",
    [string]$SubscriptionId = "e0783b50-4ca5-4059-83c1-524f39faa624"
)

Write-Host "Creating Microsoft Purview Account: $PurviewAccountName"

$token = az account get-access-token --query accessToken -o tsv
$apiVersion = "2021-07-01"
$url = "https://management.azure.com/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Purview/accounts/$PurviewAccountName?api-version=$apiVersion"

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

Write-Host "Request URL: $url"
Write-Host "Request Body: $body"

try {
    $response = Invoke-WebRequest -Uri $url -Method Put -Headers @{"Authorization" = "Bearer $token"; "Content-Type" = "application/json"} -Body $body -UseBasicParsing
    
    Write-Host "SUCCESS"
    Write-Host $response.Content
    
} catch {
    Write-Host "FAILED"
    Write-Host "Status: $($_.Exception.Response.StatusCode.value__)"
    
    $result = $_.Exception.Response.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($result)
    $responseBody = $reader.ReadToEnd()
    Write-Host "Details: $responseBody"
}
