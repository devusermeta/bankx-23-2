# BankX Infrastructure Deployment Guide

Complete step-by-step guide to deploy BankX infrastructure to a new Azure subscription or tenant.

---

## 📑 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Setup](#pre-deployment-setup)
3. [Running the Deployment](#running-the-deployment)
4. [Post-Deployment Configuration](#post-deployment-configuration)
5. [Environment Configuration](#environment-configuration)
6. [Starting the Application](#starting-the-application)
7. [Verification & Testing](#verification--testing)
8. [Troubleshooting](#troubleshooting)

---

## 1. Prerequisites

### Required Tools

Install these tools before starting:

```powershell
# Check Azure CLI version (need 2.50+)
az --version

# Check PowerShell version (need 7.0+)
$PSVersionTable.PSVersion

# Check Python version (need 3.9+)
python --version

# Check Node.js version (need 16+)
node --version
```

**If not installed:**
- Azure CLI: https://docs.microsoft.com/cli/azure/install-azure-cli
- PowerShell 7: https://learn.microsoft.com/powershell/scripting/install/installing-powershell
- Python 3.9+: https://www.python.org/downloads/
- Node.js 16+: https://nodejs.org/

### Azure Permissions

You need these permissions in the **target subscription**:

- ✅ **Owner** role (recommended), OR
- ✅ **Contributor** + **User Access Administrator** roles

Check your permissions:

```powershell
# Login to Azure
az login

# Set target subscription
az account set --subscription "your-subscription-id"

# Check your role assignments
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) --output table
```

---

## 2. Pre-Deployment Setup

### Step 2.1: Register Azure Resource Providers

```powershell
# Register all required resource providers
az provider register --namespace Microsoft.CognitiveServices
az provider register --namespace Microsoft.Search
az provider register --namespace Microsoft.DocumentDB
az provider register --namespace Microsoft.Storage
az provider register --namespace Microsoft.KeyVault
az provider register --namespace Microsoft.Communication
az provider register --namespace Microsoft.Purview
az provider register --namespace Microsoft.Insights
az provider register --namespace Microsoft.App

# Verify registration status (may take 2-3 minutes)
az provider show --namespace Microsoft.CognitiveServices --query "registrationState"
```

Wait until all providers show `"Registered"`.

### Step 2.2: Choose Your Environment

Edit the parameter file for your target environment:

**For Development:**
```powershell
# Edit this file
notepad infrastructure\bicep\parameters\dev.bicepparam
```

**For Production:**
```powershell
# Edit this file
notepad infrastructure\bicep\parameters\prod.bicepparam
```

**Key parameters to customize:**

```bicep
using '../main.bicep'

param environment = 'dev'              // 'dev', 'staging', or 'prod'
param location = 'eastus'              // Your preferred Azure region
param resourceGroupName = 'bankx-dev-rg'

// Optional: Override resource names
param openAiName = 'bankx-dev-openai'
param cosmosDbAccountName = 'bankx-dev-cosmos'
// ... etc (use defaults if unsure)
```

### Step 2.3: Cross-Tenant Deployment (Optional)

If deploying to a **different tenant**:

```powershell
# Logout from current tenant
az logout

# Login to target tenant
az login --tenant "target-tenant-id"

# Set target subscription
az account set --subscription "target-subscription-id"

# Verify you're in the right tenant
az account show
```

---

## 3. Running the Deployment

### Step 3.1: Navigate to Scripts Folder

```powershell
cd infrastructure\bicep\scripts
```

### Step 3.2: Run Deployment Script

**For Development Environment:**

```powershell
.\deploy.ps1 `
    -SubscriptionId "your-subscription-id" `
    -ResourceGroupName "bankx-dev-rg" `
    -Environment "dev" `
    -Location "eastus"
```

**For Production Environment:**

```powershell
.\deploy.ps1 `
    -SubscriptionId "your-subscription-id" `
    -ResourceGroupName "bankx-prod-rg" `
    -Environment "prod" `
    -Location "eastus"
```

**Expected output:**

```
============================================================================
 BankX Infrastructure Deployment
============================================================================

Environment: dev
Subscription: your-subscription-id
Resource Group: bankx-dev-rg
Location: eastus

Step 1/6: Setting Azure subscription...
✓ Subscription set successfully

Step 2/6: Ensuring resource group exists...
✓ Resource group created: bankx-dev-rg

Step 3/6: Deploying Bicep template...
[This will take 15-20 minutes]
✓ Deployment completed successfully

Step 4/6: Retrieving deployment outputs...
✓ Outputs retrieved

Step 5/6: Assigning RBAC roles...
✓ All RBAC role assignments completed!

Step 6/6: Deployment Summary
============================================================================
```

**⏱️ Deployment Time:** 15-20 minutes

### What Gets Deployed?

- ✅ Azure OpenAI (GPT-4o, gpt-4.1-mini, text-embedding-ada-002)
- ✅ Azure AI Foundry (AI Services Hub)
- ✅ Azure AI Search (vector search)
- ✅ Cosmos DB (3 containers: support_tickets, Conversations, decision_ledger)
- ✅ Storage Account (blob container: documents)
- ✅ Key Vault (RBAC-enabled)
- ✅ Communication Services (email)
- ✅ Purview (data lineage)
- ✅ Application Insights + Log Analytics
- ✅ Container Apps Environment
- ✅ 6 Container Apps (copilot, prodinfo, moneycoach, escalation, audit, frontend)
- ✅ Document Intelligence (invoice OCR)
- ✅ RBAC role assignments for managed identities

---

## 4. Post-Deployment Configuration

### Step 4.1: Save Deployment Outputs

After deployment, save these important values:

```powershell
# Get deployment outputs
az deployment group show `
    --name "bankx-dev-deployment-$(Get-Date -Format 'yyyyMMdd-HHmmss')" `
    --resource-group "bankx-dev-rg" `
    --query properties.outputs

# Save to file
az deployment group show `
    --name "bankx-dev-deployment-*" `
    --resource-group "bankx-dev-rg" `
    --query properties.outputs > deployment-outputs.json
```

**Key outputs you need:**

- `openAiEndpoint` - e.g., `https://bankx-dev-openai.openai.azure.com/`
- `aiFindryId` - Azure AI Foundry resource ID
- `searchEndpoint` - e.g., `https://bankx-dev-search.search.windows.net/`
- `cosmosDbEndpoint` - e.g., `https://bankx-dev-cosmos.documents.azure.com:443/`
- `storageAccountName` - e.g., `bankxdevstorage`
- `keyVaultUrl` - e.g., `https://bankx-dev-kv.vault.azure.net/`
- `copilotFqdn` - e.g., `bankx-dev-copilot.azurecontainerapps.io`
- `frontendFqdn` - e.g., `bankx-dev-frontend.azurecontainerapps.io`

### Step 4.2: Create Service Principals (7 agents)

Create a Service Principal for each agent that needs Purview access:

```powershell
# 1. Account Agent
az ad sp create-for-rbac --name "BankX-AccountAgent-Dev" --skip-assignment
# Save: appId (Client ID), password (Client Secret), tenant (Tenant ID)

# 2. Transaction Agent
az ad sp create-for-rbac --name "BankX-TransactionAgent-Dev" --skip-assignment

# 3. Payment Agent
az ad sp create-for-rbac --name "BankX-PaymentAgent-Dev" --skip-assignment

# 4. ProdInfo Agent
az ad sp create-for-rbac --name "BankX-ProdInfoAgent-Dev" --skip-assignment

# 5. MoneyCoach Agent
az ad sp create-for-rbac --name "BankX-MoneyCoachAgent-Dev" --skip-assignment

# 6. Escalation Agent
az ad sp create-for-rbac --name "BankX-EscalationAgent-Dev" --skip-assignment

# 7. Supervisor Agent
az ad sp create-for-rbac --name "BankX-SupervisorAgent-Dev" --skip-assignment
```

**Save the output for each Service Principal:**

```json
{
  "appId": "12345678-1234-1234-1234-123456789abc",     // Client ID
  "displayName": "BankX-AccountAgent-Dev",
  "password": "your-client-secret-here",               // Client Secret
  "tenant": "87654321-4321-4321-4321-abcdefghijkl"    // Tenant ID
}
```

### Step 4.3: Assign Purview RBAC (Manual)

⚠️ **Purview RBAC cannot be automated** - must be done via Portal.

**For each Service Principal:**

1. Go to **Azure Portal** → **Azure Purview** → `bankx-dev-purview`
2. Click **Data map** (left menu)
3. Click **Collections** → **Root Collection**
4. Click **Role assignments** tab
5. Click **+ Add** → **Data Curator**
6. Search for the Service Principal name (e.g., "BankX-AccountAgent-Dev")
7. Click **OK**

Repeat for all 7 Service Principals.

### Step 4.4: Store Secrets in Key Vault

```powershell
$kvName = "bankx-dev-kv"

# Communication Services connection string
$commConnString = az communication show --name "bankx-dev-comm" --resource-group "bankx-dev-rg" --query primaryConnectionString -o tsv
az keyvault secret set --vault-name $kvName --name "CommunicationServicesConnectionString" --value $commConnString

# Service Principal credentials (repeat for all 7 agents)
az keyvault secret set --vault-name $kvName --name "AccountAgentClientId" --value "your-app-id"
az keyvault secret set --vault-name $kvName --name "AccountAgentClientSecret" --value "your-client-secret"
az keyvault secret set --vault-name $kvName --name "AccountAgentTenantId" --value "your-tenant-id"

az keyvault secret set --vault-name $kvName --name "TransactionAgentClientId" --value "your-app-id"
az keyvault secret set --vault-name $kvName --name "TransactionAgentClientSecret" --value "your-client-secret"
az keyvault secret set --vault-name $kvName --name "TransactionAgentTenantId" --value "your-tenant-id"

# ... repeat for Payment, ProdInfo, MoneyCoach, Escalation, Supervisor agents
```

### Step 4.5: Create AI Foundry Agents (TODO: Script Pending)

**Manual steps until script is created:**

1. Go to **Azure Portal** → **Azure AI Foundry** → `bankx-dev-aifoundry`
2. Click **Agents** → **+ Create agent**
3. Create these 7 agents:
   - **SupervisorAgent** - Orchestrates all agents
   - **AccountAgent** - Account operations
   - **TransactionAgent** - Transaction history
   - **PaymentAgent** - Payment processing
   - **ProdInfoAgent** - Product information (attach products-faq vector store)
   - **AIMoneyCoachAgent** - Financial coaching (attach money-coach vector store)
   - **EscalationAgent** - Escalation handling

Save agent IDs for environment variables.

### Step 4.6: Create AI Search Indexes (TODO: Script Pending)

**Manual steps until script is created:**

1. Go to **Azure Portal** → **Azure AI Search** → `bankx-dev-search`
2. Click **Indexes** → **+ Add index**

**Index 1: bankx-products-faq**
- Enable vector search
- Configure text-embedding-ada-002 vectorizer
- Upload documents from `data/knowledge_base/products_faq/`

**Index 2: bankx-money-coach**
- Enable vector search
- Configure text-embedding-ada-002 vectorizer
- Upload documents from `data/knowledge_base/money_coach/`

### Step 4.7: Create Test Users (Optional)

```powershell
# Create test users for frontend authentication
az ad user create `
    --display-name "Anan Chaiyaporn" `
    --user-principal-name "anan@bankxthb.onmicrosoft.com" `
    --password "BankX2025!Ch41" `
    --force-change-password-next-sign-in false

az ad user create `
    --display-name "Pimchanok Thongchai" `
    --user-principal-name "pimchanok@bankxthb.onmicrosoft.com" `
    --password "BankX2025!Pim" `
    --force-change-password-next-sign-in false
```

---

## 5. Environment Configuration

### Step 5.1: Update Local .env File

Copy `envsample.env` to `.env` and update with deployment outputs:

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://bankx-dev-openai.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-05-01-preview
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-ada-002

# Azure AI Foundry
AZURE_AI_PROJECT_CONNECTION_STRING=<from deployment outputs>
AGENT_SUPERVISOR_ID=<from AI Foundry agent creation>
AGENT_ACCOUNT_ID=<from AI Foundry agent creation>
AGENT_TRANSACTION_ID=<from AI Foundry agent creation>
AGENT_PAYMENT_ID=<from AI Foundry agent creation>
AGENT_PRODINFO_ID=<from AI Foundry agent creation>
AGENT_MONEY_COACH_ID=<from AI Foundry agent creation>
AGENT_ESCALATION_ID=<from AI Foundry agent creation>

# Azure AI Search
AI_SEARCH_ENDPOINT=https://bankx-dev-search.search.windows.net/
AI_SEARCH_INDEX_NAME_UC2=bankx-products-faq
AI_SEARCH_INDEX_NAME_UC3=bankx-money-coach

# Cosmos DB
COSMOS_DB_ENDPOINT=https://bankx-dev-cosmos.documents.azure.com:443/
COSMOS_DB_DATABASE_NAME=bankx-database
COSMOS_DB_CONTAINER_CONVERSATIONS=Conversations
COSMOS_DB_CONTAINER_TICKETS=support_tickets
COSMOS_DB_CONTAINER_DECISION=decision_ledger

# Storage
STORAGE_ACCOUNT_NAME=bankxdevstorage
STORAGE_CONTAINER_NAME=documents

# Key Vault
KEY_VAULT_URL=https://bankx-dev-kv.vault.azure.net/

# Application Insights
APPLICATIONINSIGHTS_CONNECTION_STRING=<from deployment outputs>

# Purview
PURVIEW_ENDPOINT=https://bankx-dev-purview.purview.azure.com/
```

### Step 5.2: Update Container App Environment Variables

Update each Container App with the deployed endpoints:

```powershell
$rgName = "bankx-dev-rg"

# Copilot App
az containerapp update `
    --name "bankx-dev-copilot" `
    --resource-group $rgName `
    --set-env-vars `
        AZURE_OPENAI_ENDPOINT="https://bankx-dev-openai.openai.azure.com/" `
        COSMOS_DB_ENDPOINT="https://bankx-dev-cosmos.documents.azure.com:443/" `
        STORAGE_ACCOUNT_NAME="bankxdevstorage" `
        KEY_VAULT_URL="https://bankx-dev-kv.vault.azure.net/" `
        AI_SEARCH_ENDPOINT="https://bankx-dev-search.search.windows.net/"

# ProdInfo MCP Service
az containerapp update `
    --name "bankx-dev-prodinfo" `
    --resource-group $rgName `
    --set-env-vars `
        AZURE_OPENAI_ENDPOINT="https://bankx-dev-openai.openai.azure.com/" `
        AI_SEARCH_ENDPOINT="https://bankx-dev-search.search.windows.net/" `
        AI_SEARCH_INDEX_NAME="bankx-products-faq" `
        KEY_VAULT_URL="https://bankx-dev-kv.vault.azure.net/"

# MoneyCoach MCP Service
az containerapp update `
    --name "bankx-dev-moneycoach" `
    --resource-group $rgName `
    --set-env-vars `
        AZURE_OPENAI_ENDPOINT="https://bankx-dev-openai.openai.azure.com/" `
        AI_SEARCH_ENDPOINT="https://bankx-dev-search.search.windows.net/" `
        AI_SEARCH_INDEX_NAME="bankx-money-coach" `
        KEY_VAULT_URL="https://bankx-dev-kv.vault.azure.net/"

# Escalation MCP Service
az containerapp update `
    --name "bankx-dev-escalation" `
    --resource-group $rgName `
    --set-env-vars `
        KEY_VAULT_URL="https://bankx-dev-kv.vault.azure.net/" `
        COSMOS_DB_ENDPOINT="https://bankx-dev-cosmos.documents.azure.com:443/"

# Audit MCP Service
az containerapp update `
    --name "bankx-dev-audit" `
    --resource-group $rgName `
    --set-env-vars `
        KEY_VAULT_URL="https://bankx-dev-kv.vault.azure.net/" `
        COSMOS_DB_ENDPOINT="https://bankx-dev-cosmos.documents.azure.com:443/"

# Frontend App
az containerapp update `
    --name "bankx-dev-frontend" `
    --resource-group $rgName `
    --set-env-vars `
        VITE_COPILOT_API_URL="https://bankx-dev-copilot.azurecontainerapps.io"
```

---

## 6. Starting the Application

### Local Development Setup

**Prerequisites:**
- All environment variables configured in `.env`
- Python virtual environments created for each service
- Node modules installed for frontend

### Step 6.1: Start MCP Services (9 services)

Open separate terminal windows for each service:

**Account Service (Port 8070):**
```powershell
cd app\business-api\python\account
.venv\Scripts\Activate.ps1
$env:PROFILE="dev"
python main.py
```

**Transaction Service (Port 8071):**
```powershell
cd app\business-api\python\transaction
.venv\Scripts\Activate.ps1
$env:PROFILE="dev"
python main.py
```

**Payment Service (Port 8072):**
```powershell
cd app\business-api\python\payment
.venv\Scripts\Activate.ps1
$env:PROFILE="dev"
$env:TRANSACTIONS_API_URL="http://localhost:8071"
python main.py
```

**Limits Service (Port 8073):**
```powershell
cd app\business-api\python\limits
.venv\Scripts\Activate.ps1
$env:PROFILE="dev"
python main.py
```

**Contacts Service (Port 8074):**
```powershell
cd app\business-api\python\contacts
.venv\Scripts\Activate.ps1
$env:PROFILE="dev"
python main.py
```

**Audit Service (Port 8075):**
```powershell
cd app\business-api\python\audit
.venv\Scripts\Activate.ps1
$env:PROFILE="dev"
python main.py
```

**ProdInfo Service (Port 8076):**
```powershell
cd app\business-api\python\prodinfo_faq
.venv\Scripts\Activate.ps1
$env:PROFILE="dev"
python main.py
```

**AI Money Coach Service (Port 8077):**
```powershell
cd app\business-api\python\ai_money_coach
.venv\Scripts\Activate.ps1
$env:PROFILE="dev"
python main.py
```

**Escalation/Comms Service (Port 8078):**
```powershell
cd app\business-api\python\escalation_comms
.venv\Scripts\Activate.ps1
$env:PROFILE="dev"
python main.py
```

### Step 6.2: Start Copilot Backend (Port 8080)

```powershell
cd app\copilot
.venv\Scripts\Activate.ps1
$env:PROFILE="dev"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Step 6.3: Start Frontend (Port 8081)

```powershell
cd app\frontend
npm run dev
```

### Service Startup Order

**Recommended order:**
1. Start all MCP services first (ports 8070-8078)
2. Wait for all MCP services to show "Server running"
3. Start Copilot backend (port 8080)
4. Wait for Copilot to connect to MCP services
5. Start Frontend (port 8081)

### Verify Services Are Running

```powershell
# Check if all services are listening
netstat -ano | findstr "8070 8071 8072 8073 8074 8075 8076 8077 8078 8080 8081"
```

You should see 11 services running.

---

## 7. Verification & Testing

### Step 7.1: Test Azure Resources

```powershell
# Test OpenAI deployment
az cognitiveservices account deployment list `
    --name "bankx-dev-openai" `
    --resource-group "bankx-dev-rg"

# Test Cosmos DB connection
az cosmosdb sql database show `
    --account-name "bankx-dev-cosmos" `
    --resource-group "bankx-dev-rg" `
    --name "bankx-database"

# Test AI Search service
az search service show `
    --name "bankx-dev-search" `
    --resource-group "bankx-dev-rg"
```

### Step 7.2: Test Managed Identity Authentication

```powershell
# Get Copilot managed identity principal ID
$copilotId = az containerapp show `
    --name "bankx-dev-copilot" `
    --resource-group "bankx-dev-rg" `
    --query "identity.principalId" -o tsv

# Verify role assignments
az role assignment list --assignee $copilotId --output table
```

### Step 7.3: Test Local Services

**Test MCP Service (Account):**
```powershell
curl http://localhost:8070/health
```

**Test Copilot Backend:**
```powershell
curl http://localhost:8080/health
```

**Test Frontend:**
Open browser: http://localhost:8081

### Step 7.4: Test Container Apps (Azure)

```powershell
# Test Copilot container app
$copilotFqdn = az containerapp show --name "bankx-dev-copilot" --resource-group "bankx-dev-rg" --query "properties.configuration.ingress.fqdn" -o tsv
curl "https://$copilotFqdn/health"

# Test Frontend container app
$frontendFqdn = az containerapp show --name "bankx-dev-frontend" --resource-group "bankx-dev-rg" --query "properties.configuration.ingress.fqdn" -o tsv
# Open in browser
Start-Process "https://$frontendFqdn"
```

### Step 7.5: Test End-to-End Flow

1. Open frontend: http://localhost:8081 (or Azure FQDN)
2. Login with test user credentials
3. Test Use Case 2 (Product Information):
   - Ask: "What are the benefits of the Premium Savings Account?"
   - Verify AI Search returns product FAQ data
4. Test Use Case 3 (Money Coach):
   - Ask: "Help me create a savings plan"
   - Verify AI Money Coach provides personalized advice
5. Check Cosmos DB for conversation storage
6. Check Application Insights for telemetry

---

## 8. Troubleshooting

### Issue: Deployment Fails - "Resource Already Exists"

**Solution:**
```powershell
# Delete existing resource group
az group delete --name "bankx-dev-rg" --yes --no-wait

# Wait 5 minutes, then retry deployment
```

### Issue: RBAC Assignment Fails - "Insufficient Permissions"

**Solution:**
```powershell
# Check your role
az role assignment list --assignee $(az ad signed-in-user show --query id -o tsv) --output table

# Request Owner role from subscription admin
az role assignment create `
    --assignee "your-user-email@domain.com" `
    --role "Owner" `
    --scope "/subscriptions/your-subscription-id"
```

### Issue: Container App Won't Start - "ImagePullBackOff"

**Cause:** Default placeholder image doesn't exist.

**Solution:**
```powershell
# Build and push your own images
cd app\copilot
docker build -t yourregistry.azurecr.io/copilot:latest .
docker push yourregistry.azurecr.io/copilot:latest

# Update Container App
az containerapp update `
    --name "bankx-dev-copilot" `
    --resource-group "bankx-dev-rg" `
    --image "yourregistry.azurecr.io/copilot:latest"
```

### Issue: MCP Service Can't Connect to Azure Resources

**Cause:** Managed identity not configured or missing RBAC roles.

**Solution:**
```powershell
# Re-run RBAC assignment script
cd infrastructure\bicep\scripts
.\assign-rbac-roles.ps1 `
    -ResourceGroupName "bankx-dev-rg" `
    -SubscriptionId "your-subscription-id"
```

### Issue: AI Search Index Not Found

**Cause:** Indexes not created yet (manual step pending automation).

**Solution:**
1. Go to Azure Portal → AI Search → Indexes
2. Create indexes manually (see Step 4.6)
3. Upload documents from `data/knowledge_base/`

### Issue: Purview RBAC Not Working

**Cause:** Purview RBAC must be assigned manually via Portal.

**Solution:**
1. Follow Step 4.3 instructions
2. Verify each Service Principal has "Data Curator" role
3. Wait 5 minutes for permissions to propagate

### Issue: Frontend Can't Authenticate Users

**Cause:** App Registration not configured for frontend.

**Solution:**
1. Create App Registration in Azure Portal
2. Configure Redirect URIs: `http://localhost:8081`, `https://your-frontend-fqdn`
3. Update frontend `.env`:
```
VITE_AZURE_AD_CLIENT_ID=your-app-registration-client-id
VITE_AZURE_AD_TENANT_ID=your-tenant-id
```

### Check Deployment Logs

```powershell
# View deployment operation details
az deployment group show `
    --name "bankx-dev-deployment-*" `
    --resource-group "bankx-dev-rg" `
    --query "properties.error"

# View Container App logs
az containerapp logs show `
    --name "bankx-dev-copilot" `
    --resource-group "bankx-dev-rg" `
    --follow
```

---

## 📞 Support & Resources

- **Bicep Templates Documentation**: See `infrastructure/bicep/README.md`
- **IAM Permissions Reference**: See `infrastructure/IAM_PERMISSIONS_MAPPING.md`
- **Azure Bicep Docs**: https://learn.microsoft.com/azure/azure-resource-manager/bicep/
- **Azure OpenAI Docs**: https://learn.microsoft.com/azure/cognitive-services/openai/
- **Container Apps Docs**: https://learn.microsoft.com/azure/container-apps/

---

## ✅ Deployment Checklist

Use this checklist to track your deployment progress:

- [ ] Install required tools (Azure CLI, PowerShell 7, Python, Node.js)
- [ ] Verify Azure permissions (Owner or Contributor + UAA)
- [ ] Register Azure resource providers
- [ ] Customize parameter file (dev.bicepparam or prod.bicepparam)
- [ ] Run deployment script (`deploy.ps1`)
- [ ] Wait 15-20 minutes for deployment to complete
- [ ] Save deployment outputs to file
- [ ] Create 7 Service Principals (one per agent)
- [ ] Assign Purview RBAC via Portal (7 SPs → Data Curator)
- [ ] Store all secrets in Key Vault (connection strings, SP credentials)
- [ ] Create 7 AI Foundry agents (or wait for automation script)
- [ ] Create 2 AI Search indexes (or wait for automation script)
- [ ] Update local `.env` file with deployment outputs
- [ ] Update Container App environment variables
- [ ] Create test users (optional)
- [ ] Start local MCP services (9 services)
- [ ] Start local Copilot backend
- [ ] Start local frontend
- [ ] Test Azure resources (OpenAI, Cosmos DB, AI Search)
- [ ] Test managed identity authentication
- [ ] Test local services (health endpoints)
- [ ] Test Container Apps in Azure
- [ ] Test end-to-end flow (UC2 and UC3)
- [ ] Verify telemetry in Application Insights

---

**Last Updated**: January 2025  
**Author**: BankX DevOps Team  
**Version**: 1.0
