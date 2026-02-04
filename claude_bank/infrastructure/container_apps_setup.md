# Azure Container Apps Deployment Guide

This guide provides step-by-step instructions for deploying the BankX Multi-Agent System to Azure Container Apps.

## Prerequisites

1. **Azure CLI** - Install and login:
   ```bash
   az login
   az account set --subscription <subscription-id>
   ```

2. **Azure Subscription** with permissions to create:
   - Resource Groups
   - Azure Container Registry
   - Container Apps
   - Container Apps Environment

3. **Provisioned Azure Resources** (from `azure_provision.py`):
   - Redis Cache (or Azure Cache for Redis)
   - Cosmos DB
   - Azure OpenAI
   - Storage Account

## Quick Start

### 1. Set Environment Variables

```bash
# Azure settings
export SUBSCRIPTION_ID="your-subscription-id"
export RESOURCE_GROUP="bankx-agents-rg"
export LOCATION="eastus"

# Container Apps settings
export CONTAINER_ENV="bankx-agents-env"
export CONTAINER_REGISTRY="bankxagentsacr"

# Azure services (from provisioning)
export REDIS_CONNECTION="your-redis-connection-string"
export COSMOS_ENDPOINT="https://bankx-cosmos.documents.azure.com:443/"
export COSMOS_KEY="your-cosmos-key"
export OPENAI_ENDPOINT="https://bankx-openai.openai.azure.com"
export OPENAI_KEY="your-openai-key"
```

### 2. Run Deployment Script

```bash
python infrastructure/deploy_container_apps.py \
  --subscription-id "$SUBSCRIPTION_ID" \
  --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" \
  --environment "$CONTAINER_ENV" \
  --registry "$CONTAINER_REGISTRY" \
  --redis-connection "$REDIS_CONNECTION" \
  --cosmos-endpoint "$COSMOS_ENDPOINT" \
  --cosmos-key "$COSMOS_KEY" \
  --openai-endpoint "$OPENAI_ENDPOINT" \
  --openai-key "$OPENAI_KEY"
```

## What Gets Deployed

The deployment script creates the following Azure resources:

### 1. Azure Container Registry (ACR)
- **Name**: `bankxagentsacr` (or custom)
- **SKU**: Basic
- **Purpose**: Stores Docker images for all agents

### 2. Container Apps Environment
- **Name**: `bankx-agents-env` (or custom)
- **Purpose**: Shared environment for all container apps
- **Features**: Built-in load balancing, automatic scaling, networking

### 3. Agent Registry Service
- **Name**: `agent-registry`
- **Image**: `bankxagentsacr.azurecr.io/bankx/agent-registry:1.0.0`
- **Port**: 9000
- **Replicas**: 2-5 (auto-scaling)
- **Ingress**: Internal (only accessible within environment)
- **Resources**: 0.5 CPU, 1 GiB memory

### 4. Domain Agents

#### Account Agent
- **Name**: `account-agent`
- **Port**: 8100
- **Replicas**: 2-10
- **Capabilities**: account.balance, account.limits, account.disambiguation

#### Transaction Agent
- **Name**: `transaction-agent`
- **Port**: 8101
- **Replicas**: 2-10
- **Capabilities**: transaction.history, transaction.aggregation

#### Payment Agent
- **Name**: `payment-agent`
- **Port**: 8102
- **Replicas**: 2-10
- **Capabilities**: payment.transfer, payment.validate

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Azure Container Apps Environment                │
│                                                          │
│  ┌────────────────────┐    ┌───────────────────────┐   │
│  │  Agent Registry    │    │   Account Agent       │   │
│  │  (2-5 replicas)    │    │   (2-10 replicas)     │   │
│  │  Port: 9000        │◄───┤   Port: 8100          │   │
│  └────────────────────┘    └───────────────────────┘   │
│           ▲                                             │
│           │                ┌───────────────────────┐   │
│           │                │  Transaction Agent    │   │
│           └────────────────┤  (2-10 replicas)      │   │
│                            │  Port: 8101           │   │
│                            └───────────────────────┘   │
│                                                         │
│                            ┌───────────────────────┐   │
│                            │  Payment Agent        │   │
│                            │  (2-10 replicas)      │   │
│                            │  Port: 8102           │   │
│                            └───────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                    │                    │
                    ▼                    ▼
        ┌─────────────────┐   ┌──────────────────┐
        │  Azure Redis    │   │  Cosmos DB       │
        │  (Cache)        │   │  (Persistence)   │
        └─────────────────┘   └──────────────────┘
```

## Networking

### Internal Communication
- All agents communicate via **internal ingress**
- Agent Registry has internal FQDN: `agent-registry.internal.{env-name}.eastus.azurecontainerapps.io`
- Agents discover each other through registry
- No public internet access required for A2A calls

### External Access (Optional)
To expose the Copilot API (Supervisor Agent) publicly:

```bash
az containerapp create \
  --name supervisor-agent \
  --resource-group bankx-agents-rg \
  --environment bankx-agents-env \
  --image bankxagentsacr.azurecr.io/bankx/supervisor-agent:1.0.0 \
  --target-port 8080 \
  --ingress external \  # PUBLIC access
  --min-replicas 2 \
  --max-replicas 20
```

## Auto-Scaling

Container Apps automatically scales based on:
- **HTTP traffic**: Requests per second
- **CPU utilization**: Percentage
- **Memory utilization**: Percentage

### Default Scaling Rules
```yaml
min_replicas: 2        # Always keep 2 instances running
max_replicas: 10       # Scale up to 10 instances under load
scale_rule: http       # Scale based on concurrent HTTP requests
```

### Custom Scaling (if needed)
```bash
az containerapp update \
  --name account-agent \
  --resource-group bankx-agents-rg \
  --scale-rule-name http-rule \
  --scale-rule-type http \
  --scale-rule-http-concurrency 50  # Scale when > 50 concurrent requests
```

## Monitoring

### View Logs
```bash
# Real-time logs
az containerapp logs show \
  --name agent-registry \
  --resource-group bankx-agents-rg \
  --follow

# Tail logs
az containerapp logs tail \
  --name account-agent \
  --resource-group bankx-agents-rg
```

### Check Health
```bash
# Get agent registry status
az containerapp show \
  --name agent-registry \
  --resource-group bankx-agents-rg \
  --query "properties.runningStatus"
```

### View Metrics
```bash
# List revisions
az containerapp revision list \
  --name account-agent \
  --resource-group bankx-agents-rg \
  --output table

# Get replica count
az containerapp replica list \
  --name account-agent \
  --resource-group bankx-agents-rg \
  --output table
```

## Updating Agents

### Update Single Agent
```bash
# Build new image
az acr build \
  --registry bankxagentsacr \
  --image bankx/account-agent:1.1.0 \
  --file app/agents/account-agent/Dockerfile \
  app/agents/account-agent

# Update container app
az containerapp update \
  --name account-agent \
  --resource-group bankx-agents-rg \
  --image bankxagentsacr.azurecr.io/bankx/account-agent:1.1.0
```

### Rolling Updates
Container Apps automatically performs **zero-downtime rolling updates**:
1. Creates new revision with updated image
2. Gradually shifts traffic to new revision
3. Removes old revision when traffic shifted

## Troubleshooting

### Agent Not Registering
```bash
# Check agent logs
az containerapp logs show --name account-agent --resource-group bankx-agents-rg

# Verify registry is running
az containerapp show --name agent-registry --resource-group bankx-agents-rg

# Check network connectivity
az containerapp exec \
  --name account-agent \
  --resource-group bankx-agents-rg \
  --command curl agent-registry:9000/health
```

### Scaling Issues
```bash
# Check current replicas
az containerapp replica list \
  --name account-agent \
  --resource-group bankx-agents-rg

# View scaling rules
az containerapp show \
  --name account-agent \
  --resource-group bankx-agents-rg \
  --query "properties.template.scale"
```

### Performance Issues
```bash
# Increase resources
az containerapp update \
  --name account-agent \
  --resource-group bankx-agents-rg \
  --cpu 1.0 \
  --memory 2Gi
```

## Cost Optimization

### Development Environment
```yaml
min_replicas: 0      # Scale to zero when not in use
max_replicas: 2      # Limit maximum instances
cpu: 0.25            # Minimum CPU
memory: 0.5Gi        # Minimum memory
```

### Production Environment
```yaml
min_replicas: 2      # Always available
max_replicas: 20     # Handle traffic spikes
cpu: 1.0             # Higher performance
memory: 2Gi          # More memory for caching
```

## Security

### Managed Identity
Enable managed identity for agents to access Azure resources:

```bash
az containerapp identity assign \
  --name account-agent \
  --resource-group bankx-agents-rg \
  --system-assigned
```

### Secrets Management
Store sensitive values as secrets:

```bash
az containerapp secret set \
  --name account-agent \
  --resource-group bankx-agents-rg \
  --secrets openai-key=your-key cosmos-key=your-key

# Reference in environment variables
az containerapp update \
  --name account-agent \
  --resource-group bankx-agents-rg \
  --set-env-vars \
    AZURE_OPENAI_API_KEY=secretref:openai-key \
    AZURE_COSMOS_KEY=secretref:cosmos-key
```

## Clean Up

### Delete All Container Apps
```bash
az containerapp delete --name agent-registry --resource-group bankx-agents-rg --yes
az containerapp delete --name account-agent --resource-group bankx-agents-rg --yes
az containerapp delete --name transaction-agent --resource-group bankx-agents-rg --yes
az containerapp delete --name payment-agent --resource-group bankx-agents-rg --yes
```

### Delete Environment
```bash
az containerapp env delete \
  --name bankx-agents-env \
  --resource-group bankx-agents-rg \
  --yes
```

### Delete Resource Group (ALL resources)
```bash
az group delete \
  --name bankx-agents-rg \
  --yes
```

## Next Steps

1. ✅ Deploy MCP services (separate container apps)
2. ✅ Deploy Supervisor Agent with public ingress
3. ✅ Configure Application Insights for monitoring
4. ✅ Set up CI/CD with GitHub Actions or Azure DevOps
5. ✅ Configure custom domains and TLS certificates

## Support

For issues or questions:
- Container Apps Documentation: https://learn.microsoft.com/azure/container-apps/
- BankX Architecture Team: architecture@bankx.com
