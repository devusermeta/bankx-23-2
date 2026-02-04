# A2A Implementation Summary - BankX Multi-Agent System

**Date**: November 7, 2025
**Status**: Phase 1 Completed - Foundation Layer Ready
**Deployment Target**: Azure Container Apps (NOT Kubernetes)

---

## Executive Summary

Successfully implemented the foundational components for Agent-to-Agent (A2A) communication in the BankX Multi-Agent Banking System. The implementation provides:

✅ **Agent Registry Service** - Centralized service discovery with dual storage (Redis + Cosmos DB)
✅ **A2A SDK** - Python library for agent communication with circuit breaker, retry logic, and distributed tracing
✅ **Azure Container Apps Deployment** - Complete deployment automation for container-based agents
✅ **Agent Card Schemas** - Standardized capability definitions

---

## What Was Implemented

### 1. Agent Registry Service (`app/agent-registry/`)

A FastAPI-based service for agent discovery and lifecycle management.

**Key Components:**
- **Models** (`models/agent_registration.py`): Pydantic models for agent registration, discovery, heartbeat
- **Storage Layer**:
  - `storage/redis_store.py`: Fast lookups with TTL-based caching
  - `storage/cosmos_store.py`: Persistent storage with query support
- **Business Logic**:
  - `services/registry_service.py`: Core registry operations
  - `services/health_service.py`: Automated health checking and stale agent removal
- **REST API** (`api/agents_router.py`):
  - `POST /api/v1/agents/register` - Register new agent
  - `GET /api/v1/agents/discover` - Discover agents by capability
  - `POST /api/v1/agents/{id}/heartbeat` - Heartbeat mechanism
  - `DELETE /api/v1/agents/{id}` - Deregister agent
- **Authentication** (`api/auth.py`): JWT-based agent authentication
- **Configuration** (`config/settings.py`): Environment-based settings
- **FastAPI App** (`main.py`): Main application with lifecycle management
- **Docker Support**: Production-ready Dockerfile with health checks

**Features:**
- Dual storage (Redis + Cosmos DB) for performance + persistence
- Health checking with automatic stale agent removal
- JWT or Azure Entra ID authentication
- Circuit breaker pattern integration
- Metrics endpoint for monitoring
- Auto-scaling support (2-5 replicas)

---

### 2. A2A SDK (`app/a2a-sdk/`)

A Python library that agents use to communicate with each other.

**Key Components:**
- **Models** (`models/messages.py`):
  - `A2AMessage`: Standardized request message
  - `A2AResponse`: Standardized response message
  - `AgentIdentifier`: Agent identity
  - `A2AMetadata`: Trace IDs, timeouts, retry counts
- **Clients**:
  - `client/a2a_client.py`: Main A2A client with retry/circuit breaker
  - `client/registry_client.py`: Registry interaction client
- **Utilities**:
  - `utils/circuit_breaker.py`: Circuit breaker implementation (closed/open/half-open states)
- **Features**:
  - Automatic service discovery via registry
  - Exponential backoff retry logic (configurable attempts)
  - Circuit breaker per target agent (prevents cascading failures)
  - OpenTelemetry distributed tracing support
  - Async/await modern Python API
  - Type-safe with Pydantic models

**Configuration:**
```python
A2AConfig(
    timeout_seconds=30,
    max_retries=3,
    retry_backoff_seconds=2,
    circuit_breaker_threshold=5,
    circuit_breaker_timeout_seconds=60,
    enable_tracing=True
)
```

**Usage Example:**
```python
# Initialize clients
registry = RegistryClient(registry_url="http://agent-registry:9000")
a2a_client = A2AClient(
    agent_id="supervisor-001",
    agent_name="SupervisorAgent",
    registry_client=registry
)

# Call another agent
response = await a2a_client.send_message(
    target_capability="account.balance",
    intent="account.get_balance",
    payload={"customer_id": "CUST-001"}
)
```

---

### 3. Azure Container Apps Deployment (`infrastructure/`)

Complete deployment automation for Azure Container Apps (NOT Kubernetes).

**Scripts:**
- `deploy_container_apps.py`: Python deployment automation
- `container_apps_setup.md`: Comprehensive deployment guide

**What Gets Deployed:**
1. **Azure Container Registry** (ACR): Stores Docker images
2. **Container Apps Environment**: Shared environment for all agents
3. **Agent Registry**: 2-5 replicas, internal ingress, port 9000
4. **Domain Agents**: 2-10 replicas each, internal ingress
   - Account Agent: port 8100
   - Transaction Agent: port 8101
   - Payment Agent: port 8102

**Deployment Command:**
```bash
python infrastructure/deploy_container_apps.py \
  --subscription-id "$SUBSCRIPTION_ID" \
  --resource-group "bankx-agents-rg" \
  --location "eastus" \
  --environment "bankx-agents-env" \
  --registry "bankxagentsacr" \
  --redis-connection "$REDIS_CONNECTION" \
  --cosmos-endpoint "$COSMOS_ENDPOINT" \
  --cosmos-key "$COSMOS_KEY" \
  --openai-endpoint "$OPENAI_ENDPOINT" \
  --openai-key "$OPENAI_KEY"
```

**Networking:**
- All agents use **internal ingress** (private communication only)
- Agent Registry accessible via internal FQDN: `agent-registry.internal.{env}.eastus.azurecontainerapps.io`
- Auto-scaling based on HTTP requests, CPU, memory
- Zero-downtime rolling updates

**No Kubernetes:**
- Uses Azure Container Apps native features
- Managed service (no cluster management)
- Built-in load balancing and auto-scaling
- Simplified deployment (no kubectl, no YAML manifests)

---

### 4. Agent Card Schemas (`docs/agent-cards/`)

Updated agent cards with deployment specifications.

**Example: Account Agent Card**
```json
{
  "agent_name": "AccountAgent",
  "agent_type": "domain",
  "capabilities": [
    {"name": "account.balance", "output_schema": "BALANCE_CARD"},
    {"name": "account.limits", "output_schema": "BALANCE_CARD"},
    {"name": "account.disambiguation", "output_schema": "ACCOUNT_PICKER"}
  ],
  "deployment": {
    "container_image": "bankx/account-agent:1.0.0",
    "port": 8100,
    "min_replicas": 2,
    "max_replicas": 10,
    "cpu": "0.5",
    "memory": "1Gi",
    "env_requirements": ["ACCOUNT_MCP_URL", "AGENT_REGISTRY_URL"]
  }
}
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│          Azure Container Apps Environment                   │
│                                                              │
│  ┌──────────────────┐                                       │
│  │  Agent Registry  │  ← All agents register here          │
│  │  (2-5 replicas)  │                                       │
│  │  Port: 9000      │                                       │
│  └────────┬─────────┘                                       │
│           │                                                  │
│           │ Service Discovery                               │
│           │                                                  │
│    ┌──────┴─────────────┬────────────────┬─────────────┐   │
│    │                    │                │             │   │
│    ▼                    ▼                ▼             ▼   │
│  ┌─────────┐      ┌──────────┐    ┌─────────┐   ┌────────┐│
│  │ Account │      │Transaction│    │ Payment │   │ProdInfo││
│  │  Agent  │      │   Agent   │    │  Agent  │   │  FAQ   ││
│  │ 2-10    │      │   2-10    │    │  2-10   │   │ Agent  ││
│  └────┬────┘      └─────┬─────┘    └────┬────┘   └────┬───┘│
│       │                 │               │             │    │
│       └─────────────────┴───────────────┴─────────────┘    │
│                         │                                   │
└─────────────────────────┼───────────────────────────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │   MCP Services via     │
              │   APIM Gateway         │
              │   (Unchanged)          │
              └────────────────────────┘
```

---

## Key Benefits

### 1. **Scalability**
- Each agent can scale independently (2-10 replicas)
- Auto-scaling based on load
- Agent Registry ensures service discovery at scale

### 2. **Fault Tolerance**
- Circuit breaker prevents cascading failures
- Retry logic handles transient failures
- Health monitoring removes unhealthy agents
- Multi-replica deployment (no single point of failure)

### 3. **Observability**
- Distributed tracing with OpenTelemetry
- Metrics endpoint for Prometheus/Grafana
- Structured logging (JSON format)
- Decision ledger integration (audit trail)

### 4. **Developer Experience**
- Type-safe Python SDK
- Automatic service discovery
- Simple deployment (single command)
- No Kubernetes complexity

### 5. **Production Ready**
- JWT authentication
- Secrets management via Azure Key Vault
- Managed identities for Azure resources
- Zero-downtime deployments

---

## What's Next (Phase 2)

### Immediate Tasks

1. **Create Docker Images for Agents**
   - Build Dockerfile for each agent (Account, Transaction, Payment, etc.)
   - Add A2A server endpoint to each agent
   - Register agents on startup

2. **Refactor Existing Agents**
   - Add A2A SDK dependency
   - Implement A2A server endpoints (`POST /a2a/invoke`)
   - Register with registry on startup
   - Send periodic heartbeats
   - Example refactoring:
     ```python
     class AccountAgent:
         async def startup(self):
             # Register with registry
             await self.registry_client.register(
                 agent_name="AccountAgent",
                 capabilities=["account.balance", "account.limits"],
                 endpoints={
                     "http": "http://localhost:8100",
                     "health": "http://localhost:8100/health",
                     "a2a": "http://localhost:8100/a2a/invoke"
                 }
             )

             # Start heartbeat
             asyncio.create_task(self._heartbeat_loop())

         @app.post("/a2a/invoke")
         async def a2a_invoke(self, message: A2AMessage) -> A2AResponse:
             # Route to appropriate capability handler
             if message.intent == "account.get_balance":
                 result = await self.get_balance(message.payload)

             return A2AResponse(
                 correlation_id=message.message_id,
                 source=message.target,
                 target=message.source,
                 status="success",
                 response=result
             )
     ```

3. **Refactor Supervisor Agent**
   - Replace direct Python method calls with A2A SDK calls
   - Use registry for agent discovery
   - Example:
     ```python
     # OLD: Direct call
     result = await account_agent.get_balance(customer_id)

     # NEW: A2A call
     response = await a2a_client.send_message(
         target_capability="account.balance",
         intent="account.get_balance",
         payload={"customer_id": customer_id}
     )
     result = response.response
     ```

4. **Integration Testing**
   - End-to-end A2A communication tests
   - Load testing (1000+ concurrent requests)
   - Chaos testing (network failures, agent crashes)
   - Circuit breaker validation

5. **Deploy to Azure**
   - Run `deploy_container_apps.py`
   - Validate health endpoints
   - Monitor metrics
   - Test auto-scaling

---

## File Structure

```
app/
├── agent-registry/               # Agent Registry Service
│   ├── models/
│   │   ├── agent_registration.py
│   │   └── __init__.py
│   ├── storage/
│   │   ├── redis_store.py
│   │   ├── cosmos_store.py
│   │   └── __init__.py
│   ├── services/
│   │   ├── registry_service.py
│   │   ├── health_service.py
│   │   └── __init__.py
│   ├── api/
│   │   ├── agents_router.py
│   │   ├── auth.py
│   │   └── __init__.py
│   ├── config/
│   │   ├── settings.py
│   │   └── __init__.py
│   ├── main.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── README.md
│
├── a2a-sdk/                      # A2A Client Library
│   ├── models/
│   │   ├── messages.py
│   │   └── __init__.py
│   ├── client/
│   │   ├── a2a_client.py
│   │   ├── registry_client.py
│   │   └── __init__.py
│   ├── utils/
│   │   ├── circuit_breaker.py
│   │   └── __init__.py
│   ├── __init__.py
│   ├── requirements.txt
│   └── README.md
│
├── copilot/                      # Existing copilot (to be refactored)
└── business-api/                 # Existing MCP services (unchanged)

infrastructure/
├── azure_provision.py            # Provision Azure resources
├── deploy_container_apps.py      # Deploy to Container Apps
├── container_apps_setup.md       # Deployment guide
└── README.md

docs/
├── agent-cards/
│   ├── account-agent-card.json   # Updated with deployment info
│   ├── transaction-agent-card.json
│   └── ...
├── A2A_IMPLEMENTATION_PLAN.md    # Original plan
└── A2A_IMPLEMENTATION_SUMMARY.md # This document
```

---

## Testing the Implementation

### 1. Start Agent Registry Locally

```bash
cd app/agent-registry

# Install dependencies
pip install -r requirements.txt

# Run with in-memory storage (no Redis/Cosmos needed)
export AUTH_ENABLED=false
python main.py
```

Access at: http://localhost:9000

### 2. Register a Test Agent

```bash
curl -X POST http://localhost:9000/api/v1/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "TestAgent",
    "agent_type": "domain",
    "capabilities": ["test.capability"],
    "endpoints": {
      "http": "http://localhost:8200",
      "health": "http://localhost:8200/health",
      "a2a": "http://localhost:8200/a2a/invoke"
    }
  }'
```

### 3. Discover Agents

```bash
curl http://localhost:9000/api/v1/agents/discover?capability=test.capability
```

### 4. Check Metrics

```bash
curl http://localhost:9000/metrics
```

---

## Configuration

### Environment Variables (Agent Registry)

```bash
# Redis (optional - uses in-memory if not available)
REDIS_URL=redis://localhost:6379

# Cosmos DB (optional)
AZURE_COSMOS_ENDPOINT=https://bankx-cosmos.documents.azure.com:443/
AZURE_COSMOS_KEY=your-key
USE_COSMOS=true

# Authentication
AUTH_ENABLED=true
A2A_JWT_SECRET_KEY=your-secret-key

# Health Checks
A2A_HEALTH_CHECK_ENABLED=true
A2A_HEALTH_CHECK_INTERVAL_SECONDS=30

# Logging
LOG_LEVEL=INFO
```

### Environment Variables (Agents)

```bash
# Agent Registry
AGENT_REGISTRY_URL=http://agent-registry:9000

# MCP Services
ACCOUNT_MCP_URL=http://account-mcp:8070
TRANSACTION_MCP_URL=http://transaction-mcp:8071
PAYMENT_MCP_URL=http://payment-mcp:8072

# Azure Services
AZURE_OPENAI_ENDPOINT=https://bankx-openai.openai.azure.com
AZURE_OPENAI_API_KEY=your-key
```

---

## Success Criteria (Phase 1) ✅

- [x] Agent Registry service running and healthy
- [x] A2A SDK library functional with retry/circuit breaker
- [x] Dual storage (Redis + Cosmos DB) working
- [x] Agent registration/discovery endpoints operational
- [x] Health monitoring service functional
- [x] JWT authentication implemented
- [x] Docker images buildable
- [x] Azure Container Apps deployment script ready
- [x] Documentation complete

---

## Next Milestones

### Phase 2: Agent Refactoring (Week 3-4)
- [ ] Add A2A server endpoints to all domain agents
- [ ] Refactor Supervisor Agent to use A2A SDK
- [ ] Integration testing
- [ ] Load testing (1000+ concurrent requests)

### Phase 3: Production Deployment (Week 5-6)
- [ ] Deploy to Azure Container Apps
- [ ] Configure Application Insights
- [ ] Set up monitoring dashboards
- [ ] Performance tuning
- [ ] Production validation

---

## Support & Contact

- **Architecture Team**: architecture@bankx.com
- **DevOps Team**: devops@bankx.com
- **Documentation**: See `/docs/` folder
- **Issues**: GitHub Issues

---

**Status**: ✅ Phase 1 Complete - Ready for Phase 2 (Agent Refactoring)
