# BankX Deployment Runbook

Complete deployment guide for UC1/UC2/UC3 services and Azure infrastructure.

**Last Updated**: November 7, 2025
**Version**: 2.0
**Environment**: Production

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Azure Resources Provisioning](#azure-resources-provisioning)
4. [Knowledge Base Setup](#knowledge-base-setup)
5. [Service Deployment](#service-deployment)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Rollback Procedures](#rollback-procedures)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
- Azure CLI (`az`) version 2.50.0 or higher
- Azure Developer CLI (`azd`) version 1.5.0 or higher
- Python 3.11 or higher
- Docker Desktop (for local testing)
- Git

### Required Access
- Azure Subscription with Owner or Contributor role
- GitHub repository access
- Azure DevOps (if using)

### Required Information
- Subscription ID
- Resource Group name
- Region (e.g., `southeastasia`)
- Domain name for emails (e.g., `bankx.com`)

---

## Pre-Deployment Checklist

### 1. Code Review ✅
- [ ] All code merged to main/deployment branch
- [ ] All tests passing
- [ ] Code review completed
- [ ] Documentation updated

### 2. Configuration Review ✅
- [ ] Environment variables reviewed
- [ ] Secrets stored in Azure Key Vault
- [ ] Connection strings validated
- [ ] Port assignments confirmed

### 3. Knowledge Base Preparation ✅
- [ ] UC2 PDFs available (5 files)
- [ ] UC2 FAQ HTML scraped
- [ ] UC3 Money Coach PDF available
- [ ] Documents validated for quality

### 4. Azure Resources Plan ✅
- [ ] Resource group created
- [ ] Naming convention agreed
- [ ] Cost estimate reviewed
- [ ] Tags defined

---

## Azure Resources Provisioning

### Phase 1: Core Infrastructure (30 minutes)

#### 1.1 Create Resource Group

```bash
# Set variables
SUBSCRIPTION_ID="your-subscription-id"
RESOURCE_GROUP="bankx-prod-rg"
LOCATION="southeastasia"

# Login to Azure
az login
az account set --subscription ${SUBSCRIPTION_ID}

# Create resource group
az group create \
  --name ${RESOURCE_GROUP} \
  --location ${LOCATION} \
  --tags environment=production application=bankx
```

#### 1.2 Create Azure AI Foundry Project

```bash
# Create AI Foundry project
az ml workspace create \
  --name bankx-ai-foundry \
  --resource-group ${RESOURCE_GROUP} \
  --location ${LOCATION} \
  --application-insights /subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Insights/components/bankx-appinsights

# Note the endpoint for FOUNDRY_PROJECT_ENDPOINT
```

#### 1.3 Create Azure OpenAI Service

```bash
# Create OpenAI resource
az cognitiveservices account create \
  --name bankx-openai \
  --resource-group ${RESOURCE_GROUP} \
  --kind OpenAI \
  --sku S0 \
  --location ${LOCATION}

# Deploy GPT-4o model
az cognitiveservices account deployment create \
  --name bankx-openai \
  --resource-group ${RESOURCE_GROUP} \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-05-13" \
  --model-format OpenAI \
  --sku-capacity 50 \
  --sku-name Standard

# Deploy ada-002 embeddings model (for RAG)
az cognitiveservices account deployment create \
  --name bankx-openai \
  --resource-group ${RESOURCE_GROUP} \
  --deployment-name text-embedding-ada-002 \
  --model-name text-embedding-ada-002 \
  --model-version "2" \
  --model-format OpenAI \
  --sku-capacity 120 \
  --sku-name Standard
```

### Phase 2: UC2/UC3 Infrastructure (45 minutes)

#### 2.1 Create Azure AI Search

```bash
# Create AI Search service
az search service create \
  --name bankx-search \
  --resource-group ${RESOURCE_GROUP} \
  --sku standard \
  --location ${LOCATION} \
  --partition-count 1 \
  --replica-count 2

# Enable semantic search
az search service update \
  --name bankx-search \
  --resource-group ${RESOURCE_GROUP} \
  --semantic-search free

# Get admin key
SEARCH_KEY=$(az search admin-key show \
  --resource-group ${RESOURCE_GROUP} \
  --service-name bankx-search \
  --query primaryKey -o tsv)

echo "Azure AI Search Key: ${SEARCH_KEY}"
```

#### 2.2 Create CosmosDB

```bash
# Create CosmosDB account
az cosmosdb create \
  --name bankx-cosmos \
  --resource-group ${RESOURCE_GROUP} \
  --locations regionName=${LOCATION} failoverPriority=0 \
  --default-consistency-level Session \
  --enable-automatic-failover false

# Create database
az cosmosdb sql database create \
  --account-name bankx-cosmos \
  --resource-group ${RESOURCE_GROUP} \
  --name bankx

# Create container for support tickets
az cosmosdb sql container create \
  --account-name bankx-cosmos \
  --resource-group ${RESOURCE_GROUP} \
  --database-name bankx \
  --name support_tickets \
  --partition-key-path "/customer_id" \
  --throughput 400

# Get connection string
COSMOS_ENDPOINT=$(az cosmosdb show \
  --name bankx-cosmos \
  --resource-group ${RESOURCE_GROUP} \
  --query documentEndpoint -o tsv)

echo "CosmosDB Endpoint: ${COSMOS_ENDPOINT}"
```

#### 2.3 Create Azure Communication Services

```bash
# Create Communication Services
az communication create \
  --name bankx-acs \
  --resource-group ${RESOURCE_GROUP} \
  --location global \
  --data-location UnitedStates

# Get connection string
ACS_CONNECTION=$(az communication list-key \
  --name bankx-acs \
  --resource-group ${RESOURCE_GROUP} \
  --query primaryConnectionString -o tsv)

echo "ACS Connection String: ${ACS_CONNECTION}"

# Configure email domain (manual step in portal)
echo "⚠️  MANUAL STEP: Configure email domain in Azure Portal"
echo "   1. Go to Azure Communication Services > bankx-acs"
echo "   2. Add email domain (e.g., bankx.com)"
echo "   3. Verify DNS records (SPF, DKIM, DMARC)"
```

### Phase 3: Governance & Monitoring (20 minutes)

#### 3.1 Create Azure Purview

```bash
# Create Purview account
az purview account create \
  --name bankx-purview \
  --resource-group ${RESOURCE_GROUP} \
  --location ${LOCATION} \
  --managed-group-name bankx-purview-managed

# Get endpoint
PURVIEW_ENDPOINT=$(az purview account show \
  --name bankx-purview \
  --resource-group ${RESOURCE_GROUP} \
  --query endpoints.catalog -o tsv)

echo "Purview Endpoint: ${PURVIEW_ENDPOINT}"
```

#### 3.2 Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app bankx-appinsights \
  --location ${LOCATION} \
  --resource-group ${RESOURCE_GROUP} \
  --application-type web

# Get instrumentation key
APPINSIGHTS_KEY=$(az monitor app-insights component show \
  --app bankx-appinsights \
  --resource-group ${RESOURCE_GROUP} \
  --query connectionString -o tsv)

echo "App Insights Connection String: ${APPINSIGHTS_KEY}"
```

### Phase 4: Storage & Additional Services (15 minutes)

#### 4.1 Storage Account

```bash
# Create storage account
az storage account create \
  --name bankxstorage \
  --resource-group ${RESOURCE_GROUP} \
  --location ${LOCATION} \
  --sku Standard_LRS

# Create blob container
az storage container create \
  --name content \
  --account-name bankxstorage
```

#### 4.2 Document Intelligence

```bash
# Create Document Intelligence
az cognitiveservices account create \
  --name bankx-docintelligence \
  --resource-group ${RESOURCE_GROUP} \
  --kind FormRecognizer \
  --sku S0 \
  --location ${LOCATION}
```

---

## Knowledge Base Setup

See [KNOWLEDGE_BASE_SETUP.md](./KNOWLEDGE_BASE_SETUP.md) for detailed instructions.

### Quick Steps

```bash
# 1. Place knowledge base files
mkdir -p knowledge-bases/uc2-product-info
mkdir -p knowledge-bases/uc3-money-coach

# Copy files to respective directories

# 2. Index UC2 documents
export AZURE_SEARCH_ENDPOINT="https://bankx-search.search.windows.net"
export AZURE_SEARCH_KEY="${SEARCH_KEY}"
export AZURE_OPENAI_ENDPOINT="https://bankx-openai.openai.azure.com/"
export AZURE_OPENAI_KEY="..."

python scripts/index_uc2_documents.py

# 3. Index UC3 documents
python scripts/index_uc3_documents.py

# 4. Validate indexes
az search index show \
  --service-name bankx-search \
  --name bankx-products-faq

az search index show \
  --service-name bankx-search \
  --name bankx-money-coach
```

---

## Service Deployment

### Option A: Azure Developer CLI (azd) - Recommended

```bash
# 1. Configure environment
azd auth login
azd env new prod

# 2. Set environment variables
azd env set AZURE_LOCATION ${LOCATION}
azd env set AZURE_SUBSCRIPTION_ID ${SUBSCRIPTION_ID}

# 3. Deploy all services
azd up

# This will deploy:
# - Copilot backend (port 8080)
# - 6 UC1 MCP services (ports 8070-8075)
# - 3 UC2/UC3 MCP services (ports 8076-8078)
# - Frontend (port 8081)
```

### Option B: Manual Deployment

#### Step 1: Build and Push Docker Images

```bash
# Build images for all services
docker build -t bankx.azurecr.io/copilot:latest ./app/copilot
docker build -t bankx.azurecr.io/account-mcp:latest ./app/business-api/python/account
docker build -t bankx.azurecr.io/transaction-mcp:latest ./app/business-api/python/transaction
docker build -t bankx.azurecr.io/payment-mcp:latest ./app/business-api/python/payment
docker build -t bankx.azurecr.io/prodinfo-faq-mcp:latest ./app/business-api/python/prodinfo_faq
docker build -t bankx.azurecr.io/ai-money-coach-mcp:latest ./app/business-api/python/ai_money_coach
docker build -t bankx.azurecr.io/escalation-comms-mcp:latest ./app/business-api/python/escalation_comms
docker build -t bankx.azurecr.io/frontend:latest ./app/frontend

# Push to Azure Container Registry
az acr login --name bankx
docker push bankx.azurecr.io/copilot:latest
# ... push all images
```

#### Step 2: Create Container Apps Environment

```bash
# Create Container Apps environment
az containerapp env create \
  --name bankx-env \
  --resource-group ${RESOURCE_GROUP} \
  --location ${LOCATION}
```

#### Step 3: Deploy Each Service

```bash
# Example: Deploy ProdInfoFAQ MCP service
az containerapp create \
  --name prodinfo-faq \
  --resource-group ${RESOURCE_GROUP} \
  --environment bankx-env \
  --image bankx.azurecr.io/prodinfo-faq-mcp:latest \
  --target-port 8076 \
  --ingress external \
  --env-vars \
    PROFILE=prod \
    AZURE_AI_SEARCH_ENDPOINT=${SEARCH_ENDPOINT} \
    AZURE_AI_SEARCH_KEY=${SEARCH_KEY} \
    AZURE_CONTENT_UNDERSTANDING_ENDPOINT=${FOUNDRY_ENDPOINT}

# Repeat for all services...
```

---

## Post-Deployment Verification

### 1. Service Health Checks

```bash
# Check all services are running
az containerapp list \
  --resource-group ${RESOURCE_GROUP} \
  --query "[].{Name:name, Status:properties.runningStatus, FQDN:properties.configuration.ingress.fqdn}" \
  --output table

# Expected: All services showing "Running"
```

### 2. MCP Service Tests

```bash
# Test UC2 ProdInfoFAQ service
curl -X POST https://prodinfo-faq.${REGION}.azurecontainerapps.io/mcp/tools/search_documents \
  -H "Content-Type: application/json" \
  -d '{"query": "savings account interest rate", "top_k": 5}'

# Expected: JSON response with search results

# Test UC3 AIMoneyCoach service
curl -X POST https://ai-money-coach.${REGION}.azurecontainerapps.io/mcp/tools/AISearchRAGResults \
  -H "Content-Type: application/json" \
  -d '{"query": "debt management advice", "top_k": 5}'

# Expected: JSON response with chapter results

# Test EscalationComms service
curl -X POST https://escalation-comms.${REGION}.azurecontainerapps.io/mcp/tools/sendemail \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-TEST-001",
    "customer_id": "CUST-TEST",
    "customer_email": "test@example.com",
    "query": "Test query",
    "use_case": "UC2",
    "reason": "Testing"
  }'

# Expected: JSON response with email_id and status
```

### 3. End-to-End User Story Tests

#### UC2 Test: Product Information Query

```bash
# Call copilot backend
curl -X POST https://copilot.${REGION}.azurecontainerapps.io/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the interest rate for savings account?",
    "thread_id": null
  }'

# Expected: KNOWLEDGE_CARD response with sources
```

#### UC3 Test: Debt Management Advice

```bash
curl -X POST https://copilot.${REGION}.azurecontainerapps.io/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I have 3 credit cards with high balances, what should I do?",
    "thread_id": null
  }'

# Expected: Clarification questions or ADVICE_CARD
```

### 4. Monitoring Dashboard

```bash
# Open Application Insights
az monitor app-insights component show \
  --app bankx-appinsights \
  --resource-group ${RESOURCE_GROUP} \
  --query id -o tsv

# Open in portal for live metrics
```

---

## Rollback Procedures

### Scenario 1: Service Deployment Failure

```bash
# Rollback to previous revision
az containerapp revision list \
  --name prodinfo-faq \
  --resource-group ${RESOURCE_GROUP}

# Activate previous revision
az containerapp revision activate \
  --name prodinfo-faq \
  --resource-group ${RESOURCE_GROUP} \
  --revision prodinfo-faq--previous-revision
```

### Scenario 2: Configuration Error

```bash
# Update environment variables
az containerapp update \
  --name prodinfo-faq \
  --resource-group ${RESOURCE_GROUP} \
  --set-env-vars AZURE_SEARCH_ENDPOINT=https://correct-endpoint
```

### Scenario 3: Complete Rollback

```bash
# Use azd to rollback
azd down
azd up --from-backup
```

---

## Troubleshooting

### Issue: Service not starting

**Check logs**:
```bash
az containerapp logs show \
  --name prodinfo-faq \
  --resource-group ${RESOURCE_GROUP} \
  --follow
```

**Common causes**:
- Missing environment variables
- Invalid Azure credentials
- Port conflicts

### Issue: Search returning no results

**Validate index**:
```bash
# Check document count
az search index statistics show \
  --service-name bankx-search \
  --name bankx-products-faq

# If count is 0, re-run indexing scripts
python scripts/index_uc2_documents.py
```

### Issue: Email not sending

**Verify ACS configuration**:
```bash
# Check domain verification
az communication email domain list \
  --email-service-name bankx-acs-email \
  --resource-group ${RESOURCE_GROUP}

# Status should be "Verified"
```

### Issue: Purview lineage not tracking

**Check Managed Identity**:
```bash
# Verify identity has Purview permissions
az role assignment list \
  --assignee <container-app-identity> \
  --scope <purview-resource-id>
```

---

## Maintenance Tasks

### Daily
- [ ] Monitor Application Insights for errors
- [ ] Check service health status
- [ ] Review alert notifications

### Weekly
- [ ] Review cost analysis
- [ ] Check knowledge base index statistics
- [ ] Review Purview lineage reports

### Monthly
- [ ] Update knowledge base documents
- [ ] Re-index if needed
- [ ] Security patch updates
- [ ] Performance optimization review

---

## Contact & Support

**Deployment Team**: deployment@bankx.com
**On-Call**: +66-XXX-XXX-XXXX
**Runbook Location**: https://github.com/bankx/docs/deployment

---

**Document Version**: 2.0
**Last Updated**: November 7, 2025
**Next Review**: December 7, 2025
