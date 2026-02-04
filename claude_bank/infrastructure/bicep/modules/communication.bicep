// ============================================================================
// Communication Services Module: Email Notifications
// ============================================================================

@description('Azure region (Communication Services is global)')
param location string

@description('Environment name')
param environment string

@description('Communication service name')
param communicationServiceName string

@description('Resource tags')
param tags object

// ============================================================================
// COMMUNICATION SERVICE
// ============================================================================

resource communicationService 'Microsoft.Communication/communicationServices@2023-04-01' = {
  name: communicationServiceName
  location: location
  properties: {
    dataLocation: 'United States'
  }
  tags: tags
}

// ============================================================================
// OUTPUTS
// ============================================================================

output communicationServiceId string = communicationService.id
output communicationServiceName string = communicationService.name

// Note: Connection string must be retrieved via Azure CLI or Portal:
// az communication list-key --name <name> --resource-group <rg>
// Store in Key Vault using post-deployment script
