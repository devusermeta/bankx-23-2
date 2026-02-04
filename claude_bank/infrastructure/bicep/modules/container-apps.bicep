// ============================================================================
// Container Apps Module: Container Apps Environment and Applications
// ============================================================================

@description('Azure region for resources')
param location string

@description('Environment name')
param environment string

@description('Name prefix for resources')
param namePrefix string

@description('Log Analytics Workspace ID')
param logAnalyticsWorkspaceId string

@description('Application Insights Connection String')
param appInsightsConnectionString string

@description('Resource tags')
param tags object

// ============================================================================
// CONTAINER APPS ENVIRONMENT
// ============================================================================

resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: '${namePrefix}-containerenv'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: reference(logAnalyticsWorkspaceId, '2022-10-01').customerId
        sharedKey: listKeys(logAnalyticsWorkspaceId, '2022-10-01').primarySharedKey
      }
    }
    zoneRedundant: false
  }
  tags: tags
}

// ============================================================================
// CONTAINER APP 1: COPILOT BACKEND (FastAPI)
// ============================================================================

resource copilotApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${namePrefix}-copilot'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8080
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
      dapr: {
        enabled: false
      }
    }
    template: {
      containers: [
        {
          name: 'copilot'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // Placeholder
          resources: {
            cpu: json('1.0')
            memory: '2Gi'
          }
          env: [
            {
              name: 'PROFILE'
              value: environment
            }
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: appInsightsConnectionString
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
      }
    }
  }
  tags: tags
}

// ============================================================================
// CONTAINER APP 2: PRODINFO FAQ MCP SERVICE
// ============================================================================

resource prodinfoApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${namePrefix}-prodinfo'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8076
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'prodinfo'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // Placeholder
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'PROFILE'
              value: environment
            }
            {
              name: 'PORT'
              value: '8076'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
  tags: tags
}

// ============================================================================
// CONTAINER APP 3: AI MONEY COACH MCP SERVICE
// ============================================================================

resource moneyCoachApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${namePrefix}-moneycoach'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8077
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'moneycoach'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // Placeholder
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'PROFILE'
              value: environment
            }
            {
              name: 'PORT'
              value: '8077'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
  tags: tags
}

// ============================================================================
// CONTAINER APP 4: ESCALATION COMMS MCP SERVICE
// ============================================================================

resource escalationApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${namePrefix}-escalation'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8078
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'escalation'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // Placeholder
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'PROFILE'
              value: environment
            }
            {
              name: 'PORT'
              value: '8078'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
  tags: tags
}

// ============================================================================
// CONTAINER APP 5: AUDIT MCP SERVICE
// ============================================================================

resource auditApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${namePrefix}-audit'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8075
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'audit'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // Placeholder
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'PROFILE'
              value: environment
            }
            {
              name: 'PORT'
              value: '8075'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
  tags: tags
}

// ============================================================================
// CONTAINER APP 6: FRONTEND (React/Vite)
// ============================================================================

resource frontendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${namePrefix}-frontend'
  location: location
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8081
        allowInsecure: false
        traffic: [
          {
            latestRevision: true
            weight: 100
          }
        ]
      }
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest' // Placeholder
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'VITE_BACKEND_URI'
              value: 'https://${copilotApp.properties.configuration.ingress.fqdn}'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
  tags: tags
}

// ============================================================================
// OUTPUTS
// ============================================================================

output containerAppsEnvironmentId string = containerAppsEnvironment.id

// Managed Identity Principal IDs (for RBAC assignments)
output copilotManagedIdentityPrincipalId string = copilotApp.identity.principalId
output prodinfoManagedIdentityPrincipalId string = prodinfoApp.identity.principalId
output moneyCoachManagedIdentityPrincipalId string = moneyCoachApp.identity.principalId
output escalationManagedIdentityPrincipalId string = escalationApp.identity.principalId
output auditManagedIdentityPrincipalId string = auditApp.identity.principalId
output frontendManagedIdentityPrincipalId string = frontendApp.identity.principalId

// App FQDNs
output copilotAppFqdn string = copilotApp.properties.configuration.ingress.fqdn
output frontendAppFqdn string = frontendApp.properties.configuration.ingress.fqdn

// Note: Actual container images must be pushed to Azure Container Registry
// and referenced in azd deployment or CI/CD pipeline
