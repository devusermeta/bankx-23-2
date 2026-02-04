# ============================================================================
# Assign RBAC Roles to Container App Managed Identities
# ============================================================================
# This script assigns Azure RBAC roles to managed identities created by
# Container Apps deployment
# ============================================================================

param(
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroupName,
    
    [Parameter(Mandatory=$true)]
    [string]$SubscriptionId
)

$ErrorActionPreference = 'Stop'

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host " Assigning RBAC Roles" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Set subscription
az account set --subscription $SubscriptionId

# ============================================================================
# Get Managed Identity Principal IDs from Container Apps
# ============================================================================

Write-Host "Retrieving Managed Identity Principal IDs..." -ForegroundColor Yellow

$containerApps = @(
    @{Name="bankx-dev-copilot"; VarName="copilotPrincipalId"},
    @{Name="bankx-dev-prodinfo"; VarName="prodinfoPrincipalId"},
    @{Name="bankx-dev-moneycoach"; VarName="moneyCoachPrincipalId"},
    @{Name="bankx-dev-escalation"; VarName="escalationPrincipalId"},
    @{Name="bankx-dev-audit"; VarName="auditPrincipalId"}
)

$principalIds = @{}

foreach ($app in $containerApps) {
    $principalId = az containerapp show `
        --name $app.Name `
        --resource-group $ResourceGroupName `
        --query "identity.principalId" `
        --output tsv
    
    if ($LASTEXITCODE -eq 0 -and $principalId) {
        $principalIds[$app.VarName] = $principalId
        Write-Host "✓ $($app.Name): $principalId" -ForegroundColor Green
    } else {
        Write-Warning "Failed to get principal ID for $($app.Name)"
    }
}

Write-Host ""

# ============================================================================
# Get Resource IDs
# ============================================================================

Write-Host "Retrieving Azure Resource IDs..." -ForegroundColor Yellow

$openAiId = az cognitiveservices account show -n "bankx-dev-openai" -g $ResourceGroupName --query "id" -o tsv
$aiFindryId = az cognitiveservices account show -n "bankx-dev-aifoundry" -g $ResourceGroupName --query "id" -o tsv
$docIntelId = az cognitiveservices account show -n "bankx-dev-docintel" -g $ResourceGroupName --query "id" -o tsv
$searchId = az search service show -n "bankx-dev-search" -g $ResourceGroupName --query "id" -o tsv
$cosmosId = az cosmosdb show -n "bankx-dev-cosmos" -g $ResourceGroupName --query "id" -o tsv
$storageId = az storage account show -n "bankxdevstorage" -g $ResourceGroupName --query "id" -o tsv
$kvId = az keyvault show -n "bankx-dev-kv" -g $ResourceGroupName --query "id" -o tsv

Write-Host "✓ Resource IDs retrieved" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Role Definition IDs (Built-in Azure Roles)
# ============================================================================

$roles = @{
    CognitiveServicesOpenAiUser = "5e0bd9bd-7b93-4f28-af87-19fc36ad61bd"
    CognitiveServicesUser = "a97b65f3-24c7-4388-baec-2e87135dc908"
    StorageBlobDataContributor = "ba92f5b4-2d11-453d-a403-e96b0029c9fe"
    SearchIndexDataReader = "1407120a-92aa-4202-b7e9-c0e197c71c8f"
    KeyVaultSecretsUser = "4633458b-17de-408a-b874-0445c86b69e6"
}

# ============================================================================
# Assign Roles - Copilot App
# ============================================================================

Write-Host "Assigning roles for Copilot App..." -ForegroundColor Yellow

if ($principalIds["copilotPrincipalId"]) {
    $copilotId = $principalIds["copilotPrincipalId"]
    
    # OpenAI User
    az role assignment create --assignee $copilotId --role $roles.CognitiveServicesOpenAiUser --scope $openAiId --output none
    Write-Host "✓ Copilot → OpenAI (Cognitive Services OpenAI User)" -ForegroundColor Green
    
    # AI Foundry User
    az role assignment create --assignee $copilotId --role $roles.CognitiveServicesUser --scope $aiFindryId --output none
    Write-Host "✓ Copilot → AI Foundry (Cognitive Services User)" -ForegroundColor Green
    
    # Document Intelligence User
    az role assignment create --assignee $copilotId --role $roles.CognitiveServicesUser --scope $docIntelId --output none
    Write-Host "✓ Copilot → Document Intelligence (Cognitive Services User)" -ForegroundColor Green
    
    # Storage Contributor
    az role assignment create --assignee $copilotId --role $roles.StorageBlobDataContributor --scope $storageId --output none
    Write-Host "✓ Copilot → Storage (Storage Blob Data Contributor)" -ForegroundColor Green
    
    # Key Vault Secrets User
    az role assignment create --assignee $copilotId --role $roles.KeyVaultSecretsUser --scope $kvId --output none
    Write-Host "✓ Copilot → Key Vault (Key Vault Secrets User)" -ForegroundColor Green
    
    # Cosmos DB (Data Plane)
    az cosmosdb sql role assignment create `
        --account-name "bankx-dev-cosmos" `
        --resource-group $ResourceGroupName `
        --scope "/" `
        --principal-id $copilotId `
        --role-definition-id "00000000-0000-0000-0000-000000000002" `
        --output none
    Write-Host "✓ Copilot → Cosmos DB (Data Contributor)" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# Assign Roles - ProdInfo MCP Service
# ============================================================================

Write-Host "Assigning roles for ProdInfo MCP Service..." -ForegroundColor Yellow

if ($principalIds["prodinfoPrincipalId"]) {
    $prodinfoId = $principalIds["prodinfoPrincipalId"]
    
    az role assignment create --assignee $prodinfoId --role $roles.CognitiveServicesOpenAiUser --scope $openAiId --output none
    Write-Host "✓ ProdInfo → OpenAI" -ForegroundColor Green
    
    az role assignment create --assignee $prodinfoId --role $roles.SearchIndexDataReader --scope $searchId --output none
    Write-Host "✓ ProdInfo → AI Search" -ForegroundColor Green
    
    az role assignment create --assignee $prodinfoId --role $roles.KeyVaultSecretsUser --scope $kvId --output none
    Write-Host "✓ ProdInfo → Key Vault" -ForegroundColor Green
    
    az cosmosdb sql role assignment create `
        --account-name "bankx-dev-cosmos" `
        --resource-group $ResourceGroupName `
        --scope "/" `
        --principal-id $prodinfoId `
        --role-definition-id "00000000-0000-0000-0000-000000000002" `
        --output none
    Write-Host "✓ ProdInfo → Cosmos DB" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# Assign Roles - MoneyCoach MCP Service
# ============================================================================

Write-Host "Assigning roles for MoneyCoach MCP Service..." -ForegroundColor Yellow

if ($principalIds["moneyCoachPrincipalId"]) {
    $moneyCoachId = $principalIds["moneyCoachPrincipalId"]
    
    az role assignment create --assignee $moneyCoachId --role $roles.CognitiveServicesOpenAiUser --scope $openAiId --output none
    Write-Host "✓ MoneyCoach → OpenAI" -ForegroundColor Green
    
    az role assignment create --assignee $moneyCoachId --role $roles.SearchIndexDataReader --scope $searchId --output none
    Write-Host "✓ MoneyCoach → AI Search" -ForegroundColor Green
    
    az role assignment create --assignee $moneyCoachId --role $roles.KeyVaultSecretsUser --scope $kvId --output none
    Write-Host "✓ MoneyCoach → Key Vault" -ForegroundColor Green
    
    az cosmosdb sql role assignment create `
        --account-name "bankx-dev-cosmos" `
        --resource-group $ResourceGroupName `
        --scope "/" `
        --principal-id $moneyCoachId `
        --role-definition-id "00000000-0000-0000-0000-000000000002" `
        --output none
    Write-Host "✓ MoneyCoach → Cosmos DB" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# Assign Roles - Escalation MCP Service
# ============================================================================

Write-Host "Assigning roles for Escalation MCP Service..." -ForegroundColor Yellow

if ($principalIds["escalationPrincipalId"]) {
    $escalationId = $principalIds["escalationPrincipalId"]
    
    az role assignment create --assignee $escalationId --role $roles.KeyVaultSecretsUser --scope $kvId --output none
    Write-Host "✓ Escalation → Key Vault" -ForegroundColor Green
    
    az cosmosdb sql role assignment create `
        --account-name "bankx-dev-cosmos" `
        --resource-group $ResourceGroupName `
        --scope "/" `
        --principal-id $escalationId `
        --role-definition-id "00000000-0000-0000-0000-000000000002" `
        --output none
    Write-Host "✓ Escalation → Cosmos DB" -ForegroundColor Green
}

Write-Host ""

# ============================================================================
# Assign Roles - Audit MCP Service
# ============================================================================

Write-Host "Assigning roles for Audit MCP Service..." -ForegroundColor Yellow

if ($principalIds["auditPrincipalId"]) {
    $auditId = $principalIds["auditPrincipalId"]
    
    az role assignment create --assignee $auditId --role $roles.KeyVaultSecretsUser --scope $kvId --output none
    Write-Host "✓ Audit → Key Vault" -ForegroundColor Green
    
    az cosmosdb sql role assignment create `
        --account-name "bankx-dev-cosmos" `
        --resource-group $ResourceGroupName `
        --scope "/" `
        --principal-id $auditId `
        --role-definition-id "00000000-0000-0000-0000-000000000002" `
        --output none
    Write-Host "✓ Audit → Cosmos DB" -ForegroundColor Green
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "✓ All RBAC role assignments completed!" -ForegroundColor Green
Write-Host "============================================================================" -ForegroundColor Cyan
