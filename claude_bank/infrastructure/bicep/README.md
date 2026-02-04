# BankX Infrastructure Deployment Guide

This folder contains modular Bicep templates for deploying the complete BankX Azure infrastructure to any subscription or tenant.

## 📁 Directory Structure

```
bicep/
├── main.bicep                      # Main orchestration template
├── modules/                        # Modular resource templates
│   ├── ai-services.bicep          # OpenAI + AI Foundry + Document Intelligence
│   ├── search.bicep               # Azure AI Search
│   ├── cosmos.bicep               # Cosmos DB with containers
│   ├── storage.bicep              # Storage Account + blob container
│   ├── keyvault.bicep             # Key Vault (RBAC-enabled)
│   ├── communication.bicep        # Communication Services (email)
│   ├── purview.bicep              # Purview (data lineage)
│   ├── monitoring.bicep           # Application Insights + Log Analytics
│   ├── container-apps.bicep       # Container Apps Environment + 6 apps
│   └── rbac.bicep                 # Output-only RBAC helper
├── parameters/
│   ├── dev.bicepparam             # Development environment parameters
│   └── prod.bicepparam            # Production environment parameters
└── scripts/
    ├── deploy.ps1                 # Main deployment orchestrator
    ├── assign-rbac-roles.ps1      # RBAC role assignment script
    ├── setup-purview-rbac.ps1     # Purview RBAC setup (manual)
    ├── setup-agents.py            # AI Foundry agent creation
    └── setup-search-indexes.py    # AI Search index creation
```

## 🎯 What Gets Deployed

### Azure Services (12 total)

1. **Azure OpenAI** - GPT-4o, gpt-4.1-mini, text-embedding-ada-002
2. **Azure AI Foundry (AI Services Hub)** - Agent management platform
3. **Azure AI Search** - Vector search service
4. **Azure Cosmos DB (Serverless)** - 3 containers (support_tickets, Conversations, decision_ledger)
5. **Azure Storage** - Blob storage for documents/invoices
6. **Azure Key Vault** - Secrets management (RBAC-enabled)
7. **Azure Communication Services** - Email notifications
8. **Azure Purview** - Data lineage tracking
9. **Application Insights** - Telemetry
10. **Log Analytics Workspace** - Monitoring
11. **Container Apps Environment** - Hosting platform
12. **Azure Document Intelligence** - Invoice OCR

### Container Apps (6 apps)

- **Copilot Service** (external ingress, port 8080)
- **ProdInfo MCP Service** (internal ingress, port 8001)
- **MoneyCoach MCP Service** (internal ingress, port 8002)
- **Escalation MCP Service** (internal ingress, port 8003)
- **Audit MCP Service** (internal ingress, port 8004)
- **Frontend App** (external ingress, port 8081)

All Container Apps have **system-assigned managed identities**.

## 🔐 Authentication & RBAC

### Managed Identities (Auto-Created)

- 1 managed identity per Container App (5 total)
- Used for passwordless authentication to Azure services

### Service Principals (Manual Creation Required)

You must create **7 Service Principals** for Purview access:

1. **AccountAgent** - Account operations
2. **TransactionAgent** - Transaction history
3. **PaymentAgent** - Payment processing
4. **ProdInfoAgent** - Product information
5. **MoneyCoachAgent** - Financial coaching
6. **EscalationAgent** - Escalation handling
7. **SupervisorAgent** - Supervisor oversight

### App Registration (Manual Creation Required)

- **Frontend User Authentication** (Entra ID OIDC)

## 📋 Prerequisites

### Required Tools

- **Azure CLI** v2.50+ ([Install](https://docs.microsoft.com/cli/azure/install-azure-cli))
- **Bicep CLI** v0.20+ (bundled with Azure CLI)
- **PowerShell 7+** ([Install](https://learn.microsoft.com/powershell/scripting/install/installing-powershell))
- **Python 3.9+** (for post-deployment scripts)

### Required Azure Permissions

In the **target subscription**, you need:

- `Owner` role (for RBAC assignments), OR
- `Contributor` + `User Access Administrator` roles

### Azure Resource Providers

Ensure these providers are registered in the target subscription:

```powershell
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.Search
az provider register --namespace Microsoft.DocumentDB
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.Communication
az provider register --namespace Microsoft.Purview
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.App
```

## 🚀 Deployment Steps

### Step 1: Customize Parameters

Edit `parameters/dev.bicepparam` or `parameters/prod.bicepparam`:

```bicep
using '../main.bicep'

param environment = 'dev'              // 'dev', 'staging', or 'prod'
param location = 'eastus'              // Azure region
param resourceGroupName = 'bankx-dev-rg'

// Optional: Override default names
param openAiName = 'bankx-dev-openai'
param aiFindryName = 'bankx-dev-aifoundry'
// ... etc
```

### Step 2: Run Deployment Script

```powershell
cd infrastructure/bicep/scripts

# Deploy to dev environment
.\deploy.ps1 `
    -SubscriptionId "your-subscription-id" `
    -ResourceGroupName "bankx-dev-rg" `
    -Environment "dev" `
    -Location "eastus"

# Deploy to prod environment
.\deploy.ps1 `
    -SubscriptionId "your-subscription-id" `
    -ResourceGroupName "bankx-prod-rg" `
    -Environment "prod" `
    -Location "eastus"
```

**Deployment time**: 15-20 minutes

### Step 3: Post-Deployment Configuration

The deployment script will guide you through these steps:

#### 3.1 Verify RBAC Assignments

The script automatically assigns RBAC roles to managed identities:

- ✅ Copilot → OpenAI, AI Foundry, Document Intelligence, Storage, Key Vault, Cosmos DB
- ✅ ProdInfo → OpenAI, AI Search, Key Vault, Cosmos DB
- ✅ MoneyCoach → OpenAI, AI Search, Key Vault, Cosmos DB
- ✅ Escalation → Key Vault, Cosmos DB
- ✅ Audit → Key Vault, Cosmos DB

#### 3.2 Create Service Principals (Manual)

For each of the 7 Service Principals:

```bash
# Example: Create AccountAgent Service Principal
az ad sp create-for-rbac --name "BankX-AccountAgent-Dev" --skip-assignment

# Save the output:
# - appId (Client ID)
# - password (Client Secret)
# - tenant (Tenant ID)
```

Repeat for all 7 agents: Account, Transaction, Payment, ProdInfo, MoneyCoach, Escalation, Supervisor.

#### 3.3 Assign Purview RBAC (Manual)

Purview RBAC **cannot** be assigned via Bicep/ARM. Use Azure Portal:

1. Navigate to **Azure Purview** → **bankx-dev-purview**
2. Go to **Data map** → **Collections** → **Root Collection**
3. Click **Role assignments**
4. Add each Service Principal with **Data Curator** role

Or run the helper script (provides manual instructions):

```powershell
.\setup-purview-rbac.ps1 -ResourceGroupName "bankx-dev-rg"
```

#### 3.4 Create AI Foundry Agents

```bash
# Install Python dependencies
pip install azure-ai-projects azure-identity

# Run agent creation script
python setup-agents.py --resource-group bankx-dev-rg --environment dev
```

This creates 7 agents in AI Foundry and outputs agent IDs for your `.env` file.

#### 3.5 Create AI Search Indexes

```bash
# Install Python dependencies
pip install azure-search-documents azure-identity

# Run index creation script
python setup-search-indexes.py --resource-group bankx-dev-rg --environment dev
```

This creates 2 indexes:
- **bankx-products-faq** (UC2: Product information)
- **bankx-money-coach** (UC3: Financial coaching)

#### 3.6 Store Secrets in Key Vault

```bash
# Communication Services connection string
az keyvault secret set --vault-name bankx-dev-kv --name "CommunicationServicesConnectionString" --value "your-connection-string"

# Service Principal credentials (7 agents)
az keyvault secret set --vault-name bankx-dev-kv --name "AccountAgentClientId" --value "your-client-id"
az keyvault secret set --vault-name bankx-dev-kv --name "AccountAgentClientSecret" --value "your-client-secret"
# ... repeat for all 7 agents
```

#### 3.7 Update Container App Environment Variables

Update each Container App with the deployed resource endpoints:

```bash
az containerapp update \
    --name bankx-dev-copilot \
    --resource-group bankx-dev-rg \
    --set-env-vars \
        AZURE_OPENAI_ENDPOINT="https://bankx-dev-openai.openai.azure.com/" \
        AZURE_AI_PROJECT_CONNECTION_STRING="your-connection-string" \
        COSMOS_DB_ENDPOINT="https://bankx-dev-cosmos.documents.azure.com:443/" \
        STORAGE_ACCOUNT_NAME="bankxdevstorage" \
        KEY_VAULT_URL="https://bankx-dev-kv.vault.azure.net/" \
        AI_SEARCH_ENDPOINT="https://bankx-dev-search.search.windows.net/"
```

## 📊 Deployment Outputs

After deployment, you'll receive these outputs:

```json
{
  "openAiEndpoint": "https://bankx-dev-openai.openai.azure.com/",
  "aiFindryId": "/subscriptions/.../providers/Microsoft.CognitiveServices/accounts/bankx-dev-aifoundry",
  "searchEndpoint": "https://bankx-dev-search.search.windows.net/",
  "cosmosDbEndpoint": "https://bankx-dev-cosmos.documents.azure.com:443/",
  "storageAccountName": "bankxdevstorage",
  "keyVaultUrl": "https://bankx-dev-kv.vault.azure.net/",
  "appInsightsConnectionString": "InstrumentationKey=...",
  "copilotFqdn": "bankx-dev-copilot.azurecontainerapps.io",
  "frontendFqdn": "bankx-dev-frontend.azurecontainerapps.io"
}
```

## 🔄 Cross-Tenant Deployment

To deploy to a **different tenant**:

1. **Switch tenant context**:

```bash
az logout
az login --tenant "target-tenant-id"
az account set --subscription "target-subscription-id"
```

2. **Re-create identities** in target tenant:
   - Service Principals (7 agents)
   - App Registration (frontend auth)

3. **Run deployment** with target subscription:

```powershell
.\deploy.ps1 `
    -SubscriptionId "target-subscription-id" `
    -ResourceGroupName "bankx-prod-rg" `
    -Environment "prod" `
    -Location "eastus"
```

4. **Update Entra ID integration** for frontend app in target tenant.

## 🧪 Validation

After deployment, validate the infrastructure:

### Check Resource Deployment

```bash
# List all resources in resource group
az resource list --resource-group bankx-dev-rg --output table

# Verify Container Apps are running
az containerapp list --resource-group bankx-dev-rg --output table
```

### Test Managed Identity Authentication

```bash
# Test OpenAI access from Copilot app
az containerapp exec --name bankx-dev-copilot --resource-group bankx-dev-rg --command "/bin/sh"

# Inside container:
curl -H "Authorization: Bearer $(cat /var/run/secrets/azure/msi/token)" \
     https://bankx-dev-openai.openai.azure.com/openai/deployments?api-version=2023-05-15
```

### Verify RBAC Assignments

```bash
# List role assignments for Copilot managed identity
az role assignment list --assignee <copilot-principal-id> --output table

# Check Cosmos DB data plane roles
az cosmosdb sql role assignment list \
    --account-name bankx-dev-cosmos \
    --resource-group bankx-dev-rg
```

## 🛠️ Troubleshooting

### Issue: Bicep Deployment Fails with "Resource Already Exists"

**Solution**: Delete the existing resource group or use a different name:

```bash
az group delete --name bankx-dev-rg --yes
```

### Issue: RBAC Role Assignments Fail

**Cause**: Insufficient permissions in target subscription.

**Solution**: Ensure you have `Owner` role or `User Access Administrator` role:

```bash
az role assignment create \
    --assignee your-user-id \
    --role "User Access Administrator" \
    --scope /subscriptions/your-subscription-id
```

### Issue: Cosmos DB Role Assignment Fails

**Cause**: Built-in role definition ID not found.

**Solution**: Use Cosmos DB's built-in role definition:

- **Cosmos DB Built-in Data Reader**: `00000000-0000-0000-0000-000000000001`
- **Cosmos DB Built-in Data Contributor**: `00000000-0000-0000-0000-000000000002`

### Issue: Container Apps Fail to Start

**Cause**: Missing environment variables or invalid container images.

**Solution**: 
1. Check Container App logs:
```bash
az containerapp logs show --name bankx-dev-copilot --resource-group bankx-dev-rg
```

2. Update with correct container image:
```bash
az containerapp update \
    --name bankx-dev-copilot \
    --resource-group bankx-dev-rg \
    --image "your-registry.azurecr.io/copilot:latest"
```

### Issue: Purview RBAC Not Working

**Cause**: Purview RBAC is tenant-scoped and cannot be assigned via ARM/Bicep.

**Solution**: Manually assign roles via Azure Portal (see step 3.3).

### Issue: AI Search Index Creation Fails

**Cause**: Managed identity doesn't have Search Index Data Contributor role.

**Solution**: Assign the role manually:

```bash
az role assignment create \
    --assignee <prodinfo-principal-id> \
    --role "Search Index Data Contributor" \
    --scope /subscriptions/.../resourceGroups/bankx-dev-rg/providers/Microsoft.Search/searchServices/bankx-dev-search
```

## 📖 Additional Resources

- **IAM Permissions Mapping**: See `infrastructure/IAM_PERMISSIONS_MAPPING.md` for detailed permission requirements
- **Azure Bicep Documentation**: https://learn.microsoft.com/azure/azure-resource-manager/bicep/
- **Azure OpenAI Service**: https://learn.microsoft.com/azure/cognitive-services/openai/
- **Azure AI Foundry**: https://learn.microsoft.com/azure/ai-services/
- **Managed Identities**: https://learn.microsoft.com/azure/active-directory/managed-identities-azure-resources/

## 🔒 Security Best Practices

1. **Never commit secrets** to version control - use Key Vault
2. **Enable network isolation** for production (VNet integration)
3. **Use separate subscriptions** for dev/staging/prod
4. **Rotate Service Principal credentials** every 90 days
5. **Enable Azure Policy** for compliance enforcement
6. **Configure diagnostic settings** for all resources
7. **Use Azure Private Link** for private connectivity

## 📝 Clean Up

To delete all deployed resources:

```bash
# Delete resource group (deletes all resources inside)
az group delete --name bankx-dev-rg --yes --no-wait

# Verify deletion
az group show --name bankx-dev-rg
```

**Note**: This does **not** delete:
- Service Principals (delete manually via `az ad sp delete`)
- App Registrations (delete via Azure Portal)
- Role assignments at subscription scope

## 📞 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review deployment logs in Azure Portal
3. Consult `IAM_PERMISSIONS_MAPPING.md` for identity issues
4. File an issue in the project repository

---

**Last Updated**: January 2025  
**Bicep Version**: 0.20+  
**Azure CLI Version**: 2.50+
