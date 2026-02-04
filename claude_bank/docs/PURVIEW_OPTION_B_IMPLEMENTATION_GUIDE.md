# Microsoft Purview Integration - Option B: Per-Agent Service Principals

## 🎯 Executive Summary

**Option B** implements granular authentication for Microsoft Purview by creating **6 separate service principals** - one for each specialized agent in the BankX system. This approach provides maximum audit granularity and allows fine-grained RBAC control at the agent level.

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Concepts](#key-concepts)
3. [Implementation Phases](#implementation-phases)
4. [Detailed Step-by-Step Approach](#detailed-step-by-step-approach)
5. [Configuration Requirements](#configuration-requirements)
6. [Security Considerations](#security-considerations)
7. [Operational Overhead](#operational-overhead)
8. [Testing Strategy](#testing-strategy)
9. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
10. [Comparison with Option A](#comparison-with-option-a)
11. [Decision Checklist](#decision-checklist)

---

## 🏗️ Architecture Overview

### Current Architecture (No Purview)
```
User Request
    ↓
SupervisorAgent (routes)
    ↓
AccountAgent / TransactionAgent / PaymentAgent / etc.
    ↓
MCP Tools (account, transaction, payment)
    ↓
Data Sources (accounts.json, transactions.json)
```

### Option B Architecture (Per-Agent Service Principals)
```
User Request
    ↓
SupervisorAgent
    ├─ Uses: SP-Account (authenticates to Purview)
    ↓
AccountAgent
    ├─ Service Principal: BankX-AccountAgent-SP
    ├─ Client ID: <unique-id-1>
    ├─ Client Secret: <secret-1>
    ├─ Purview Role: Data Curator
    ├─ Tracks: Account lookups, balance queries
    ↓
TransactionAgent
    ├─ Service Principal: BankX-TransactionAgent-SP
    ├─ Client ID: <unique-id-2>
    ├─ Client Secret: <secret-2>
    ├─ Purview Role: Data Curator
    ├─ Tracks: Transaction history, spending patterns
    ↓
PaymentAgent
    ├─ Service Principal: BankX-PaymentAgent-SP
    ├─ Client ID: <unique-id-3>
    ├─ Client Secret: <secret-3>
    ├─ Purview Role: Data Curator
    ├─ Tracks: Payment initiation, invoice processing
    ↓
... (3 more agents with their own SPs)
```

### Data Flow with Purview Tracking
```
1. User: "What's my account balance?"
2. SupervisorAgent → Routes to AccountAgent
3. AccountAgent:
   ├─ Authenticates to Purview using SP-Account
   ├─ Creates lineage event: User Query → AccountAgent
4. AccountAgent → Calls MCP Tool: get_account_details
5. AccountAgent:
   ├─ Tracks MCP call lineage: AccountAgent → accounts.json
   ├─ All tracked using BankX-AccountAgent-SP credentials
6. Purview Catalog:
   ├─ Records: Which agent (AccountAgent)
   ├─ Records: Which customer (customer_id)
   ├─ Records: Which data (accounts.json)
   ├─ Records: Which service principal (SP-Account)
   ├─ Timestamp, request_id, conversation_id
```

---

## 🔑 Key Concepts

### Service Principal (Authentication Layer)
- **What**: Azure AD identity used by the agent to authenticate to Purview
- **Purpose**: Proves the agent's identity to Azure services
- **Granularity**: One per agent (6 total)
- **Credentials**: Client ID + Client Secret
- **Lifecycle**: Secrets expire every 90 days (configurable)

### Agent ID (Identification Layer)
- **What**: Azure AI Foundry agent unique identifier (e.g., `asst_abc123`)
- **Purpose**: Identifies which agent performed the action in Purview metadata
- **Granularity**: Already exists, one per agent
- **Credentials**: None (just an identifier)
- **Lifecycle**: Permanent (tied to Azure AI Foundry agent)

### Why Both?
```
Service Principal = "How the agent authenticates"
Agent ID = "Which agent is acting"

Example in Purview lineage:
- Authenticated by: BankX-AccountAgent-SP (client_id: xxx)
- Acting as: AccountAgent (agent_id: asst_abc123)
- Action: Retrieved account balance
- Customer: customer_001
- Data source: accounts.json
```

### RBAC Model
```
Option B allows:
✅ Grant AccountAgent SP access to account-related data only
✅ Grant PaymentAgent SP access to payment-related data only
✅ Restrict TransactionAgent SP from accessing payment data
✅ Audit which SP accessed what data when

Note: This is MORE granular than needed for most compliance requirements,
but provides maximum control if your compliance team requires it.
```

---

## 📅 Implementation Phases

### Phase 1: Azure Setup (Infrastructure)
**Duration**: 1-2 hours  
**Complexity**: Low  
**Dependencies**: Azure CLI access, Purview account created

**Tasks**:
1. Create 6 service principals in Metakaal tenant
2. Assign "Purview Data Curator" role to each
3. Store credentials securely (Azure Key Vault recommended)
4. Document client IDs and secret expiration dates

---

### Phase 2: Configuration (Settings)
**Duration**: 30 minutes  
**Complexity**: Low  
**Dependencies**: Service principals created

**Tasks**:
1. Add 12 new environment variables to `.env` file
   - 6 client IDs
   - 6 client secrets
2. Add 4 Purview configuration variables
   - Purview account name
   - Purview tenant ID
   - Purview endpoint URL
   - Enable/disable flag
3. Update `settings.py` to load new variables
4. Validate configuration loading

---

### Phase 3: Core Purview Service (Backend)
**Duration**: 4-6 hours  
**Complexity**: Medium  
**Dependencies**: Azure Purview SDK installed

**Tasks**:
1. Create `AgentPurviewService` class
   - Accepts agent-specific credentials
   - Handles Purview authentication per agent
   - Provides methods: `track_agent_action()`, `track_mcp_tool_call()`, `track_rag_search()`
2. Create `PurviewServiceFactory` class
   - Factory methods for each agent type
   - `create_for_account_agent()`, `create_for_transaction_agent()`, etc.
   - Centralizes agent-specific credential retrieval
3. Implement error handling and fallback logic
   - Graceful degradation if Purview unavailable
   - Logging for failed lineage tracking

---

### Phase 4: Dependency Injection (IoC Container)
**Duration**: 2-3 hours  
**Complexity**: Medium  
**Dependencies**: Core Purview service implemented

**Tasks**:
1. Wire `PurviewServiceFactory` as singleton in container
2. Inject factory into each agent constructor
3. Update all 6 agent classes to accept `purview_service_factory` parameter
4. Ensure factory is available during agent initialization

---

### Phase 5: Agent Integration (6 Agents)
**Duration**: 6-8 hours (1-1.5 hours per agent)  
**Complexity**: Medium  
**Dependencies**: Factory wired, agents updated

**Tasks for EACH agent**:
1. Accept `purview_service_factory` in constructor
2. During initialization, call factory to get agent-specific Purview service
   ```
   self.purview_service = purview_service_factory.create_for_account_agent(self.agent_id)
   ```
3. Before calling MCP tool, track lineage:
   ```
   self.purview_service.track_agent_action(
       action_type="account_lookup",
       input_data={query},
       output_data={result},
       mcp_tool="get_account_details",
       customer_id=customer_id
   )
   ```
4. Test agent independently with Purview enabled/disabled

**Agents to update**:
- AccountAgent
- TransactionAgent
- PaymentAgent
- ProdInfoFAQAgent
- AIMoneyCoachAgent
- EscalationCommsAgent

---

### Phase 6: Testing & Validation
**Duration**: 4-6 hours  
**Complexity**: Medium  
**Dependencies**: All agents integrated

**Tasks**:
1. Unit tests for `AgentPurviewService`
2. Integration tests for each agent + Purview
3. End-to-end test: User query → Supervisor → Agent → MCP → Purview
4. Verify Purview catalog shows correct lineage
5. Test with Purview disabled (should work normally)
6. Test with invalid credentials (should log error, continue)

---

### Phase 7: Secret Rotation (Operational)
**Duration**: 2-3 hours  
**Complexity**: Medium  
**Dependencies**: Agents deployed to production

**Tasks**:
1. Create secret rotation script (runs every 85 days)
2. Automate using Azure Automation or GitHub Actions
3. Rotate secrets for all 6 service principals
4. Update Key Vault with new secrets
5. Restart application to load new secrets
6. Monitor for authentication errors

---

### Phase 8: Monitoring & Alerts
**Duration**: 2-3 hours  
**Complexity**: Low-Medium  
**Dependencies**: Production deployment

**Tasks**:
1. Add Application Insights metrics for Purview calls
2. Create dashboard showing:
   - Lineage tracking success rate per agent
   - Failed authentication attempts
   - Secret expiration countdown
3. Set up alerts:
   - Secrets expiring in < 7 days
   - Purview call failure rate > 5%
   - Agent authentication failures

---

## 📝 Detailed Step-by-Step Approach

### Step 1: Create Service Principals in Azure

**Prerequisites**:
- Azure CLI installed
- Logged into Metakaal tenant
- Purview account created
- Resource group name
- Subscription ID

**Commands to Execute**:
```bash
# Login to Metakaal tenant
az login --tenant metakaal.com

# Create service principal for AccountAgent
az ad sp create-for-rbac \
  --name "BankX-AccountAgent-SP" \
  --role "Purview Data Curator" \
  --scopes "/subscriptions/<subscription-id>/resourceGroups/<rg-name>/providers/Microsoft.Purview/accounts/<purview-name>" \
  --years 1

# Output:
# {
#   "appId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",  ← Client ID
#   "displayName": "BankX-AccountAgent-SP",
#   "password": "xxxxxxxxxxxxxxxxxxxxxxxxxx",         ← Client Secret
#   "tenant": "c1e8c736-fd22-4d7b-a7a2-12c6f36ac388"
# }

# Repeat for 5 other agents:
# - BankX-TransactionAgent-SP
# - BankX-PaymentAgent-SP
# - BankX-ProdInfoAgent-SP
# - BankX-MoneyCoachAgent-SP
# - BankX-EscalationAgent-SP
```

**Important**: Save all 6 client IDs and secrets immediately. Secrets cannot be retrieved later!

---

### Step 2: Store Credentials in Azure Key Vault (Recommended)

**Why Key Vault?**
- Centralized secret management
- Automatic secret rotation support
- Access logging and auditing
- No secrets in `.env` files (more secure)

**Commands**:
```bash
# Create Key Vault (if not exists)
az keyvault create \
  --name bankx-purview-secrets \
  --resource-group <rg-name> \
  --location eastus

# Store AccountAgent secret
az keyvault secret set \
  --vault-name bankx-purview-secrets \
  --name "purview-account-agent-client-secret" \
  --value "<client-secret-from-step-1>"

# Repeat for 5 other agents
```

**Alternative**: Store directly in `.env` file (simpler but less secure)

---

### Step 3: Update Configuration Files

**File**: `app/copilot/app/config/settings.py`

**Add these fields to Settings class**:
```python
# Microsoft Purview Configuration
PURVIEW_ACCOUNT_NAME: str | None
PURVIEW_TENANT_ID: str | None
PURVIEW_ENDPOINT: str | None

# Per-Agent Service Principal Configuration
PURVIEW_ACCOUNT_AGENT_CLIENT_ID: str | None
PURVIEW_ACCOUNT_AGENT_CLIENT_SECRET: str | None

PURVIEW_TRANSACTION_AGENT_CLIENT_ID: str | None
PURVIEW_TRANSACTION_AGENT_CLIENT_SECRET: str | None

PURVIEW_PAYMENT_AGENT_CLIENT_ID: str | None
PURVIEW_PAYMENT_AGENT_CLIENT_SECRET: str | None

PURVIEW_PRODINFO_AGENT_CLIENT_ID: str | None
PURVIEW_PRODINFO_AGENT_CLIENT_SECRET: str | None

PURVIEW_MONEYCOACH_AGENT_CLIENT_ID: str | None
PURVIEW_MONEYCOACH_AGENT_CLIENT_SECRET: str | None

PURVIEW_ESCALATION_AGENT_CLIENT_ID: str | None
PURVIEW_ESCALATION_AGENT_CLIENT_SECRET: str | None
```

**File**: `.env` or `.env.prod`

**Add these variables**:
```bash
# Purview Global Configuration
PURVIEW_ACCOUNT_NAME="your-purview-account"
PURVIEW_TENANT_ID="c1e8c736-fd22-4d7b-a7a2-12c6f36ac388"
PURVIEW_ENDPOINT="https://your-purview-account.purview.azure.com"

# AccountAgent Service Principal
PURVIEW_ACCOUNT_AGENT_CLIENT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
PURVIEW_ACCOUNT_AGENT_CLIENT_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxx"

# TransactionAgent Service Principal
PURVIEW_TRANSACTION_AGENT_CLIENT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
PURVIEW_TRANSACTION_AGENT_CLIENT_SECRET="xxxxxxxxxxxxxxxxxxxxxxxxxx"

# ... (repeat for 4 other agents)
```

---

### Step 4: Implement AgentPurviewService Class

**File**: `app/copilot/app/purview/agent_purview_service.py`

**Class Purpose**: Handle Purview operations for a single agent with its own credentials

**Key Methods**:
1. `__init__(agent_name, agent_id, client_id, client_secret, ...)`
   - Initialize with agent-specific credentials
   - Create `ClientSecretCredential` for this agent
   - Create `PurviewCatalogClient` authenticated with agent's SP

2. `track_agent_action(action_type, input_data, output_data, ...)`
   - Create source entity (user query)
   - Create target entity (agent response)
   - Create process entity (agent operation)
   - Create lineage relationships in Purview

3. `track_mcp_tool_call(mcp_tool_name, tool_input, tool_output, data_source, ...)`
   - Create data source entity (e.g., accounts.json)
   - Create MCP tool entity (e.g., get_account_details)
   - Link: DataSource → MCPTool (lineage)

4. `track_rag_search(vector_store_id, search_query, search_results, ...)`
   - Create vector store entity
   - Create RAG search entity
   - Link: VectorStore → RAGSearch (lineage)

**Error Handling**:
- Graceful degradation if Purview unavailable
- Log errors but don't block agent execution
- Return `None` or `{"status": "error"}` on failure

---

### Step 5: Implement PurviewServiceFactory Class

**File**: `app/copilot/app/purview/purview_service_factory.py`

**Class Purpose**: Centralize creation of agent-specific Purview services

**Key Methods**:
```python
def create_for_account_agent(agent_id: str) -> AgentPurviewService:
    return AgentPurviewService(
        agent_name="AccountAgent",
        agent_id=agent_id,
        client_id=settings.PURVIEW_ACCOUNT_AGENT_CLIENT_ID,
        client_secret=settings.PURVIEW_ACCOUNT_AGENT_CLIENT_SECRET,
        ...
    )

def create_for_transaction_agent(agent_id: str) -> AgentPurviewService:
    # Similar for TransactionAgent

# ... (create_for_payment_agent, create_for_prodinfo_agent, etc.)
```

**Benefits**:
- Single place to manage all agent credentials
- Easy to add new agents
- Simplifies agent code (no credential handling)

---

### Step 6: Wire Factory into Dependency Injection Container

**File**: `app/copilot/app/config/container_foundry.py`

**Changes Required**:

1. **Import factory**:
   ```python
   from app.purview.purview_service_factory import PurviewServiceFactory
   ```

2. **Create singleton factory**:
   ```python
   purview_service_factory = providers.Singleton(PurviewServiceFactory)
   ```

3. **Inject factory into each agent**:
   ```python
   _foundry_account_agent = providers.Singleton(
       AccountAgent,
       foundry_project_client=_foundry_project_client,
       # ... existing parameters ...
       purview_service_factory=purview_service_factory  # ← Add this
   )
   ```

4. **Repeat for all 6 agents**

---

### Step 7: Update Agent Classes (6 agents)

**Files**:
- `app/copilot/app/agents/foundry/account_agent_foundry.py`
- `app/copilot/app/agents/foundry/transaction_agent_foundry.py`
- `app/copilot/app/agents/foundry/payment_agent_foundry.py`
- `app/copilot/app/agents/foundry/prodinfo_faq_agent_knowledge_base_foundry.py`
- `app/copilot/app/agents/foundry/ai_money_coach_agent_knowledge_base_foundry.py`
- `app/copilot/app/agents/foundry/escalation_comms_agent_foundry.py`

**Changes for AccountAgent (example)**:

1. **Update constructor**:
   ```python
   def __init__(
       self,
       foundry_project_client,
       chat_deployment_name,
       account_mcp_server_url,
       limits_mcp_server_url,
       foundry_endpoint,
       agent_id=None,
       purview_service_factory=None  # ← Add this parameter
   ):
       self.purview_service_factory = purview_service_factory
       # ... rest of initialization ...
   ```

2. **Initialize Purview service**:
   ```python
   # After agent_id is set
   if self.purview_service_factory:
       self.purview_service = self.purview_service_factory.create_for_account_agent(
           agent_id=self.agent_id
       )
   else:
       self.purview_service = None
   ```

3. **Track actions before MCP calls**:
   ```python
   # Before calling MCP tool
   if self.purview_service and self.purview_service.enabled:
       self.purview_service.track_agent_action(
           action_type="account_lookup",
           input_data={"customer_id": customer_id},
           output_data=account_details,
           mcp_tool="get_account_details",
           customer_id=customer_id,
           conversation_id=thread_id,
           request_id=request_id
       )
   ```

4. **Track MCP tool calls**:
   ```python
   # After MCP tool returns
   if self.purview_service and self.purview_service.enabled:
       self.purview_service.track_mcp_tool_call(
           mcp_tool_name="get_account_details",
           tool_input={"customer_id": customer_id},
           tool_output=result,
           data_source="accounts.json",
           customer_id=customer_id
       )
   ```

**Repeat for all 6 agents with appropriate method names**

---

### Step 8: Testing Strategy

#### Unit Tests
**File**: `tests/test_agent_purview_service.py`

**Test Cases**:
1. Test AgentPurviewService initialization with valid credentials
2. Test AgentPurviewService initialization with missing credentials (should disable gracefully)
3. Mock Purview API, test `track_agent_action()` creates correct entities
4. Test error handling when Purview API fails
5. Test that agents work normally when Purview is disabled

#### Integration Tests
**File**: `tests/test_purview_integration.py`

**Test Cases**:
1. Create real service principal in test environment
2. Test AccountAgent → Purview lineage end-to-end
3. Verify lineage appears in Purview catalog
4. Test all 6 agents independently
5. Test supervisor routing with Purview tracking

#### Manual Testing Checklist
- [ ] Create service principals in Azure
- [ ] Configure `.env` with all credentials
- [ ] Start application, verify no errors
- [ ] Send test query to AccountAgent
- [ ] Check Application Insights for Purview calls
- [ ] Log into Purview portal, verify lineage entities created
- [ ] Disable Purview (remove credentials), verify app still works
- [ ] Test with invalid credentials, verify graceful error handling

---

### Step 9: Secret Rotation Implementation

**File**: `scripts/rotate_purview_secrets.sh`

**Purpose**: Automate credential rotation every 90 days

**Logic**:
1. For each service principal:
   - Generate new client secret
   - Store new secret in Key Vault
   - Keep old secret active for 7 days (grace period)
   - Remove old secret after grace period
2. Send notification to DevOps team
3. Trigger application restart to load new secrets

**Scheduling Options**:
- Azure Automation (Runbook)
- GitHub Actions (scheduled workflow)
- Azure DevOps Pipeline (scheduled)
- Kubernetes CronJob (if using AKS)

**Script Outline**:
```bash
#!/bin/bash
# For each service principal
for sp_name in BankX-AccountAgent-SP BankX-TransactionAgent-SP ...; do
    # Get SP object ID
    sp_id=$(az ad sp list --display-name "$sp_name" --query "[0].id" -o tsv)
    
    # Create new credential (expires in 90 days)
    new_secret=$(az ad sp credential reset --id "$sp_id" --append --years 1 --query "password" -o tsv)
    
    # Update Key Vault
    az keyvault secret set \
        --vault-name bankx-purview-secrets \
        --name "purview-${agent_name}-client-secret" \
        --value "$new_secret"
    
    echo "✓ Rotated secret for $sp_name"
done

# Restart application to load new secrets
# (implementation depends on deployment method)
```

---

### Step 10: Monitoring & Dashboards

#### Application Insights Metrics

**Custom Metrics to Track**:
1. `purview_lineage_tracking_success` (per agent)
2. `purview_lineage_tracking_failure` (per agent)
3. `purview_authentication_error` (per agent)
4. `purview_api_latency` (per agent)
5. `purview_secret_expiration_days` (per agent)

**Implementation**:
```python
# In AgentPurviewService
from azure.monitor.opentelemetry import configure_azure_monitor

def track_agent_action(...):
    start_time = time.time()
    try:
        result = self.client.entity.create_or_update(...)
        # Success metric
        telemetry.track_metric(
            "purview_lineage_tracking_success",
            1,
            properties={"agent": self.agent_name}
        )
    except Exception as e:
        # Failure metric
        telemetry.track_metric(
            "purview_lineage_tracking_failure",
            1,
            properties={"agent": self.agent_name, "error": str(e)}
        )
    finally:
        latency = time.time() - start_time
        telemetry.track_metric(
            "purview_api_latency",
            latency,
            properties={"agent": self.agent_name}
        )
```

#### Azure Dashboard

**Widgets**:
1. Line chart: Purview calls per agent over time
2. Pie chart: Success vs failure rate
3. Table: Secret expiration dates for all 6 agents
4. Alert status: Any secrets expiring < 7 days
5. Log query: Recent Purview authentication errors

---

## 🔒 Security Considerations

### Credential Storage

**Options**:
1. **Azure Key Vault** (Recommended)
   - ✅ Centralized secret management
   - ✅ Automatic rotation support
   - ✅ Access auditing
   - ✅ Integration with Managed Identity
   - ❌ Additional service dependency

2. **Environment Variables in `.env`**
   - ✅ Simple to implement
   - ✅ No additional dependencies
   - ❌ Secrets visible in file
   - ❌ Manual rotation required
   - ❌ Risk of accidental commit to Git

3. **Azure App Configuration** (Alternative)
   - ✅ Centralized configuration
   - ✅ Feature flags support
   - ❌ Additional service cost
   - ❌ More complex setup

**Recommendation**: Use Key Vault for production, `.env` for development

---

### Secret Rotation Schedule

**Best Practices**:
- Rotate secrets every **90 days** (Azure default expiration)
- Set rotation schedule to **85 days** (5-day buffer)
- Keep old secret active for **7 days** grace period during rotation
- Monitor for authentication errors after rotation
- Have rollback plan (restore old secret if issues)

**Automation Required**: Manual rotation for 6 agents every 90 days is operationally risky!

---

### Least Privilege Access

**Purview Roles**:
- **Data Curator**: Can create/edit entities and lineage (what agents need)
- **Data Reader**: Can only read entities (too restrictive)
- **Data Source Administrator**: Can manage data sources (too permissive)

**Recommendation**: Grant "Purview Data Curator" to all 6 service principals

**Future Enhancement**: If specific agents only need read access, use Data Reader role

---

### Audit Logging

**Track These Events**:
1. Service principal authentication attempts (success/failure)
2. Purview API calls (entity creation, lineage updates)
3. Secret rotation events
4. Configuration changes (new agents, credential updates)

**Implementation**: Use Azure Monitor + Application Insights

---

## 🛠️ Operational Overhead

### Complexity Comparison

| Aspect | Option A (Single SP) | Option B (Per-Agent SPs) |
|--------|---------------------|-------------------------|
| **Service Principals** | 1 | 6 |
| **Secrets to Manage** | 1 | 6 |
| **Rotation Frequency** | Every 90 days | Every 90 days (× 6) |
| **Configuration Variables** | 4 | 16 |
| **Debugging Complexity** | Low | Medium-High |
| **Authentication Failures** | 1 point of failure | 6 points of failure |
| **RBAC Granularity** | Service-level | Agent-level |
| **Audit Granularity** | Service-level | Agent-level |

---

### Ongoing Maintenance Tasks

#### Monthly
- Monitor secret expiration dates (all 6 agents)
- Review Purview lineage quality per agent
- Check for authentication errors

#### Quarterly
- Rotate all 6 service principal secrets (automated)
- Review Purview Data Curator permissions
- Audit which agents accessed what data

#### Annually
- Review whether per-agent SPs still needed
- Evaluate if any agents can share SPs
- Consider migration to Managed Identity (if available)

---

### Troubleshooting Common Issues

#### Issue 1: Agent Authentication Failure
**Symptoms**: Agent works but Purview lineage not tracked

**Debug Steps**:
1. Check if credentials are set in `.env`
2. Verify service principal still exists in Azure AD
3. Check if secret has expired (90-day limit)
4. Test authentication manually:
   ```python
   from azure.identity import ClientSecretCredential
   cred = ClientSecretCredential(tenant_id, client_id, client_secret)
   token = cred.get_token("https://purview.azure.com/.default")
   print(token)  # Should not error
   ```

**Solutions**:
- Rotate secret if expired
- Recreate service principal if deleted
- Verify correct tenant ID (should be Metakaal, not BankX)

---

#### Issue 2: Lineage Not Appearing in Purview
**Symptoms**: No errors but lineage not visible in Purview portal

**Debug Steps**:
1. Check if Purview catalog has been indexed (may take 5-10 minutes)
2. Verify correct Purview account name in settings
3. Check if entity types are registered (may need custom types)
4. Review Application Insights logs for Purview API errors

**Solutions**:
- Wait for indexing
- Register custom entity types in Purview
- Check Purview role assignments (need Data Curator)

---

#### Issue 3: One Agent Works, Others Don't
**Symptoms**: AccountAgent tracks lineage, but TransactionAgent doesn't

**Debug Steps**:
1. Compare environment variables for both agents
2. Check if TransactionAgent's SP has correct permissions
3. Review factory method for TransactionAgent
4. Test TransactionAgent's Purview service independently

**Solutions**:
- Verify all 6 agents have credentials configured
- Check factory returns correct service for each agent
- Ensure dependency injection wires factory correctly

---

## ⚖️ Comparison with Option A

### Option A: Single Service Principal + Azure AI Foundry Agent IDs

**Architecture**:
- 1 service principal for entire BankX service
- Agent identity tracked via `agent_id` in Purview metadata
- Simpler configuration (4 variables vs 16)

**Pros**:
- ✅ Much simpler to implement (1-2 days vs 5-7 days)
- ✅ Lower operational overhead (1 secret vs 6)
- ✅ Easier debugging (1 authentication point)
- ✅ Still provides agent-level audit trail (via agent_id metadata)
- ✅ Sufficient for most compliance requirements

**Cons**:
- ❌ All agents share same authentication
- ❌ Cannot revoke specific agent's Purview access without affecting others
- ❌ Less granular RBAC (cannot restrict agent to specific data)

---

### Option B: Per-Agent Service Principals

**Architecture**:
- 6 service principals, one per agent
- Each agent authenticates independently to Purview
- Agent identity tracked via both SP and agent_id

**Pros**:
- ✅ Maximum audit granularity (know exactly which SP made calls)
- ✅ Fine-grained RBAC (restrict agents to specific Purview collections)
- ✅ Can revoke individual agent's access without affecting others
- ✅ Meets strictest compliance requirements

**Cons**:
- ❌ 6× operational complexity
- ❌ 6× more secrets to manage
- ❌ 6× more potential points of failure
- ❌ Longer implementation time
- ❌ More difficult debugging (which SP failed?)

---

### When to Choose Option B

**Choose Option B if**:
- ✅ Compliance requires separate authentication per agent
- ✅ Need to restrict specific agents to specific data collections
- ✅ Audit trail must show separate service principals
- ✅ Budget allows for additional operational overhead
- ✅ Team has automation for secret rotation

**Choose Option A if**:
- ✅ Standard compliance requirements (agent_id tracking sufficient)
- ✅ Want simpler implementation and maintenance
- ✅ Limited DevOps automation capability
- ✅ Can track agent identity through metadata (agent_id)
- ✅ All agents have same data access permissions anyway

---

## ✅ Decision Checklist

### Questions to Ask Before Choosing Option B

1. **Compliance Requirements**
   - [ ] Does your compliance framework require separate authentication per agent?
   - [ ] Is tracking agent_id in metadata sufficient, or do you need separate SPs?
   - [ ] Do auditors require seeing 6 different service principals in logs?

2. **RBAC Requirements**
   - [ ] Do different agents need access to different Purview collections?
   - [ ] Should AccountAgent be restricted from payment-related data?
   - [ ] Is service-level RBAC (all agents share permissions) acceptable?

3. **Operational Readiness**
   - [ ] Do you have automation for secret rotation?
   - [ ] Can your team handle 6× the secrets?
   - [ ] Is debugging authentication issues for 6 SPs manageable?

4. **Implementation Timeline**
   - [ ] Can you allocate 5-7 days for implementation?
   - [ ] Is there budget for additional Azure Key Vault usage?
   - [ ] Can testing cover all 6 agents independently?

5. **Long-term Maintenance**
   - [ ] Who will monitor secret expiration for 6 SPs?
   - [ ] Is there a plan for quarterly secret rotation?
   - [ ] Can alerts be set up for each agent's authentication status?

---

## 🎯 Recommendation

### Start with Option A, Migrate to Option B if Needed

**Rationale**:
- Option A satisfies 95% of compliance requirements
- Azure AI Foundry agent IDs provide sufficient audit trail
- Can always migrate to Option B later if compliance requires it
- Lower risk, faster time to value

**Migration Path** (A → B):
1. Implement Option A (1-2 days)
2. Deploy to production
3. Collect feedback from compliance team
4. If separate SPs required:
   - Create 6 service principals
   - Add new configuration variables
   - Update agents to use factory pattern
   - Deploy incrementally (1 agent at a time)

---

## 📚 Additional Resources

### Azure Documentation
- [Microsoft Purview Data Catalog](https://learn.microsoft.com/en-us/azure/purview/)
- [Service Principal Best Practices](https://learn.microsoft.com/en-us/azure/active-directory/develop/howto-create-service-principal-portal)
- [Azure Key Vault Secret Management](https://learn.microsoft.com/en-us/azure/key-vault/secrets/)

### Azure Purview SDK
- [Python SDK Documentation](https://learn.microsoft.com/en-us/python/api/overview/azure/purview-catalog-readme)
- [Lineage Tracking Guide](https://learn.microsoft.com/en-us/azure/purview/tutorial-lineage)

### Security
- [Secret Rotation Automation](https://learn.microsoft.com/en-us/azure/key-vault/secrets/tutorial-rotation)
- [Managed Identity for Azure Resources](https://learn.microsoft.com/en-us/azure/active-directory/managed-identities-azure-resources/overview)

---

## 📞 Support & Questions

For questions about this implementation approach:
1. Review this document thoroughly
2. Check Azure Purview documentation
3. Test in development environment first
4. Consult with compliance team on requirements

**Key Takeaway**: Option B provides maximum granularity but comes with significant operational overhead. Only choose if compliance explicitly requires separate authentication per agent. Otherwise, Option A with Azure AI Foundry agent IDs is strongly recommended.

---

**Document Version**: 1.0  
**Last Updated**: November 17, 2025  
**Status**: Theoretical Implementation Guide (No Code Written Yet)
