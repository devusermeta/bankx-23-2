// ============================================================================
// Cosmos DB Module: NoSQL Database with RBAC Role Definitions
// ============================================================================

@description('Azure region for resources')
param location string

@description('Environment name')
param environment string

@description('Cosmos DB account name')
param cosmosDbAccountName string

@description('Resource tags')
param tags object

@description('Database name')
param databaseName string = 'bankx'

// ============================================================================
// COSMOS DB ACCOUNT (Serverless)
// ============================================================================

resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: cosmosDbAccountName
  location: location
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: false
    enableMultipleWriteLocations: false
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    publicNetworkAccess: 'Enabled'
    enableFreeTier: false
    disableKeyBasedMetadataWriteAccess: false
  }
  tags: tags
}

// ============================================================================
// COSMOS DB DATABASE
// ============================================================================

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  parent: cosmosDbAccount
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
  }
}

// ============================================================================
// COSMOS DB CONTAINERS
// ============================================================================

// Container 1: Support Tickets (UC2/UC3)
resource supportTicketsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'support_tickets'
  properties: {
    resource: {
      id: 'support_tickets'
      partitionKey: {
        paths: [
          '/ticket_id'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
  }
}

// Container 2: Conversations (Chat History)
resource conversationsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'Conversations'
  properties: {
    resource: {
      id: 'Conversations'
      partitionKey: {
        paths: [
          '/session_id'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
      }
    }
  }
}

// Container 3: Decision Ledger (Audit Trails)
resource decisionLedgerContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'decision_ledger'
  properties: {
    resource: {
      id: 'decision_ledger'
      partitionKey: {
        paths: [
          '/agent_id'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
      }
    }
  }
}

// ============================================================================
// OUTPUTS
// ============================================================================

output cosmosDbAccountId string = cosmosDbAccount.id
output cosmosDbEndpoint string = cosmosDbAccount.properties.documentEndpoint
output cosmosDbAccountName string = cosmosDbAccount.name
output databaseName string = database.name

// Built-in Cosmos DB RBAC Role Definition IDs (Data Plane)
output cosmosDataContributorRoleId string = '${cosmosDbAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
output cosmosDataReaderRoleId string = '${cosmosDbAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000001'
