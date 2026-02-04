// ============================================================================
// BankX Multi-Agent Banking System - Main Infrastructure Template
// ============================================================================
// This template orchestrates all Azure resources in a single resource group
// Version: 1.0
// Last Updated: 2025-11-21
// ============================================================================

targetScope = 'resourceGroup'

// ============================================================================
// PARAMETERS
// ============================================================================

@description('Environment name (dev, staging, prod)')
@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'

@description('Project name prefix for resource naming')
param projectName string = 'bankx'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('Azure OpenAI deployment name for GPT-4o')
param openAiDeploymentName string = 'gpt-4o'

@description('Azure OpenAI mini deployment name for gpt-4.1-mini')
param openAiMiniDeploymentName string = 'gpt-4.1-mini'

@description('Tenant ID for Entra ID authentication')
param tenantId string = tenant().tenantId

@description('Enable Purview data lineage tracking')
param enablePurview bool = true

@description('Tags to apply to all resources')
param tags object = {
  project: 'BankX'
  environment: environment
  managedBy: 'Bicep'
  createdDate: utcNow('yyyy-MM-dd')
}

// ============================================================================
// VARIABLES
// ============================================================================

var namePrefix = '${projectName}-${environment}'
var namePrefixNoHyphen = '${projectName}${environment}'

// Resource names
var openAiAccountName = '${namePrefix}-openai'
var aiFindryAccountName = '${namePrefix}-aifoundry'
var searchServiceName = '${namePrefix}-search'
var cosmosDbAccountName = '${namePrefix}-cosmos'
var storageAccountName = '${namePrefixNoHyphen}storage'
var documentIntelligenceName = '${namePrefix}-docintel'
var communicationServiceName = '${namePrefix}-commservice'
var keyVaultName = '${namePrefix}-kv'
var appInsightsName = '${namePrefix}-appinsights'
var purviewAccountName = '${projectName}-purview'
var logAnalyticsName = '${namePrefix}-logs'

// ============================================================================
// MODULE 1: MONITORING (Deploy first - needed by other resources)
// ============================================================================

module monitoring './modules/monitoring.bicep' = {
  name: 'monitoring-deployment'
  params: {
    location: location
    environment: environment
    appInsightsName: appInsightsName
    logAnalyticsName: logAnalyticsName
    tags: tags
  }
}

// ============================================================================
// MODULE 2: AI SERVICES (OpenAI, AI Foundry, Document Intelligence)
// ============================================================================

module aiServices './modules/ai-services.bicep' = {
  name: 'ai-services-deployment'
  params: {
    location: location
    environment: environment
    openAiAccountName: openAiAccountName
    aiFindryAccountName: aiFindryAccountName
    documentIntelligenceName: documentIntelligenceName
    openAiDeploymentName: openAiDeploymentName
    openAiMiniDeploymentName: openAiMiniDeploymentName
    tags: tags
  }
}

// ============================================================================
// MODULE 3: AI SEARCH
// ============================================================================

module search './modules/search.bicep' = {
  name: 'search-deployment'
  params: {
    location: location
    environment: environment
    searchServiceName: searchServiceName
    tags: tags
  }
}

// ============================================================================
// MODULE 4: COSMOS DB (with RBAC role definitions)
// ============================================================================

module cosmos './modules/cosmos.bicep' = {
  name: 'cosmos-deployment'
  params: {
    location: location
    environment: environment
    cosmosDbAccountName: cosmosDbAccountName
    tags: tags
  }
}

// ============================================================================
// MODULE 5: STORAGE ACCOUNT
// ============================================================================

module storage './modules/storage.bicep' = {
  name: 'storage-deployment'
  params: {
    location: location
    environment: environment
    storageAccountName: storageAccountName
    tags: tags
  }
}

// ============================================================================
// MODULE 6: COMMUNICATION SERVICES
// ============================================================================

module communication './modules/communication.bicep' = {
  name: 'communication-deployment'
  params: {
    location: 'global'
    environment: environment
    communicationServiceName: communicationServiceName
    tags: tags
  }
}

// ============================================================================
// MODULE 7: KEY VAULT
// ============================================================================

module keyVault './modules/keyvault.bicep' = {
  name: 'keyvault-deployment'
  params: {
    location: location
    environment: environment
    keyVaultName: keyVaultName
    tenantId: tenantId
    tags: tags
  }
}

// ============================================================================
// MODULE 8: PURVIEW (Optional - for data lineage)
// ============================================================================

module purview './modules/purview.bicep' = if (enablePurview) {
  name: 'purview-deployment'
  params: {
    location: location
    environment: environment
    purviewAccountName: purviewAccountName
    tags: tags
  }
}

// ============================================================================
// MODULE 9: CONTAINER APPS ENVIRONMENT & APPS
// ============================================================================

module containerApps './modules/container-apps.bicep' = {
  name: 'container-apps-deployment'
  params: {
    location: location
    environment: environment
    namePrefix: namePrefix
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    tags: tags
  }
}

// ============================================================================
// MODULE 10: IAM ROLE ASSIGNMENTS
// ============================================================================

module rbac './modules/rbac.bicep' = {
  name: 'rbac-deployment'
  params: {
    // Managed Identities from Container Apps
    copilotManagedIdentityPrincipalId: containerApps.outputs.copilotManagedIdentityPrincipalId
    prodinfoManagedIdentityPrincipalId: containerApps.outputs.prodinfoManagedIdentityPrincipalId
    moneyCoachManagedIdentityPrincipalId: containerApps.outputs.moneyCoachManagedIdentityPrincipalId
    escalationManagedIdentityPrincipalId: containerApps.outputs.escalationManagedIdentityPrincipalId
    auditManagedIdentityPrincipalId: containerApps.outputs.auditManagedIdentityPrincipalId
    
    // Resource IDs
    openAiAccountId: aiServices.outputs.openAiAccountId
    aiFindryAccountId: aiServices.outputs.aiFindryAccountId
    documentIntelligenceId: aiServices.outputs.documentIntelligenceId
    searchServiceId: search.outputs.searchServiceId
    cosmosDbAccountId: cosmos.outputs.cosmosDbAccountId
    storageAccountId: storage.outputs.storageAccountId
    keyVaultId: keyVault.outputs.keyVaultId
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

@description('Resource Group Name')
output resourceGroupName string = resourceGroup().name

@description('Azure OpenAI Endpoint')
output openAiEndpoint string = aiServices.outputs.openAiEndpoint

@description('Azure AI Foundry Endpoint')
output aiFindryEndpoint string = aiServices.outputs.aiFindryEndpoint

@description('Azure AI Search Endpoint')
output searchEndpoint string = search.outputs.searchEndpoint

@description('Cosmos DB Endpoint')
output cosmosDbEndpoint string = cosmos.outputs.cosmosDbEndpoint

@description('Storage Account Name')
output storageAccountName string = storage.outputs.storageAccountName

@description('Key Vault URI')
output keyVaultUri string = keyVault.outputs.keyVaultUri

@description('Application Insights Connection String')
output appInsightsConnectionString string = monitoring.outputs.appInsightsConnectionString

@description('Purview Account Endpoint (if enabled)')
output purviewEndpoint string = enablePurview ? purview!.outputs.purviewEndpoint : ''

@description('Container Apps Environment ID')
output containerAppsEnvironmentId string = containerApps.outputs.containerAppsEnvironmentId

@description('Copilot App FQDN')
output copilotAppFqdn string = containerApps.outputs.copilotAppFqdn

@description('Frontend App FQDN')
output frontendAppFqdn string = containerApps.outputs.frontendAppFqdn
