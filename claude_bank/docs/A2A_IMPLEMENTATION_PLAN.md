# Agent-to-Agent (A2A) Implementation Plan
## BankX Multi-Agent Banking System

**Document Version:** 1.0
**Last Updated:** November 7, 2025
**Author:** BankX Architecture Team
**Status:** Implementation Specification

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Agent Registry](#agent-registry)
4. [Agent Communication Protocol](#agent-communication-protocol)
5. [Agent Cards Specification](#agent-cards-specification)
6. [Implementation Phases](#implementation-phases)
7. [Integration with MCP Tools](#integration-with-mcp-tools)
8. [Security & Governance](#security--governance)
9. [Testing Strategy](#testing-strategy)
10. [Deployment Guide](#deployment-guide)

---

## Executive Summary

### Purpose
This document outlines the complete implementation plan for Agent-to-Agent (A2A) communication in the BankX Multi-Agent Banking System, enabling seamless coordination between the Supervisor Agent and domain agents (Account, Transaction, Payment, ProdInfoFAQ, and AIMoneyCoach).

### Key Objectives
- ✅ Enable dynamic agent discovery and registration
- ✅ Implement standardized communication protocol
- ✅ Ensure secure agent-to-agent authentication
- ✅ Maintain complete audit trail of agent interactions
- ✅ Support current MCP tools implementation
- ✅ Enable horizontal scaling of agents
- ✅ Provide fault tolerance and circuit breaking

### Success Criteria
1. All agents can discover and communicate with each other
2. Sub-second latency for agent-to-agent calls
3. 99.9% success rate for agent communication
4. Complete traceability of all agent interactions
5. Zero impact on existing MCP tools functionality

---

## Architecture Overview

### Current System State

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INTERACTION LAYER                        │
│                         (Web Chat UI)                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SUPERVISOR AGENT                               │
│              (Intent Classification & Routing)                   │
│                                                                  │
│  Current Implementation:                                         │
│  - Direct Python method calls to domain agents                  │
│  - In-process communication                                      │
│  - No service discovery                                          │
└──────────────┬──────────────────┬──────────────┬────────────────┘
               │                  │              │
       ┌───────┴────────┐  ┌─────┴──────┐  ┌───┴────────┐
       ▼                ▼  ▼            ▼  ▼            ▼
┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐
│ Account  │  │ Transaction  │  │ Payment  │  │ Product  │
│  Agent   │  │    Agent     │  │  Agent   │  │   FAQ    │
│          │  │              │  │          │  │  Agent   │
└────┬─────┘  └──────┬───────┘  └────┬─────┘  └────┬─────┘
     │               │               │             │
     └───────────────┴───────────────┴─────────────┘
                     │
                     ▼
        ┌────────────────────────┐
        │   MCP TOOLS via APIM   │
        │  (Business Services)   │
        └────────────────────────┘
```

### Target A2A Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER INTERACTION LAYER                        │
│                         (Web Chat UI)                            │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SUPERVISOR AGENT                               │
│              (Intent Classification & Routing)                   │
│                                                                  │
│  Enhanced with:                                                  │
│  ✅ Agent Registry Client                                        │
│  ✅ A2A Communication SDK                                        │
│  ✅ Service Discovery                                            │
│  ✅ Circuit Breaker Pattern                                      │
└──────────────┬──────────────────┬──────────────┬────────────────┘
               │                  │              │
               │   A2A Protocol   │              │
               │   (HTTP/JSON)    │              │
               │                  │              │
       ┌───────┴────────┬─────┴──────┬───┴────────┬─────┴──────┬───┴────────┬─────┴──────┐
       ▼                ▼            ▼            ▼            ▼            ▼            ▼
┌──────────┐  ┌──────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Account  │  │ Transaction  │  │ Payment  │  │ Product  │  │Escalation│  │ AI Money │
│  Agent   │  │    Agent     │  │  Agent   │  │   FAQ    │  │  Comms   │  │  Coach   │
│ Service  │  │   Service    │  │ Service  │  │ Service  │  │ Service  │  │ Service  │
│          │  │              │  │          │  │          │  │          │  │          │
│ Port:    │  │ Port:        │  │ Port:    │  │ Port:    │  │ Port:    │  │ Port:    │
│ 8100     │  │ 8101         │  │ 8102     │  │ 8104     │  │ 8105     │  │ 8106     │
└────┬─────┘  └──────┬───────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
     │               │               │             │             │             │
     │                All Agents Register with Agent Registry                 │
     │               │               │             │             │             │
     └───────────────┴───────────────┴─────────────┴─────────────┴─────────────┘
                     │
        ┌────────────┴───────────┐
        │                        │
        ▼                        ▼
┌────────────────┐   ┌────────────────────────┐
│ AGENT REGISTRY │   │   MCP TOOLS via APIM   │
│   (Service)    │   │  (Business Services)   │
│                │   │                        │
│ Port: 9000     │   │  Account MCP: 8070     │
│                │   │  Transaction: 8071     │
│ Features:      │   │  Payment: 8072         │
│ • Discovery    │   │  Limits: 8073          │
│ • Health Check │   │  ProdInfo: 8074        │
│ • Load Balance │   │  AIMoneyCoach: 8075    │
│ • Versioning   │   │  Escalation: 8076      │
└────────────────┘   └────────────────────────┘
         │
         ▼
┌────────────────────────────────────┐
│   DECISION LEDGER (Cosmos DB)      │
│   Logs all A2A interactions        │
└────────────────────────────────────┘
```

### Key Architectural Changes

1. **Agent Registry Service**
   - Centralized service discovery
   - Health checking
   - Load balancing
   - Agent capability discovery

2. **A2A Communication SDK**
   - Standardized protocol (HTTP/JSON)
   - Authentication (JWT or Entra ID)
   - Retry logic with exponential backoff
   - Circuit breaker pattern
   - Distributed tracing

3. **Agent Services**
   - Each agent runs as independent service
   - RESTful API endpoints
   - Health check endpoints
   - Metrics exposure (Prometheus format)

4. **Integration Points**
   - Zero changes to MCP tools
   - MCP tools remain unchanged
   - Agents call MCP tools as before
   - A2A only for inter-agent communication

---

## Agent Registry

### Purpose
The Agent Registry is a centralized service discovery system that allows agents to:
- Register themselves on startup
- Discover other agents dynamically
- Monitor agent health
- Load balance requests
- Version compatibility checking

### Registry Data Model

```python
class AgentRegistration:
    """Agent registration information."""
    agent_id: str                    # Unique identifier (UUID)
    agent_name: str                  # Human-readable name
    agent_type: str                  # Type: supervisor, domain, knowledge
    version: str                     # Semantic version (e.g., "1.0.0")
    capabilities: List[str]          # List of capabilities
    endpoints: Dict[str, str]        # Service endpoints
    health_check_url: str            # Health check endpoint
    metadata: Dict[str, Any]         # Additional metadata
    status: str                      # Status: active, inactive, maintenance
    registered_at: datetime          # Registration timestamp
    last_heartbeat: datetime         # Last heartbeat timestamp
    tags: List[str]                  # Searchable tags
```

### Agent Card Schema

```json
{
  "agent_id": "account-agent-001",
  "agent_name": "AccountAgent",
  "agent_type": "domain",
  "version": "1.0.0",
  "capabilities": [
    "account.balance",
    "account.limits",
    "account.details",
    "account.disambiguation"
  ],
  "endpoints": {
    "http": "http://localhost:8100",
    "health": "http://localhost:8100/health",
    "metrics": "http://localhost:8100/metrics"
  },
  "health_check_url": "http://localhost:8100/health",
  "metadata": {
    "description": "Handles account resolution and balance inquiries",
    "mcp_tools": ["Account.getCustomerAccounts", "Account.getAccountDetails"],
    "output_formats": ["BALANCE_CARD", "ACCOUNT_PICKER"],
    "max_concurrent_requests": 100,
    "average_response_time_ms": 250
  },
  "status": "active",
  "registered_at": "2025-11-07T10:00:00Z",
  "last_heartbeat": "2025-11-07T10:05:00Z",
  "tags": ["uc1", "financial-operations", "account-management"]
}
```

### Registry API Specification

#### 1. Register Agent
```http
POST /api/v1/agents/register
Content-Type: application/json
Authorization: Bearer <jwt-token>

{
  "agent_name": "AccountAgent",
  "agent_type": "domain",
  "version": "1.0.0",
  "capabilities": ["account.balance", "account.limits"],
  "endpoints": {
    "http": "http://localhost:8100"
  },
  "metadata": {...}
}

Response: 201 Created
{
  "agent_id": "account-agent-001",
  "status": "registered",
  "message": "Agent registered successfully"
}
```

#### 2. Discover Agents
```http
GET /api/v1/agents/discover?capability=account.balance&status=active
Authorization: Bearer <jwt-token>

Response: 200 OK
{
  "agents": [
    {
      "agent_id": "account-agent-001",
      "agent_name": "AccountAgent",
      "endpoints": {"http": "http://localhost:8100"},
      ...
    }
  ],
  "count": 1
}
```

#### 3. Heartbeat
```http
POST /api/v1/agents/{agent_id}/heartbeat
Authorization: Bearer <jwt-token>

Response: 200 OK
{
  "status": "alive",
  "last_heartbeat": "2025-11-07T10:05:00Z"
}
```

#### 4. Deregister Agent
```http
DELETE /api/v1/agents/{agent_id}
Authorization: Bearer <jwt-token>

Response: 200 OK
{
  "status": "deregistered",
  "message": "Agent removed from registry"
}
```

### Registry Implementation

**Technology Stack:**
- **Framework:** FastAPI (Python) or Express.js (Node.js)
- **Database:** Redis (for fast lookups) + Cosmos DB (for persistence)
- **Authentication:** JWT or Azure Entra ID
- **Deployment:** Azure Container Apps or Kubernetes

**Directory Structure:**
```
app/agent-registry/
├── main.py                      # FastAPI application
├── models/
│   ├── agent_registration.py   # Pydantic models
│   └── agent_card.py
├── services/
│   ├── registry_service.py     # Business logic
│   ├── health_service.py       # Health checking
│   └── discovery_service.py    # Agent discovery
├── api/
│   ├── agents_router.py        # API routes
│   └── auth.py                 # Authentication
├── storage/
│   ├── redis_store.py          # Redis client
│   └── cosmos_store.py         # Cosmos DB client
├── config/
│   └── settings.py             # Configuration
└── requirements.txt
```

---

## Agent Communication Protocol

### A2A Message Format

```json
{
  "message_id": "msg-uuid-12345",
  "correlation_id": "req-uuid-67890",
  "protocol_version": "1.0",
  "timestamp": "2025-11-07T10:00:00Z",
  "source": {
    "agent_id": "supervisor-001",
    "agent_name": "SupervisorAgent"
  },
  "target": {
    "agent_id": "account-agent-001",
    "agent_name": "AccountAgent"
  },
  "intent": "account.get_balance",
  "payload": {
    "customer_id": "CUST-001",
    "account_id": "CHK-001",
    "requester_role": "customer",
    "context": {
      "conversation_id": "conv-12345",
      "user_message": "What's my balance?"
    }
  },
  "metadata": {
    "timeout_seconds": 30,
    "retry_count": 0,
    "trace_id": "trace-abc123",
    "span_id": "span-xyz789"
  }
}
```

### A2A Response Format

```json
{
  "message_id": "msg-uuid-54321",
  "correlation_id": "req-uuid-67890",
  "protocol_version": "1.0",
  "timestamp": "2025-11-07T10:00:01Z",
  "source": {
    "agent_id": "account-agent-001",
    "agent_name": "AccountAgent"
  },
  "target": {
    "agent_id": "supervisor-001",
    "agent_name": "SupervisorAgent"
  },
  "status": "success",
  "response": {
    "type": "BALANCE_CARD",
    "account_id": "CHK-001",
    "account_name": "Somchai's Checking",
    "currency": "THB",
    "ledger_balance": 99650.00,
    "available_balance": 99650.00,
    ...
  },
  "metadata": {
    "processing_time_ms": 245,
    "trace_id": "trace-abc123",
    "span_id": "span-xyz789"
  }
}
```

### Communication Patterns

#### 1. Synchronous Request-Response (Primary)

```python
# Supervisor Agent calls Account Agent
async def call_account_agent(customer_id: str):
    """Call Account Agent to get balance."""

    # Discover agent
    agent_info = await registry_client.discover_agent(
        capability="account.balance"
    )

    # Build A2A message
    message = A2AMessage(
        intent="account.get_balance",
        payload={
            "customer_id": customer_id
        },
        timeout_seconds=30
    )

    # Send request
    response = await a2a_client.send_request(
        target_agent_id=agent_info.agent_id,
        endpoint=agent_info.endpoints["http"],
        message=message
    )

    return response.payload
```

#### 2. Asynchronous Message Queue (Optional)

For long-running operations or high-volume scenarios:

```python
# Publish message to queue
await message_queue.publish(
    queue="agent-messages",
    message=a2a_message
)

# Agent subscribes to queue
async def handle_message(message):
    # Process message
    result = await process_request(message)

    # Send response
    await message_queue.publish(
        queue="agent-responses",
        message=result
    )
```

### A2A Client SDK

```python
class A2AClient:
    """SDK for agent-to-agent communication."""

    def __init__(self, config: A2AConfig):
        self.config = config
        self.registry_client = RegistryClient(config.registry_url)
        self.http_client = httpx.AsyncClient(timeout=config.timeout)
        self.circuit_breaker = CircuitBreaker(threshold=5)

    async def send_request(
        self,
        target_agent_id: str,
        endpoint: str,
        message: A2AMessage
    ) -> A2AResponse:
        """Send A2A request with retry and circuit breaker."""

        # Circuit breaker check
        if not self.circuit_breaker.can_execute():
            raise CircuitBreakerOpenError()

        # Retry logic
        for attempt in range(self.config.max_retries):
            try:
                # Add authentication
                headers = await self._get_auth_headers()

                # Send request
                response = await self.http_client.post(
                    f"{endpoint}/a2a/invoke",
                    json=message.dict(),
                    headers=headers
                )

                # Success - reset circuit breaker
                self.circuit_breaker.record_success()

                return A2AResponse.parse_obj(response.json())

            except Exception as e:
                # Record failure
                self.circuit_breaker.record_failure()

                # Retry with exponential backoff
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(
                        self.config.retry_backoff * (2 ** attempt)
                    )
                else:
                    raise

    async def _get_auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers."""
        if self.config.auth_type == "jwt":
            token = self._generate_jwt()
            return {"Authorization": f"Bearer {token}"}
        elif self.config.auth_type == "entra_id":
            token = await self._get_entra_token()
            return {"Authorization": f"Bearer {token}"}
        return {}
```

---

## Agent Cards Specification

### Standard Agent Card Template

Each agent must provide a card describing its capabilities:

```json
{
  "agent_id": "GENERATED_ON_STARTUP",
  "agent_name": "AccountAgent",
  "agent_type": "domain",
  "version": "1.0.0",
  "description": "Handles account resolution, balance inquiries, and limits checking",

  "capabilities": [
    {
      "name": "account.balance",
      "description": "Retrieve account balance and available funds",
      "input_schema": {
        "customer_id": "string",
        "account_id": "string (optional)"
      },
      "output_schema": "BALANCE_CARD"
    },
    {
      "name": "account.limits",
      "description": "Check transaction and daily limits",
      "input_schema": {
        "customer_id": "string",
        "account_id": "string (optional)"
      },
      "output_schema": "BALANCE_CARD"
    },
    {
      "name": "account.disambiguation",
      "description": "Resolve account when multiple accounts exist",
      "input_schema": {
        "customer_id": "string"
      },
      "output_schema": "ACCOUNT_PICKER"
    }
  ],

  "mcp_tools": [
    {
      "tool_name": "Account.getCustomerAccounts",
      "description": "Get all accounts for a customer",
      "endpoint": "http://localhost:8070"
    },
    {
      "tool_name": "Account.getAccountDetails",
      "description": "Get detailed account information",
      "endpoint": "http://localhost:8070"
    }
  ],

  "endpoints": {
    "http": "http://localhost:8100",
    "health": "http://localhost:8100/health",
    "metrics": "http://localhost:8100/metrics",
    "a2a": "http://localhost:8100/a2a/invoke"
  },

  "performance": {
    "average_latency_ms": 250,
    "p95_latency_ms": 500,
    "p99_latency_ms": 1000,
    "max_concurrent_requests": 100
  },

  "dependencies": {
    "mcp_services": ["Account MCP Server"],
    "other_agents": [],
    "external_services": ["APIM Gateway"]
  },

  "output_formats": ["BALANCE_CARD", "ACCOUNT_PICKER"],

  "metadata": {
    "owner_team": "UC1 Team",
    "support_contact": "uc1-support@bankx.com",
    "documentation_url": "https://docs.bankx.com/agents/account"
  },

  "tags": ["uc1", "financial-operations", "account-management"]
}
```

### Agent Card for Each Agent

#### 1. **Supervisor Agent Card**
```json
{
  "agent_name": "SupervisorAgent",
  "agent_type": "supervisor",
  "version": "1.0.0",
  "description": "Orchestrates user intent classification and routes requests to appropriate domain agents",
  "capabilities": [
    {
      "name": "intent.classify",
      "description": "Classify user intent and route to appropriate agent",
      "input_schema": {
        "user_message": "string",
        "conversation_context": "object (optional)"
      },
      "output_schema": "ROUTING_DECISION"
    },
    {
      "name": "response.aggregate",
      "description": "Aggregate responses from multiple agents",
      "input_schema": {
        "agent_responses": "array"
      },
      "output_schema": "AGGREGATED_RESPONSE"
    },
    {
      "name": "conversation.orchestrate",
      "description": "Orchestrate multi-turn conversations across agents",
      "input_schema": {
        "conversation_id": "string",
        "user_message": "string"
      },
      "output_schema": "CONVERSATION_RESPONSE"
    }
  ],
  "endpoints": {
    "http": "http://localhost:8099",
    "health": "http://localhost:8099/health",
    "metrics": "http://localhost:8099/metrics",
    "a2a": "http://localhost:8099/a2a/invoke"
  },
  "mcp_tools": [],
  "dependencies": {
    "other_agents": [
      "AccountAgent",
      "TransactionAgent",
      "PaymentAgent",
      "ProdInfoFAQAgent",
      "AIMoneyCoachAgent",
      "EscalationCommsAgent"
    ],
    "external_services": ["Agent Registry"]
  },
  "output_formats": ["ROUTING_DECISION", "AGGREGATED_RESPONSE", "CONVERSATION_RESPONSE"],
  "metadata": {
    "owner_team": "Platform Team",
    "support_contact": "platform-support@bankx.com",
    "documentation_url": "https://docs.bankx.com/agents/supervisor"
  },
  "tags": ["supervisor", "orchestration", "routing"]
}
```

#### 2. **Transaction Agent Card**
```json
{
  "agent_name": "TransactionHistoryAgent",
  "agent_type": "domain",
  "capabilities": [
    {
      "name": "transaction.history",
      "description": "Retrieve transaction history with date filtering",
      "output_schema": "TXN_TABLE"
    },
    {
      "name": "transaction.aggregation",
      "description": "Aggregate transactions (SUM, COUNT, CATEGORY)",
      "output_schema": "INSIGHTS_CARD"
    },
    {
      "name": "transaction.details",
      "description": "Get single transaction details",
      "output_schema": "TXN_DETAIL"
    }
  ],
  "mcp_tools": [
    "Reporting.searchTransactions",
    "Reporting.aggregateTransactions",
    "Reporting.getTransactionDetails"
  ]
}
```

#### 3. **Payment Agent Card**
```json
{
  "agent_name": "PaymentAgent",
  "agent_type": "domain",
  "capabilities": [
    {
      "name": "payment.transfer",
      "description": "Process money transfers with approval workflow",
      "output_schema": "TRANSFER_APPROVAL / TRANSFER_RESULT"
    },
    {
      "name": "payment.validate",
      "description": "Validate transfer against policy gates"
    }
  ],
  "mcp_tools": [
    "Payments.validateTransfer",
    "Payments.submitPayment",
    "Limits.checkLimits"
  ],
  "dependencies": {
    "other_agents": ["AccountAgent"]
  }
}
```

#### 4. **Product Info FAQ Agent Card**
```json
{
  "agent_name": "ProdInfoFAQAgent",
  "agent_type": "knowledge",
  "version": "1.0.0",
  "description": "Handles product information queries and FAQs using RAG with Azure AI Search",
  "capabilities": [
    {
      "name": "product.info",
      "description": "Retrieve product information using RAG",
      "input_schema": {
        "query": "string",
        "product_category": "string (optional)"
      },
      "output_schema": "KNOWLEDGE_CARD"
    },
    {
      "name": "faq.answer",
      "description": "Answer frequently asked questions",
      "input_schema": {
        "question": "string"
      },
      "output_schema": "FAQ_CARD"
    },
    {
      "name": "ticket.create",
      "description": "Create support ticket when answer not found",
      "input_schema": {
        "customer_id": "string",
        "query": "string",
        "category": "string"
      },
      "output_schema": "TICKET_CARD"
    }
  ],
  "mcp_tools": [
    {
      "tool_name": "ProdInfoFAQ.search",
      "description": "Search product information knowledge base",
      "endpoint": "http://localhost:8074"
    },
    {
      "tool_name": "ProdInfoFAQ.createTicket",
      "description": "Create support ticket for unanswered queries",
      "endpoint": "http://localhost:8074"
    }
  ],
  "endpoints": {
    "http": "http://localhost:8104",
    "health": "http://localhost:8104/health",
    "metrics": "http://localhost:8104/metrics",
    "a2a": "http://localhost:8104/a2a/invoke"
  },
  "dependencies": {
    "mcp_services": ["ProdInfoFAQ MCP Server"],
    "other_agents": ["EscalationCommsAgent"],
    "external_services": ["Azure AI Search", "APIM Gateway"]
  },
  "output_formats": ["KNOWLEDGE_CARD", "FAQ_CARD", "TICKET_CARD"],
  "tags": ["uc2", "knowledge", "product-info", "faq"]
}
```

#### 5. **EscalationComms Agent Card**
```json
{
  "agent_name": "EscalationCommsAgent",
  "agent_type": "communication",
  "version": "1.0.0",
  "description": "Handles email notifications and escalation communications via Azure Communication Services",
  "capabilities": [
    {
      "name": "email.send_customer_notification",
      "description": "Send ticket confirmation email to customer",
      "input_schema": {
        "customer_email": "string",
        "customer_name": "string",
        "ticket_id": "string",
        "ticket_summary": "string",
        "category": "string"
      },
      "output_schema": "EMAIL_CONFIRMATION"
    },
    {
      "name": "email.send_employee_notification",
      "description": "Send ticket notification to bank employee",
      "input_schema": {
        "employee_email": "string",
        "ticket_id": "string",
        "customer_id": "string",
        "customer_name": "string",
        "priority": "string",
        "category": "string",
        "details": "string"
      },
      "output_schema": "EMAIL_CONFIRMATION"
    },
    {
      "name": "email.send_dual_notification",
      "description": "Send notifications to both customer and employee",
      "input_schema": {
        "ticket_data": "object",
        "customer_email": "string",
        "employee_email": "string"
      },
      "output_schema": "EMAIL_CONFIRMATION"
    }
  ],
  "mcp_tools": [
    {
      "tool_name": "EscalationComms.sendEmail",
      "description": "Send email via Azure Communication Services",
      "endpoint": "http://localhost:8076"
    }
  ],
  "endpoints": {
    "http": "http://localhost:8105",
    "health": "http://localhost:8105/health",
    "metrics": "http://localhost:8105/metrics",
    "a2a": "http://localhost:8105/a2a/invoke"
  },
  "performance": {
    "average_latency_ms": 500,
    "p95_latency_ms": 1000,
    "p99_latency_ms": 2000,
    "max_concurrent_requests": 50
  },
  "dependencies": {
    "mcp_services": ["EscalationComms MCP Server"],
    "other_agents": [],
    "external_services": ["Azure Communication Services", "APIM Gateway"]
  },
  "output_formats": ["EMAIL_CONFIRMATION"],
  "metadata": {
    "owner_team": "UC2/UC3 Team",
    "support_contact": "uc2-uc3-support@bankx.com",
    "documentation_url": "https://docs.bankx.com/agents/escalation-comms"
  },
  "tags": ["uc2", "uc3", "communication", "escalation", "email"]
}
```

#### 6. **AI Money Coach Agent Card**
```json
{
  "agent_name": "AIMoneyCoachAgent",
  "agent_type": "knowledge",
  "version": "1.0.0",
  "description": "Provides AI-powered personal finance coaching and debt management guidance grounded in financial literacy content",
  "capabilities": [
    {
      "name": "coaching.debt_management",
      "description": "Provide debt management coaching from 'Debt-Free to Financial Freedom' guide",
      "input_schema": {
        "customer_id": "string",
        "query": "string",
        "financial_context": "object (optional)"
      },
      "output_schema": "COACHING_CARD"
    },
    {
      "name": "coaching.financial_health",
      "description": "Assess financial health level (Ordinary vs Critical Patient)",
      "input_schema": {
        "customer_id": "string",
        "debt_to_income_ratio": "number (optional)",
        "situation_description": "string"
      },
      "output_schema": "HEALTH_ASSESSMENT_CARD"
    },
    {
      "name": "coaching.clarification",
      "description": "Clarification-first approach for personalized financial advice",
      "input_schema": {
        "customer_id": "string",
        "initial_query": "string"
      },
      "output_schema": "CLARIFICATION_CARD"
    },
    {
      "name": "coaching.emergency_plan",
      "description": "Provide Strong Medicine Plan for critical financial situations",
      "input_schema": {
        "customer_id": "string",
        "debt_details": "array",
        "income_expense_data": "object"
      },
      "output_schema": "EMERGENCY_PLAN_CARD"
    },
    {
      "name": "ticket.create_escalation",
      "description": "Create escalation ticket for complex cases requiring human intervention",
      "input_schema": {
        "customer_id": "string",
        "case_summary": "string",
        "urgency_level": "string"
      },
      "output_schema": "TICKET_CARD"
    }
  ],
  "mcp_tools": [
    {
      "tool_name": "AIMoneyCoach.ai_search_rag_results",
      "description": "Search 'Debt-Free to Financial Freedom' using Azure AI Search",
      "endpoint": "http://localhost:8075"
    },
    {
      "tool_name": "AIMoneyCoach.ai_foundry_content_understanding",
      "description": "Validate and ground responses using AI Foundry",
      "endpoint": "http://localhost:8075"
    },
    {
      "tool_name": "AIMoneyCoach.createTicket",
      "description": "Create support ticket for escalation",
      "endpoint": "http://localhost:8075"
    }
  ],
  "endpoints": {
    "http": "http://localhost:8106",
    "health": "http://localhost:8106/health",
    "metrics": "http://localhost:8106/metrics",
    "a2a": "http://localhost:8106/a2a/invoke"
  },
  "performance": {
    "average_latency_ms": 800,
    "p95_latency_ms": 2000,
    "p99_latency_ms": 4000,
    "max_concurrent_requests": 30
  },
  "dependencies": {
    "mcp_services": ["AIMoneyCoach MCP Server"],
    "other_agents": ["EscalationCommsAgent"],
    "external_services": ["Azure AI Search", "Azure AI Foundry", "APIM Gateway"]
  },
  "output_formats": ["COACHING_CARD", "HEALTH_ASSESSMENT_CARD", "CLARIFICATION_CARD", "EMERGENCY_PLAN_CARD", "TICKET_CARD"],
  "metadata": {
    "owner_team": "UC3 Team",
    "support_contact": "uc3-support@bankx.com",
    "documentation_url": "https://docs.bankx.com/agents/ai-money-coach",
    "knowledge_base": "Debt-Free to Financial Freedom (12 chapters)"
  },
  "tags": ["uc3", "knowledge", "financial-coaching", "debt-management", "ai-powered"]
}
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Deliverables:**
1. ✅ Agent Registry Service
   - FastAPI application
   - Redis + Cosmos DB storage
   - Registration/discovery APIs
   - Health check system

2. ✅ A2A Client SDK
   - Python package
   - HTTP communication
   - JWT authentication
   - Retry/circuit breaker

3. ✅ Agent Card Schema
   - JSON schema definition
   - Validation logic
   - Agent card templates

**Tasks:**
```
□ Create agent-registry service
  □ Setup FastAPI project structure
  □ Implement registration API
  □ Implement discovery API
  □ Add Redis caching layer
  □ Add Cosmos DB persistence
  □ Implement health checking
  □ Add authentication (JWT)

□ Create a2a-sdk package
  □ Setup Python package
  □ Implement A2AClient class
  □ Add retry logic
  □ Add circuit breaker
  □ Add distributed tracing
  □ Write unit tests

□ Define agent cards
  □ Create JSON schemas
  □ Generate cards for all agents
  □ Add validation
```

### Phase 2: Agent Refactoring (Week 3-4)

**Deliverables:**
1. ✅ Refactor Supervisor Agent
   - Add A2A client
   - Integrate with registry
   - Replace direct calls with A2A

2. ✅ Refactor Domain Agents
   - Add A2A server endpoints
   - Register with registry
   - Maintain MCP tool integration

3. ✅ Testing Infrastructure
   - Unit tests
   - Integration tests
   - Load tests

**Tasks:**
```
□ Refactor SupervisorAgent
  □ Add A2A client initialization
  □ Add registry client
  □ Replace direct method calls
  □ Add error handling
  □ Add distributed tracing
  □ Test routing logic

□ Refactor AccountAgent
  □ Add A2A server endpoints
  □ Register on startup
  □ Implement heartbeat
  □ Add health check
  □ Test with supervisor

□ Refactor TransactionAgent
  □ Same as AccountAgent

□ Refactor PaymentAgent
  □ Same as AccountAgent

□ Refactor Knowledge Agents
  □ ProdInfoFAQAgent
  □ AIMoneyCoachAgent
```

### Phase 3: Testing & Optimization (Week 5)

**Deliverables:**
1. ✅ Comprehensive Testing
   - Unit tests (80%+ coverage)
   - Integration tests
   - Load tests
   - Chaos testing

2. ✅ Performance Optimization
   - Latency optimization
   - Connection pooling
   - Caching strategies

3. ✅ Documentation
   - API documentation
   - Deployment guides
   - Troubleshooting guides

**Tasks:**
```
□ Testing
  □ Write unit tests for all components
  □ Integration tests for A2A flows
  □ Load test with 1000 concurrent requests
  □ Chaos testing (network failures, agent crashes)
  □ Security testing

□ Optimization
  □ Profile A2A latency
  □ Optimize serialization
  □ Add connection pooling
  □ Add response caching
  □ Tune circuit breaker parameters

□ Documentation
  □ API reference documentation
  □ Architecture diagrams
  □ Deployment runbooks
  □ Troubleshooting guides
```

### Phase 4: Deployment & Monitoring (Week 6)

**Deliverables:**
1. ✅ Production Deployment
   - Azure Container Apps
   - Kubernetes manifests
   - CI/CD pipelines

2. ✅ Monitoring & Alerting
   - Application Insights dashboards
   - Alerts for failures
   - Performance metrics

3. ✅ Documentation & Training
   - User guides
   - Team training
   - Runbooks

**Tasks:**
```
□ Deployment
  □ Create Docker images for all agents
  □ Deploy agent registry
  □ Deploy agents to Container Apps
  □ Configure networking
  □ Set up load balancers
  □ Configure auto-scaling

□ Monitoring
  □ Create App Insights dashboards
  □ Set up alerts
  □ Configure distributed tracing
  □ Add custom metrics
  □ Set up log aggregation

□ Training
  □ Create user documentation
  □ Conduct team training
  □ Create runbooks
  □ Document troubleshooting procedures
```

---

## Integration with MCP Tools

### Key Principle: Zero Impact

**MCP tools remain completely unchanged.** A2A is ONLY for agent-to-agent communication.

### Integration Architecture

```
┌────────────────────────────────────────────────────────────┐
│                  SUPERVISOR AGENT                          │
│                                                            │
│  A2A Client → Discovers & Calls Domain Agents             │
│  (New)                                                     │
└─────────────────────┬──────────────────────────────────────┘
                      │
                      │ A2A Protocol
                      │
              ┌───────┴────────┐
              ▼                ▼
    ┌──────────────┐  ┌──────────────┐
    │   Account    │  │ Transaction  │
    │   Agent      │  │   Agent      │
    │              │  │              │
    │ A2A Server   │  │ A2A Server   │
    │ (New)        │  │ (New)        │
    │      │       │  │      │       │
    │      └───────┼──┼──────┘       │
    │              │  │              │
    │ MCP Client   │  │ MCP Client   │
    │ (Unchanged)  │  │ (Unchanged)  │
    └──────┬───────┘  └──────┬───────┘
           │                 │
           │ Existing MCP    │
           │ Protocol        │
           │                 │
           └────────┬────────┘
                    │
                    ▼
        ┌────────────────────────┐
        │   MCP TOOLS via APIM   │
        │    (Unchanged)         │
        │                        │
        │  • Account MCP         │
        │  • Transaction MCP     │
        │  • Payment MCP         │
        │  • etc.                │
        └────────────────────────┘
```

### Agent Implementation Pattern

```python
class AccountAgent:
    """Account Agent with A2A support."""

    def __init__(self):
        # Existing MCP client (UNCHANGED)
        self.mcp_client = AccountMCPClient()

        # NEW: A2A server
        self.a2a_server = A2AServer(port=8100)

        # NEW: Registry client
        self.registry_client = RegistryClient()

    async def startup(self):
        """Initialize agent and register with registry."""

        # Register with registry
        await self.registry_client.register(
            agent_name="AccountAgent",
            capabilities=["account.balance", "account.limits"],
            endpoint="http://localhost:8100"
        )

        # Start heartbeat
        asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        """Send periodic heartbeats to registry."""
        while True:
            await self.registry_client.heartbeat()
            await asyncio.sleep(30)

    # Existing methods (UNCHANGED)
    async def get_balance(self, customer_id: str) -> Dict:
        """Get account balance - EXISTING METHOD."""
        # Still uses MCP client
        accounts = await self.mcp_client.get_customer_accounts(customer_id)
        return {"balance": accounts[0].balance}

    # NEW: A2A endpoint
    @a2a_server.route("account.balance")
    async def handle_balance_request(self, message: A2AMessage) -> A2AResponse:
        """Handle A2A balance request."""

        # Delegate to existing method
        result = await self.get_balance(message.payload["customer_id"])

        return A2AResponse(
            status="success",
            payload=result
        )
```

### No Changes to MCP Servers

```python
# app/business-api/python/account/mcp_tools.py
# THIS FILE REMAINS COMPLETELY UNCHANGED

@mcp.tool()
async def get_customer_accounts(customer_id: str) -> List[Account]:
    """Get all accounts for a customer."""
    # Existing implementation
    df = pd.read_csv("accounts.csv")
    accounts = df[df["customer_id"] == customer_id]
    return accounts.to_dict("records")

# NO CHANGES NEEDED TO MCP TOOLS!
```

---

## Security & Governance

### Authentication & Authorization

#### Option 1: JWT Tokens (Recommended for Development)

```python
# Generate JWT for agent-to-agent auth
def generate_agent_jwt(agent_id: str, secret_key: str) -> str:
    """Generate JWT for agent authentication."""
    payload = {
        "agent_id": agent_id,
        "exp": datetime.utcnow() + timedelta(hours=1),
        "iat": datetime.utcnow(),
        "iss": "bankx-agent-registry"
    }
    return jwt.encode(payload, secret_key, algorithm="HS256")

# Verify JWT
def verify_agent_jwt(token: str, secret_key: str) -> Dict:
    """Verify and decode agent JWT."""
    try:
        return jwt.decode(token, secret_key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")
```

#### Option 2: Azure Entra ID (Recommended for Production)

```python
from azure.identity import DefaultAzureCredential
from azure.identity import ManagedIdentityCredential

# Each agent gets managed identity
credential = ManagedIdentityCredential(client_id=agent_client_id)

# Get token for calling other agent
token = credential.get_token("api://bankx-agents/.default")

# Verify token from calling agent
def verify_entra_token(token: str):
    """Verify Entra ID token."""
    # Use Microsoft's JWT validation
    # Verify issuer, audience, signature
    pass
```

### Audit Trail

All A2A communications logged to Decision Ledger:

```python
async def log_a2a_interaction(
    source_agent: str,
    target_agent: str,
    message: A2AMessage,
    response: A2AResponse,
    latency_ms: int
):
    """Log A2A interaction to Decision Ledger."""

    log_entry = {
        "id": str(uuid4()),
        "timestamp": datetime.utcnow(),
        "interaction_type": "a2a",
        "source_agent_id": source_agent,
        "target_agent_id": target_agent,
        "intent": message.intent,
        "request_payload": message.payload,
        "response_status": response.status,
        "response_payload": response.payload,
        "latency_ms": latency_ms,
        "trace_id": message.metadata.get("trace_id"),
        "correlation_id": message.correlation_id
    }

    await cosmos_client.create_item(
        database="bankx_db",
        container="decision_ledger",
        item=log_entry
    )
```

### Distributed Tracing

```python
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Initialize tracer
tracer = trace.get_tracer(__name__)

# Trace A2A call
with tracer.start_as_current_span("a2a.call") as span:
    span.set_attribute("target.agent", "AccountAgent")
    span.set_attribute("intent", "account.balance")

    response = await a2a_client.send_request(
        target_agent_id="account-agent-001",
        endpoint="http://localhost:8100",
        message=message
    )

    span.set_attribute("response.status", response.status)
    span.set_attribute("latency.ms", latency)
```

---

## Testing Strategy

### Unit Tests

```python
# tests/test_a2a_client.py
@pytest.mark.asyncio
async def test_a2a_client_send_request():
    """Test A2A client sends request correctly."""

    # Mock HTTP response
    with aioresponses() as mocked:
        mocked.post(
            "http://localhost:8100/a2a/invoke",
            payload={
                "status": "success",
                "payload": {"balance": 1000}
            }
        )

        # Create client
        client = A2AClient(config)

        # Send request
        response = await client.send_request(
            target_agent_id="account-agent-001",
            endpoint="http://localhost:8100",
            message=A2AMessage(intent="account.balance")
        )

        # Assert
        assert response.status == "success"
        assert response.payload["balance"] == 1000
```

### Integration Tests

```python
# tests/integration/test_supervisor_to_account.py
@pytest.mark.asyncio
async def test_supervisor_calls_account_agent():
    """Test Supervisor can call Account Agent via A2A."""

    # Start agent registry
    registry = await start_agent_registry()

    # Start Account Agent
    account_agent = await start_account_agent()
    await account_agent.register_with_registry(registry.url)

    # Create Supervisor
    supervisor = SupervisorAgent(registry_url=registry.url)

    # Send request
    response = await supervisor.handle_request(
        user_message="What's my balance?",
        customer_id="CUST-001"
    )

    # Assert
    assert response["type"] == "BALANCE_CARD"
    assert "ledger_balance" in response
```

### Load Tests

```python
# tests/load/test_a2a_load.py
import locust

class A2AUser(locust.HttpUser):
    """Simulate agent-to-agent calls under load."""

    @locust.task
    def call_account_agent(self):
        """Call account agent."""
        self.client.post(
            "/a2a/invoke",
            json={
                "intent": "account.balance",
                "payload": {"customer_id": "CUST-001"}
            }
        )

# Run: locust -f test_a2a_load.py --users 1000 --spawn-rate 10
```

---

## Deployment Guide

### Docker Images

```dockerfile
# Dockerfile for Agent Registry
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9000"]
```

```dockerfile
# Dockerfile for Account Agent
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8100

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]
```

### Kubernetes Manifests

```yaml
# k8s/agent-registry-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-registry
spec:
  replicas: 2
  selector:
    matchLabels:
      app: agent-registry
  template:
    metadata:
      labels:
        app: agent-registry
    spec:
      containers:
      - name: agent-registry
        image: bankx/agent-registry:1.0.0
        ports:
        - containerPort: 9000
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: COSMOS_ENDPOINT
          valueFrom:
            secretKeyRef:
              name: bankx-secrets
              key: cosmos-endpoint
---
apiVersion: v1
kind: Service
metadata:
  name: agent-registry
spec:
  selector:
    app: agent-registry
  ports:
  - port: 9000
    targetPort: 9000
  type: ClusterIP
```

```yaml
# k8s/account-agent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: account-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: account-agent
  template:
    metadata:
      labels:
        app: account-agent
    spec:
      containers:
      - name: account-agent
        image: bankx/account-agent:1.0.0
        ports:
        - containerPort: 8100
        env:
        - name: AGENT_REGISTRY_URL
          value: "http://agent-registry:9000"
        - name: MCP_ACCOUNT_URL
          value: "http://account-mcp:8070"
        livenessProbe:
          httpGet:
            path: /health
            port: 8100
          initialDelaySeconds: 10
          periodSeconds: 30
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: account-agent
spec:
  selector:
    app: account-agent
  ports:
  - port: 8100
    targetPort: 8100
  type: ClusterIP
```

### Azure Container Apps

```bash
# Create Container App Environment
az containerapp env create \
  --name bankx-agent-env \
  --resource-group bankx-dev-rg \
  --location eastus

# Deploy Agent Registry
az containerapp create \
  --name agent-registry \
  --resource-group bankx-dev-rg \
  --environment bankx-agent-env \
  --image bankx/agent-registry:1.0.0 \
  --target-port 9000 \
  --ingress external \
  --min-replicas 2 \
  --max-replicas 5

# Deploy Account Agent
az containerapp create \
  --name account-agent \
  --resource-group bankx-dev-rg \
  --environment bankx-agent-env \
  --image bankx/account-agent:1.0.0 \
  --target-port 8100 \
  --ingress internal \
  --min-replicas 3 \
  --max-replicas 10 \
  --env-vars \
    AGENT_REGISTRY_URL=https://agent-registry.eastus.azurecontainerapps.io \
    MCP_ACCOUNT_URL=http://account-mcp:8070
```

---

## Success Metrics

### Performance Targets

| Metric | Target | Measurement |
|--------|--------|-------------|
| A2A Latency (p50) | < 100ms | Application Insights |
| A2A Latency (p95) | < 300ms | Application Insights |
| A2A Latency (p99) | < 500ms | Application Insights |
| A2A Success Rate | > 99.9% | Application Insights |
| Agent Discovery Time | < 50ms | Custom metric |
| Agent Registration Time | < 100ms | Custom metric |
| Circuit Breaker Trips | < 0.1% | Custom metric |

### Operational Metrics

| Metric | Target |
|--------|--------|
| Agent Availability | > 99.95% |
| Registry Availability | > 99.99% |
| Mean Time to Recovery (MTTR) | < 5 minutes |
| Agent Restart Time | < 30 seconds |

---

## Conclusion

This A2A implementation plan provides a comprehensive roadmap for transforming the BankX multi-agent system from in-process method calls to a distributed, scalable agent architecture. The implementation maintains complete backward compatibility with existing MCP tools while adding enterprise-grade features like service discovery, authentication, circuit breaking, and distributed tracing.

### Next Steps

1. ✅ Review and approve this implementation plan
2. ✅ Set up development environment
3. ✅ Begin Phase 1: Foundation (Agent Registry + SDK)
4. ✅ Proceed with Phase 2-4 as outlined

### Questions & Support

For questions or clarifications, contact:
- Architecture Team: architecture@bankx.com
- UC1 Team: uc1-team@bankx.com
- DevOps Team: devops@bankx.com

---

**Document Status:** Ready for Implementation
**Next Review Date:** 2 weeks after Phase 1 completion
