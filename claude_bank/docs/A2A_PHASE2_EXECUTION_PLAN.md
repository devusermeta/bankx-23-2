# A2A Phase 2 Execution Plan - Complete Implementation

**Status**: AWAITING APPROVAL
**Date**: November 7, 2025
**Estimated Time**: 4-6 hours of implementation
**Priority**: HIGH - Missing critical Azure SDKs and Application Insights

---

## 🚨 CRITICAL GAPS IDENTIFIED

### Missing Azure SDKs
```python
# Currently MISSING from all requirements.txt files:
azure-search-documents==11.5.0      # For AI Search (UC2, UC3)
azure-cosmos==4.5.1                 # For Cosmos DB (Decision Ledger, Agent Registry)
azure-monitor-opentelemetry==1.2.0  # For Application Insights
azure-purview-account==1.0.0        # For data governance (optional but planned)

# Missing OpenTelemetry packages:
opentelemetry-api==1.24.0                      # Core API
opentelemetry-sdk==1.24.0                      # Core SDK
opentelemetry-exporter-azure-monitor==1.0.0b15 # App Insights exporter
opentelemetry-instrumentation-fastapi          # Auto-instrument FastAPI
opentelemetry-instrumentation-httpx            # Auto-instrument HTTP calls
opentelemetry-instrumentation-redis            # Auto-instrument Redis
```

### Missing Application Insights Integration
- No Application Insights connection string in environment
- No OpenTelemetry configuration in agents
- No distributed tracing across A2A calls
- No custom metrics collection
- No error tracking

### Missing A2A Implementation in Agents
- Agents don't have A2A server endpoints
- Agents don't register with registry
- Supervisor still uses direct Python calls
- No Docker images for agents

---

## 📋 EXECUTION PLAN - 5 PHASES

### **PHASE 2A: Dependencies & Observability Setup** ⏱️ 30 minutes

**Objectives:**
1. Add all missing Azure SDK dependencies
2. Configure Application Insights integration
3. Set up OpenTelemetry instrumentation
4. Update environment configuration

**Tasks:**
- [ ] Update root `requirements.txt` with all Azure SDKs
- [ ] Update agent-registry `requirements.txt`
- [ ] Update a2a-sdk `requirements.txt`
- [ ] Create `app/common/observability/` module
  - [ ] `app_insights.py` - Application Insights setup
  - [ ] `telemetry.py` - OpenTelemetry configuration
  - [ ] `logging_config.py` - Structured logging
  - [ ] `metrics.py` - Custom metrics
- [ ] Update `envsample.env` with Application Insights variables
- [ ] Create observability documentation

**Deliverables:**
```
requirements.txt (updated)
app/agent-registry/requirements.txt (updated)
app/a2a-sdk/requirements.txt (updated)
app/common/observability/__init__.py
app/common/observability/app_insights.py
app/common/observability/telemetry.py
app/common/observability/logging_config.py
app/common/observability/metrics.py
envsample.env (updated with APPLICATIONINSIGHTS_CONNECTION_STRING)
docs/observability_setup.md
```

---

### **PHASE 2B: Agent A2A Server Implementation** ⏱️ 2 hours

**Objectives:**
1. Add A2A server endpoints to all agents
2. Implement agent registration on startup
3. Add heartbeat mechanism
4. Integrate Application Insights

**Tasks:**

#### For Each Agent (Account, Transaction, Payment, ProdInfoFAQ, AIMoneyCoach):

- [ ] Create `app/agents/{agent_name}/`
  - [ ] `main.py` - FastAPI app with A2A endpoint
  - [ ] `a2a_handler.py` - A2A message handler
  - [ ] `config.py` - Agent configuration
  - [ ] `Dockerfile` - Container image
  - [ ] `requirements.txt` - Dependencies

- [ ] Implement A2A Server Endpoint:
  ```python
  @app.post("/a2a/invoke")
  async def a2a_invoke(message: A2AMessage) -> A2AResponse:
      # Route to capability handler
      # Track with Application Insights
      # Return standardized response
  ```

- [ ] Implement Startup Registration:
  ```python
  @app.on_event("startup")
  async def startup():
      # Register with Agent Registry
      # Start heartbeat task
      # Initialize Application Insights
  ```

- [ ] Add Health Endpoint:
  ```python
  @app.get("/health")
  async def health():
      # Check MCP service connectivity
      # Check registry connectivity
      # Return health status
  ```

- [ ] Add Metrics Endpoint:
  ```python
  @app.get("/metrics")
  async def metrics():
      # Return Prometheus metrics
      # A2A call count, latency, errors
  ```

**Agent-Specific Implementation:**

1. **Account Agent** (Port 8100)
   - Capabilities: account.balance, account.limits, account.disambiguation
   - MCP Dependencies: Account MCP (8070), Limits MCP (8073)

2. **Transaction Agent** (Port 8101)
   - Capabilities: transaction.history, transaction.aggregation
   - MCP Dependencies: Transaction MCP (8071)

3. **Payment Agent** (Port 8102)
   - Capabilities: payment.transfer, payment.validate
   - MCP Dependencies: Payment MCP (8072), Limits MCP (8073)

4. **ProdInfoFAQ Agent** (Port 8103)
   - Capabilities: product.info, faq.answer, ticket.create
   - MCP Dependencies: ProdInfoFAQ MCP (8074)
   - Azure Dependencies: AI Search

5. **AIMoneyCoach Agent** (Port 8104)
   - Capabilities: coaching.debt_management, coaching.financial_health
   - MCP Dependencies: AIMoneyCoach MCP (8075)
   - Azure Dependencies: AI Search

**Deliverables:**
```
app/agents/account-agent/
├── main.py
├── a2a_handler.py
├── config.py
├── Dockerfile
└── requirements.txt

app/agents/transaction-agent/
├── main.py
├── a2a_handler.py
├── config.py
├── Dockerfile
└── requirements.txt

app/agents/payment-agent/
├── main.py
├── a2a_handler.py
├── config.py
├── Dockerfile
└── requirements.txt

app/agents/prodinfo-faq-agent/
├── main.py
├── a2a_handler.py
├── config.py
├── Dockerfile
└── requirements.txt

app/agents/ai-money-coach-agent/
├── main.py
├── a2a_handler.py
├── config.py
├── Dockerfile
└── requirements.txt
```

---

### **PHASE 2C: Supervisor Agent Refactoring** ⏱️ 1 hour

**Objectives:**
1. Refactor Supervisor to use A2A SDK
2. Replace direct Python calls with A2A messages
3. Add distributed tracing
4. Integrate Application Insights

**Tasks:**
- [ ] Update `app/copilot/app/agents/azure_chat/supervisor_agent.py`
  - [ ] Initialize A2A client
  - [ ] Initialize Registry client
  - [ ] Replace direct agent calls with A2A calls
  - [ ] Add distributed tracing
  - [ ] Add error handling with circuit breaker

- [ ] Update `app/copilot/app/agents/foundry/supervisor_agent_foundry.py`
  - [ ] Same as above for Foundry version

**Code Changes Example:**

```python
# BEFORE (Direct call)
class SupervisorAgent:
    def __init__(self):
        self.account_agent = AccountAgent()
        self.transaction_agent = TransactionAgent()

    async def route_request(self, intent: str, payload: dict):
        if intent == "check_balance":
            return await self.account_agent.get_balance(payload)

# AFTER (A2A call)
class SupervisorAgent:
    def __init__(self):
        self.registry_client = RegistryClient(registry_url=AGENT_REGISTRY_URL)
        self.a2a_client = A2AClient(
            agent_id="supervisor-001",
            agent_name="SupervisorAgent",
            registry_client=self.registry_client,
            config=A2AConfig(enable_tracing=True)
        )

    async def route_request(self, intent: str, payload: dict):
        if intent == "check_balance":
            response = await self.a2a_client.send_message(
                target_capability="account.balance",
                intent="account.get_balance",
                payload=payload
            )
            return response.response
```

**Deliverables:**
```
app/copilot/app/agents/azure_chat/supervisor_agent.py (refactored)
app/copilot/app/agents/foundry/supervisor_agent_foundry.py (refactored)
app/copilot/app/config/a2a_config.py (new)
```

---

### **PHASE 2D: Docker Containerization** ⏱️ 1 hour

**Objectives:**
1. Create optimized Docker images for all agents
2. Add health checks
3. Configure multi-stage builds
4. Test images locally

**Tasks:**
- [ ] Create standardized Dockerfile template
- [ ] Implement Dockerfiles for all 5 agents
- [ ] Add .dockerignore files
- [ ] Create docker-compose.yml for local testing
- [ ] Build and test all images locally

**Dockerfile Template:**
```dockerfile
# Multi-stage build for {AgentName}
FROM python:3.11-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

ENV PATH=/root/.local/bin:$PATH

# Expose port
EXPOSE {PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:{PORT}/health').raise_for_status()" || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{PORT}"]
```

**Local Testing Setup:**
```yaml
# docker-compose.yml
version: '3.8'

services:
  agent-registry:
    build: ./app/agent-registry
    ports:
      - "9000:9000"
    environment:
      - AUTH_ENABLED=false

  account-agent:
    build: ./app/agents/account-agent
    ports:
      - "8100:8100"
    environment:
      - AGENT_REGISTRY_URL=http://agent-registry:9000
    depends_on:
      - agent-registry

  # ... other agents
```

**Deliverables:**
```
app/agents/account-agent/Dockerfile
app/agents/account-agent/.dockerignore
app/agents/transaction-agent/Dockerfile
app/agents/transaction-agent/.dockerignore
app/agents/payment-agent/Dockerfile
app/agents/payment-agent/.dockerignore
app/agents/prodinfo-faq-agent/Dockerfile
app/agents/prodinfo-faq-agent/.dockerignore
app/agents/ai-money-coach-agent/Dockerfile
app/agents/ai-money-coach-agent/.dockerignore
docker-compose.yml (local testing)
docker-compose.prod.yml (production reference)
```

---

### **PHASE 2E: Testing & Validation** ⏱️ 1.5 hours

**Objectives:**
1. Integration testing of A2A communication
2. Application Insights validation
3. Load testing
4. End-to-end testing

**Tasks:**

#### 1. Unit Tests
- [ ] Test Agent Registry endpoints
- [ ] Test A2A SDK client
- [ ] Test Circuit Breaker logic
- [ ] Test Agent A2A handlers

#### 2. Integration Tests
- [ ] Test Supervisor → Account Agent flow
- [ ] Test Supervisor → Transaction Agent flow
- [ ] Test Supervisor → Payment Agent flow
- [ ] Test agent registration on startup
- [ ] Test heartbeat mechanism
- [ ] Test service discovery

#### 3. Application Insights Validation
- [ ] Verify traces appear in App Insights
- [ ] Verify custom metrics are collected
- [ ] Verify errors are tracked
- [ ] Verify distributed tracing works end-to-end
- [ ] Test dependency tracking (A2A calls)

#### 4. Load Testing
- [ ] 100 concurrent requests
- [ ] 1000 concurrent requests
- [ ] Circuit breaker triggering test
- [ ] Auto-scaling validation

#### 5. End-to-End Testing
- [ ] User request → Supervisor → Domain Agent → MCP → Response
- [ ] Multi-agent orchestration (e.g., payment requires account check)
- [ ] Error scenarios (agent down, timeout, etc.)

**Test Scripts:**
```python
# tests/integration/test_a2a_flow.py
import pytest
from a2a_sdk import A2AClient, RegistryClient

@pytest.mark.asyncio
async def test_supervisor_to_account_agent():
    """Test Supervisor can call Account Agent via A2A."""
    registry = RegistryClient(registry_url="http://localhost:9000")
    a2a_client = A2AClient(
        agent_id="test-supervisor",
        agent_name="TestSupervisor",
        registry_client=registry
    )

    response = await a2a_client.send_message(
        target_capability="account.balance",
        intent="account.get_balance",
        payload={"customer_id": "CUST-001"}
    )

    assert response.status == "success"
    assert "balance" in response.response
```

**Deliverables:**
```
tests/integration/test_a2a_flow.py
tests/integration/test_agent_registration.py
tests/integration/test_app_insights.py
tests/load/locustfile.py
tests/e2e/test_complete_flow.py
docs/testing_guide.md
```

---

### **PHASE 2F: Deployment & Documentation** ⏱️ 30 minutes

**Objectives:**
1. Update deployment scripts
2. Create comprehensive documentation
3. Update README files
4. Create runbooks

**Tasks:**
- [ ] Update `infrastructure/deploy_container_apps.py`
  - [ ] Add Application Insights configuration
  - [ ] Add all 5 agent deployments
  - [ ] Add environment variable injection

- [ ] Create deployment documentation
  - [ ] Local development setup
  - [ ] Azure deployment guide
  - [ ] Troubleshooting guide
  - [ ] Monitoring guide

- [ ] Update README files
  - [ ] Root README.md
  - [ ] Agent-specific READMEs
  - [ ] Infrastructure README

**Deliverables:**
```
infrastructure/deploy_container_apps.py (updated)
docs/deployment/local_setup.md
docs/deployment/azure_deployment.md
docs/deployment/troubleshooting.md
docs/monitoring/app_insights_setup.md
docs/monitoring/metrics_guide.md
README.md (updated)
```

---

## 📦 COMPLETE FILE STRUCTURE (After Phase 2)

```
app/
├── agent-registry/                   # ✅ Done (Phase 1)
│   ├── models/
│   ├── storage/
│   ├── services/
│   ├── api/
│   ├── config/
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt (✨ UPDATED)
│
├── a2a-sdk/                          # ✅ Done (Phase 1)
│   ├── models/
│   ├── client/
│   ├── utils/
│   ├── __init__.py
│   └── requirements.txt (✨ UPDATED)
│
├── common/                           # ✨ NEW
│   └── observability/
│       ├── __init__.py
│       ├── app_insights.py
│       ├── telemetry.py
│       ├── logging_config.py
│       └── metrics.py
│
├── agents/                           # ✨ NEW
│   ├── account-agent/
│   │   ├── main.py
│   │   ├── a2a_handler.py
│   │   ├── config.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── transaction-agent/
│   │   ├── main.py
│   │   ├── a2a_handler.py
│   │   ├── config.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── payment-agent/
│   │   ├── main.py
│   │   ├── a2a_handler.py
│   │   ├── config.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── prodinfo-faq-agent/
│   │   ├── main.py
│   │   ├── a2a_handler.py
│   │   ├── config.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── ai-money-coach-agent/
│       ├── main.py
│       ├── a2a_handler.py
│       ├── config.py
│       ├── Dockerfile
│       └── requirements.txt
│
├── copilot/                          # ✨ REFACTORED
│   └── app/
│       ├── agents/
│       │   ├── azure_chat/
│       │   │   └── supervisor_agent.py (✨ REFACTORED)
│       │   └── foundry/
│       │       └── supervisor_agent_foundry.py (✨ REFACTORED)
│       └── config/
│           └── a2a_config.py (✨ NEW)
│
└── business-api/                     # ✅ Unchanged (MCP services)

infrastructure/
├── azure_provision.py                # ✅ Done
├── deploy_container_apps.py          # ✨ UPDATED
├── container_apps_setup.md           # ✅ Done
└── README.md                         # ✨ UPDATED

tests/                                # ✨ NEW
├── integration/
│   ├── test_a2a_flow.py
│   ├── test_agent_registration.py
│   └── test_app_insights.py
├── load/
│   └── locustfile.py
└── e2e/
    └── test_complete_flow.py

docs/
├── A2A_IMPLEMENTATION_PLAN.md        # ✅ Done
├── A2A_IMPLEMENTATION_SUMMARY.md     # ✅ Done
├── A2A_PHASE2_EXECUTION_PLAN.md      # ✅ This document
├── deployment/                       # ✨ NEW
│   ├── local_setup.md
│   ├── azure_deployment.md
│   └── troubleshooting.md
├── monitoring/                       # ✨ NEW
│   ├── app_insights_setup.md
│   └── metrics_guide.md
└── testing_guide.md                  # ✨ NEW

docker-compose.yml                    # ✨ NEW (local testing)
requirements.txt                      # ✨ UPDATED
envsample.env                         # ✨ UPDATED
```

---

## 🎯 SUCCESS CRITERIA

### Phase 2A: Dependencies & Observability
- [ ] All Azure SDKs added to requirements files
- [ ] Application Insights module created and tested
- [ ] OpenTelemetry configuration working
- [ ] Traces visible in Application Insights portal

### Phase 2B: Agent A2A Server
- [ ] All 5 agents have A2A endpoints
- [ ] Agents register on startup
- [ ] Heartbeat mechanism working
- [ ] Health endpoints returning 200 OK
- [ ] Metrics endpoints exposing data

### Phase 2C: Supervisor Refactoring
- [ ] Supervisor uses A2A SDK
- [ ] No direct Python calls to domain agents
- [ ] Distributed tracing end-to-end
- [ ] Error handling with circuit breaker

### Phase 2D: Docker Containerization
- [ ] All agent Docker images build successfully
- [ ] Health checks pass
- [ ] docker-compose.yml works locally
- [ ] Images optimized (multi-stage build)

### Phase 2E: Testing & Validation
- [ ] All unit tests pass
- [ ] Integration tests pass (A2A communication)
- [ ] Load test handles 1000 concurrent requests
- [ ] Application Insights shows all traces/metrics
- [ ] Circuit breaker triggers correctly under failure

### Phase 2F: Deployment & Documentation
- [ ] Deployment script updated
- [ ] Documentation complete
- [ ] README files updated
- [ ] Runbooks created

---

## ⚠️ RISKS & MITIGATIONS

### Risk 1: OpenTelemetry Version Conflicts
**Mitigation**: Pin exact versions, test locally first

### Risk 2: Application Insights Configuration Complexity
**Mitigation**: Create reusable configuration module, thorough documentation

### Risk 3: Agent Refactoring Breaking Changes
**Mitigation**: Maintain backward compatibility, feature flags for A2A vs direct calls

### Risk 4: Docker Image Size
**Mitigation**: Multi-stage builds, minimal base images, .dockerignore

### Risk 5: Testing Takes Longer Than Estimated
**Mitigation**: Automated tests, parallel execution, prioritize critical paths

---

## 📅 TIMELINE ESTIMATE

| Phase | Duration | Cumulative |
|-------|----------|------------|
| 2A: Dependencies & Observability | 30 min | 30 min |
| 2B: Agent A2A Server (5 agents) | 2 hours | 2.5 hours |
| 2C: Supervisor Refactoring | 1 hour | 3.5 hours |
| 2D: Docker Containerization | 1 hour | 4.5 hours |
| 2E: Testing & Validation | 1.5 hours | 6 hours |
| 2F: Deployment & Documentation | 30 min | 6.5 hours |

**Total Estimated Time**: 6-7 hours

---

## 🚀 DEPLOYMENT READINESS CHECKLIST

Before deploying to Azure Container Apps:

- [ ] All dependencies installed
- [ ] Application Insights connection string configured
- [ ] All agents have Docker images
- [ ] All agents register successfully with registry
- [ ] Supervisor can discover and call all agents
- [ ] Distributed tracing works end-to-end
- [ ] Health checks pass for all services
- [ ] Load testing completed (1000+ concurrent requests)
- [ ] Documentation complete
- [ ] Runbooks created

---

## 💰 COST ESTIMATE (Azure Container Apps)

**Development Environment** (per month):
- Agent Registry: 2 replicas × 0.5 vCPU × 1GB = ~$15
- Account Agent: 2 replicas × 0.5 vCPU × 1GB = ~$15
- Transaction Agent: 2 replicas × 0.5 vCPU × 1GB = ~$15
- Payment Agent: 2 replicas × 0.5 vCPU × 1GB = ~$15
- ProdInfo Agent: 2 replicas × 0.5 vCPU × 1GB = ~$15
- AIMoneyCoach Agent: 2 replicas × 0.5 vCPU × 1GB = ~$15
- Application Insights: ~$10-20
- Redis Cache: ~$20
- Cosmos DB (Serverless): ~$10-30

**Total Dev Environment**: ~$120-150/month

**Production Environment** (with max replicas):
- Multiply by 3-5x depending on load
- Est. ~$400-750/month

---

## ❓ APPROVAL REQUIRED

**Please review this plan and confirm:**

1. ✅ Approve proceeding with all phases?
2. ✅ Approve adding all Azure SDK dependencies?
3. ✅ Approve Application Insights integration (mandatory)?
4. ✅ Approve creating new agent services (5 agents)?
5. ✅ Approve Docker containerization?
6. ✅ Any specific requirements or changes needed?

**Once approved, I will execute this plan phase by phase with commits after each phase.**

---

**Status**: ⏸️ AWAITING YOUR APPROVAL TO PROCEED
