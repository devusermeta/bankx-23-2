# BankX Agent Cards

This directory contains agent card specifications for all agents in the BankX Multi-Agent Banking System. Agent cards are standardized JSON documents that describe each agent's capabilities, endpoints, dependencies, and metadata.

## Purpose

Agent cards serve multiple purposes:

1. **Service Discovery**: Agents register their capabilities with the Agent Registry using these cards
2. **Documentation**: Developers can understand agent capabilities without reading code
3. **Integration**: Other agents discover what capabilities are available and how to invoke them
4. **Monitoring**: Operations teams understand dependencies and performance characteristics
5. **Validation**: Schema validation ensures all agents conform to standards

## Agent Card Structure

Each agent card contains:

- **Identity**: agent_id, agent_name, agent_type, version
- **Capabilities**: List of operations the agent can perform with input/output schemas
- **MCP Tools**: MCP tools the agent uses (if any)
- **Endpoints**: HTTP, health check, metrics, and A2A endpoints
- **Performance**: Latency metrics and concurrency limits
- **Dependencies**: Other agents, MCP services, and external services
- **Metadata**: Owner team, documentation, deployment configuration

## Available Agent Cards

### Supervisor Agent
**File**: `supervisor-agent-card.json`
**Type**: Supervisor
**Description**: Meta-orchestrator responsible for intent classification and routing

**Capabilities**:
- Intent classification
- Request routing
- Response aggregation

**Dependencies**: All domain and knowledge agents

---

### Account Agent
**File**: `account-agent-card.json`
**Type**: Domain
**Description**: Handles account resolution, balance inquiries, and limits

**Capabilities**:
- `account.balance` - Get account balance
- `account.limits` - Check transaction limits
- `account.disambiguation` - Resolve multiple accounts

**MCP Tools**:
- Account.getCustomerAccounts
- Account.getAccountDetails

---

### Transaction History Agent
**File**: `transaction-agent-card.json`
**Type**: Domain
**Description**: Manages transaction history queries and aggregations

**Capabilities**:
- `transaction.history` - Get transaction history with natural language dates
- `transaction.aggregation` - Aggregate transactions (SUM, COUNT, CATEGORY)
- `transaction.details` - Get single transaction details

**MCP Tools**:
- Reporting.searchTransactions
- Reporting.aggregateTransactions
- Reporting.getTransactionDetails

**Special Features**:
- Natural language date parsing
- Timezone normalization (Asia/Bangkok)

---

### Payment Agent
**File**: `payment-agent-card.json`
**Type**: Domain
**Description**: Processes money transfers with approval workflow

**Capabilities**:
- `payment.transfer` - Two-phase transfer with approval
- `payment.validate` - Validate against policy gates
- `beneficiary.resolve` - Resolve beneficiary from name

**MCP Tools**:
- Payments.validateTransfer
- Payments.submitPayment
- Limits.checkLimits

**Special Features**:
- Explicit approval workflow
- Policy gate validation
- Idempotency enforcement

---

### Product Info FAQ Agent
**File**: `prodinfo-faq-agent-card.json`
**Type**: Knowledge
**Description**: Answers product questions using RAG with Azure AI Search

**Capabilities**:
- `product.info` - Retrieve product information
- `faq.answer` - Answer FAQs with citations
- `product.compare` - Compare products side-by-side
- `banking_terms.explain` - Explain banking terms
- `ticket.create` - Create support tickets

**Knowledge Base**:
- Current Account product document
- Savings Account product document
- Fixed Account product document
- Time Deposit (24M, 36M) documents
- SCB FAQ webpage

**RAG Configuration**:
- Azure AI Search index: `product-info-faq-index`
- Top-K results: 5
- Confidence threshold: 0.7
- Reranking enabled

---

### AI Money Coach Agent
**File**: `ai-money-coach-agent-card.json`
**Type**: Knowledge
**Description**: Provides personal finance coaching using RAG

**Capabilities**:
- `coaching.debt_management` - Debt management strategies
- `coaching.financial_health` - Assess financial health
- `coaching.clarification_first` - Ask clarifying questions
- `coaching.multiple_income` - Multiple income strategies
- `ticket.create` - Create support tickets

**Knowledge Base**:
- Primary: "Debt-Free to Financial Freedom" book
- Supplementary: Financial wellness best practices

**RAG Configuration**:
- Azure AI Search index: `money-coach-index`
- Top-K results: 10
- Confidence threshold: 0.6
- Cache TTL: 168 hours (1 week)

**Special Features**:
- Clarification-first approach
- Ordinary vs Critical Patient assessment
- Empathetic coaching style

---

## Usage

### For Developers

When developing a new agent:

1. Copy an existing agent card as template
2. Update all fields to match your agent
3. Validate against schema (see validation section)
4. Place in this directory
5. Update this README

### For Operations

When deploying an agent:

1. Agent reads its card on startup
2. Agent registers with Agent Registry using card data
3. Other agents discover this agent via registry
4. Monitoring systems use card metadata

### For Integration

When calling an agent:

1. Query Agent Registry for capability
2. Get agent's endpoint from card
3. Check input/output schema requirements
4. Invoke using A2A protocol

## Validation

Validate agent cards against JSON schema:

```bash
# Install jsonschema
pip install jsonschema

# Validate a card
python scripts/validate_agent_card.py docs/agent-cards/account-agent-card.json
```

## Agent Card Schema

```json
{
  "agent_id": "string (generated on startup)",
  "agent_name": "string (required)",
  "agent_type": "string (supervisor|domain|knowledge)",
  "version": "string (semantic version)",
  "description": "string",
  "capabilities": [
    {
      "name": "string (dot notation)",
      "description": "string",
      "input_schema": "object",
      "output_schema": "string or object"
    }
  ],
  "mcp_tools": [
    {
      "tool_name": "string",
      "description": "string",
      "endpoint": "string (URL)",
      "apim_route": "string (optional)"
    }
  ],
  "endpoints": {
    "http": "string (URL)",
    "health": "string (URL)",
    "metrics": "string (URL)",
    "a2a": "string (URL)"
  },
  "performance": {
    "average_latency_ms": "number",
    "p95_latency_ms": "number",
    "p99_latency_ms": "number",
    "max_concurrent_requests": "number"
  },
  "dependencies": {
    "mcp_services": ["string"],
    "other_agents": ["string"],
    "external_services": ["string"]
  },
  "output_formats": ["string"],
  "metadata": {
    "owner_team": "string",
    "support_contact": "string",
    "documentation_url": "string",
    "use_cases": ["string"],
    "deployment_mode": "string (singleton|replicated)"
  },
  "tags": ["string"]
}
```

## Naming Conventions

### Capability Names

Use dot notation with verb or noun:
- `account.balance` (noun - get balance)
- `transaction.history` (noun - get history)
- `payment.validate` (verb - validate something)

### Agent Names

Use PascalCase:
- `AccountAgent`
- `TransactionHistoryAgent`
- `ProdInfoFAQAgent`

### MCP Tool Names

Use Service.operation format:
- `Account.getCustomerAccounts`
- `Reporting.searchTransactions`
- `Payments.submitPayment`

## Best Practices

1. **Versioning**: Use semantic versioning (MAJOR.MINOR.PATCH)
2. **Capabilities**: Group related operations under same namespace
3. **Performance Targets**: Set realistic latency targets based on profiling
4. **Dependencies**: List ALL dependencies explicitly
5. **Examples**: Include example requests/responses in capability definitions
6. **Metadata**: Keep support contact and documentation URLs up to date
7. **Tags**: Use consistent tags for filtering and discovery

## Updating Agent Cards

When updating an agent card:

1. Increment version number (semantic versioning)
2. Update `last_updated` field
3. Update relevant sections (capabilities, dependencies, etc.)
4. Validate against schema
5. Update this README if new agent added
6. Notify Agent Registry of changes (if running)

## Related Documentation

- [A2A Implementation Plan](../A2A_IMPLEMENTATION_PLAN.md)
- [Agent Architecture](../../Agent_Architecture.txt)
- [Agent Registry API](../agent-registry/API_REFERENCE.md)
- [MCP Tools Documentation](../mcp-tools/)

## Support

For questions or issues with agent cards:
- Architecture Team: architecture@bankx.com
- UC1 Team (Financial): uc1-team@bankx.com
- UC2 Team (Product Info): uc2-team@bankx.com
- UC3 Team (Money Coach): uc3-team@bankx.com

---

**Last Updated**: November 7, 2025
**Maintained By**: BankX Architecture Team
