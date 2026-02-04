// ============================================================================
// RBAC Module: Role Assignment Information (Output Only)
// ============================================================================
// Due to Bicep limitations with scope references across modules,
// actual role assignments are done via PowerShell script
// This module collects and outputs all necessary information
// ============================================================================

// ============================================================================
// PARAMETERS - Managed Identity Principal IDs
// ============================================================================

@description('Copilot App Managed Identity Principal ID')
param copilotManagedIdentityPrincipalId string

@description('ProdInfo MCP Service Managed Identity Principal ID')
param prodinfoManagedIdentityPrincipalId string

@description('Money Coach MCP Service Managed Identity Principal ID')
param moneyCoachManagedIdentityPrincipalId string

@description('Escalation Comms MCP Service Managed Identity Principal ID')
param escalationManagedIdentityPrincipalId string

@description('Audit MCP Service Managed Identity Principal ID')
param auditManagedIdentityPrincipalId string

// ============================================================================
// PARAMETERS - Azure Resource IDs
// ============================================================================

@description('Azure OpenAI Account Resource ID')
param openAiAccountId string

@description('Azure AI Foundry Account Resource ID')
param aiFindryAccountId string

@description('Document Intelligence Resource ID')
param documentIntelligenceId string

@description('AI Search Service Resource ID')
param searchServiceId string

@description('Cosmos DB Account Resource ID')
param cosmosDbAccountId string

@description('Storage Account Resource ID')
param storageAccountId string

@description('Key Vault Resource ID')
param keyVaultId string

// ============================================================================
// OUTPUTS - For PowerShell Role Assignment Script
// ============================================================================

output copilotPrincipalId string = copilotManagedIdentityPrincipalId
output prodinfoPrincipalId string = prodinfoManagedIdentityPrincipalId
output moneyCoachPrincipalId string = moneyCoachManagedIdentityPrincipalId
output escalationPrincipalId string = escalationManagedIdentityPrincipalId
output auditPrincipalId string = auditManagedIdentityPrincipalId

output openAiResourceId string = openAiAccountId
output aiFindryResourceId string = aiFindryAccountId
output documentIntelligenceResourceId string = documentIntelligenceId
output searchServiceResourceId string = searchServiceId
output cosmosDbResourceId string = cosmosDbAccountId
output storageResourceId string = storageAccountId
output keyVaultResourceId string = keyVaultId

// Note: Role assignments must be done post-deployment using:
// scripts/assign-rbac-roles.ps1
