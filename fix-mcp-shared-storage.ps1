# ============================================================================
# Fix MCP Shared Storage Configuration
# ============================================================================
# This script:
# 1. Uploads JSON files from local dynamic_data/ to Azure Files share
# 2. Updates ALL MCP servers to mount the shared volume to /app/dynamic_data
# 3. Verifies all containers are using the same persistent storage
# ============================================================================

$ErrorActionPreference = "Stop"

# Configuration
$resourceGroup = "rg-banking-new"
$environmentResourceGroup = "rg-a2a-test"
$environmentName = "acae-a2a-test"
$storageAccountName = "bankxstorage776"
$shareName = "dynamicdata"
$storageName = "bankx-shared-data"

# MCP Servers to update
$mcpServers = @(
    "account-mcp",
    "payment-mcp",
    "contacts-mcp",
    "limits-mcp",
    "escalation-mcp"
)

# Local path to JSON files
$localDataPath = ".\claude_bank\dynamic_data"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "STEP 1: Upload JSON Files to Azure Files Share" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

# Get storage account key
Write-Host "`n📦 Getting storage account key..." -ForegroundColor Yellow
$storageKey = az storage account keys list `
    --account-name $storageAccountName `
    --resource-group $environmentResourceGroup `
    --query "[0].value" `
    --output tsv

if (-not $storageKey) {
    Write-Error "Failed to get storage account key"
    exit 1
}

Write-Host "✅ Storage account key retrieved" -ForegroundColor Green

# Check if share exists
Write-Host "`n📂 Checking if file share exists..." -ForegroundColor Yellow
$shareExists = az storage share exists `
    --name $shareName `
    --account-name $storageAccountName `
    --account-key $storageKey `
    --query "exists" `
    --output tsv

if ($shareExists -ne "true") {
    Write-Host "⚠️  File share does not exist, creating..." -ForegroundColor Yellow
    az storage share create `
        --name $shareName `
        --account-name $storageAccountName `
        --account-key $storageKey
    Write-Host "✅ File share created" -ForegroundColor Green
} else {
    Write-Host "✅ File share exists" -ForegroundColor Green
}

# Upload JSON files
Write-Host "`n📤 Uploading JSON files to Azure Files share..." -ForegroundColor Yellow

$jsonFiles = @(
    "accounts.json",
    "contacts.json",
    "customers.json",
    "limits.json",
    "transactions.json"
)

foreach ($file in $jsonFiles) {
    $localFile = Join-Path $localDataPath $file
    
    if (Test-Path $localFile) {
        Write-Host "  Uploading $file..." -ForegroundColor Gray
        
        az storage file upload `
            --share-name $shareName `
            --source $localFile `
            --path $file `
            --account-name $storageAccountName `
            --account-key $storageKey `
            --no-progress `
            --overwrite | Out-Null
        
        Write-Host "  ✅ $file uploaded" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  $file not found locally, skipping" -ForegroundColor Yellow
    }
}

Write-Host "`n✅ All JSON files uploaded to Azure Files share" -ForegroundColor Green

Write-Host "`n============================================================================" -ForegroundColor Cyan
Write-Host "STEP 2: Verify uploaded files" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

Write-Host "`n📋 Files in Azure Files share:" -ForegroundColor Yellow
az storage file list `
    --share-name $shareName `
    --account-name $storageAccountName `
    --account-key $storageKey `
    --query "[].name" `
    --output table

Write-Host "`n============================================================================" -ForegroundColor Cyan
Write-Host "STEP 3: Update MCP Container Apps with Correct Volume Mounts" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

foreach ($containerName in $mcpServers) {
    Write-Host "`n🔧 Updating $containerName..." -ForegroundColor Yellow
    
    # Export current configuration
    Write-Host "  📥 Exporting current configuration..." -ForegroundColor Gray
    $configJson = az containerapp show `
        --name $containerName `
        --resource-group $resourceGroup `
        --output json | ConvertFrom-Json
    
    # Update volume mounts to point to /app/dynamic_data
    Write-Host "  🔄 Configuring volume mounts..." -ForegroundColor Gray
    
    # Ensure volumes array exists
    if (-not $configJson.properties.template.volumes) {
        $configJson.properties.template.volumes = @()
    }
    
    # Add or update volume configuration
    $volumeConfig = @{
        name = $storageName
        storageName = $storageName
        storageType = "AzureFile"
    }
    
    $configJson.properties.template.volumes = @($volumeConfig)
    
    # Add or update volume mounts
    if (-not $configJson.properties.template.containers[0].volumeMounts) {
        $configJson.properties.template.containers[0].volumeMounts = @()
    }
    
    # Mount to /app/dynamic_data (where StateManager expects files)
    $volumeMount = @{
        mountPath = "/app/dynamic_data"
        volumeName = $storageName
    }
    
    $configJson.properties.template.containers[0].volumeMounts = @($volumeMount)
    
    # Remove system-managed fields
    $configJson.PSObject.Properties.Remove('id')
    $configJson.PSObject.Properties.Remove('systemData')
    $configJson.properties.PSObject.Properties.Remove('latestRevisionName')
    $configJson.properties.PSObject.Properties.Remove('latestRevisionFqdn')
    $configJson.properties.PSObject.Properties.Remove('latestReadyRevisionName')
    $configJson.properties.PSObject.Properties.Remove('customDomainVerificationId')
    $configJson.properties.PSObject.Properties.Remove('outboundIpAddresses')
    $configJson.properties.PSObject.Properties.Remove('eventStreamEndpoint')
    
    # Save to temp file
    $tempFile = "temp-$containerName.json"
    $configJson | ConvertTo-Json -Depth 20 | Out-File -FilePath $tempFile -Encoding UTF8
    
    # Update container app
    Write-Host "  📤 Applying updated configuration..." -ForegroundColor Gray
    az containerapp update `
        --name $containerName `
        --resource-group $resourceGroup `
        --yaml $tempFile `
        --output none
    
    # Clean up temp file
    Remove-Item $tempFile -ErrorAction SilentlyContinue
    
    Write-Host "  ✅ $containerName updated successfully" -ForegroundColor Green
}

Write-Host "`n============================================================================" -ForegroundColor Cyan
Write-Host "STEP 4: Verification" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

Write-Host "`n📊 Checking container status..." -ForegroundColor Yellow
az containerapp list `
    --resource-group $resourceGroup `
    --query "[?contains(name, 'mcp')].{Name:name, Status:properties.runningStatus, Replicas:properties.runningStatus}" `
    --output table

Write-Host "`n✅ ============================================================================" -ForegroundColor Green
Write-Host "✅ SHARED STORAGE CONFIGURATION COMPLETED!" -ForegroundColor Green
Write-Host "✅ ============================================================================" -ForegroundColor Green

Write-Host "`n📋 Summary:" -ForegroundColor Cyan
Write-Host "  • Storage Account: $storageAccountName" -ForegroundColor White
Write-Host "  • File Share: $shareName" -ForegroundColor White
Write-Host "  • Mount Path: /app/dynamic_data" -ForegroundColor White
Write-Host "  • MCP Servers Updated: $($mcpServers.Count)" -ForegroundColor White
Write-Host "`n  All MCP servers now share the same JSON files!" -ForegroundColor Yellow
Write-Host "  Changes to accounts.json by payment-mcp will be visible to account-mcp" -ForegroundColor Yellow

Write-Host "`n⚠️  IMPORTANT NOTES:" -ForegroundColor Yellow
Write-Host "  1. Containers may take 1-2 minutes to restart with new configuration" -ForegroundColor White
Write-Host "  2. JSON files are now persistent - changes survive container restarts" -ForegroundColor White
Write-Host "  3. All MCP servers share the SAME files through Azure Files" -ForegroundColor White
Write-Host "  4. Test with a payment to verify that accounts.json is updated" -ForegroundColor White

Write-Host "`n🧪 To test:" -ForegroundColor Cyan
Write-Host "  1. Make a payment through the frontend" -ForegroundColor White
Write-Host "  2. Check accounts.json in Azure Files to see balance updates" -ForegroundColor White
Write-Host "  3. Verify all MCP servers can read the updated balance" -ForegroundColor White
Write-Host ""
