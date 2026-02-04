# Microsoft Purview Integration for BankX Multi-Agent System

**Document Version**: 1.0  
**Last Updated**: November 17, 2025  
**Status**: Architecture & Vision Document  

---

## 📋 Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current BankX Architecture](#current-bankx-architecture)
3. [Why Purview? Core Benefits](#why-purview-core-benefits)
4. [How Purview Integrates with Your System](#how-purview-integrates-with-your-system)
5. [Use Cases & Scenarios](#use-cases--scenarios)
6. [Integration Points](#integration-points)
7. [Service Principal Architecture](#service-principal-architecture)
8. [Data Sources to Track](#data-sources-to-track)
9. [Lineage Tracking Examples](#lineage-tracking-examples)
10. [Clarifying Questions (Decision Required)](#clarifying-questions-decision-required)
11. [Next Steps](#next-steps)

---

## 🎯 Executive Summary

Microsoft Purview will provide **end-to-end data lineage tracking** and **regulatory compliance** capabilities for the BankX multi-agent banking system. With **7 service principals already created** (one per agent), Purview will enable:

- **Visual data lineage maps** showing data flow from source → agent → customer
- **Automated compliance tracking** (GDPR, PCI-DSS, Thai Banking regulations)
- **Agent governance & accountability** with full audit trails
- **Cross-system data discovery** as you scale to Cosmos DB and Azure SQL
- **Root cause analysis** for debugging agent behavior and data issues

**Current Status**: Service principals created, Purview account not yet deployed. This document outlines the vision, benefits, and integration strategy.

---

## 🏗️ Current BankX Architecture

### **System Overview**

BankX is a production-ready multi-agent banking assistant built on Azure AI Foundry with 7 specialized agents:

| Agent | Agent ID | Purpose | MCP Tools |
|-------|----------|---------|-----------|
| **SupervisorAgent** | `asst_n2vjRRiUPZAnewYc73GNvwFA` | Orchestration & routing | None (routes only) |
| **AccountAgent** | `asst_keTclryY22YcSXceBXzXeGmU` | Balance, cards, limits | Account, Limits |
| **TransactionAgent** | `asst_PQswtc01Lzubjc3yLATPQm8U` | Transaction history | Transaction |
| **PaymentAgent** | `asst_JLallrPGtBWrWJDCpny0GqzH` | Money transfers | Payment, Limits |
| **ProdInfoFAQAgent** | `asst_XoEA7BkjnXaFpElLuNWD81E1` | Product information | ProdInfo FAQ |
| **AIMoneyCoachAgent** | `asst_WJ9JomBttAWTu7JMwmrFRdZb` | Financial advice | AI Money Coach |
| **EscalationCommsAgent** | `asst_OZGs7bJTO2zK1Yly2xtVLisL` | Support tickets | Escalation Comms |

### **Current Data Flow**

```
User Request
    ↓
SupervisorAgent (Azure AI Foundry)
    ├─ Routes to appropriate agent
    ↓
Domain Agent (AccountAgent/TransactionAgent/PaymentAgent/etc.)
    ├─ Authenticates with Azure AD
    ├─ Calls MCP Tool (Model Context Protocol microservice)
    ↓
MCP Server (HTTP microservice)
    ├─ Validates request
    ├─ Accesses data source (JSON files, Cosmos DB)
    ↓
Data Source
    ├─ accounts.json (customer accounts)
    ├─ transactions.json (transaction history)
    ├─ beneficiaries.json (payment beneficiaries)
    ├─ cosmos_support_tickets (Cosmos DB for tickets)
    ↓
Response flows back through same path
    ↓
Observability: Logged to NDJSON files (banking_telemetry)
```

### **Current Observability System**

**Location**: `app/copilot/app/observability/banking_telemetry.py`

**Tracks**:
- ✅ **MCP Audit Logs**: Which tool was called, by which customer, with what parameters
- ✅ **Agent Decisions**: Which agent was invoked, routing decisions by SupervisorAgent
- ✅ **RAG Evaluations**: Retrieval-Augmented Generation quality metrics
- ✅ **User Messages**: Conversation history and context

**Storage**: NDJSON files in `observability/` directory
- `mcp_audit_2025-11-17.ndjson`
- `agent_decisions_2025-11-17.ndjson`
- `rag_evaluations_2025-11-17.ndjson`

**Dashboard**: FastAPI endpoints expose this data:
- `/api/dashboard/stats` - Summary statistics
- `/api/dashboard/mcp-audit` - MCP tool call logs
- `/api/dashboard/agent-decisions` - Agent routing logs

### **What's Missing (The Gap Purview Fills)**

Your current observability system captures **WHAT happened** and **WHEN**, but it **DOESN'T show**:

| Missing Capability | Impact |
|--------------------|--------|
| **Data Lineage** | Can't trace where data originated or where it flows downstream |
| **Visual Maps** | No graphical representation of data flow through agents |
| **Data Classification** | No automated tagging of PII, financial data, or sensitive fields |
| **Cross-System Discovery** | When you add Cosmos DB or Azure SQL, no unified catalog |
| **Compliance Dashboard** | Manual effort to prove GDPR/PCI-DSS compliance |
| **Impact Analysis** | If `accounts.json` changes, can't see which agents are affected |
| **Field-Level Tracking** | Can't answer "which agent accessed customer_email field?" |

---

## 🔍 Why Purview? Core Benefits

### **1. END-TO-END DATA LINEAGE TRACKING**

**The Problem**:
Your current audit logs capture **WHAT happened** (which tool was called, which customer), but they **DON'T show**:
- Where did this data come from originally?
- Which downstream systems used this data?
- If `accounts.json` is updated, which agents/customers are affected?
- What's the full journey of customer data through your system?

**Purview Solution**:

Visual lineage map in Purview UI:

```
accounts.json (Data Source)
    ↓ [read operation]
Account MCP Server (HTTP://localhost:8070/mcp)
    ↓ [API call: Account.getAccountDetails]
AccountAgent (asst_keTclryY22Yc...)
    ├─ Authenticated by: BankX-AccountAgent-SP
    ├─ Customer: customer_001 (somchai@bankx.com)
    ├─ Action: retrieve_account_balance
    ↓ [response]
Customer Request: "What's my balance?"
    ↓ [response delivered]
Response: "99,650.00 THB"
    ↓ [logged]
observability/mcp_audit_2025-11-17.ndjson
```

**You Can Click on ANY Node** and see:
- **Upstream**: Where did this data originate? (`accounts.json` → loaded from file system)
- **Downstream**: Who consumed this data? (AccountAgent → Customer Request)
- **Transformations**: What happened to the data? (Raw JSON → Formatted balance response)
- **Metadata**: When, who, compliance tags, sensitivity level

---

### **2. REGULATORY COMPLIANCE (Thai Banking + GDPR + PCI-DSS)**

**Your Current Gap**:
Your `AuditedMCPTool` logs WHO accessed WHAT and WHEN, but:
- ❌ No proof that sensitive data (PII, financial data) stayed within authorized boundaries
- ❌ No automated way to prove "data didn't leave the system"
- ❌ Auditors ask: "Show me all systems that touched customer Somchai's transaction data in October 2025" → you'd need to manually grep NDJSON files across multiple days
- ❌ No automatic data classification (PII, financial, sensitive)

**Purview Solution**:

#### **A. Automatic Data Classification**

Purview scans your data sources and automatically tags fields:

| Data Field | Classification Tags | Justification |
|------------|-------------------|---------------|
| `customer.email` | PII, GDPR_PERSONAL_DATA | Email is personally identifiable |
| `customer.full_name` | PII, GDPR_PERSONAL_DATA | Name is personal data |
| `account.balance` | PCI_DSS, FINANCIAL_DATA | Financial information |
| `transaction.amount` | HIGH_VALUE_TRANSACTION | If > 50,000 THB |
| `transaction.merchant` | BUSINESS_DATA | Non-sensitive |
| `payment.beneficiary_account` | PCI_DSS, FINANCIAL_DATA | Bank account number |

#### **B. Compliance Dashboard**

Single pane of glass showing:

**Question**: "Which agents accessed PII data this month?"
```
AccountAgent: 4,500 calls (expected - retrieves customer info)
PaymentAgent: 1,200 calls (expected - validates beneficiaries)
TransactionAgent: 3,800 calls (expected - shows transaction history)
ProdInfoFAQAgent: 0 calls (✅ GOOD - shouldn't access PII)
AIMoneyCoachAgent: 0 calls (✅ GOOD - shouldn't access PII)
```

**Question**: "Did any agent access data outside their scope?"
```
PaymentAgent:
  ✅ Called Limits API 200 times (expected)
  ✅ Called Account API 180 times (expected - validate accounts)
  ✅ Never called ProdInfo API (good!)
  ❌ Called Transaction API 5 times (UNEXPECTED - investigate!)
```

**Question**: "Is sensitive data encrypted?"
```
✅ Service principal secrets stored in Azure Key Vault (kv-bankx-9843)
✅ MCP communication over HTTPS
✅ Cosmos DB connection strings encrypted
⚠️ accounts.json stored as plain text (recommendation: move to encrypted storage)
```

#### **C. Audit Report Generation**

Purview can generate compliance reports for auditors:

```
GDPR Compliance Report - November 2025

Data Subject: Somchai Rattanakorn (customer_001)
Personal Data Accessed:
  - customer.email: 45 times (AccountAgent, PaymentAgent)
  - customer.full_name: 45 times (AccountAgent, PaymentAgent)
  - account.balance: 12 times (AccountAgent)
  - transaction history: 8 times (TransactionAgent)

Access Patterns:
  - All access authenticated via service principals
  - No unauthorized access detected
  - Data retention: 90 days (observability logs)
  - Right to erasure: Supported (delete customer data script)
  
Compliance Status: ✅ PASSED
```

---

### **3. AGENT GOVERNANCE & ACCOUNTABILITY**

**Your Vision Alignment**:
You mentioned wanting **"agent governance"** and **"agent accountability"** - Purview provides this through:

#### **A. Agent Identity in Lineage**

Every action in Purview includes full agent context:

```json
{
  "action": "Transfer 10,000 THB from CHK-001 to CHK-005",
  "authentication": {
    "service_principal": "BankX-PaymentAgent-SP",
    "client_id": "19c0d01f-228b-45e0-b337-291679acb75c",
    "tenant_id": "c1e8c736-fd22-4d7b-a7a2-12c6f36ac388"
  },
  "agent": {
    "agent_id": "asst_JLallrPGtBWrWJDCpny0GqzH",
    "agent_name": "PaymentAgent",
    "agent_type": "Azure AI Foundry Assistant"
  },
  "customer": {
    "customer_id": "customer_001",
    "customer_email": "somchai@bankx.com"
  },
  "mcp_tools_called": [
    "Payments.validateTransfer",
    "Limits.checkLimits",
    "Payments.submitPayment"
  ],
  "data_sources_accessed": [
    "accounts.json (source account CHK-001)",
    "beneficiaries.json (destination CHK-005)",
    "limits.json (daily limit check)"
  ],
  "timestamp": "2025-11-17T14:32:45Z",
  "status": "SUCCESS",
  "compliance_tags": ["PCI_DSS", "HIGH_VALUE_TRANSACTION"]
}
```

#### **B. Agent Audit Trail**

**Scenario**: Unauthorized transfer detected!

**Investigation with Purview**:

1. **Search**: "Transfer 10,000 THB customer_001 2025-11-17"
2. **Purview Shows**:
   - ✅ Service Principal: BankX-PaymentAgent-SP (proves authentication)
   - ✅ Agent ID: asst_JLallrPGtBWrWJDCpny0GqzH (proves which AI agent)
   - ✅ Customer: customer_001 (proves user context)
   - ✅ MCP Tools: Payments.validateTransfer (SUCCESS), Limits.checkLimits (SUCCESS), Payments.submitPayment (SUCCESS)
   - ✅ Data Sources: accounts.json, beneficiaries.json
   - ✅ Approval: User confirmed transfer in conversation
   - ✅ Idempotency: request_id=pay_1234567890 (no duplicate)

3. **Conclusion**: Transfer was legitimate, fully auditable, compliant

#### **C. Agent Performance Analytics**

Purview tracks agent efficiency:

| Agent | Avg Response Time | Data Sources Hit | Most Used Tool | Error Rate |
|-------|------------------|------------------|----------------|------------|
| AccountAgent | 1.2s | accounts.json, limits.json | Account.getAccountDetails | 0.5% |
| TransactionAgent | 2.3s | transactions.json | Reporting.searchTransactions | 1.2% |
| PaymentAgent | 3.1s | accounts.json, beneficiaries.json | Payments.submitPayment | 2.1% |

**Insights**:
- PaymentAgent is slowest (complex validation logic)
- TransactionAgent has highest error rate (investigate date parsing)
- AccountAgent most efficient (simple lookups)

---

### **4. CROSS-SYSTEM DATA DISCOVERY**

**Your Future Scaling**:

You mentioned:
- ✅ Currently using JSON files (`accounts.json`, `transactions.json`, `beneficiaries.json`)
- ✅ Already using Cosmos DB for support tickets (`cosmos_support_tickets`)
- 🔜 Potential migration to Azure SQL or Cosmos DB for all data

**Purview Solution**:

When you add new data sources, Purview automatically:
1. **Scans** them (Cosmos DB, Azure SQL, Blob Storage, Data Lake)
2. **Discovers** schema (columns, types, relationships)
3. **Maps** relationships (foreign keys, dependencies)
4. **Shows** in unified catalog

#### **Unified Data Catalog**

**Example Search**: "customer_email"

```
Purview Search Results:

1. accounts.json
   Path: d:/Metakaal/BankX/data/accounts.json
   Field: customers[].customer_email
   Type: string
   Classification: PII, GDPR_PERSONAL_DATA
   Used by: AccountAgent, PaymentAgent
   Last accessed: 2025-11-17T15:30:00Z

2. transactions.json
   Path: d:/Metakaal/BankX/data/transactions.json
   Field: transactions[].customer_id
   Type: string (foreign key → customers.customer_id)
   Classification: REFERENCE_DATA
   Used by: TransactionAgent
   Last accessed: 2025-11-17T15:28:00Z

3. cosmos_support_tickets (Cosmos DB)
   Database: bankx
   Container: support_tickets
   Field: tickets[].customer_email
   Type: string
   Classification: PII, GDPR_PERSONAL_DATA
   Used by: EscalationCommsAgent
   Last accessed: 2025-11-17T14:55:00Z

4. observability/mcp_audit_*.ndjson
   Path: d:/Metakaal/BankX/observability/
   Field: mcp_audit[].customer_id
   Type: string (reference)
   Classification: AUDIT_LOG
   Used by: Dashboard API
   Last accessed: 2025-11-17T15:32:00Z

Lineage: All 4 sources trace back to BankX CRM System (upstream source)
```

#### **Relationship Mapping**

Purview automatically discovers relationships:

```
customers (accounts.json)
    ├─ customer_id (primary key)
    ├─ customer_email (unique)
    └─ customer_full_name
    
    ↓ [1:N relationship]
    
transactions (transactions.json)
    ├─ transaction_id (primary key)
    ├─ customer_id (foreign key → customers.customer_id)
    └─ merchant_name
    
    ↓ [referenced by]
    
mcp_audit (observability/*.ndjson)
    ├─ customer_id (reference → customers.customer_id)
    └─ tool_name
```

**Value**: You can see the full data model without manually documenting it!

---

### **5. DEBUGGING & ROOT CAUSE ANALYSIS**

**Real Scenario**:

User complains: "I transferred 5,000 THB yesterday to my wife's account, but my balance shows 10,000 THB was deducted!"

#### **Without Purview** (Manual Investigation):

1. Grep through NDJSON files for `customer_002`
2. Find MCP audit logs for PaymentAgent
3. Check transaction history manually in `transactions.json`
4. Compare `accounts.json` balance before/after
5. Manually trace through logs to find discrepancy
6. Guess which step failed or had wrong data

**Time**: 30-60 minutes of manual investigation

#### **With Purview** (Visual Root Cause Analysis):

1. Search Purview: `"customer_002 payment 2025-11-16"`
2. Purview shows visual lineage:

```
User Request (2025-11-16 10:23:45)
    ↓
SupervisorAgent → routes to PaymentAgent
    ↓
PaymentAgent (asst_JLallrPGtBWrWJDCpny0GqzH)
    ├─ Authenticates with BankX-PaymentAgent-SP
    ↓
Payments.validateTransfer
    ├─ Input: {amount: 5000, source: CHK-002, destination: CHK-008}
    ├─ Result: SUCCESS
    ↓
Limits.checkLimits
    ├─ Input: {customer_id: customer_002, amount: 5000}
    ├─ Daily limit: 200,000 THB
    ├─ Remaining: 195,000 THB
    ├─ Result: SUCCESS
    ↓
Payments.submitPayment
    ├─ Input: {amount: 5000, source: CHK-002, destination: CHK-008}
    ├─ Result: SUCCESS
    ├─ ⚠️ WARNING: Double charge detected!
    ├─ Idempotency check: request_id=pay_987654321
    ├─ FOUND: Same request_id submitted twice!
    ↓
accounts.json (CHK-002)
    ├─ Balance before: 100,000 THB
    ├─ Deduction 1: -5,000 THB (10:23:45)
    ├─ Deduction 2: -5,000 THB (10:23:47) ⚠️ DUPLICATE!
    ├─ Balance after: 90,000 THB (should be 95,000 THB)
    
ROOT CAUSE: Idempotency check failed - payment submitted twice
RECOMMENDATION: Fix idempotency validation in Payments.submitPayment
```

**Time**: 2-3 minutes to identify root cause

**Value**: Visual lineage immediately shows the duplicate submission and wrong balance calculation.

---

## 🔧 How Purview Integrates with Your System

### **Integration Architecture**

Purview sits **alongside** your existing observability system:

```
User Request
    ↓
SupervisorAgent
    ↓
Domain Agent (e.g., AccountAgent)
    ├─ Creates MCP connection (existing)
    ├─ Creates Purview service (NEW)
    ↓
MCP Tool Call (e.g., Account.getAccountDetails)
    ├─ AuditedMCPTool.call_tool() (existing)
    │   ├─ Log to NDJSON (banking_telemetry) ← KEEP THIS
    │   └─ Log to Purview (purview_service) ← ADD THIS
    ↓
Data Source (accounts.json)
    ↓
Response
    ↓
Customer
```

**Key Points**:
- ✅ **Non-invasive**: No changes to agent logic or MCP servers
- ✅ **Complementary**: NDJSON logging continues (local debugging)
- ✅ **Asynchronous**: Purview calls don't block agent responses (optional)
- ✅ **Graceful degradation**: If Purview is down, agents continue working

---

## 📍 Integration Points

### **Point 1: Agent Initialization**

**File**: `app/copilot/app/agents/foundry/account_agent_foundry.py`

**Current Code**:
```python
async def build_af_agent(self, thread_id, customer_id):
    # Create MCP tools with audit logging
    account_mcp_server = AuditedMCPTool(
        name="Account MCP server client",
        url=self.account_mcp_server_url,
        customer_id=customer_id,
        thread_id=thread_id,
        mcp_server_name="account"
    )
```

**With Purview** (Future):
```python
async def build_af_agent(self, thread_id, customer_id):
    # 1. Existing: Create MCP tools with audit logging
    account_mcp_server = AuditedMCPTool(...)
    
    # 2. NEW: Create Purview service for this agent
    from app.purview.purview_service_factory import PurviewServiceFactory
    purview_service = PurviewServiceFactory.create_for_account_agent(
        agent_id="asst_keTclryY22YcSXceBXzXeGmU",
        customer_id=customer_id,
        thread_id=thread_id
    )
    
    # 3. Track agent initialization in Purview
    await purview_service.track_agent_action(
        action="agent_initialized",
        metadata={"thread_id": thread_id, "customer_id": customer_id}
    )
```

---

### **Point 2: MCP Tool Calls**

**File**: `app/copilot/app/tools/audited_mcp_tool.py`

**Current Code**:
```python
async def call_tool(self, tool_name: str, **arguments):
    start_time = time.time()
    
    # Call the actual MCP tool
    result = await super().call_tool(tool_name, **arguments)
    
    duration = time.time() - start_time
    
    # Log to NDJSON (existing)
    self.telemetry.log_mcp_audit(
        customer_id=self.customer_id,
        thread_id=self.thread_id,
        tool_name=tool_name,
        arguments=arguments,
        result=result,
        duration=duration,
        mcp_server=self.mcp_server_name
    )
    
    return result
```

**With Purview** (Future):
```python
async def call_tool(self, tool_name: str, **arguments):
    start_time = time.time()
    
    # Call the actual MCP tool
    result = await super().call_tool(tool_name, **arguments)
    
    duration = time.time() - start_time
    
    # 1. Existing: Log to NDJSON
    self.telemetry.log_mcp_audit(...)
    
    # 2. NEW: Also log to Purview
    if self.purview_service:  # Optional - graceful degradation
        await self.purview_service.track_mcp_tool_call(
            tool_name=tool_name,
            arguments=arguments,
            result=result,
            duration=duration,
            data_sources=self._extract_data_sources(tool_name),
            compliance_tags=self._extract_compliance_tags(arguments, result)
        )
    
    return result
```

---

### **Point 3: Data Source Registration**

**When**: One-time setup after creating Purview account

**How**: Azure CLI commands to register data sources

```bash
# Register accounts.json
az purview asset create \
  --account-name bankx-purview \
  --asset-type DataSet \
  --name accounts.json \
  --qualified-name "file://d:/Metakaal/BankX/data/accounts.json" \
  --properties '{
    "description": "Customer account master data",
    "owner": "BankX Data Team",
    "classification": ["PII", "PCI_DSS", "GDPR_PERSONAL_DATA"],
    "retention": "7 years (regulatory requirement)"
  }'

# Register transactions.json
az purview asset create \
  --account-name bankx-purview \
  --asset-type DataSet \
  --name transactions.json \
  --qualified-name "file://d:/Metakaal/BankX/data/transactions.json" \
  --properties '{
    "description": "Transaction history for all customers",
    "owner": "BankX Data Team",
    "classification": ["PCI_DSS", "FINANCIAL_DATA"],
    "retention": "7 years (regulatory requirement)"
  }'

# Register Cosmos DB (support tickets)
az purview scan create \
  --account-name bankx-purview \
  --data-source-name cosmos-support-tickets \
  --scan-ruleset-name Cosmos \
  --properties '{
    "endpoint": "https://bankx-cosmos.documents.azure.com:443/",
    "database": "bankx",
    "container": "support_tickets"
  }'
```

---

## 🎯 Use Cases & Scenarios

### **Use Case 1: Customer Data Access Audit**

**Scenario**: Auditor asks, "Show me all systems that accessed customer Somchai's data in October 2025"

**Without Purview**:
- Manually grep NDJSON files for `customer_001` across 31 days
- Parse JSON logs to extract tool calls
- Manually list agents that made those calls
- Time: 2-4 hours

**With Purview**:
1. Search: `"customer_001" date:2025-10-01..2025-10-31`
2. Purview generates report:
   - AccountAgent: 45 calls (balance checks, account details)
   - TransactionAgent: 23 calls (transaction history queries)
   - PaymentAgent: 12 calls (payment validations)
   - Total data accessed: 80 records (accounts, transactions, beneficiaries)
3. Export to CSV for auditor
4. Time: 5 minutes

---

### **Use Case 2: Compliance Verification (GDPR Article 15)**

**Scenario**: Customer Somchai requests "Right to Access" - show all personal data you have about me

**Without Purview**:
- Manually search `accounts.json` for customer_001
- Manually search `transactions.json` for customer_001
- Manually search Cosmos DB for customer_001
- Manually search observability logs
- Compile into report
- Time: 1-2 hours

**With Purview**:
1. Search: `"customer_001" classification:PII`
2. Purview shows:
   - accounts.json: email, full_name, phone, address
   - transactions.json: transaction history (linked by customer_id)
   - cosmos_support_tickets: support ticket emails
   - observability logs: audit trail (metadata only, no PII)
3. Generate GDPR-compliant report
4. Time: 10 minutes

---

### **Use Case 3: Data Impact Analysis**

**Scenario**: You need to migrate `accounts.json` from JSON to Azure SQL. What will break?

**Without Purview**:
- Manually search codebase for references to `accounts.json`
- Test each agent manually
- Hope you didn't miss anything
- Time: 4-8 hours + risk of breaking production

**With Purview**:
1. Click on `accounts.json` in Purview catalog
2. View "Downstream Dependencies":
   - AccountAgent (2 MCP tools: Account.getAccountDetails, Account.getCustomerAccounts)
   - PaymentAgent (1 MCP tool: Payments.validateTransfer - checks source account)
   - TransactionAgent (0 direct dependencies)
3. View "Impact Analysis":
   - 3 agents affected
   - 3 MCP tools need schema updates
   - 5,400 monthly calls to this data source
   - Estimated migration effort: 2-3 hours (update MCP server schemas)
4. Time: 5 minutes to understand full impact

---

### **Use Case 4: Security Incident Investigation**

**Scenario**: Security alert - "Unusual data access pattern detected for customer_005"

**Without Purview**:
- Grep logs for customer_005
- Manually trace through agent calls
- Check if access was legitimate
- Time: 30-60 minutes

**With Purview**:
1. Search: `"customer_005" date:today`
2. Purview shows timeline:
   ```
   09:15:00 - AccountAgent - Account.getAccountDetails (NORMAL)
   09:15:30 - TransactionAgent - Reporting.searchTransactions (NORMAL)
   14:32:00 - ProdInfoFAQAgent - Account.getAccountDetails (⚠️ ANOMALY!)
   ```
3. Click on anomaly:
   - ProdInfoFAQAgent should NOT access account data
   - Service principal: BankX-ProdInfoAgent-SP
   - Thread ID: thread_xyz123
   - Customer request: "What's my current account balance?" (routed incorrectly)
4. Root cause: SupervisorAgent routing bug - sent account query to ProdInfoFAQAgent instead of AccountAgent
5. Time: 5 minutes to identify root cause

---

### **Use Case 5: Performance Optimization**

**Scenario**: Users complain that TransactionAgent is slow

**Without Purview**:
- Analyze NDJSON logs for duration metrics
- Manually correlate tool calls with performance
- Guess which data source is slow
- Time: 1-2 hours

**With Purview**:
1. View TransactionAgent lineage
2. Sort by duration (slowest first)
3. Purview shows:
   ```
   Reporting.searchTransactions → transactions.json
     Average duration: 2.3s
     95th percentile: 4.5s
     Slowest query: date_range=90_days, customer=customer_003 (8.2s)
   
   Root cause: transactions.json is 50MB (70,000 transactions)
   No indexing on customer_id or date fields
   
   Recommendation: Migrate to Azure SQL with indexed columns
   Expected improvement: 2.3s → 0.3s (8x faster)
   ```
4. Time: 10 minutes to identify bottleneck

---

## 🔐 Service Principal Architecture

### **7 Service Principals Created**

| Service Principal | Client ID | Agent | Purpose |
|-------------------|-----------|-------|---------|
| **BankX-AccountAgent-SP** | `f7219061-e3db-4dfb-a8de-2b5fa4b98ccf` | AccountAgent | Authenticate Purview API calls for account operations |
| **BankX-TransactionAgent-SP** | `abdde3bd-954f-4626-be85-c995faeec314` | TransactionAgent | Authenticate Purview API calls for transaction operations |
| **BankX-PaymentAgent-SP** | `19c0d01f-228b-45e0-b337-291679acb75c` | PaymentAgent | Authenticate Purview API calls for payment operations |
| **BankX-ProdInfoAgent-SP** | `cd8e9191-1d08-4bd2-9dbe-e23139dcbd90` | ProdInfoFAQAgent | Authenticate Purview API calls for product info operations |
| **BankX-MoneyCoachAgent-SP** | `b81a5e18-1760-4836-8a5e-e4ef2e8f1113` | AIMoneyCoachAgent | Authenticate Purview API calls for financial coaching |
| **BankX-EscalationAgent-SP** | `019b1746-a104-437a-b1ff-a911ba8c356c` | EscalationCommsAgent | Authenticate Purview API calls for support ticket operations |
| **BankX-SupervisorAgent-SP** | `cbb7c307-5c43-4999-ada4-63a934853ec5` | SupervisorAgent | Authenticate Purview API calls for routing operations |

**Tenant**: Metakaal (`c1e8c736-fd22-4d7b-a7a2-12c6f36ac388`)  
**Expiration**: November 17, 2026 (1 year)  
**Status**: ✅ Created, ⏳ Purview roles not yet assigned (waiting for Purview account creation)

### **Authentication Flow**

```
AccountAgent (agent_id: asst_keTclryY22Yc...)
    ↓
Uses Service Principal: BankX-AccountAgent-SP
    ├─ Client ID: f7219061-e3db-4dfb-a8de-2b5fa4b98ccf
    ├─ Client Secret: (stored in Azure Key Vault: kv-bankx-9843)
    ├─ Tenant ID: c1e8c736-fd22-4d7b-a7a2-12c6f36ac388
    ↓
Authenticates to Azure AD
    ↓
Gets OAuth2 Token
    ↓
Calls Purview API with token
    ├─ POST /catalog/api/atlas/v2/lineage
    ├─ Headers: { Authorization: "Bearer <token>" }
    ├─ Body: { entity: {...}, lineage: {...} }
    ↓
Purview verifies token & RBAC role (Purview Data Curator)
    ↓
Logs lineage event
```

### **Why Per-Agent Service Principals?**

**Option A** (Single SP for all agents):
- ❌ Can't differentiate which agent made Purview API call
- ❌ All agents share same credentials (security risk)
- ❌ Can't revoke access for one agent without affecting all

**Option B** (Per-agent SPs) ✅ **SELECTED**:
- ✅ Full audit trail (know exactly which agent accessed Purview)
- ✅ Granular RBAC (can restrict each agent's Purview permissions)
- ✅ Independent credential rotation (rotate AccountAgent SP without affecting PaymentAgent)
- ✅ Compliance-friendly (regulators love fine-grained access control)

---

## 📊 Data Sources to Track

### **Current Data Sources**

| Data Source | Type | Location | Classification | Agents Using |
|-------------|------|----------|----------------|--------------|
| **accounts.json** | JSON File | `d:/Metakaal/BankX/data/` | PII, PCI_DSS, GDPR_PERSONAL_DATA | AccountAgent, PaymentAgent |
| **transactions.json** | JSON File | `d:/Metakaal/BankX/data/` | PCI_DSS, FINANCIAL_DATA | TransactionAgent |
| **beneficiaries.json** | JSON File | `d:/Metakaal/BankX/data/` | PCI_DSS, FINANCIAL_DATA | PaymentAgent |
| **limits.json** | JSON File | `d:/Metakaal/BankX/data/` | BUSINESS_RULE | AccountAgent, PaymentAgent |
| **cosmos_support_tickets** | Cosmos DB | Azure Cosmos DB | PII, SUPPORT_DATA | EscalationCommsAgent |

### **Future Data Sources (Migration Candidates)**

| Data Source | Current | Future | Migration Priority |
|-------------|---------|--------|-------------------|
| accounts.json | JSON File | Azure SQL / Cosmos DB | HIGH (performance + security) |
| transactions.json | JSON File | Azure SQL / Cosmos DB | HIGH (scalability - growing to 100k+ records) |
| beneficiaries.json | JSON File | Azure SQL / Cosmos DB | MEDIUM |
| limits.json | JSON File | Azure App Configuration | LOW (rarely changes) |

**Value**: When you migrate, Purview will automatically discover the new data sources and update lineage!

---

## 📈 Lineage Tracking Examples

### **Example 1: Account Balance Query**

**User Request**: "What's my account balance?"

**Purview Lineage Map**:

```
User (customer_001)
    ↓ [user_message]
SupervisorAgent (asst_n2vjRRiUPZ...)
    ├─ Authenticated by: BankX-SupervisorAgent-SP
    ├─ Intent: Transactions.View → routes to AccountAgent
    ↓ [agent_routing]
AccountAgent (asst_keTclryY22Yc...)
    ├─ Authenticated by: BankX-AccountAgent-SP
    ├─ Thread ID: thread_abc123
    ↓ [mcp_tool_call]
Account MCP Server (HTTP://localhost:8070/mcp)
    ├─ Tool: Account.getAccountDetails
    ├─ Arguments: {customer_id: "customer_001"}
    ↓ [data_access]
accounts.json
    ├─ Record: customers[0] (customer_id: customer_001)
    ├─ Fields: account_id, balance, currency
    ├─ Classification: PII, PCI_DSS
    ↓ [data_response]
Account MCP Server
    ├─ Response: {account_id: "CHK-001", balance: 99650.00, currency: "THB"}
    ├─ Duration: 45ms
    ↓ [agent_response]
AccountAgent
    ├─ Format response: "Your balance is 99,650.00 THB"
    ├─ Duration: 1.2s
    ↓ [user_response]
User (customer_001)
    ├─ Receives: "Your balance is 99,650.00 THB"
    ↓ [audit_log]
observability/mcp_audit_2025-11-17.ndjson
    ├─ Log entry: {customer_id, tool_name, duration, result}
```

**Metadata in Purview**:
- **Timestamp**: 2025-11-17T15:45:32Z
- **Compliance Tags**: PII, PCI_DSS, GDPR_PERSONAL_DATA
- **Duration**: 1.2s (total), 45ms (MCP call)
- **Status**: SUCCESS
- **Data Volume**: 1 record accessed (customer_001)

---

### **Example 2: Money Transfer (Complex Multi-Step)**

**User Request**: "Transfer 10,000 THB to my wife's account (CHK-005)"

**Purview Lineage Map**:

```
User (customer_001)
    ↓
SupervisorAgent
    ├─ Intent: Payment.Transfer → routes to PaymentAgent
    ↓
PaymentAgent (asst_JLallrPGtBWrWJ...)
    ├─ Authenticated by: BankX-PaymentAgent-SP
    ├─ Step 1: Validate transfer
    ↓
Payments.validateTransfer (MCP Tool)
    ├─ Checks: source account exists, destination valid
    ├─ Data sources: accounts.json, beneficiaries.json
    ├─ Result: SUCCESS
    ↓
PaymentAgent
    ├─ Step 2: Check limits
    ↓
Limits.checkLimits (MCP Tool)
    ├─ Checks: daily limit (200,000 THB), per-transaction limit (50,000 THB)
    ├─ Data source: limits.json
    ├─ Result: SUCCESS (within limits)
    ↓
PaymentAgent
    ├─ Step 3: Get user approval
    ↓
User (customer_001)
    ├─ Receives: TRANSFER_APPROVAL card
    ├─ User confirms: "Yes, proceed"
    ↓
PaymentAgent
    ├─ Step 4: Submit payment
    ↓
Payments.submitPayment (MCP Tool)
    ├─ Arguments: {source: CHK-001, destination: CHK-005, amount: 10000}
    ├─ Data sources:
    │   ├─ accounts.json (deduct from CHK-001)
    │   └─ beneficiaries.json (credit to CHK-005)
    ├─ Result: SUCCESS
    ├─ Transaction ID: TXN-2025-111545
    ↓
accounts.json (updated)
    ├─ CHK-001: 99,650.00 → 89,650.00 THB
    ├─ CHK-005: 50,000.00 → 60,000.00 THB
    ↓
transactions.json (new record)
    ├─ Transaction: {id: TXN-2025-111545, amount: 10000, status: completed}
    ↓
PaymentAgent
    ├─ Response: "Transfer successful! 10,000 THB sent to CHK-005"
    ↓
User (customer_001)
    ├─ Receives confirmation
    ↓
observability/mcp_audit_2025-11-17.ndjson
    ├─ 3 log entries (validateTransfer, checkLimits, submitPayment)
```

**Metadata in Purview**:
- **Timestamp**: 2025-11-17T14:32:45Z - 2025-11-17T14:33:12Z (27s total)
- **Compliance Tags**: PCI_DSS, HIGH_VALUE_TRANSACTION, USER_APPROVED
- **MCP Tools Called**: 3 (validateTransfer, checkLimits, submitPayment)
- **Data Sources Accessed**: 3 (accounts.json, beneficiaries.json, limits.json)
- **Data Modified**: 2 records (CHK-001, CHK-005)
- **Status**: SUCCESS
- **Idempotency**: request_id=pay_1234567890 (prevents duplicates)

---

### **Example 3: Product Information Query (RAG-Based)**

**User Request**: "What are the interest rates for savings accounts?"

**Purview Lineage Map**:

```
User
    ↓
SupervisorAgent
    ├─ Intent: Product.Information → routes to ProdInfoFAQAgent
    ↓
ProdInfoFAQAgent (asst_XoEA7BkjnXaF...)
    ├─ Authenticated by: BankX-ProdInfoAgent-SP
    ├─ Uses: Azure AI Foundry native file search
    ↓
Azure AI Foundry Vector Store (vs_jUHv9PsFTmMH...)
    ├─ Search query: "savings account interest rates"
    ├─ Top 5 chunks retrieved from:
    │   ├─ ProductBrochure_SavingsAccounts.pdf (page 3)
    │   ├─ InterestRateSheet_2025.pdf (page 1)
    │   └─ FAQ_Banking_Products.pdf (section 2.3)
    ├─ Relevance scores: 0.92, 0.89, 0.85, 0.78, 0.72
    ↓
ProdInfoFAQAgent
    ├─ Synthesizes response from retrieved chunks
    ├─ Response: "Savings account interest rates: 1.5% for balances under 100k THB, 2.0% for 100k-500k THB, 2.5% for over 500k THB"
    ↓
User
    ├─ Receives answer
    ↓
observability/rag_evaluations_2025-11-17.ndjson
    ├─ RAG quality metrics: {relevance: 0.92, answer_quality: 0.88}
```

**Metadata in Purview**:
- **Timestamp**: 2025-11-17T16:20:15Z
- **Compliance Tags**: PUBLIC_DATA (no PII/PCI)
- **RAG Source**: Azure AI Foundry vector store (vs_jUHv9PsFTmMH...)
- **Documents Retrieved**: 3 PDFs (ProductBrochure, InterestRateSheet, FAQ)
- **Relevance Score**: 0.92 (high confidence)
- **Status**: SUCCESS

---

## ❓ Clarifying Questions (Decision Required)

Before deploying Purview, please answer these questions to tailor the implementation:

### **1. Observability Evolution**

**Current State**: You log to NDJSON files in `observability/` directory

**Question**: Do you want Purview to **REPLACE** NDJSON logging or **COMPLEMENT** it?

- ☐ **Option A - Replace**: All lineage goes to Purview only (removes local files)
  - **Pros**: Single source of truth, less storage, unified dashboard
  - **Cons**: Lose local debugging files, depends on Purview availability

- ☐ **Option B - Complement** (RECOMMENDED): Keep NDJSON for local debugging + send lineage to Purview for compliance
  - **Pros**: Best of both worlds, local debugging + compliance dashboard
  - **Cons**: Slight duplication, more code

**Recommendation**: Option B (complement) - keep both systems for flexibility

---

### **2. Data Source Coverage**

**I See**: 
- ✅ `accounts.json`, `transactions.json`, `beneficiaries.json` (file-based)
- ✅ Cosmos DB (`cosmos_support_tickets`)

**Question**: Which data sources should Purview track?

- ☐ **Option A**: Only JSON files (accounts, transactions, beneficiaries, limits)
- ☐ **Option B**: JSON files + Cosmos DB support_tickets (RECOMMENDED)
- ☐ **Option C**: Everything including future databases (Azure SQL, additional Cosmos containers)

**Recommendation**: Option B initially, expand to Option C as you migrate to cloud databases

---

### **3. Purview Lineage Granularity**

**Question**: How detailed should Purview lineage be?

- ☐ **Option A - Agent Level**: Track at agent level only
  - Example: "AccountAgent accessed accounts.json at 15:45:32"
  - **Pros**: Simple, low overhead
  - **Cons**: Less detail for debugging

- ☐ **Option B - MCP Tool Level** (RECOMMENDED): Track every MCP tool call
  - Example: "AccountAgent called Account.getAccountDetails for customer_001 at 15:45:32"
  - **Pros**: Full audit trail, great for compliance
  - **Cons**: More Purview API calls (but still acceptable)

- ☐ **Option C - Field Level**: Track every field accessed
  - Example: "AccountAgent accessed customer.email and account.balance fields at 15:45:32"
  - **Pros**: Maximum granularity
  - **Cons**: High overhead, probably overkill

**Recommendation**: Option B (MCP tool level) - optimal balance of detail and performance

---

### **4. Real-Time vs. Batch Tracking**

**Question**: When should lineage events be sent to Purview?

- ☐ **Option A - Real-Time**: Every agent call → immediate Purview API call
  - **Pros**: Instant visibility, real-time monitoring
  - **Cons**: Adds 50-100ms latency per agent call

- ☐ **Option B - Asynchronous** (RECOMMENDED): Purview calls in background (non-blocking)
  - **Pros**: No latency impact on agent responses
  - **Cons**: Slight delay (1-2 seconds) before lineage appears in Purview

- ☐ **Option C - Batch**: Buffer lineage events → send every 5 minutes
  - **Pros**: Minimal performance impact
  - **Cons**: Delayed visibility (5-minute lag)

**Recommendation**: Option B (asynchronous) - best balance of performance and real-time visibility

---

### **5. SupervisorAgent Lineage**

**Current**: SupervisorAgent routes but doesn't access data directly

**Question**: Should SupervisorAgent lineage show in Purview?

- ☐ **Option A**: Only routing decisions
  - Example: "SupervisorAgent routed request to AccountAgent at 15:45:30"
  - **Pros**: Shows orchestration flow
  - **Cons**: Adds extra Purview events (but provides context)

- ☐ **Option B**: Full conversation flow (RECOMMENDED)
  - Example: "User → SupervisorAgent → AccountAgent → MCP Tool → Data Source"
  - **Pros**: Complete end-to-end lineage
  - **Cons**: More Purview API calls

- ☐ **Option C**: Nothing (exclude SupervisorAgent)
  - **Pros**: Simplest, least overhead
  - **Cons**: Missing orchestration context

**Recommendation**: Option B (full conversation flow) - provides complete picture for compliance

---

### **6. Cost & Performance Tolerance**

**Purview Costs**:
- Data Catalog: ~$1,000-1,500/month (fixed)
- Lineage API calls: ~$1-2 per 1,000 events
- Example: 100,000 agent calls/month = 100,000 lineage events = $100-200/month

**Performance Impact**:
- Real-time: 50-100ms per agent call
- Asynchronous: 0ms (no user-facing impact)
- Batch: 0ms (no user-facing impact)

**Questions**:
- ☐ Are you okay with 50-100ms latency per agent call? (if real-time tracking)
- ☐ What's your estimated monthly agent call volume?
  - Less than 10,000 calls/month
  - 10,000 - 100,000 calls/month
  - More than 100,000 calls/month
- ☐ Budget: What's acceptable monthly Purview cost?
  - $100-500/month
  - $500-1,500/month
  - $1,500-3,000/month

**Recommendation**: Use asynchronous tracking (no latency) + estimate your call volume to budget accordingly

---

## 🚀 Next Steps

Once you answer the clarifying questions above, here's the deployment roadmap:

### **Phase 1: Purview Account Creation** (Terminal Only)

**Duration**: 15-30 minutes  
**Deliverables**:
- Purview account created in Azure
- Resource group: `rg-multimodaldemo`
- Region: East US
- SKU: Standard

**Commands**:
```bash
# 1. Create Purview account
az purview account create \
  --name bankx-purview \
  --resource-group rg-multimodaldemo \
  --location eastus \
  --sku Standard

# 2. Verify creation
az purview account show \
  --name bankx-purview \
  --resource-group rg-multimodaldemo

# 3. Get Purview endpoint
az purview account show \
  --name bankx-purview \
  --resource-group rg-multimodaldemo \
  --query 'properties.endpoints.catalog' -o tsv
```

---

### **Phase 2: Service Principal Role Assignment** (Terminal Only)

**Duration**: 10-15 minutes  
**Deliverables**:
- All 7 service principals assigned "Purview Data Curator" role
- Verified access with test API calls

**Commands**:
```bash
# Get Purview resource ID
PURVIEW_ID=$(az purview account show \
  --name bankx-purview \
  --resource-group rg-multimodaldemo \
  --query 'id' -o tsv)

# Assign role to AccountAgent SP
az role assignment create \
  --role "Purview Data Curator" \
  --assignee f7219061-e3db-4dfb-a8de-2b5fa4b98ccf \
  --scope $PURVIEW_ID

# Repeat for other 6 SPs...
# (TransactionAgent, PaymentAgent, ProdInfoAgent, MoneyCoachAgent, EscalationAgent, SupervisorAgent)
```

---

### **Phase 3: Data Source Registration** (Terminal Only)

**Duration**: 20-30 minutes  
**Deliverables**:
- All data sources registered in Purview catalog
- Classification tags applied
- Initial scan completed

**Commands**:
```bash
# Register accounts.json
az purview asset create \
  --account-name bankx-purview \
  --asset-type DataSet \
  --name accounts.json \
  --qualified-name "file://d:/Metakaal/BankX/data/accounts.json" \
  --properties '{
    "description": "Customer account master data",
    "classification": ["PII", "PCI_DSS", "GDPR_PERSONAL_DATA"]
  }'

# Register Cosmos DB
az purview scan create \
  --account-name bankx-purview \
  --data-source-name cosmos-support-tickets \
  --scan-ruleset-name Cosmos
```

---

### **Phase 4: Integration Architecture Review** (No Code Yet)

**Duration**: 30-60 minutes  
**Deliverables**:
- Detailed integration plan based on your answers to clarifying questions
- Code structure design (where Purview calls will go)
- Performance & cost estimates
- Testing strategy

**Outcome**: You'll have a complete blueprint before writing any code

---

### **Phase 5: Code Implementation** (Future - After Your Approval)

**Duration**: 4-6 hours  
**Deliverables**:
- `app/purview/agent_purview_service.py` - Agent-specific Purview service
- `app/purview/purview_service_factory.py` - Factory pattern for creating services
- `app/config/settings.py` - Purview configuration
- Updated `AuditedMCPTool` to call Purview
- Updated all 7 agents to use Purview factory

**NOT STARTED YET** - waiting for your answers to clarifying questions

---

## 📚 Reference Documents

- **Service Principal Credentials**: `PURVIEW_SERVICE_PRINCIPALS_CREDENTIALS.md` (DO NOT COMMIT TO GIT)
- **Option B Implementation Guide**: `docs/PURVIEW_OPTION_B_IMPLEMENTATION_GUIDE.md`
- **Tenant Placement Strategy**: `docs/SERVICE_PRINCIPAL_TENANT_PLACEMENT.md`
- **Agent Architecture**: `Agent_Architecture.txt`

---

## 📞 Support & Questions

If you have questions or need clarification on any aspect of this integration:

1. **Architecture Questions**: Refer to this document (PURVIEW_INTEGRATION_VISION.md)
2. **Service Principal Issues**: Check `PURVIEW_SERVICE_PRINCIPALS_CREDENTIALS.md`
3. **Implementation Details**: Review `docs/PURVIEW_OPTION_B_IMPLEMENTATION_GUIDE.md`

---

**Document Status**: ✅ Complete - Ready for Decision  
**Next Action**: User to answer 6 clarifying questions above  
**Then**: Proceed with Phase 1 (Purview account creation via terminal)
