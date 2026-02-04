# Service Principal Tenant Placement: BankX vs Metakaal

## 🎯 Critical Decision: Where to Create Service Principals?

**Answer: All service principals MUST be created in the METAKAAL tenant.**

This document explains why service principals for BankX agents must be created in the Metakaal tenant (where resources exist) rather than the BankX tenant (where users exist).

---

## 📋 Current Tenant Architecture

### BankX Tenant
```
Tenant ID: ed6f4727-c993-424d-ad62-91492f3c1f41
Domain: bankxthb.onmicrosoft.com
Purpose: Identity & User Authentication (User Directory)

Contains:
├─ 5 Users
│  ├─ Somchai Rattanakorn (somchai@bankxthb.onmicrosoft.com)
│  ├─ Pimchanok Thongchai (pimchanok@bankxthb.onmicrosoft.com)
│  ├─ Nattaporn Suksawat (nattaporn@bankxthb.onmicrosoft.com)
│  ├─ Anan Chaiyaporn (anan@bankxthb.onmicrosoft.com)
│  └─ Abhinav Panchkula (external guest)
│
├─ App Registration (for frontend MSAL authentication)
│  └─ Used by React app for user login
│
└─ Purpose: Authenticate END USERS to the BankX application
```

### Metakaal Tenant
```
Tenant ID: c1e8c736-fd22-4d7b-a7a2-12c6f36ac388
Domain: metakaal.com
Purpose: Resource Tenant (Infrastructure & Services)

Contains:
├─ Azure Subscription (Metakaal Microsoft Azure subscription)
├─ Resource Groups
├─ Azure Resources
│  ├─ Microsoft Purview Account
│  ├─ Azure AI Foundry Project
│  ├─ Application Insights
│  ├─ Storage Accounts
│  ├─ Azure Communication Services
│  ├─ CosmosDB
│  ├─ Container Apps (planned)
│  └─ ALL other BankX infrastructure
│
└─ Purpose: Host ALL Azure resources for BankX application
```

---

## ✅ Why Service Principals Must Be in Metakaal Tenant

### Reason 1: Resource Access & Authorization

**Fundamental Principle**: Service principals must exist in the same tenant as the resources they need to access.

```
Service Principals = Application identities for RESOURCE access
Users = Human identities for APPLICATION access

Microsoft Purview Account location: Metakaal Tenant
↓
Service Principal needs to access: Purview Account
↓
Service Principal must exist in: Metakaal Tenant ✅
```

**Azure Rule**: You cannot grant a service principal from Tenant A access to resources in Tenant B without complex cross-tenant configuration (Azure Lighthouse, B2B, etc.) which is not suitable for this use case.

---

### Reason 2: RBAC Role Assignment Scope

When creating a service principal with role assignment:

```bash
az ad sp create-for-rbac \
  --name "BankX-AccountAgent-SP" \
  --role "Purview Data Curator" \
  --scopes "/subscriptions/<subscription-id>/resourceGroups/<rg>/providers/Microsoft.Purview/accounts/<purview-account>"
```

**What happens**:
1. Azure creates the service principal in the **current tenant**
2. Azure assigns the specified role to that service principal
3. The role assignment scope MUST be a resource in the **same tenant**

**Key Point**: The subscription, resource group, and Purview account in the scope path all belong to Metakaal tenant. You cannot assign a role from BankX tenant to resources in Metakaal tenant.

```
Scope Path: /subscriptions/<metakaal-subscription>/resourceGroups/...
                              ↑
                    This subscription exists in Metakaal tenant!
                    
Therefore: Service principal must also be in Metakaal tenant
```

---

### Reason 3: Authentication Token Flow

**Runtime authentication flow when agent accesses Purview**:

```python
# Agent code
from azure.identity import ClientSecretCredential

# Authenticate using service principal
credential = ClientSecretCredential(
    tenant_id="c1e8c736-fd22-4d7b-a7a2-12c6f36ac388",  # Metakaal!
    client_id="<service-principal-client-id>",
    client_secret="<service-principal-secret>"
)

# Request access token
token = credential.get_token("https://purview.azure.com/.default")
```

**Token acquisition process**:
1. Agent sends credentials to Azure AD endpoint: `https://login.microsoftonline.com/c1e8c736-fd22-4d7b-a7a2-12c6f36ac388/oauth2/v2.0/token`
2. Azure AD in **Metakaal tenant** validates the client_id and client_secret
3. Azure AD issues an access token with:
   - Issuer: `https://sts.windows.net/c1e8c736-fd22-4d7b-a7a2-12c6f36ac388/` (Metakaal)
   - Audience: `https://purview.azure.com`
   - Subject: Service principal object ID (from Metakaal tenant)

**Token validation by Purview**:
1. Agent calls Purview API with the token
2. Purview validates the token:
   - ✅ Checks issuer is from Metakaal tenant (where Purview exists)
   - ✅ Checks signature using Metakaal tenant's JWKS
   - ✅ Checks RBAC: Does this service principal have "Data Curator" role?
3. Purview allows the operation

**If service principal was in BankX tenant**:
- Token would be issued by BankX tenant: `https://sts.windows.net/ed6f4727-c993-424d-ad62-91492f3c1f41/`
- Purview would reject the token because:
  - ❌ Token is from wrong tenant (BankX, not Metakaal)
  - ❌ Service principal doesn't exist in Metakaal tenant's RBAC
  - ❌ Cross-tenant access not configured

---

### Reason 4: Azure Resource Manager (ARM) Boundaries

**Azure's tenant isolation model**:

```
Azure Resource Manager enforces strict tenant boundaries.

Metakaal Tenant (c1e8c736-fd22-4d7b-a7a2-12c6f36ac388)
├─ Subscription: Metakaal Microsoft Azure subscription
│  ├─ Resource Group: bankx-prod-rg
│  │  ├─ Purview Account: bankx-purview
│  │  │  └─ IAM (Access Control)
│  │  │     ├─ Role Assignments (only for Metakaal tenant identities)
│  │  │     ├─ ✅ Can assign: Metakaal service principals
│  │  │     ├─ ✅ Can assign: Metakaal users (if any)
│  │  │     ├─ ✅ Can assign: Managed identities in Metakaal
│  │  │     └─ ❌ Cannot assign: BankX tenant identities
│  │  │
│  │  └─ Other resources (AI Foundry, Storage, etc.)
│  │
│  └─ RBAC is tenant-scoped
│
└─ ARM API endpoint validates all operations against Metakaal tenant

BankX Tenant (ed6f4727-c993-424d-ad62-91492f3c1f41)
├─ No Azure subscription (or separate subscription if any)
├─ No Purview Account
├─ Service principals here exist in isolation
└─ Cannot directly access Metakaal resources without cross-tenant setup
```

**Key Insight**: Azure Resource Manager API calls for Metakaal resources require authentication tokens from Metakaal tenant.

---

### Reason 5: Subscription and Resource Hierarchy

**Azure hierarchy**:
```
Tenant (c1e8c736-fd22-4d7b-a7a2-12c6f36ac388 - Metakaal)
  ↓
Subscription (Metakaal Microsoft Azure subscription)
  ↓
Resource Group (bankx-prod-rg)
  ↓
Resource (Microsoft Purview Account)
  ↓
RBAC Assignments (Service Principals with Data Curator role)
```

**All levels of this hierarchy exist within a single tenant boundary.** You cannot inject an identity from a different tenant into this hierarchy without special cross-tenant federation.

**Service principals must exist at the Tenant level to be assignable at any level below (Subscription, Resource Group, or Resource).**

---

## 🚨 What Would Happen If You Created SPs in BankX Tenant?

### Scenario: Attempting to Create SP in Wrong Tenant

```bash
# Step 1: Login to BankX tenant (WRONG!)
az login --tenant bankxthb.onmicrosoft.com --allow-no-subscriptions

# Step 2: Try to create service principal with Metakaal resource scope
az ad sp create-for-rbac \
  --name "BankX-AccountAgent-SP" \
  --role "Purview Data Curator" \
  --scopes "/subscriptions/<metakaal-subscription-id>/resourceGroups/bankx-prod-rg/providers/Microsoft.Purview/accounts/bankx-purview"

# ERROR:
# The subscription '<metakaal-subscription-id>' does not exist in tenant 
# 'ed6f4727-c993-424d-ad62-91492f3c1f41'
```

**Why it fails**: Azure CLI is authenticated to BankX tenant but trying to reference a subscription that exists in Metakaal tenant. Cross-tenant resource references are not allowed in this context.

---

### Scenario: Creating SP Without Role Assignment

```bash
# Step 1: Create SP in BankX tenant without role
az login --tenant bankxthb.onmicrosoft.com --allow-no-subscriptions
az ad sp create-for-rbac --name "BankX-AccountAgent-SP" --skip-assignment

# This succeeds! SP is created in BankX tenant.
# Output:
# {
#   "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
#   "tenant": "ed6f4727-c993-424d-ad62-91492f3c1f41"  ← BankX tenant
# }

# Step 2: Try to manually assign role in Azure Portal
# Navigate to Purview Account (in Metakaal tenant) → Access Control (IAM) → Add role assignment
# Search for "BankX-AccountAgent-SP"
# Result: NOT FOUND ❌

# Why: Azure Portal is scoped to Metakaal tenant when viewing Purview resource.
# It only shows identities from Metakaal tenant in the assignment UI.
```

---

### Scenario: Runtime Authentication Failure

```python
# Agent code with BankX tenant service principal
from azure.identity import ClientSecretCredential
from azure.purview.catalog import PurviewCatalogClient

# Using service principal from BankX tenant
credential = ClientSecretCredential(
    tenant_id="ed6f4727-c993-424d-ad62-91492f3c1f41",  # BankX tenant
    client_id="<sp-from-bankx-tenant>",
    client_secret="<secret>"
)

# This succeeds - gets token from BankX tenant
token = credential.get_token("https://purview.azure.com/.default")

# Initialize Purview client (in Metakaal tenant)
purview_endpoint = "https://bankx-purview.purview.azure.com"
purview_client = PurviewCatalogClient(
    endpoint=purview_endpoint,
    credential=credential
)

# Try to create entity
try:
    response = purview_client.entity.create_or_update(entity={...})
except Exception as e:
    # ERROR: 401 Unauthorized
    # OR: 403 Forbidden
    # 
    # Reason: Purview validates the token and finds:
    # - Token issuer: BankX tenant (ed6f4727...)
    # - Purview location: Metakaal tenant (c1e8c736...)
    # - No cross-tenant trust configured
    # - Service principal not found in Metakaal RBAC
    print(f"Failed: {e}")
```

**Result**: Agent cannot access Purview because the authentication token is from the wrong tenant.

---

## ✅ Correct Implementation: Metakaal Tenant

### Step 1: Ensure You're in Metakaal Tenant

```bash
# Login to Metakaal tenant
az login --tenant metakaal.com

# Verify tenant
az account show --query "{TenantId:tenantId, Name:name, Domain:homeTenantId}" -o table

# Expected output:
# TenantId                              Name                   Domain
# c1e8c736-fd22-4d7b-a7a2-12c6f36ac388  Metakaal Pte Ltd      c1e8c736-fd22-4d7b-a7a2-12c6f36ac388

# List subscriptions (should see Metakaal subscription)
az account list --query "[].{Name:name, SubscriptionId:id, TenantId:tenantId}" -o table
```

---

### Step 2: Get Purview Resource Scope

```bash
# Find your Purview account
az purview account list --query "[].{Name:name, ResourceGroup:resourceGroup, Id:id}" -o table

# Or construct scope manually
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
RESOURCE_GROUP="bankx-prod-rg"  # Your resource group name
PURVIEW_ACCOUNT="bankx-purview"  # Your Purview account name

PURVIEW_SCOPE="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}/providers/Microsoft.Purview/accounts/${PURVIEW_ACCOUNT}"

echo $PURVIEW_SCOPE
# Output: /subscriptions/<sub-id>/resourceGroups/bankx-prod-rg/providers/Microsoft.Purview/accounts/bankx-purview
```

---

### Step 3: Create Service Principals (One for Each Agent)

```bash
# AccountAgent Service Principal
az ad sp create-for-rbac \
  --name "BankX-AccountAgent-SP" \
  --role "Purview Data Curator" \
  --scopes "$PURVIEW_SCOPE" \
  --years 1 \
  --output json

# Save the output:
# {
#   "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",       ← CLIENT_ID
#   "displayName": "BankX-AccountAgent-SP",
#   "password": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",         ← CLIENT_SECRET
#   "tenant": "c1e8c736-fd22-4d7b-a7a2-12c6f36ac388"       ← Metakaal tenant ✅
# }

# Repeat for other agents:
# - BankX-TransactionAgent-SP
# - BankX-PaymentAgent-SP
# - BankX-ProdInfoAgent-SP
# - BankX-MoneyCoachAgent-SP
# - BankX-EscalationAgent-SP
```

**Important**: All service principals will be created in Metakaal tenant and automatically granted "Purview Data Curator" role on the Purview account.

---

### Step 4: Verify Service Principal Creation

```bash
# List service principals (should see all 6)
az ad sp list --display-name "BankX-" --query "[].{DisplayName:displayName, AppId:appId}" -o table

# Verify role assignment on Purview
az role assignment list \
  --scope "$PURVIEW_SCOPE" \
  --query "[?roleDefinitionName=='Purview Data Curator'].{Principal:principalName, Role:roleDefinitionName}" \
  -o table

# Should show all 6 service principals with Data Curator role
```

---

### Step 5: Configure Application

**Environment Variables** (`.env` or `.env.prod`):

```bash
# Purview Configuration (Metakaal Tenant)
PURVIEW_ACCOUNT_NAME="bankx-purview"
PURVIEW_TENANT_ID="c1e8c736-fd22-4d7b-a7a2-12c6f36ac388"  # Metakaal! ✅
PURVIEW_ENDPOINT="https://bankx-purview.purview.azure.com"

# Service Principal Credentials (all from Metakaal tenant)
PURVIEW_ACCOUNT_AGENT_CLIENT_ID="<account-agent-app-id>"
PURVIEW_ACCOUNT_AGENT_CLIENT_SECRET="<account-agent-password>"

PURVIEW_TRANSACTION_AGENT_CLIENT_ID="<transaction-agent-app-id>"
PURVIEW_TRANSACTION_AGENT_CLIENT_SECRET="<transaction-agent-password>"

PURVIEW_PAYMENT_AGENT_CLIENT_ID="<payment-agent-app-id>"
PURVIEW_PAYMENT_AGENT_CLIENT_SECRET="<payment-agent-password>"

PURVIEW_PRODINFO_AGENT_CLIENT_ID="<prodinfo-agent-app-id>"
PURVIEW_PRODINFO_AGENT_CLIENT_SECRET="<prodinfo-agent-password>"

PURVIEW_MONEYCOACH_AGENT_CLIENT_ID="<moneycoach-agent-app-id>"
PURVIEW_MONEYCOACH_AGENT_CLIENT_SECRET="<moneycoach-agent-password>"

PURVIEW_ESCALATION_AGENT_CLIENT_ID="<escalation-agent-app-id>"
PURVIEW_ESCALATION_AGENT_CLIENT_SECRET="<escalation-agent-password>"

# Note: User authentication still uses BankX tenant (separate flow)
AZURE_AUTH_TENANT_ID="ed6f4727-c993-424d-ad62-91492f3c1f41"  # BankX (for users)
```

---

### Step 6: Runtime Code

**Agent Purview Service** (`app/copilot/app/purview/agent_purview_service.py`):

```python
from azure.identity import ClientSecretCredential
from azure.purview.catalog import PurviewCatalogClient

class AgentPurviewService:
    def __init__(
        self,
        agent_name: str,
        agent_id: str,
        client_id: str,
        client_secret: str,
        tenant_id: str,  # This will be Metakaal tenant ID
        purview_account_name: str,
        purview_endpoint: str
    ):
        # Create credential for Metakaal tenant ✅
        self.credential = ClientSecretCredential(
            tenant_id=tenant_id,  # c1e8c736-fd22-4d7b-a7a2-12c6f36ac388
            client_id=client_id,
            client_secret=client_secret
        )
        
        # Initialize Purview client (in Metakaal tenant)
        self.client = PurviewCatalogClient(
            endpoint=purview_endpoint,
            credential=self.credential
        )
        
        # Token will be obtained from Metakaal tenant ✅
        # Token will be validated by Purview in Metakaal tenant ✅
        # RBAC will check service principal in Metakaal tenant ✅
```

---

## 🔄 Two Separate Authentication Flows

### Authentication Flow 1: User Authentication (BankX Tenant)

**Purpose**: Authenticate end users to the BankX application

```
1. User opens https://bankx-app.com
2. MSAL.js initiates login
3. Redirects to: login.microsoftonline.com/bankxthb.onmicrosoft.com
4. User enters credentials (Somchai's username/password)
5. Azure AD (BankX tenant) authenticates user
6. Azure AD issues JWT token:
   - Issuer: BankX tenant (ed6f4727...)
   - Audience: App Registration client ID
   - Subject: User object ID (Somchai)
7. Frontend receives token, stores in session
8. Frontend sends token to backend API with each request
9. Backend validates token:
   - Uses JWKS from BankX tenant
   - Extracts customer_id from token
   - Identifies user as Somchai
10. Backend processes request using Somchai's customer_id

✅ This flow remains UNCHANGED
✅ Uses BankX tenant for user identity
```

---

### Authentication Flow 2: Service Authentication (Metakaal Tenant)

**Purpose**: Authenticate agents to Azure resources (Purview, AI Foundry, etc.)

```
1. AccountAgent needs to track lineage in Purview
2. Agent retrieves credentials from environment:
   - Client ID: <account-agent-sp-id>
   - Client Secret: <account-agent-secret>
   - Tenant ID: c1e8c736... (Metakaal)
3. Agent calls Azure AD token endpoint:
   - URL: login.microsoftonline.com/c1e8c736-fd22-4d7b-a7a2-12c6f36ac388/oauth2/v2.0/token
4. Azure AD (Metakaal tenant) validates service principal credentials
5. Azure AD issues access token:
   - Issuer: Metakaal tenant (c1e8c736...)
   - Audience: https://purview.azure.com
   - Subject: Service principal object ID
6. Agent includes token in Purview API request
7. Purview validates token:
   - Token is from Metakaal tenant ✅
   - Service principal exists in Purview RBAC ✅
   - Service principal has Data Curator role ✅
8. Purview allows the operation
9. Agent tracks lineage successfully

✅ This is NEW functionality
✅ Uses Metakaal tenant for resource access
```

---

## 📊 Complete Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BankX Tenant                                 │
│                 (ed6f4727-c993-424d-ad62-91492f3c1f41)              │
│                     bankxthb.onmicrosoft.com                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  👤 Users (Human Identities)                                         │
│  ├─ Somchai Rattanakorn                                             │
│  ├─ Pimchanok Thongchai                                             │
│  ├─ Nattaporn Suksawat                                              │
│  ├─ Anan Chaiyaporn                                                 │
│  └─ Abhinav Panchkula (guest)                                       │
│                                                                       │
│  🔐 App Registration                                                 │
│  └─ Client ID: <app-registration-id>                                │
│     └─ Used by: React frontend (MSAL.js)                            │
│                                                                       │
│  ✅ Authentication Scope: END USERS only                             │
│  ✅ Token Type: JWT (user identity)                                  │
│  ✅ Token Audience: BankX frontend application                       │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ User JWT Token
                              │ (User Identity: Somchai)
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                    BankX Backend API                                 │
│                (Validates user tokens from BankX tenant)             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  🔍 Token Validation                                                 │
│  ├─ JWKS from BankX tenant                                          │
│  ├─ Extract customer_id                                             │
│  └─ Identify user (Somchai → customer_001)                          │
│                                                                       │
│  🤖 Agents (6 agents)                                                │
│  ├─ SupervisorAgent ──┐                                             │
│  ├─ AccountAgent      │                                             │
│  ├─ TransactionAgent  ├─ Each agent needs to access Purview        │
│  ├─ PaymentAgent      │   (in Metakaal tenant)                      │
│  ├─ ProdInfoAgent     │                                             │
│  └─ MoneyCoachAgent  ─┘                                             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ Service Principal Authentication
                              │ (6 separate authentications)
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│                       Metakaal Tenant                                │
│                 (c1e8c736-fd22-4d7b-a7a2-12c6f36ac388)              │
│                           metakaal.com                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  🔧 Service Principals (Application Identities)                      │
│  ├─ BankX-AccountAgent-SP                                           │
│  │  ├─ Client ID: xxxx-xxxx-xxxx                                    │
│  │  ├─ Client Secret: ******************                            │
│  │  └─ RBAC: Purview Data Curator ✅                                │
│  │                                                                   │
│  ├─ BankX-TransactionAgent-SP                                       │
│  │  ├─ Client ID: xxxx-xxxx-xxxx                                    │
│  │  ├─ Client Secret: ******************                            │
│  │  └─ RBAC: Purview Data Curator ✅                                │
│  │                                                                   │
│  ├─ BankX-PaymentAgent-SP                                           │
│  │  └─ ... (similar structure)                                      │
│  │                                                                   │
│  ├─ BankX-ProdInfoAgent-SP                                          │
│  ├─ BankX-MoneyCoachAgent-SP                                        │
│  └─ BankX-EscalationAgent-SP                                        │
│                                                                       │
│  ☁️ Azure Resources                                                  │
│  ├─ Subscription: Metakaal Microsoft Azure subscription             │
│  │  └─ Resource Group: bankx-prod-rg                                │
│  │     ├─ Microsoft Purview Account ← Target resource              │
│  │     │  └─ IAM: All 6 SPs have Data Curator role                 │
│  │     ├─ Azure AI Foundry Project                                  │
│  │     ├─ Application Insights                                       │
│  │     ├─ Storage Accounts                                           │
│  │     ├─ CosmosDB                                                   │
│  │     ├─ Communication Services                                     │
│  │     └─ Container Apps (planned)                                   │
│                                                                       │
│  ✅ Authentication Scope: SERVICE/RESOURCE ACCESS                    │
│  ✅ Token Type: OAuth2 access token (service identity)              │
│  ✅ Token Audience: Azure Resource Manager / Purview API            │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📝 Summary

### Critical Points

1. **Service principals MUST be in Metakaal tenant** because:
   - ✅ Purview and all Azure resources are in Metakaal tenant
   - ✅ RBAC assignments only work within same tenant
   - ✅ Token validation requires matching tenant
   - ✅ Azure Resource Manager enforces tenant boundaries

2. **BankX tenant is for user authentication only**:
   - ✅ Contains user directory (Somchai, Pimchanok, etc.)
   - ✅ App Registration for MSAL.js authentication
   - ✅ Issues JWT tokens for user identity
   - ❌ Does NOT contain service principals for resource access

3. **Two separate authentication domains**:
   - **Domain 1**: Users authenticate to BankX tenant (frontend login)
   - **Domain 2**: Agents authenticate to Metakaal tenant (resource access)

4. **Configuration**:
   ```bash
   # User authentication (BankX tenant)
   AZURE_AUTH_TENANT_ID="ed6f4727-c993-424d-ad62-91492f3c1f41"
   
   # Service authentication (Metakaal tenant)
   PURVIEW_TENANT_ID="c1e8c736-fd22-4d7b-a7a2-12c6f36ac388"
   ```

5. **Service principal creation command**:
   ```bash
   # MUST login to Metakaal tenant first
   az login --tenant metakaal.com
   
   # Then create service principals
   az ad sp create-for-rbac --name "BankX-AccountAgent-SP" ...
   ```

---

## ✅ Next Steps

When ready to implement:

1. **Login to Metakaal tenant**
   ```bash
   az login --tenant metakaal.com
   ```

2. **Verify tenant context**
   ```bash
   az account show --query "{Tenant:tenantId, Name:name}"
   # Should show: c1e8c736-fd22-4d7b-a7a2-12c6f36ac388
   ```

3. **Create all 6 service principals** (see Step 3 above)

4. **Store credentials securely** (Azure Key Vault or `.env` file)

5. **Configure application** with Metakaal tenant ID

6. **Test authentication** for each agent

---

## 📚 References

- [Azure Active Directory tenants](https://learn.microsoft.com/en-us/azure/active-directory/develop/quickstart-create-new-tenant)
- [Service principals in Azure AD](https://learn.microsoft.com/en-us/azure/active-directory/develop/app-objects-and-service-principals)
- [Azure RBAC scope levels](https://learn.microsoft.com/en-us/azure/role-based-access-control/scope-overview)
- [Microsoft Purview access control](https://learn.microsoft.com/en-us/azure/purview/catalog-permissions)

---

**Document Version**: 1.0  
**Last Updated**: November 17, 2025  
**Decision**: Service Principals MUST be created in Metakaal Tenant
