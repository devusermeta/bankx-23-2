# BankX Agent Cards

This directory contains the JSON agent card definitions for all agents in the BankX Multi-Agent Banking System.

## Overview

Agent cards are standardized JSON files that describe each agent's:
- Capabilities and operations
- MCP tool dependencies
- A2A communication endpoints
- Performance characteristics
- Dependencies on other agents
- Output formats

## Agent Card Files

### Core Agents (UC1)
- `account-agent.json` - Account resolution and balance inquiries (Port: 8100)
- `transaction-agent.json` - Transaction history and aggregations (Port: 8101)
- `payment-agent.json` - Payment processing and transfers (Port: 8102)

### Knowledge Agents (UC2/UC3)
- `prodinfo-faq-agent.json` - Product information and FAQ handling (Port: 8104)
- `ai-money-coach-agent.json` - AI-powered financial coaching (Port: 8106)

### Communication Agents
- `escalation-comms-agent.json` - Email notifications via Azure Communication Services (Port: 8105)

### Orchestration
- `supervisor-agent.json` - Intent classification and routing (Port: 8099)

## Agent-to-Agent (A2A) Architecture

All agents communicate via the A2A protocol:
- **Protocol**: HTTP/JSON
- **Registry**: Port 9000
- **Authentication**: JWT or Azure Entra ID
- **Features**: Service discovery, health checks, circuit breaker, retry logic

## Port Assignments

### A2A Agent Ports
| Agent | Port | Type |
|-------|------|------|
| Supervisor | 8099 | Orchestration |
| Account | 8100 | Domain |
| Transaction | 8101 | Domain |
| Payment | 8102 | Domain |
| ProdInfoFAQ | 8104 | Knowledge |
| EscalationComms | 8105 | Communication |
| AIMoneyCoach | 8106 | Knowledge |

### MCP Tool Ports
| MCP Server | Port | Use Case |
|------------|------|----------|
| Account MCP | 8070 | UC1 |
| Transaction MCP | 8071 | UC1 |
| Payment MCP | 8072 | UC1 |
| Limits MCP | 8073 | UC1 |
| ProdInfoFAQ MCP | 8074 | UC2 |
| AIMoneyCoach MCP | 8075 | UC3 |
| EscalationComms MCP | 8076 | UC2/UC3 |

### Infrastructure Ports
| Service | Port | Purpose |
|---------|------|---------|
| Agent Registry | 9000 | Service discovery |

## Usage

These agent cards are used for:

1. **Agent Registration**: Agents register with the Agent Registry on startup
2. **Service Discovery**: Supervisor discovers available agents and their capabilities
3. **API Documentation**: Reference for agent capabilities and schemas
4. **Monitoring**: Performance SLAs and health check endpoints
5. **Development**: Understanding agent dependencies and integration points

## Integration with A2A Implementation Plan

These cards implement the specifications defined in:
- `/docs/A2A_IMPLEMENTATION_PLAN.md`

## Dependencies

### Agent Dependency Graph

```
SupervisorAgent
├── AccountAgent
├── TransactionAgent
├── PaymentAgent (depends on AccountAgent)
├── ProdInfoFAQAgent (depends on EscalationCommsAgent)
├── AIMoneyCoachAgent (depends on EscalationCommsAgent)
└── EscalationCommsAgent
```

## Related Documentation

- [A2A Implementation Plan](/docs/A2A_IMPLEMENTATION_PLAN.md)
- [Infrastructure Provisioning](/infrastructure/README.md)
- [Environment Configuration](/envsample.env)

## Updates and Versioning

All agent cards follow semantic versioning (MAJOR.MINOR.PATCH):
- **MAJOR**: Breaking changes to agent capabilities or API
- **MINOR**: New capabilities or features added
- **PATCH**: Bug fixes and performance improvements

Current version: **1.0.0** (Initial A2A implementation)

Last updated: November 7, 2025
