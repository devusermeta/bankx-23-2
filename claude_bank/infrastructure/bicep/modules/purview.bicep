// ============================================================================
// Purview Module: Data Governance and Lineage Tracking
// ============================================================================
// Note: Purview RBAC roles must be assigned manually via Portal or REST API
// ============================================================================

@description('Azure region for resources')
param location string

@description('Environment name')
param environment string

@description('Purview account name')
param purviewAccountName string

@description('Resource tags')
param tags object

// ============================================================================
// PURVIEW ACCOUNT
// ============================================================================

resource purviewAccount 'Microsoft.Purview/accounts@2021-12-01' = {
  name: purviewAccountName
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
    managedResourceGroupName: 'managed-rg-purview-${purviewAccountName}'
  }
  tags: tags
}

// ============================================================================
// OUTPUTS
// ============================================================================

output purviewAccountId string = purviewAccount.id
output purviewEndpoint string = 'https://${purviewAccount.name}.purview.azure.com'
output purviewCatalogEndpoint string = purviewAccount.properties.endpoints.catalog
output purviewScanEndpoint string = purviewAccount.properties.endpoints.scan
output purviewAccountName string = purviewAccount.name
output purviewManagedIdentityPrincipalId string = purviewAccount.identity.principalId

// ⚠️ IMPORTANT: Purview RBAC (Data Curator role) must be assigned manually
// Go to: https://{purviewAccountName}.purview.azure.com
// Navigate to: Data Map → Collections → Root Collection → Role assignments
// Add 7 Service Principals to "Data Curators" role
// See: scripts/setup-purview-rbac.py for automation
