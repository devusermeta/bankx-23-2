# ============================================================================
# BankX Infrastructure Deployment Script
# ============================================================================
# This script deploys the complete BankX infrastructure using Bicep templates
# ============================================================================

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('dev', 'prod')]
    [string]$Environment,
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId,
    
    [Parameter(Mandatory=$false)]
    [string]$Location = 'eastus'
)

# Set error action preference
$ErrorActionPreference = 'Stop'

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host " BankX Infrastructure Deployment" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Environment:      $Environment" -ForegroundColor Yellow
Write-Host "Resource Group:   $ResourceGroupName" -ForegroundColor Yellow
Write-Host "Subscription:     $SubscriptionId" -ForegroundColor Yellow
Write-Host "Location:         $Location" -ForegroundColor Yellow
Write-Host ""

# ============================================================================
# Step 1: Set Azure Subscription
# ============================================================================

Write-Host "[1/6] Setting Azure subscription..." -ForegroundColor Green
az account set --subscription $SubscriptionId
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to set subscription"
    exit 1
}
Write-Host "✓ Subscription set successfully" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Step 2: Create Resource Group (if not exists)
# ============================================================================

Write-Host "[2/6] Ensuring resource group exists..." -ForegroundColor Green
$rgExists = az group exists --name $ResourceGroupName
if ($rgExists -eq 'false') {
    Write-Host "Creating resource group: $ResourceGroupName" -ForegroundColor Yellow
    az group create --name $ResourceGroupName --location $Location
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to create resource group"
        exit 1
    }
    Write-Host "✓ Resource group created" -ForegroundColor Green
} else {
    Write-Host "✓ Resource group already exists" -ForegroundColor Green
}
Write-Host ""

# ============================================================================
# Step 3: Deploy Bicep Template
# ============================================================================

Write-Host "[3/6] Deploying Bicep infrastructure..." -ForegroundColor Green
Write-Host "This may take 15-20 minutes..." -ForegroundColor Yellow

$deploymentName = "bankx-$Environment-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
$bicepFile = Join-Path $PSScriptRoot "..\main.bicep"
$paramFile = Join-Path $PSScriptRoot "..\parameters\$Environment.bicepparam"

az deployment group create `
    --name $deploymentName `
    --resource-group $ResourceGroupName `
    --template-file $bicepFile `
    --parameters $paramFile `
    --verbose

if ($LASTEXITCODE -ne 0) {
    Write-Error "Bicep deployment failed"
    exit 1
}

Write-Host "✓ Infrastructure deployed successfully" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Step 4: Get Deployment Outputs
# ============================================================================

Write-Host "[4/6] Retrieving deployment outputs..." -ForegroundColor Green

$outputs = az deployment group show `
    --name $deploymentName `
    --resource-group $ResourceGroupName `
    --query properties.outputs `
    --output json | ConvertFrom-Json

Write-Host "✓ Deployment outputs retrieved" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Step 5: Assign RBAC Roles
# ============================================================================

Write-Host "[5/6] Assigning RBAC roles to Managed Identities..." -ForegroundColor Green
Write-Host "Running assign-rbac-roles.ps1..." -ForegroundColor Yellow

$rbacScript = Join-Path $PSScriptRoot "assign-rbac-roles.ps1"
& $rbacScript -ResourceGroupName $ResourceGroupName -SubscriptionId $SubscriptionId

if ($LASTEXITCODE -ne 0) {
    Write-Warning "RBAC role assignment had some issues. Check logs."
} else {
    Write-Host "✓ RBAC roles assigned" -ForegroundColor Green
}
Write-Host ""

# ============================================================================
# Step 6: Display Deployment Summary
# ============================================================================

Write-Host "[6/6] Deployment Summary" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Resource Group:          $ResourceGroupName" -ForegroundColor White
Write-Host "OpenAI Endpoint:         $($outputs.openAiEndpoint.value)" -ForegroundColor White
Write-Host "AI Foundry Endpoint:     $($outputs.aiFindryEndpoint.value)" -ForegroundColor White
Write-Host "Search Endpoint:         $($outputs.searchEndpoint.value)" -ForegroundColor White
Write-Host "Cosmos DB Endpoint:      $($outputs.cosmosDbEndpoint.value)" -ForegroundColor White
Write-Host "Storage Account:         $($outputs.storageAccountName.value)" -ForegroundColor White
Write-Host "Key Vault URI:           $($outputs.keyVaultUri.value)" -ForegroundColor White
Write-Host "Copilot App URL:         https://$($outputs.copilotAppFqdn.value)" -ForegroundColor White
Write-Host "Frontend App URL:        https://$($outputs.frontendAppFqdn.value)" -ForegroundColor White
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# ============================================================================
# Post-Deployment Actions Required
# ============================================================================

Write-Host "⚠️  MANUAL STEPS REQUIRED:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Assign Purview RBAC roles (Data Curator) to 7 Service Principals" -ForegroundColor Yellow
Write-Host "   → Run: .\setup-purview-rbac.ps1" -ForegroundColor White
Write-Host ""
Write-Host "2. Create AI Foundry agents (7 agents)" -ForegroundColor Yellow
Write-Host "   → Run: python setup-agents.py" -ForegroundColor White
Write-Host ""
Write-Host "3. Create AI Search indexes and upload documents" -ForegroundColor Yellow
Write-Host "   → Run: python setup-search-indexes.py" -ForegroundColor White
Write-Host ""
Write-Host "4. Store secrets in Key Vault" -ForegroundColor Yellow
Write-Host "   → Service Principal secrets for Purview" -ForegroundColor White
Write-Host "   → Communication Services connection string" -ForegroundColor White
Write-Host ""
Write-Host "5. Deploy container images to Container Apps" -ForegroundColor Yellow
Write-Host "   → Run: azd deploy" -ForegroundColor White
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "✓ Deployment completed successfully!" -ForegroundColor Green
Write-Host ""
