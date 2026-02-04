// ============================================================================
// AI Services Module: Azure OpenAI, AI Foundry, Document Intelligence
// ============================================================================

@description('Azure region for resources')
param location string

@description('Environment name')
param environment string

@description('Azure OpenAI account name')
param openAiAccountName string

@description('Azure AI Foundry account name')
param aiFindryAccountName string

@description('Document Intelligence account name')
param documentIntelligenceName string

@description('OpenAI GPT-4o deployment name')
param openAiDeploymentName string = 'gpt-4o'

@description('OpenAI gpt-4.1-mini deployment name')
param openAiMiniDeploymentName string = 'gpt-4.1-mini'

@description('Resource tags')
param tags object

// ============================================================================
// AZURE OPENAI SERVICE
// ============================================================================

resource openAiAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAiAccountName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'OpenAI'
  properties: {
    customSubDomainName: openAiAccountName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
  tags: tags
}

// GPT-4o Deployment
resource gpt4oDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openAiAccount
  name: openAiDeploymentName
  sku: {
    name: 'Standard'
    capacity: 50
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-08-06'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
    raiPolicyName: 'Microsoft.Default'
  }
}

// gpt-4.1-mini Deployment
resource gpt4oMiniDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openAiAccount
  name: openAiMiniDeploymentName
  sku: {
    name: 'Standard'
    capacity: 50
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1-mini'
      version: '2024-07-18'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
    raiPolicyName: 'Microsoft.Default'
  }
  dependsOn: [
    gpt4oDeployment
  ]
}

// text-embedding-ada-002 Deployment (for vector search)
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openAiAccount
  name: 'text-embedding-ada-002'
  sku: {
    name: 'Standard'
    capacity: 50
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-ada-002'
      version: '2'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
    raiPolicyName: 'Microsoft.Default'
  }
  dependsOn: [
    gpt4oMiniDeployment
  ]
}

// ============================================================================
// AZURE AI FOUNDRY (AI Services Hub)
// ============================================================================

resource aiFindryAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: aiFindryAccountName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'AIServices'
  properties: {
    customSubDomainName: aiFindryAccountName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
  tags: tags
}

// ============================================================================
// AZURE DOCUMENT INTELLIGENCE (Form Recognizer)
// ============================================================================

resource documentIntelligence 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: documentIntelligenceName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'FormRecognizer'
  properties: {
    customSubDomainName: documentIntelligenceName
    publicNetworkAccess: 'Enabled'
    networkAcls: {
      defaultAction: 'Allow'
    }
  }
  tags: tags
}

// ============================================================================
// OUTPUTS
// ============================================================================

output openAiAccountId string = openAiAccount.id
output openAiEndpoint string = openAiAccount.properties.endpoint
output openAiAccountName string = openAiAccount.name

output aiFindryAccountId string = aiFindryAccount.id
output aiFindryEndpoint string = aiFindryAccount.properties.endpoint
output aiFindryAccountName string = aiFindryAccount.name

output documentIntelligenceId string = documentIntelligence.id
output documentIntelligenceEndpoint string = documentIntelligence.properties.endpoint
output documentIntelligenceName string = documentIntelligence.name
