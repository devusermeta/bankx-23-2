// ============================================================================
// AI Search Module: Azure AI Search Service
// ============================================================================
// Note: Indexes must be created post-deployment via Python script
// ============================================================================

@description('Azure region for resources')
param location string

@description('Environment name')
param environment string

@description('Search service name')
param searchServiceName string

@description('Resource tags')
param tags object

@description('Search service SKU')
@allowed(['basic', 'standard', 'standard2', 'standard3', 'storage_optimized_l1', 'storage_optimized_l2'])
param searchSku string = 'standard'

// ============================================================================
// AZURE AI SEARCH SERVICE
// ============================================================================

resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  sku: {
    name: searchSku
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
    networkRuleSet: {
      ipRules: []
    }
    encryptionWithCmk: {
      enforcement: 'Unspecified'
    }
    disableLocalAuth: false
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
    semanticSearch: 'free'
  }
  tags: tags
}

// ============================================================================
// OUTPUTS
// ============================================================================

output searchServiceId string = searchService.id
output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
output searchServiceName string = searchService.name

// Note: Search indexes must be created using post-deployment script:
// - bankx-products-faq (UC2)
// - bankx-money-coach (UC3)
// Use scripts/setup-search-indexes.py
