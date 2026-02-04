# Audit MCP Service

Decision Ledger and governance logging service for BankX VB project.

## Overview

The Audit Service provides complete audit trail and decision ledger capabilities for governance, compliance, and teller dashboard operations. It implements US 1.A (Agent Governance) and US 1.T (Teller User Stories).

## Features

- **Decision Ledger Logging**: Record every agent action, decision, and rationale (US 1.A1-1.A3)
- **Agent Interaction Logs**: Simplified view of agent-customer interactions (US 1.T3)
- **Decision Audit Trail**: Governance view with policy evaluations (US 1.T4)
- **Search and Filter**: Flexible querying for teller dashboard (US 1.T5)
- **Conversation History**: Complete decision history per conversation
- **JSON Persistence**: Development storage (upgradable to Cosmos DB for production)

## Architecture

```
Audit Service
│
├── models.py                      # Pydantic models (DecisionLedgerEntry, etc.)
├── audit_persistence_service.py  # JSON storage (future: Cosmos DB)
├── services.py                    # Business logic (AuditService)
├── mcp_tools.py                   # MCP tool definitions
└── main.py                        # FastMCP server entry point
```

## MCP Tools

### 1. `logDecision`

**PRIMARY GOVERNANCE FUNCTION** - Log an agent decision to the Decision Ledger.

**Parameters:**
- `conversationId` (str): Conversation identifier
- `customerId` (str): Customer ID (hashed in production)
- `agentName` (str): Agent name (e.g., "TransactionAgent")
- `action` (str): Action type (e.g., "VIEW_TRANSACTIONS", "TRANSFER")
- `input` (dict): Sanitized input parameters
- `output` (dict): Output summary (structured output schema)
- `rationale` (str): Human-readable decision rationale
- `policyEvaluation` (dict, optional): Policy check results
- `approval` (dict, optional): Approval metadata
- `metadata` (dict, optional): Latency, request_id, etc.

**Returns:**
```json
{
  "ledger_id": "LEDGER-A1B2C3D4E5F67890",
  "status": "logged"
}
```

**Usage (Agents MUST call after every significant action):**

```python
# Example 1: Log transaction view
logDecision(
    conversationId="CONV-123",
    customerId="CUST-001",
    agentName="TransactionAgent",
    action="VIEW_TRANSACTIONS",
    input={
        "account_id": "CHK-001",
        "from_date": "2025-10-20",
        "to_date": "2025-10-26"
    },
    output={
        "type": "TXN_TABLE",
        "total_count": 10,
        "summary": {"total_in": 5000, "total_out": 700}
    },
    rationale="Retrieved transaction history for last week. Natural language date 'last week' normalized to 2025-10-20 to 2025-10-26. Found 10 transactions."
)

# Example 2: Log transfer with policy evaluation
logDecision(
    conversationId="CONV-124",
    customerId="CUST-001",
    agentName="PaymentAgent",
    action="TRANSFER",
    input={
        "from_account": "CHK-001",
        "to_account": "703-384-928",
        "amount": 1000,
        "currency": "THB"
    },
    output={
        "type": "TRANSFER_RESULT",
        "status": "SUCCESS",
        "transaction_id": "TXN-070"
    },
    rationale="Transfer approved by customer. Policy checks passed: sufficient balance (100,950 THB), within per-txn limit (50,000 THB), within daily limit (200,000 THB remaining). Balance updated: 100,950 → 99,950 THB.",
    policyEvaluation={
        "policy_name": "TransferPolicy",
        "passed": True,
        "reason": "All checks passed: balance=OK, per_txn=OK, daily=OK"
    },
    approval={
        "request_id": "REQ-ABC123",
        "approval_actor": "CUST-001",
        "approval_action": "APPROVE",
        "approval_channel": "web_chat",
        "approval_timestamp": "2025-11-06T14:30:00+07:00"
    },
    metadata={
        "latency_ms": 450,
        "request_id": "REQ-ABC123"
    }
)
```

**Use Case:** US 1.A1-1.A3 (Agent Governance)

---

### 2. `getCustomerAuditHistory`

Get complete audit history for a customer.

**Parameters:**
- `customerId` (str): Customer ID
- `limit` (int): Maximum entries (default: 50)

**Returns:**
```json
[
  {
    "ledger_id": "LEDGER-A1B2C3D4E5F67890",
    "conversation_id": "CONV-123",
    "customer_id": "CUST-001",
    "agent_name": "TransactionAgent",
    "action": "VIEW_TRANSACTIONS",
    "timestamp": "2025-11-06T14:25:00+07:00",
    "input": {...},
    "output": {...},
    "rationale": "..."
  }
]
```

**Use Case:** Teller dashboard - complete audit review

---

### 3. `getAgentInteractions`

Get agent interaction logs for teller dashboard.

**Parameters:**
- `customerId` (str): Customer ID
- `limit` (int): Maximum interactions (default: 50)

**Returns:**
```json
[
  {
    "interaction_id": "LEDGER-A1B2C3D4E5F67890",
    "conversation_id": "CONV-123",
    "customer_id": "CUST-001",
    "agent_name": "TransactionAgent",
    "action": "VIEW_TRANSACTIONS",
    "timestamp": "2025-11-06T14:25:00+07:00",
    "input_summary": "{'account_id': 'CHK-001', 'from_date': '2025-10-20'...}",
    "output_summary": "{'type': 'TXN_TABLE', 'total_count': 10...}",
    "success": true,
    "error_message": null
  }
]
```

**Use Case:** US 1.T3 (View Agent Interaction Logs)

---

### 4. `getDecisionAuditTrail`

Get decision audit trail with policy evaluations.

**Parameters:**
- `customerId` (str): Customer ID
- `limit` (int): Maximum decisions (default: 50)

**Returns:**
```json
[
  {
    "ledger_id": "LEDGER-B2C3D4E5F6789012",
    "conversation_id": "CONV-124",
    "customer_id": "CUST-001",
    "agent_name": "PaymentAgent",
    "action": "TRANSFER",
    "timestamp": "2025-11-06T14:30:00+07:00",
    "policy_evaluations": [
      {
        "policy_name": "TransferPolicy",
        "passed": true,
        "reason": "All checks passed"
      }
    ],
    "approval_status": "APPROVE",
    "rationale": "Transfer approved by customer..."
  }
]
```

**Use Case:** US 1.T4 (View Decision Audit Trail)

---

### 5. `searchAuditLogs`

Search and filter audit logs with multiple criteria.

**Parameters:**
- `customerId` (str, optional): Filter by customer
- `agentName` (str, optional): Filter by agent
- `action` (str, optional): Filter by action type
- `fromTimestamp` (str, optional): Start date/time (ISO 8601)
- `toTimestamp` (str, optional): End date/time (ISO 8601)
- `page` (int): Page number (default: 1)
- `pageSize` (int): Results per page (default: 50)

**Returns:**
```json
{
  "total_count": 125,
  "results": [...],
  "page": 1,
  "page_size": 50
}
```

**Example Queries:**
```python
# All transfers
searchAuditLogs(action="TRANSFER")

# All TransactionAgent actions
searchAuditLogs(agentName="TransactionAgent")

# Specific customer in date range
searchAuditLogs(
    customerId="CUST-001",
    fromTimestamp="2025-10-20T00:00:00+07:00",
    toTimestamp="2025-10-26T23:59:59+07:00"
)
```

**Use Case:** US 1.T5 (Search and Filter Records)

---

### 6. `getConversationHistory`

Get all decisions in a conversation.

**Parameters:**
- `conversationId` (str): Conversation ID

**Returns:**
```json
[
  {
    "ledger_id": "LEDGER-A1...",
    "conversation_id": "CONV-123",
    "action": "VIEW_TRANSACTIONS",
    "timestamp": "2025-11-06T14:25:00+07:00",
    ...
  },
  {
    "ledger_id": "LEDGER-B2...",
    "conversation_id": "CONV-123",
    "action": "TRANSFER",
    "timestamp": "2025-11-06T14:30:00+07:00",
    ...
  }
]
```

**Use Case:** Debugging, conversation analysis

---

## Data Flow

### Decision Logging Flow (US 1.A)

```
1. Agent performs action (e.g., view transactions, transfer)
2. Agent calls logDecision MCP tool with:
   - Action details (input, output)
   - Decision rationale
   - Policy evaluations (if applicable)
   - Approval metadata (if applicable)
3. Audit Service generates unique ledger_id
4. Entry saved to decision_ledger.json (or Cosmos DB in production)
5. Returns ledger_id for reference
```

### Teller Dashboard Flow (US 1.T)

```
1. Teller opens customer profile
2. Teller dashboard calls:
   - getCustomerAuditHistory → Complete audit trail
   - getAgentInteractions → Simplified interaction log
   - getDecisionAuditTrail → Governance view
3. Teller can filter/search using searchAuditLogs
4. Teller views conversation details using getConversationHistory
```

## Data Storage

### JSON: `data/decision_ledger.json`

Development storage (array of ledger entries):

```json
[
  {
    "ledger_id": "LEDGER-A1B2C3D4E5F67890",
    "conversation_id": "CONV-123",
    "customer_id": "CUST-001",
    "agent_name": "TransactionAgent",
    "action": "VIEW_TRANSACTIONS",
    "timestamp": "2025-11-06T14:25:00+07:00",
    "input": {
      "account_id": "CHK-001",
      "from_date": "2025-10-20",
      "to_date": "2025-10-26"
    },
    "output": {
      "type": "TXN_TABLE",
      "total_count": 10
    },
    "policy_evaluation": null,
    "approval": null,
    "metadata": {
      "latency_ms": 250
    },
    "rationale": "Retrieved transaction history for last week..."
  }
]
```

### Future: Cosmos DB

For production, migrate to Cosmos DB with:
- Partitioning by `customer_id`
- TTL for data retention policies
- Indexing on `timestamp`, `action`, `agent_name`
- Encryption at rest

## Running the Service

### Development Mode (port 8075)

```bash
export PROFILE=dev
python main.py
```

### Production Mode (port 8080)

```bash
export PROFILE=prod
python main.py
```

## Integration with Other Services

### Called By

- **All Agents**: Must call `logDecision` after every significant action
- **Teller Dashboard**: Calls query tools for audit review

### Integration Points

- **Agents**: Add `logDecision` calls to agent workflows
- **Supervisor**: Log intent classification decisions
- **Transaction Agent**: Log transaction views and aggregations
- **Payment Agent**: Log transfers with policy evaluations and approvals
- **Account Agent**: Log balance checks

## Agent Integration Example

```python
# In TransactionAgent after retrieving transactions
result = searchTransactions(account_id, from_date, to_date)

# Log decision to audit
logDecision(
    conversationId=current_conversation_id,
    customerId=customer_id,
    agentName="TransactionAgent",
    action="VIEW_TRANSACTIONS",
    input={
        "account_id": account_id,
        "from_date": from_date,
        "to_date": to_date,
        "natural_language_date": user_query
    },
    output={
        "type": "TXN_TABLE",
        "total_count": len(result),
        "summary": result.summary
    },
    rationale=f"Retrieved {len(result)} transactions for period {from_date} to {to_date}. Natural language query '{user_query}' normalized using DateNormalizer.",
    metadata={
        "latency_ms": elapsed_ms,
        "tool_used": "searchTransactions"
    }
)

return result  # Return to user
```

## Testing

Test the service:

```bash
# Start the service
PROFILE=dev python main.py

# Test logging a decision
curl -X POST http://localhost:8075/mcp/tools/logDecision \
  -H "Content-Type: application/json" \
  -d '{
    "conversationId": "CONV-TEST-001",
    "customerId": "CUST-001",
    "agentName": "TestAgent",
    "action": "TEST_ACTION",
    "input": {"test": "data"},
    "output": {"result": "success"},
    "rationale": "Testing decision logging"
  }'

# Query audit history
curl -X POST http://localhost:8075/mcp/tools/getCustomerAuditHistory \
  -H "Content-Type: application/json" \
  -d '{"customerId": "CUST-001", "limit": 10}'
```

## Compliance & Governance

### Audit Requirements

- **Complete Audit Trail**: Every agent action logged
- **Rationale Capture**: Human-readable explanation for every decision
- **Policy Evaluation**: Document all policy checks
- **Approval Tracking**: Record user approvals for financial transactions
- **Timestamp Accuracy**: All timestamps in Asia/Bangkok timezone (+07:00)
- **Data Retention**: JSON storage for development, Cosmos DB with TTL for production

### Compliance Use Cases

1. **Regulatory Audits**: Complete trace of all customer interactions
2. **Dispute Resolution**: Conversation history with decision rationale
3. **Policy Compliance**: Track policy evaluations and pass/fail rates
4. **Risk Management**: Identify patterns in approvals/rejections
5. **Performance Monitoring**: Latency and success rate tracking

## Future Enhancements

1. **Cosmos DB Migration**: Replace JSON with Cosmos DB for production
2. **Real-time Analytics**: Dashboard with live metrics
3. **Anomaly Detection**: AI-based detection of unusual patterns
4. **Compliance Reports**: Automated generation of compliance reports
5. **Data Lineage Integration**: Full integration with Azure Purview
6. **Metrics Export**: Integration with Azure Monitor/Application Insights
7. **Alert System**: Notifications for policy violations or errors
8. **Audit Export**: Export audit logs to CSV/PDF for compliance

## Architecture Alignment

**Port 8075** - Completes the 6-MCP-service architecture:
1. Account Service (8070)
2. Transaction/Reporting Service (8071)
3. Payments Service (8072)
4. Limits Service (8073)
5. Contacts Service (8074)
6. **Audit Service (8075)** ✅

All services consume Audit Service for governance logging.
