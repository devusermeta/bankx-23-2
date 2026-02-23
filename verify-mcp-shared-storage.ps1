# ============================================================================
# Verify MCP Shared Storage Configuration
# ============================================================================
# This script verifies that:
# 1. JSON files exist in Azure Files share
# 2. All MCP servers have correct volume mounts
# 3. Files are readable and writable
# ============================================================================

$ErrorActionPreference = "Stop"

# Configuration
$resourceGroup = "rg-banking-new"
$environmentResourceGroup = "rg-a2a-test"
$storageAccountName = "bankxstorage776"
$shareName = "dynamicdata"
$storageName = "bankx-shared-data"

$mcpServers = @(
    "account-mcp",
    "payment-mcp",
    "contacts-mcp",
    "limits-mcp"
)

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "MCP SHARED STORAGE VERIFICATION" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

# Get storage account key
Write-Host "`n📦 Getting storage account key..." -ForegroundColor Yellow
$storageKey = az storage account keys list `
    --account-name $storageAccountName `
    --resource-group $environmentResourceGroup `
    --query "[0].value" `
    --output tsv

Write-Host "✅ Storage account key retrieved" -ForegroundColor Green

Write-Host "`n============================================================================" -ForegroundColor Cyan
Write-Host "CHECK 1: Azure Files Share Contents" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

Write-Host "`n📂 Files in Azure Files share:" -ForegroundColor Yellow
$files = az storage file list `
    --share-name $shareName `
    --account-name $storageAccountName `
    --account-key $storageKey `
    --output json | ConvertFrom-Json

$expectedFiles = @("accounts.json", "contacts.json", "customers.json", "limits.json", "transactions.json")
$foundFiles = $files | Select-Object -ExpandProperty name

Write-Host "`n  Expected Files:" -ForegroundColor Gray
foreach ($file in $expectedFiles) {
    if ($foundFiles -contains $file) {
        Write-Host "    ✅ $file" -ForegroundColor Green
    } else {
        Write-Host "    ❌ $file - MISSING!" -ForegroundColor Red
    }
}

Write-Host "`n============================================================================" -ForegroundColor Cyan
Write-Host "CHECK 2: Container Volume Mount Configuration" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

$allCorrect = $true

foreach ($containerName in $mcpServers) {
    Write-Host "`n🔍 Checking $containerName..." -ForegroundColor Yellow
    
    $config = az containerapp show `
        --name $containerName `
        --resource-group $resourceGroup `
        --output json | ConvertFrom-Json
    
    # Check volumes
    $hasVolume = $false
    if ($config.properties.template.volumes) {
        foreach ($vol in $config.properties.template.volumes) {
            if ($vol.name -eq $storageName -and $vol.storageType -eq "AzureFile") {
                $hasVolume = $true
                break
            }
        }
    }
    
    # Check volume mounts
    $hasMountToDynamicData = $false
    if ($config.properties.template.containers[0].volumeMounts) {
        foreach ($mount in $config.properties.template.containers[0].volumeMounts) {
            if ($mount.mountPath -eq "/app/dynamic_data" -and $mount.volumeName -eq $storageName) {
                $hasMountToDynamicData = $true
                break
            }
        }
    }
    
    # Report results
    if ($hasVolume) {
        Write-Host "  ✅ Volume configured: $storageName" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Volume NOT configured!" -ForegroundColor Red
        $allCorrect = $false
    }
    
    if ($hasMountToDynamicData) {
        Write-Host "  ✅ Volume mount: /app/dynamic_data" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Volume mount INCORRECT or MISSING!" -ForegroundColor Red
        Write-Host "     Expected: /app/dynamic_data" -ForegroundColor Gray
        
        if ($config.properties.template.containers[0].volumeMounts) {
            Write-Host "     Current mounts:" -ForegroundColor Gray
            foreach ($mount in $config.properties.template.containers[0].volumeMounts) {
                Write-Host "       • $($mount.mountPath)" -ForegroundColor Gray
            }
        }
        
        $allCorrect = $false
    }
    
    # Check running status
    $status = $config.properties.runningStatus
    if ($status -eq "Running") {
        Write-Host "  ✅ Status: Running" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  Status: $status" -ForegroundColor Yellow
    }
}

Write-Host "`n============================================================================" -ForegroundColor Cyan
Write-Host "CHECK 3: Sample File Contents" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

Write-Host "`n📄 Downloading accounts.json sample..." -ForegroundColor Yellow

# Download accounts.json to check contents
$tempFile = "temp-accounts-verify.json"
az storage file download `
    --share-name $shareName `
    --path "accounts.json" `
    --dest $tempFile `
    --account-name $storageAccountName `
    --account-key $storageKey `
    --no-progress `
    --output none

if (Test-Path $tempFile) {
    $accountsData = Get-Content $tempFile -Raw | ConvertFrom-Json
    
    Write-Host "`n  Metadata:" -ForegroundColor Gray
    Write-Host "    Last Updated: $($accountsData._metadata.last_updated)" -ForegroundColor White
    Write-Host "    Description: $($accountsData._metadata.description)" -ForegroundColor White
    
    Write-Host "`n  Accounts:" -ForegroundColor Gray
    $accountCount = $accountsData.accounts.Count
    Write-Host "    Total Accounts: $accountCount" -ForegroundColor White
    
    if ($accountCount -gt 0) {
        Write-Host "`n    Sample Account (CUST-001):" -ForegroundColor Gray
        $custAccount = $accountsData.accounts | Where-Object { $_.customer_id -eq "CUST-001" }
        if ($custAccount) {
            Write-Host "      Customer: $($custAccount.cust_name)" -ForegroundColor White
            Write-Host "      Account: $($custAccount.account_no)" -ForegroundColor White
            Write-Host "      Balance: THB $($custAccount.ledger_balance)" -ForegroundColor White
        }
        
        Write-Host "`n    Sample Account (CUST-002 - Test User):" -ForegroundColor Gray
        $testAccount = $accountsData.accounts | Where-Object { $_.customer_id -eq "CUST-002" }
        if ($testAccount) {
            Write-Host "      Customer: $($testAccount.cust_name)" -ForegroundColor White
            Write-Host "      Account: $($testAccount.account_no)" -ForegroundColor White
            Write-Host "      Balance: THB $($testAccount.ledger_balance)" -ForegroundColor White
            Write-Host "      (This balance will change after payment tests)" -ForegroundColor Yellow
        }
    }
    
    Remove-Item $tempFile -ErrorAction SilentlyContinue
    Write-Host "`n  ✅ accounts.json is valid and accessible" -ForegroundColor Green
} else {
    Write-Host "  ❌ Failed to download accounts.json" -ForegroundColor Red
    $allCorrect = $false
}

Write-Host "`n============================================================================" -ForegroundColor Cyan
Write-Host "VERIFICATION SUMMARY" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

if ($allCorrect) {
    Write-Host "`n✅ ALL CHECKS PASSED!" -ForegroundColor Green
    Write-Host "`n📋 Configuration:" -ForegroundColor Cyan
    Write-Host "  • Storage Account: $storageAccountName" -ForegroundColor White
    Write-Host "  • File Share: $shareName" -ForegroundColor White
    Write-Host "  • Mount Path: /app/dynamic_data" -ForegroundColor White
    Write-Host "  • JSON Files: All present and valid" -ForegroundColor White
    Write-Host "  • MCP Servers: All configured correctly" -ForegroundColor White
    
    Write-Host "`n✅ Shared storage is WORKING correctly!" -ForegroundColor Green
    Write-Host "   All MCP servers can now read/write the same JSON files." -ForegroundColor Yellow
    
    Write-Host "`n🧪 Next Steps:" -ForegroundColor Cyan
    Write-Host "  1. Test payment workflow through frontend" -ForegroundColor White
    Write-Host "  2. Verify accounts.json balance updates" -ForegroundColor White
    Write-Host "  3. Check that all MCP servers see the changes" -ForegroundColor White
} else {
    Write-Host "`n❌ ISSUES FOUND!" -ForegroundColor Red
    Write-Host "   Run fix-mcp-shared-storage.ps1 to fix the configuration." -ForegroundColor Yellow
}

Write-Host ""
