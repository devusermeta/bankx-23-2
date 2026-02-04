# 🔐 BankX Project - Complete IAM & Permissions Mapping

**Document Version**: 1.0  
**Last Updated**: November 21, 2025  
**Purpose**: Comprehensive IAM role assignments for replicating BankX infrastructure across Azure subscriptions

---

## 📋 **EXECUTIVE SUMMARY**

This document maps **ALL** identities, resources, and permissions required for the BankX Multi-Agent Banking System to function correctly across subscriptions.

### **Identity Types Used:**
1. **7 Service Principals** - For Purview data lineage tracking (per-agent authentication)
2. **1 App Registration** - For frontend authentication (Microsoft Entra ID)
3. **9+ Managed Identities** - For Container Apps (one per service)
4. **1 System-Assigned Managed Identity** - For Purview Account itself
5. **Test Users** - For end-user authentication testing

---

## 🎯 **RESOURCE GROUPS & SCOPE**

All resources are deployed in **ONE resource group**:
- **Resource Group Name**: `bankx-{environment}-rg` (e.g., `bankx-dev-rg`, `bankx-prod-rg`)
- **Location**: Configurable (e.g., `eastus`, `southeastasia`)
- **Subscription**: Target Azure subscription ID

---

## 🔑 **IDENTITY PRINCIPALS DETAILED**

### **1. Service Principals (7 total - Purview Authentication)**

| Name | App/Client ID | Purpose | Tenant | Created In |
|------|---------------|---------|--------|------------|
| BankX-AccountAgent-SP | `f7219061-e3db-4dfb-a8de-2b5fa4b98ccf` | AccountAgent Purview auth | Metakaal | Azure AD |
| BankX-TransactionAgent-SP | `abdde3bd-954f-4626-be85-c995faeec314` | TransactionAgent Purview auth | Metakaal | Azure AD |
| BankX-PaymentAgent-SP | `19c0d01f-228b-45e0-b337-291679acb75c` | PaymentAgent Purview auth | Metakaal | Azure AD |
| BankX-ProdInfoAgent-SP | `cd8e9191-1d08-4bd2-9dbe-e23139dcbd90` | ProdInfoFAQAgent Purview auth | Metakaal | Azure AD |
| BankX-MoneyCoachAgent-SP | `b81a5e18-1760-4836-8a5e-e4ef2e8f1113` | AIMoneyCoachAgent Purview auth | Metakaal | Azure AD |
| BankX-EscalationAgent-SP | `019b1746-a104-437a-b1ff-a911ba8c356c` | EscalationComms Purview auth | Metakaal | Azure AD |
| BankX-SupervisorAgent-SP | `cbb7c307-5c43-4999-ada4-63a934853ec5` | SupervisorAgent Purview auth | Metakaal | Azure AD |

**⚠️ IMPORTANT**: These Service Principals must be created in the **SAME TENANT** as the Azure subscription where Purview is deployed. Secrets are stored in Azure Key Vault.

---

### **2. App Registration (1 total - Frontend Authentication)**

| Name | Client ID | Purpose | Tenant | Redirect URIs |
|------|-----------|---------|--------|---------------|
| BankX-Frontend-App | `c37e62a7-a62f-4ebf-a7c2-d6a3d318f76b` | Frontend user authentication | BankX (or target) | `http://localhost:8081`, `https://<app-url>` |

**Tenant Placement**: Can be in a **separate BankX tenant** for user authentication (multi-tenant architecture) OR in the same tenant as resources.

---

### **3. Managed Identities (9+ total - Container Apps)**

Each Container App gets a **System-Assigned Managed Identity** automatically created during deployment:

| Container App | Managed Identity (System-Assigned) | Purpose |
|---------------|-------------------------------------|---------|
| copilot-app | Auto-generated | Access AI Foundry, Key Vault, Cosmos DB, Storage |
| account-mcp | Auto-generated | Access Key Vault (if needed) |
| transaction-mcp | Auto-generated | Access Key Vault (if needed) |
| payment-mcp | Auto-generated | Access Key Vault (if needed) |
| prodinfo-faq-mcp | Auto-generated | Access AI Search, Key Vault, Cosmos DB |
| ai-money-coach-mcp | Auto-generated | Access AI Search, Key Vault, Cosmos DB |
| escalation-comms-mcp | Auto-generated | Access Communication Services, Cosmos DB, Key Vault |
| limits-mcp | Auto-generated | Access Key Vault (if needed) |
| contacts-mcp | Auto-generated | Access Key Vault (if needed) |
| audit-mcp | Auto-generated | Access Cosmos DB, Key Vault |
| frontend-app | Auto-generated | Access backend API (minimal permissions) |

**Note**: Managed Identity Object IDs are generated at deployment time and cannot be pre-determined.

---

### **4. Purview System-Assigned Managed Identity**

| Resource | Managed Identity Type | Principal ID | Purpose |
|----------|----------------------|--------------|---------|
| bankx-purview | SystemAssigned | Auto-generated | Internal Purview operations |

---

## 📊 **AZURE RESOURCES & REQUIRED PERMISSIONS**

### **Resource 1: Azure OpenAI**

**Resource Name**: `bankx-{env}-openai`  
**Type**: `Microsoft.CognitiveServices/accounts` (kind: OpenAI)  
**SKU**: S0

| Identity | Role | Scope | Reason |
|----------|------|-------|--------|
| copilot-app (Managed Identity) | **Cognitive Services OpenAI User** | Resource | Agent framework needs to call OpenAI API |
| prodinfo-faq-mcp (Managed Identity) | **Cognitive Services OpenAI User** | Resource | Embeddings generation for search |
| ai-money-coach-mcp (Managed Identity) | **Cognitive Services OpenAI User** | Resource | Embeddings generation for search |
| Developer/Operator | **Cognitive Services OpenAI Contributor** | Resource | Deploy models, manage deployments |

**Bicep Role Assignment**:
```bicep
resource openaiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openaiAccount.id, copilotManagedIdentity.principalId, 'Cognitive Services OpenAI User')
  scope: openaiAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd') // Cognitive Services OpenAI User
    principalId: copilotManagedIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}
```

---

### **Resource 2: Azure AI Foundry (AI Services Hub)**

**Resource Name**: `bankx-{env}-aifoundry`  
**Type**: `Microsoft.CognitiveServices/accounts` (kind: AIServices)

| Identity | Role | Scope | Reason |
|----------|------|-------|--------|
| copilot-app (Managed Identity) | **Cognitive Services User** | Resource | Access AI Foundry project, agents, threads |
| Developer/Operator | **Cognitive Services Contributor** | Resource | Create agents, manage projects |

---

### **Resource 3: Azure AI Search**

**Resource Name**: `bankx-{env}-search`  
**Type**: `Microsoft.Search/searchServices`  
**SKU**: Standard

**Indexes**: `bankx-products-faq`, `bankx-money-coach`

| Identity | Role | Scope | Reason |
|----------|------|-------|--------|
| prodinfo-faq-mcp (Managed Identity) | **Search Index Data Reader** | Resource | Query UC2 index for product info |
| ai-money-coach-mcp (Managed Identity) | **Search Index Data Reader** | Resource | Query UC3 index for money advice |
| Developer/Operator | **Search Service Contributor** | Resource | Create indexes, manage service |
| Developer/Operator | **Search Index Data Contributor** | Resource | Upload documents, test queries |

**Note**: For API Key authentication (dev), use `AZURE_AI_SEARCH_KEY` from env. For production, use Managed Identity with RBAC.

---

### **Resource 4: Azure Cosmos DB**

**Resource Name**: `bankx-{env}-cosmos`  
**Type**: `Microsoft.DocumentDB/databaseAccounts`  
**Kind**: GlobalDocumentDB (SQL API)  
**Mode**: Serverless

**Database**: `bankx` or `bankx_db`  
**Containers**: 
- `support_tickets` (for UC2/UC3 escalations)
- `Conversations` (for chat history)
- `decision_ledger` (for audit trails)

| Identity | Role | Scope | Reason |
|----------|------|-------|--------|
| copilot-app (Managed Identity) | **Cosmos DB Account Reader** | Resource | Read connection metadata |
| copilot-app (Managed Identity) | **Cosmos DB Built-in Data Contributor** | Database | Read/write conversations, audit logs |
| prodinfo-faq-mcp (Managed Identity) | **Cosmos DB Built-in Data Contributor** | Database | Store/retrieve support tickets |
| ai-money-coach-mcp (Managed Identity) | **Cosmos DB Built-in Data Contributor** | Database | Store/retrieve support tickets |
| escalation-comms-mcp (Managed Identity) | **Cosmos DB Built-in Data Contributor** | Database | Store/retrieve support tickets |
| audit-mcp (Managed Identity) | **Cosmos DB Built-in Data Contributor** | Database | Write audit logs |
| Developer/Operator | **Cosmos DB Account Contributor** | Resource | Manage containers, throughput |

**⚠️ IMPORTANT**: Cosmos DB RBAC roles are **data plane** roles, assigned at the account level, not ARM-level IAM.

**Bicep Example**:
```bicep
resource cosmosRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-04-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, copilotManagedIdentity.principalId, 'Cosmos DB Built-in Data Contributor')
  properties: {
    roleDefinitionId: '${cosmosAccount.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002' // Built-in Data Contributor
    principalId: copilotManagedIdentity.properties.principalId
    scope: cosmosAccount.id
  }
}
```

---

### **Resource 5: Azure Storage Account**

**Resource Name**: `bankx{env}storage` (no hyphens, lowercase)  
**Type**: `Microsoft.Storage/storageAccounts`  
**SKU**: Standard_LRS

**Container**: `content` (for invoice uploads, documents)

| Identity | Role | Scope | Reason |
|----------|------|-------|--------|
| copilot-app (Managed Identity) | **Storage Blob Data Contributor** | Resource | Upload/read invoices, documents |
| Developer/Operator | **Storage Blob Data Owner** | Resource | Manage containers, upload test data |

---

### **Resource 6: Azure Document Intelligence**

**Resource Name**: `bankx-{env}-docintel`  
**Type**: `Microsoft.CognitiveServices/accounts` (kind: FormRecognizer)  
**SKU**: S0

| Identity | Role | Scope | Reason |
|----------|------|-------|--------|
| copilot-app (Managed Identity) | **Cognitive Services User** | Resource | Scan invoices, extract data |
| Developer/Operator | **Cognitive Services Contributor** | Resource | Train custom models (if needed) |

---

### **Resource 7: Azure Communication Services**

**Resource Name**: `bankx-{env}-commservice`  
**Type**: `Microsoft.Communication/communicationServices`

| Identity | Role | Scope | Reason |
|----------|------|-------|--------|
| escalation-comms-mcp (Managed Identity) | **Contributor** | Resource | Send support emails |
| Developer/Operator | **Contributor** | Resource | Configure email domains |

**Note**: Communication Services uses **Connection String** authentication (no RBAC for email sending yet).

---

### **Resource 8: Azure Key Vault**

**Resource Name**: `bankx-{env}-kv`  
**Type**: `Microsoft.KeyVault/vaults`  
**SKU**: Standard  
**RBAC Mode**: Enabled

**Secrets Stored**:
- Service Principal secrets for Purview agents (7 secrets)
- OpenAI API keys (if not using Managed Identity)
- Cosmos DB connection strings (if not using Managed Identity)
- Communication Services connection string
- AI Search admin keys

| Identity | Role | Scope | Reason |
|----------|------|-------|--------|
| copilot-app (Managed Identity) | **Key Vault Secrets User** | Resource | Read service principal secrets for Purview |
| prodinfo-faq-mcp (Managed Identity) | **Key Vault Secrets User** | Resource | Read Purview SP secret (if needed) |
| ai-money-coach-mcp (Managed Identity) | **Key Vault Secrets User** | Resource | Read Purview SP secret (if needed) |
| escalation-comms-mcp (Managed Identity) | **Key Vault Secrets User** | Resource | Read Communication Services connection string |
| All other MCP services | **Key Vault Secrets User** | Resource | Read shared secrets |
| Developer/Operator | **Key Vault Administrator** | Resource | Manage secrets, access policies |

---

### **Resource 9: Azure Purview**

**Resource Name**: `bankx-purview`  
**Type**: `Microsoft.Purview/accounts`  
**SKU**: Standard  
**Location**: Southeast Asia (or your region)

**⚠️ CRITICAL**: Purview uses **TWO separate RBAC systems**:
1. **Azure RBAC** (control plane) - Manage the Purview account itself
2. **Purview RBAC** (data plane) - Access Purview catalog, lineage, data sources

| Identity | Azure RBAC Role | Scope | Reason |
|----------|------------------|-------|--------|
| Developer/Operator | **Contributor** | Resource | Manage Purview account, collections |
| copilot-app (Managed Identity) | **Reader** | Resource | Read Purview metadata (optional) |

| Identity | Purview RBAC Role | Scope (Collection) | Reason |
|----------|-------------------|-------------------|--------|
| BankX-AccountAgent-SP | **Purview Data Curator** | Root Collection | Write lineage for account operations |
| BankX-TransactionAgent-SP | **Purview Data Curator** | Root Collection | Write lineage for transaction operations |
| BankX-PaymentAgent-SP | **Purview Data Curator** | Root Collection | Write lineage for payment operations |
| BankX-ProdInfoAgent-SP | **Purview Data Curator** | Root Collection | Write lineage for product info queries |
| BankX-MoneyCoachAgent-SP | **Purview Data Curator** | Root Collection | Write lineage for money coach queries |
| BankX-EscalationAgent-SP | **Purview Data Curator** | Root Collection | Write lineage for escalation flows |
| BankX-SupervisorAgent-SP | **Purview Data Curator** | Root Collection | Write lineage for supervisor routing |

**Purview Roles Explained**:
- **Data Curator**: Can create/edit entities, relationships, and lineage (what agents need)
- **Data Reader**: Read-only access to catalog (too restrictive)
- **Data Source Administrator**: Manage data sources (too permissive)

**⚠️ PURVIEW RBAC ASSIGNMENT MUST BE DONE MANUALLY**:
Purview RBAC cannot be assigned via Bicep/ARM templates. Must use:
1. **Purview Governance Portal UI** (easiest)
2. **Purview REST API** (scriptable)

**Manual Assignment Steps**:
```
1. Go to https://{purview-account-name}.purview.azure.com
2. Click "Data Map" → "Collections"
3. Select root collection (same name as account)
4. Click "Role assignments" tab
5. Add each Service Principal (by App ID) to "Data Curators" role
6. Repeat for all 7 service principals
```

---

### **Resource 10: Azure Application Insights**

**Resource Name**: `bankx-{env}-appinsights`  
**Type**: `Microsoft.Insights/components`

| Identity | Role | Scope | Reason |
|----------|------|-------|--------|
| All Container Apps (Managed Identities) | **Monitoring Metrics Publisher** | Resource | Send telemetry, metrics |
| Developer/Operator | **Application Insights Component Contributor** | Resource | View logs, configure alerts |

---

### **Resource 11: Azure Container Apps Environment**

**Resource Name**: `bankx-{env}-containerapps-env`  
**Type**: `Microsoft.App/managedEnvironments`

| Identity | Role | Scope | Reason |
|----------|------|-------|--------|
| Developer/Operator | **Contributor** | Resource | Deploy apps, manage environment |

---

### **Resource 12: Container Apps (9+ apps)**

Each Container App gets auto-generated Managed Identity. No explicit role assignment needed on the Container App resource itself.

---

## 🔐 **CROSS-RESOURCE PERMISSIONS SUMMARY**

### **Copilot Backend (Primary Orchestrator)**

**Identity**: System-Assigned Managed Identity (auto-generated)

**Required Access**:
- ✅ Azure OpenAI → **Cognitive Services OpenAI User**
- ✅ Azure AI Foundry → **Cognitive Services User**
- ✅ Cosmos DB → **Cosmos DB Built-in Data Contributor**
- ✅ Storage Account → **Storage Blob Data Contributor**
- ✅ Document Intelligence → **Cognitive Services User**
- ✅ Key Vault → **Key Vault Secrets User**
- ✅ Application Insights → **Monitoring Metrics Publisher**

---

### **ProdInfo FAQ MCP Service**

**Identity**: System-Assigned Managed Identity

**Required Access**:
- ✅ AI Search → **Search Index Data Reader** (for `bankx-products-faq` index)
- ✅ Cosmos DB → **Cosmos DB Built-in Data Contributor** (for tickets)
- ✅ Key Vault → **Key Vault Secrets User**
- ✅ Azure OpenAI → **Cognitive Services OpenAI User** (for embeddings)

---

### **AI Money Coach MCP Service**

**Identity**: System-Assigned Managed Identity

**Required Access**:
- ✅ AI Search → **Search Index Data Reader** (for `bankx-money-coach` index)
- ✅ Cosmos DB → **Cosmos DB Built-in Data Contributor** (for cache)
- ✅ Key Vault → **Key Vault Secrets User**
- ✅ Azure OpenAI → **Cognitive Services OpenAI User** (for embeddings)

---

### **Escalation Comms MCP Service**

**Identity**: System-Assigned Managed Identity

**Required Access**:
- ✅ Communication Services → **Contributor** (send emails)
- ✅ Cosmos DB → **Cosmos DB Built-in Data Contributor** (store tickets)
- ✅ Key Vault → **Key Vault Secrets User** (read connection string)

---

### **Other MCP Services (Account, Transaction, Payment, Limits, Contacts, Audit)**

**Identity**: System-Assigned Managed Identities

**Required Access**:
- ✅ Key Vault → **Key Vault Secrets User** (minimal)
- ✅ Cosmos DB → **Cosmos DB Built-in Data Contributor** (audit service only)

---

## 🎯 **REPLICATION CHECKLIST FOR NEW SUBSCRIPTION**

### **Phase 1: Pre-Deployment (Azure Portal/CLI)**

- [ ] Create target Resource Group: `bankx-{env}-rg`
- [ ] Create 7 Service Principals in target tenant with `az ad sp create-for-rbac`
- [ ] Store Service Principal secrets in secure location (will go to Key Vault later)
- [ ] Create App Registration for frontend authentication (if separate tenant)
- [ ] Configure App Registration redirect URIs

### **Phase 2: Deploy Infrastructure (Bicep Template)**

- [ ] Deploy main Bicep template with all Azure resources
- [ ] Bicep automatically creates:
  - Azure OpenAI
  - AI Foundry
  - AI Search
  - Cosmos DB
  - Storage Account
  - Document Intelligence
  - Communication Services
  - Key Vault
  - Application Insights
  - Purview Account
- [ ] Bicep automatically assigns IAM roles (where possible)

### **Phase 3: Post-Deployment Manual Steps**

- [ ] **Purview RBAC Assignment** (MUST be manual):
  - Open Purview Governance Portal
  - Add all 7 Service Principals to "Data Curators" role
- [ ] **Upload Service Principal secrets to Key Vault**:
  - 7 secrets for Purview agents
  - Communication Services connection string
  - AI Search admin key (if using API key mode)
- [ ] **Create AI Foundry Agents** (via Python script or Portal):
  - Supervisor Agent
  - Account Agent
  - Transaction Agent
  - Payment Agent
  - ProdInfo FAQ Agent
  - AI Money Coach Agent
  - Escalation Comms Agent
- [ ] **Create AI Search Indexes** (via Python script):
  - `bankx-products-faq` with vector search enabled
  - `bankx-money-coach` with vector search enabled
- [ ] **Upload Knowledge Base Documents**:
  - Product FAQs to UC2 index
  - Money coach guides to UC3 index
- [ ] **Deploy Container Apps** (via `azd up` or Bicep):
  - Managed Identities created automatically
  - IAM roles assigned via Bicep

### **Phase 4: Configuration & Testing**

- [ ] Update `.env` files with new resource endpoints
- [ ] Test authentication for all services
- [ ] Verify Purview lineage tracking
- [ ] Test end-to-end flows (UC1, UC2, UC3)

---

## 🚨 **COMMON PERMISSION ISSUES & SOLUTIONS**

### **Issue 1: "403 Forbidden" from Azure OpenAI**

**Cause**: Managed Identity doesn't have `Cognitive Services OpenAI User` role

**Solution**:
```bash
az role assignment create \
  --assignee <managed-identity-principal-id> \
  --role "Cognitive Services OpenAI User" \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<openai-name>
```

---

### **Issue 2: "Unauthorized" from Cosmos DB**

**Cause**: Managed Identity doesn't have Cosmos DB data plane role

**Solution** (Azure CLI):
```bash
# Get Cosmos DB account ID
COSMOS_ID=$(az cosmosdb show -n <cosmos-name> -g <rg> --query id -o tsv)

# Get Managed Identity Principal ID
MI_PRINCIPAL_ID=$(az identity show -n <container-app-name> -g <rg> --query principalId -o tsv)

# Assign role (Built-in Data Contributor)
az cosmosdb sql role assignment create \
  --account-name <cosmos-name> \
  --resource-group <rg> \
  --scope "/" \
  --principal-id $MI_PRINCIPAL_ID \
  --role-definition-id "00000000-0000-0000-0000-000000000002"
```

---

### **Issue 3: Cannot find Service Principal in Purview Portal**

**Cause**: Service Principal created in wrong tenant

**Solution**: 
- Service Principal MUST be in same tenant as Purview account
- Re-create in correct tenant: `az login --tenant <correct-tenant-id>`

---

### **Issue 4: Key Vault Access Denied**

**Cause**: Key Vault using Access Policies instead of RBAC, or wrong role

**Solution**:
```bash
# Enable RBAC for Key Vault
az keyvault update --name <kv-name> --enable-rbac-authorization true

# Assign role
az role assignment create \
  --assignee <managed-identity-principal-id> \
  --role "Key Vault Secrets User" \
  --scope /subscriptions/<sub-id>/resourceGroups/<rg>/providers/Microsoft.KeyVault/vaults/<kv-name>
```

---

## 📚 **AZURE RBAC ROLE DEFINITIONS (Built-in)**

### **Cognitive Services**
- `5e0bd9bd-7b93-4f28-af87-19fc36ad61bd` = Cognitive Services OpenAI User
- `a97b65f3-24c7-4388-baec-2e87135dc908` = Cognitive Services User
- `25fbc0a9-bd7c-42a3-aa1a-3b75d497ee68` = Cognitive Services Contributor

### **Storage**
- `ba92f5b4-2d11-453d-a403-e96b0029c9fe` = Storage Blob Data Contributor
- `b7e6dc6d-f1e8-4753-8033-0f276bb0955b` = Storage Blob Data Owner
- `2a2b9908-6ea1-4ae2-8e65-a410df84e7d1` = Storage Blob Data Reader

### **Cosmos DB (ARM-level)**
- `5bd9cd88-fe45-4216-938b-f97437e15450` = Cosmos DB Account Reader
- `00000000-0000-0000-0000-000000000001` = Cosmos DB Account Reader (data plane)
- `00000000-0000-0000-0000-000000000002` = Cosmos DB Built-in Data Contributor (data plane)

### **Key Vault**
- `4633458b-17de-408a-b874-0445c86b69e6` = Key Vault Secrets User
- `00482a5a-887f-4fb3-b363-3b7fe8e74483` = Key Vault Administrator

### **Search**
- `1407120a-92aa-4202-b7e9-c0e197c71c8f` = Search Index Data Reader
- `8ebe5a00-799e-43f5-93ac-243d3dce84a7` = Search Index Data Contributor
- `7ca78c08-252a-4471-8644-bb5ff32d4ba0` = Search Service Contributor

### **Monitoring**
- `3913510d-42f4-4e42-8a64-420c390055eb` = Monitoring Metrics Publisher

---

## 🔗 **REFERENCE LINKS**

- [Azure Built-in Roles](https://learn.microsoft.com/en-us/azure/role-based-access-control/built-in-roles)
- [Cosmos DB RBAC](https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-setup-rbac)
- [Cognitive Services RBAC](https://learn.microsoft.com/en-us/azure/ai-services/openai/how-to/managed-identity)
- [Purview RBAC](https://learn.microsoft.com/en-us/purview/catalog-permissions)
- [Managed Identity Best Practices](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview)

---

## ✅ **DOCUMENT CHANGE LOG**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-21 | Initial comprehensive IAM mapping |

