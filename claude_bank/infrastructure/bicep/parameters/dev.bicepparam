using '../main.bicep'

// ============================================================================
// Development Environment Parameters
// ============================================================================

param environment = 'dev'
param projectName = 'bankx'
param location = 'eastus'
param enablePurview = true

param openAiDeploymentName = 'gpt-4o'
param openAiMiniDeploymentName = 'gpt-4.1-mini'

param tags = {
  project: 'BankX'
  environment: 'dev'
  managedBy: 'Bicep'
  owner: 'DevTeam'
  costCenter: 'Engineering'
}
