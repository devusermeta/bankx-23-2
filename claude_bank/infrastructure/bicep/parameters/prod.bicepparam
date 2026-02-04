using '../main.bicep'

// ============================================================================
// Production Environment Parameters
// ============================================================================

param environment = 'prod'
param projectName = 'bankx'
param location = 'eastus'
param enablePurview = true

param openAiDeploymentName = 'gpt-4o'
param openAiMiniDeploymentName = 'gpt-4.1-mini'

param tags = {
  project: 'BankX'
  environment: 'prod'
  managedBy: 'Bicep'
  owner: 'ProductionTeam'
  costCenter: 'Operations'
}
