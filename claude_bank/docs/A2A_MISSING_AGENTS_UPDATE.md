# A2A Implementation - Missing Agents Update

**Date:** November 7, 2025
**Author:** BankX Development Team
**Status:** Completed
**Related:** A2A_IMPLEMENTATION_PLAN.md

---

## Executive Summary

This document summarizes the updates made to the A2A Implementation Plan to include the **EscalationComms Agent** and the expanded **AIMoneyCoach Agent** specifications that were previously missing or incomplete.

### What Was Missing

1. **EscalationCommsAgent**: No agent card specification existed in the A2A Implementation Plan
2. **AIMoneyCoachAgent**: Card existed but was incomplete (missing detailed capabilities, endpoints, and full specifications)
3. **Architecture Diagram**: Did not show EscalationComms and AIMoneyCoach agents
4. **Supervisor Dependencies**: Did not list EscalationComms agent
5. **Port Assignments**: Not clearly documented for new agents

---

## Changes Made

### 1. Added EscalationComms Agent Card Specification

**Location:** `/docs/A2A_IMPLEMENTATION_PLAN.md` (Section 5)

**New Agent Card Includes:**
- **Agent Type:** communication
- **Version:** 1.0.0
- **A2A Port:** 8105
- **MCP Port:** 8076

**Capabilities:**
- `email.send_customer_notification` - Send ticket confirmation to customer
- `email.send_employee_notification` - Send ticket notification to bank employee
- `email.send_dual_notification` - Send to both customer and employee

**MCP Tools:**
- `EscalationComms.sendEmail` - Azure Communication Services integration

**Dependencies:**
- Azure Communication Services
- APIM Gateway
- No agent dependencies (terminal agent)

**Use Cases:** UC2 (Product Info FAQ), UC3 (AI Money Coach)

---

### 2. Expanded AIMoneyCoach Agent Card Specification

**Location:** `/docs/A2A_IMPLEMENTATION_PLAN.md` (Section 6)

**Enhanced Specifications:**
- **A2A Port:** 8106
- **MCP Port:** 8075

**New Capabilities Added:**
- `coaching.debt_management` - Debt management coaching
- `coaching.financial_health` - Financial health assessment (Ordinary vs Critical Patient)
- `coaching.clarification` - Clarification-first approach
- `coaching.emergency_plan` - Strong Medicine Plan for critical situations
- `ticket.create_escalation` - Escalation ticket creation

**MCP Tools:**
- `AIMoneyCoach.ai_search_rag_results` - Azure AI Search for RAG
- `AIMoneyCoach.ai_foundry_content_understanding` - AI Foundry validation
- `AIMoneyCoach.createTicket` - Support ticket creation

**Dependencies:**
- EscalationCommsAgent (for ticket escalation)
- Azure AI Search
- Azure AI Foundry
- APIM Gateway

**Knowledge Base:** "Debt-Free to Financial Freedom" (12 chapters)

---

### 3. Updated Supervisor Agent Dependencies

**Location:** `/docs/A2A_IMPLEMENTATION_PLAN.md` (Section 1)

**Added to Supervisor Agent Card:**
```json
"dependencies": {
  "other_agents": [
    "AccountAgent",
    "TransactionAgent",
    "PaymentAgent",
    "ProdInfoFAQAgent",
    "AIMoneyCoachAgent",
    "EscalationCommsAgent"  // <-- ADDED
  ]
}
```

**New Capabilities:**
- `intent.classify` - Intent classification with expanded context
- `response.aggregate` - Multi-agent response aggregation
- `conversation.orchestrate` - Multi-turn conversation orchestration

**Supervisor A2A Port:** 8099

---

### 4. Updated Architecture Diagram

**Location:** `/docs/A2A_IMPLEMENTATION_PLAN.md` (Target A2A Architecture)

**Changes:**
- Added EscalationComms Agent Service (Port 8105)
- Added AI Money Coach Agent Service (Port 8106)
- Updated MCP port listing to include:
  - AIMoneyCoach MCP: 8075
  - Escalation MCP: 8076

**Complete Agent Topology:**
```
SupervisorAgent (8099)
├── AccountAgent (8100) → Account MCP (8070)
├── TransactionAgent (8101) → Transaction MCP (8071)
├── PaymentAgent (8102) → Payment MCP (8072)
├── ProdInfoFAQAgent (8104) → ProdInfoFAQ MCP (8074) → EscalationComms
├── EscalationCommsAgent (8105) → EscalationComms MCP (8076)
└── AIMoneyCoachAgent (8106) → AIMoneyCoach MCP (8075) → EscalationComms
```

---

### 5. Created JSON Agent Card Files

**Location:** `/config/agent-cards/`

**New Files Created:**
1. `escalation-comms-agent.json` - Full EscalationComms agent card
2. `ai-money-coach-agent.json` - Complete AIMoneyCoach agent card
3. `prodinfo-faq-agent.json` - Updated ProdInfoFAQ agent card
4. `README.md` - Agent cards documentation with port assignments

**Agent Cards Include:**
- Standardized JSON schema for all agents
- Agent IDs, versions, descriptions
- Capabilities with input/output schemas
- MCP tool endpoints
- A2A communication endpoints
- Performance characteristics
- Dependencies and metadata
- Tags for use case categorization

---

### 6. Updated ProdInfoFAQ Agent Card

**Location:** `/docs/A2A_IMPLEMENTATION_PLAN.md` (Section 4)

**Enhanced with:**
- Complete capability specifications
- Input/output schemas
- A2A endpoint configuration (Port 8104)
- Dependency on EscalationCommsAgent
- Performance SLAs

---

## Port Assignment Reference

### A2A Agent Ports (HTTP/JSON Communication)

| Agent | Port | Type | Use Case |
|-------|------|------|----------|
| SupervisorAgent | 8099 | Orchestration | All |
| AccountAgent | 8100 | Domain | UC1 |
| TransactionAgent | 8101 | Domain | UC1 |
| PaymentAgent | 8102 | Domain | UC1 |
| ProdInfoFAQAgent | 8104 | Knowledge | UC2 |
| EscalationCommsAgent | 8105 | Communication | UC2, UC3 |
| AIMoneyCoachAgent | 8106 | Knowledge | UC3 |

### MCP Tool Ports (Backend Services)

| MCP Server | Port | Agent Consumer |
|------------|------|----------------|
| Account MCP | 8070 | AccountAgent |
| Transaction MCP | 8071 | TransactionAgent |
| Payment MCP | 8072 | PaymentAgent |
| Limits MCP | 8073 | PaymentAgent |
| ProdInfoFAQ MCP | 8074 | ProdInfoFAQAgent |
| AIMoneyCoach MCP | 8075 | AIMoneyCoachAgent |
| EscalationComms MCP | 8076 | EscalationCommsAgent |

### Infrastructure Ports

| Service | Port | Purpose |
|---------|------|---------|
| Agent Registry | 9000 | Service discovery, health checks |

---

## Agent Dependency Graph

```
┌─────────────────────────────────────────────────────────────┐
│                    SupervisorAgent                          │
│                    (Port: 8099)                             │
└──────┬────────┬──────────┬──────────┬──────────┬───────────┘
       │        │          │          │          │
       ▼        ▼          ▼          ▼          ▼
   ┌────────┐ ┌──────┐  ┌──────┐  ┌──────┐  ┌─────────┐
   │Account │ │Trans │  │Payment│ │ProdFAQ│ │AI Coach │
   │  8100  │ │ 8101 │  │ 8102  │ │ 8104  │ │  8106   │
   └────────┘ └──────┘  └───┬───┘ └───┬───┘ └────┬────┘
                            │         │          │
                            │         │          │
                            │    ┌────▼──────────▼────┐
                            │    │ EscalationComms    │
                            │    │    (Port: 8105)    │
                            │    └────────────────────┘
                            │
                         Uses AccountAgent
```

**Key Dependencies:**
- **PaymentAgent** depends on **AccountAgent** (for account validation)
- **ProdInfoFAQAgent** depends on **EscalationCommsAgent** (for ticket escalation)
- **AIMoneyCoachAgent** depends on **EscalationCommsAgent** (for ticket escalation)

---

## Files Modified

1. **`/docs/A2A_IMPLEMENTATION_PLAN.md`**
   - Added EscalationComms agent card (Section 5)
   - Expanded AIMoneyCoach agent card (Section 6)
   - Updated Supervisor agent card (Section 1)
   - Updated ProdInfoFAQ agent card (Section 4)
   - Updated architecture diagram
   - Updated MCP port listings

2. **`/config/agent-cards/escalation-comms-agent.json`** (NEW)
   - Complete JSON agent card specification

3. **`/config/agent-cards/ai-money-coach-agent.json`** (NEW)
   - Complete JSON agent card specification

4. **`/config/agent-cards/prodinfo-faq-agent.json`** (NEW)
   - Complete JSON agent card specification

5. **`/config/agent-cards/README.md`** (NEW)
   - Agent cards documentation
   - Port assignment reference
   - Usage guidelines

---

## Integration Points

### UC2: Product Info & FAQ
```
User Query
    ↓
SupervisorAgent (8099)
    ↓ [A2A]
ProdInfoFAQAgent (8104)
    ↓ [MCP]
ProdInfoFAQ MCP Server (8074)
    ↓ [Azure AI Search RAG]
Knowledge Base

If Answer Not Found:
    ↓
ProdInfoFAQAgent creates ticket
    ↓ [A2A]
EscalationCommsAgent (8105)
    ↓ [MCP]
EscalationComms MCP (8076)
    ↓ [Azure Communication Services]
Email sent to customer + support team
```

### UC3: AI Money Coach
```
User Query
    ↓
SupervisorAgent (8099)
    ↓ [A2A]
AIMoneyCoachAgent (8106)
    ↓ [MCP]
AIMoneyCoach MCP Server (8075)
    ↓ [Azure AI Search + AI Foundry]
"Debt-Free to Financial Freedom" Knowledge Base
    ↓ [100% Grounding Validation]
Validated Financial Advice

If Escalation Needed:
    ↓ [A2A]
EscalationCommsAgent (8105)
    ↓ [Email Notification]
Support Team
```

---

## Next Steps

### Phase 1: Implementation (Completed)
- ✅ Document EscalationComms agent card specification
- ✅ Complete AIMoneyCoach agent card specification
- ✅ Update architecture diagrams
- ✅ Create JSON agent card files
- ✅ Update port assignments

### Phase 2: Development (Pending)
- ⬜ Implement Agent Registry Service (Port 9000)
- ⬜ Implement A2A Client SDK
- ⬜ Add A2A server endpoints to existing agents
- ⬜ Implement EscalationCommsAgent A2A integration
- ⬜ Implement AIMoneyCoachAgent A2A integration
- ⬜ Add agent registration logic on startup

### Phase 3: Testing (Pending)
- ⬜ Unit tests for agent cards
- ⬜ Integration tests for A2A communication
- ⬜ End-to-end tests for UC2 with EscalationComms
- ⬜ End-to-end tests for UC3 with EscalationComms
- ⬜ Load testing for agent mesh

### Phase 4: Deployment (Pending)
- ⬜ Deploy Agent Registry to Azure Container Apps
- ⬜ Deploy agents with A2A endpoints
- ⬜ Configure networking and service discovery
- ⬜ Set up monitoring and alerting

---

## Validation Checklist

- ✅ EscalationComms agent card complete and documented
- ✅ AIMoneyCoach agent card complete and documented
- ✅ Supervisor agent dependencies updated
- ✅ Architecture diagram includes all agents
- ✅ Port assignments documented and conflict-free
- ✅ Agent dependency graph updated
- ✅ JSON agent card files created
- ✅ Integration flows documented
- ✅ MCP tool endpoints mapped correctly
- ✅ Use case coverage verified (UC1, UC2, UC3)

---

## References

- **Main Document:** `/docs/A2A_IMPLEMENTATION_PLAN.md`
- **Agent Cards:** `/config/agent-cards/`
- **Environment Config:** `/envsample.env`
- **Infrastructure:** `/infrastructure/azure_provision.py`
- **Agent Implementations:**
  - `/app/copilot/app/agents/azure_chat/escalation_comms_agent.py`
  - `/app/copilot/app/agents/azure_chat/ai_money_coach_agent.py`
  - `/app/copilot/app/agents/azure_chat/prodinfo_faq_agent.py`

---

## Summary

The A2A Implementation Plan is now **complete** with full specifications for:

1. **EscalationCommsAgent** - Email notification service for UC2 and UC3
2. **AIMoneyCoachAgent** - AI-powered financial coaching for UC3
3. **Complete agent topology** - All 6 domain agents + 1 supervisor
4. **Port assignments** - A2A ports (8099-8106) and MCP ports (8070-8076)
5. **Agent cards** - Standardized JSON specifications for service discovery

This update ensures that **all agents required for UC1, UC2, and UC3** are fully documented and ready for A2A implementation.

---

**Status:** ✅ Documentation Complete
**Next:** Begin Phase 2 - A2A Infrastructure Development
