# BankX Multi-Agent Banking System

> A sophisticated conversational banking platform built with Azure AI Foundry and Model Context Protocol (MCP)

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.2.0-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.2.2-blue.svg)](https://www.typescriptlang.org/)

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Project Status](#project-status)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the Application](#running-the-application)
- [Project Structure](#project-structure)
- [Use Cases](#use-cases)
- [API Documentation](#api-documentation)
- [Data Model](#data-model)
- [Configuration](#configuration)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

BankX is a production-ready multi-agent banking assistant that demonstrates enterprise-grade conversational AI using Azure AI Foundry. The system implements intelligent routing, zero-hallucination patterns, and comprehensive agent governance through Model Context Protocol (MCP) microservices.

### Key Highlights

- **7 Specialized Agents**: Supervisor, Account, Transaction, Payment, Product FAQ, AI Money Coach, and Escalation Comms agents
- **9 MCP Microservices**: Account, Transaction, Payment, Limits, Contacts, Audit, ProdInfoFAQ, AI Money Coach, and Escalation Comms services
- **Zero-Hallucination Architecture**: All data retrieved through structured MCP tools
- **Agent Governance**: Complete decision ledger for regulatory compliance
- **Thai Banking System**: 10 customers with real synthetic data (70 transactions)
- **React Frontend**: Modern UI with Fluent UI components and Azure MSAL authentication

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    React Frontend (Port 8081)                    │
│              TypeScript + Fluent UI + Azure MSAL                 │
└───────────────────────────────┬─────────────────────────────────┘
                                │ REST API / WebSocket
┌───────────────────────────────▼─────────────────────────────────┐
│              FastAPI Copilot Backend (Port 8080)                 │
│                  Multi-Agent Orchestration                       │
│ ┌─────────────────────────────────────────────────────────────┐ │
│ │               SupervisorAgent (Meta-Orchestrator)           │ │
│ └──┬────────┬─────────┬─────────────┬──────────────────────┬──┘ │
│    │        │         │             │                      │    │
│    │ UC1 Agents       │      UC2 & UC3 Agents             │    │
│    │ (Financial Ops)  │      (Knowledge-based with         │    │
│    │                  │       EscalationComms)             │    │
│    │                  │                                     │    │
│ ┌──▼────┐ ┌──▼─────┐ ┌▼──────┐ ┌───▼────────┐ ┌──────────▼──┐ │
│ │Account│ │Transact│ │Payment│ │  ProdInfo  │ │AIMoneyCoach │ │
│ │ Agent │ │  ion   │ │ Agent │ │ FAQ Agent  │ │   Agent     │ │
│ │       │ │ Agent  │ │       │ │            │ │             │ │
│ └───┬───┘ └───┬────┘ └───┬───┘ └─────┬──────┘ └──────┬──────┘ │
│     │         │           │           │                │        │
│     │         │           │           │ (When needed)  │        │
│     │         │           │           ▼                ▼        │
│     │         │           │      ┌────────────────────────┐    │
│     │         │           │      │  EscalationComms Agent │    │
│     │         │           │      │ (Ticket & Email Only)  │    │
│     │         │           │      └──────────┬─────────────┘    │
│     │         │           │                 │                  │
└─────┼─────────┼───────────┼─────────────────┼──────────────────┘
      │         │           │                 │
      │    MCP HTTP Calls                     │
      │         │           │                 │
┌─────▼─────────▼───────────▼─────────────────▼──────────────────┐
│              Model Context Protocol (MCP) Services               │
│                                                                  │
│  UC1 MCP Services (Ports 8070-8075):                            │
│  ┌────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌─────────┐    │
│  │Account │ │Transaction│ │Payment│ │ Limits │ │Contacts│     │
│  │  8070  │ │   8071   │ │  8072 │ │  8073  │ │  8074  │     │
│  └────────┘ └──────────┘ └────────┘ └────────┘ └─────────┘    │
│                                                                  │
│  ┌────────┐                                                     │
│  │ Audit  │                                                     │
│  │  8075  │                                                     │
│  └────────┘                                                     │
│                                                                  │
│  UC2/UC3 MCP Services (NOT USED - See Note):                    │
│  ┌──────────────┐  ┌─────────────────┐                         │
│  │  ProdInfo    │  │  AIMoneyCoach   │  (OLD - Commented out)  │
│  │    FAQ       │  │      MCP        │  (Agents use Azure AI   │
│  │   8076       │  │     8077        │   Foundry file_search)  │
│  └──────────────┘  └─────────────────┘                         │
│                                                                  │
│  UC2/UC3 Escalation (Port 8078):                                │
│  ┌──────────┐                                                   │
│  │Escalation│  (Called ONLY by ProdInfoFAQ & AIMoneyCoach)     │
│  │  Comms   │  (Ticket creation & email notifications)         │
│  │   8078   │                                                   │
│  └──────────┘                                                   │
│                                                                  │
│  Data Layer (CSV + JSON + Azure AI Foundry Vector Stores):      │
│  • customers.csv        • transactions.csv                      │
│  • accounts.csv         • balances.json (dynamic)               │
│  • contacts.csv         • beneficiaries.json (runtime)          │
│  • limits.csv           • audit_logs.json                       │
│  • UC2: Product docs in Azure AI Foundry vector stores          │
│  • UC3: Book chapters in Azure AI Foundry vector stores         │
└──────────────────────────────────────────────────────────────────┘

Note: UC2 & UC3 use Azure AI Foundry's native file_search (in-memory
vector search) instead of custom MCP servers on ports 8076/8077.
```

### Multi-Agent Architecture

The system employs a **hierarchical multi-agent pattern** using **Azure AI Foundry**:

1. **SupervisorAgent**: Intent classification and intelligent routing
2. **Domain Agents**: Specialized agents for specific banking operations (in-process)
3. **MCP Services**: Stateless microservices providing business logic

**Current Implementation**: Azure AI Foundry agents with direct in-process communication
**Architecture**: All agents run within the copilot backend process and communicate via direct method calls

**Note**: The system includes a complete A2A (Agent-to-Agent) microservices architecture codebase for distributed deployment, but this is not currently deployed. See [Future Releases](#future-releases) for planned A2A implementation.

---

## Features

### ✅ Use Case 1: Financial Operations (PRODUCTION READY)

| User Story | Feature | Status |
|-----------|---------|--------|
| **US 1.1** | View Transaction History | ✅ Complete |
| **US 1.2** | Transaction Aggregations & Insights | ✅ Complete |
| **US 1.3** | Check Account Balance & Limits | ✅ Complete |
| **US 1.4** | Transfer to Registered Contact | ✅ Complete |
| **US 1.5** | View Transaction Details | ✅ Complete |
| **US 1.A1-A3** | Agent Governance Logging | ✅ Complete |
| **US 1.T1-T5** | Teller Audit Dashboard | ✅ Complete |

**Key Features**:
- Zero-hallucination pattern with structured MCP tools
- Policy gates: 50K THB per transaction, 200K THB daily limit
- Beneficiary management (pre-registered + runtime additions)
- Bidirectional transaction creation (sender OUT + recipient IN)
- Balance persistence with CSV + JSON hybrid storage
- Complete decision ledger for compliance
- Idempotency with request IDs
- 3-attempt account verification with retry logic

### ✅ Use Case 2: Product Info & FAQ (PRODUCTION READY)

**Status**: Fully functional using Azure AI Foundry native file search

**User Stories**:
- US 2.1: Answer Product Information Queries
- US 2.2: Answer FAQ Questions
- US 2.3: Compare Account Types
- US 2.4: Handle Unknown Queries with Ticket Creation
- US 2.5: Explain Banking Terms and Calculations

**Architecture**:
- ✅ ProdInfoFAQ Agent registered in Azure AI Foundry portal
- ✅ Product documents uploaded to Azure AI Foundry vector stores
- ✅ Native `file_search` tool for RAG (in-memory vector search)
- ✅ EscalationComms MCP Service (Port 8078) for ticket/email handling

**What's Already Configured**:
- Agent created in Azure AI Foundry portal with pre-configured agent ID
- Product documents (5 PDFs + FAQ HTML) uploaded to vector stores
- In-memory vector search handled by Azure AI Foundry
- No external Azure AI Search required

**Setup Requirements**:
```bash
# Environment variables needed:
PRODINFO_FAQ_AGENT_ID=<agent-id-from-portal>
PRODINFO_FAQ_VECTOR_STORE_IDS=<vector-store-ids-comma-separated>
ESCALATION_COMMS_MCP_URL=http://localhost:8078
```

**Key Features**:
- Zero external dependencies (no Azure AI Search, no Content Understanding API)
- Automatic grounding validation through Azure AI Foundry
- Support ticket creation with email notifications
- Answers grounded in uploaded product documentation

### ✅ Use Case 3: AI Money Coach (PRODUCTION READY)

**Status**: Fully functional using Azure AI Foundry native file search

**User Stories** (12 total):
- UC3-001: Basic Debt Management Advice
- UC3-002: Emergency Financial Situation (Debt Detox)
- UC3-003: Good Debt vs Bad Debt Education
- UC3-004: Building Emergency Fund Guidance
- UC3-005: Mindset and Psychological Support
- UC3-006: Multiple Income Stream Strategy
- UC3-007: Sufficiency Economy Application
- UC3-008: Financial Intelligence Development
- UC3-009: Out-of-Scope Query Handling
- UC3-010: Debt Consolidation Inquiry
- UC3-011: Investment Readiness While in Debt
- UC3-012: Complex Multi-Topic Consultation

**Key Principles**:
- Clarification-first approach
- 100% grounded in "Debt-Free to Financial Freedom" book
- Personalized coaching based on financial health assessment
- Actionable, practical recommendations

**Architecture**:
- ✅ AIMoneyCoach Agent registered in Azure AI Foundry portal
- ✅ Book chapters (12 chapters) uploaded to Azure AI Foundry vector stores
- ✅ Native `file_search` tool for RAG (in-memory vector search)
- ✅ EscalationComms MCP Service (Port 8078) for ticket/email handling

**What's Already Configured**:
- Agent created in Azure AI Foundry portal with pre-configured agent ID
- "Debt-Free to Financial Freedom" book (12 chapters) uploaded to vector stores
- In-memory vector search handled by Azure AI Foundry
- No external Azure AI Search required

**Setup Requirements**:
```bash
# Environment variables needed:
AI_MONEY_COACH_AGENT_ID=<agent-id-from-portal>
AI_MONEY_COACH_VECTOR_STORE_IDS=<vector-store-ids-comma-separated>
ESCALATION_COMMS_MCP_URL=http://localhost:8078
```

**Key Features**:
- Zero external dependencies (no Azure AI Search, no Content Understanding API)
- Automatic grounding validation through Azure AI Foundry
- Support ticket creation for out-of-scope questions
- 100% grounded advice from uploaded book content

---

## Project Status

### Overall Progress: ~95% Complete (Functional Components)

| Component | Status | Completion | Notes |
|-----------|--------|-----------|-------|
| UC1 - Financial Operations | ✅ Production Ready | 100% | Fully functional and tested |
| UC2 - Product FAQ | ✅ Production Ready | 100% | Using Azure AI Foundry native file search |
| UC3 - AI Money Coach | ✅ Production Ready | 100% | Using Azure AI Foundry native file search |
| Frontend | ✅ Complete | 100% | Fully functional |
| MCP Services (UC1) | ✅ Complete | 100% | Fully functional (6 services) |
| EscalationComms MCP | ✅ Complete | 100% | Ticket/email handling (Port 8078) |
| Agent Framework (Foundry) | ✅ Complete | 100% | All agents functional with vector stores |
| A2A Architecture | 🔴 Not Deployed | 0% | Code exists, see Future Releases |
| Data Layer | ✅ Complete | 100% | CSV+JSON hybrid + vector stores |
| Documentation | ✅ Updated | 100% | Accurate as of Nov 18, 2025 |

### Recent Updates (Latest Commits)

- **9f8fa3d**: fix(uc2-uc3): CORRECTED implementation per official specifications
- **99da2c2**: feat(uc2-uc3): Implement Product FAQ (UC2) and Money Coach (UC3) agents
- **b5d2a07**: fix(uc1): Fix MCP service startup issues and add missing dependencies
- **2f52f4f**: feat(uc1): Update Supervisor Agent with context-aware routing
- **24098dd**: feat(uc1): Update Payment Agent with US 1.4 transfer approval workflow

---

## Technology Stack

### Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.11+ | Runtime environment |
| **FastAPI** | 0.116.1 | REST API & WebSocket framework |
| **Uvicorn** | 0.35.0 | ASGI server |
| **Agent Framework Azure AI** | Custom | Multi-agent orchestration |
| **FastMCP** | 2.0.0+ | Model Context Protocol implementation |
| **Pydantic** | 2.0+ | Data validation & serialization |
| **Azure Identity** | 1.24.0 | Managed Identity authentication |
| **Azure Blob Storage** | 12.26.0 | File storage service |
| **Azure Document Intelligence** | 1.0.1 | OCR & invoice parsing |
| **Dependency Injector** | 4.48.1 | Constructor injection pattern |

### Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| **React** | 18.2.0 | UI library |
| **TypeScript** | 5.2.2 | Type safety |
| **React Router** | 6.18.0 | Client-side routing |
| **Fluent UI (v8)** | 8.112.5 | Office UI Fabric components |
| **Fluent UI (v9)** | 9.37.3 | Modern Fluent UI components |
| **Azure MSAL Browser** | 3.1.0 | Microsoft authentication |
| **Azure MSAL React** | 2.0.4 | React MSAL integration |
| **Vite** | 6.3.1 | Build tool |
| **DOMPurify** | 3.2.4 | XSS protection |

### Data Layer

- **Storage**: CSV (original data) + JSON (runtime state)
- **Currency**: Thai Baht (THB) only
- **Timezone**: Asia/Bangkok (UTC+07:00)
- **Customers**: 10 Thai customers (CUST-001 to CUST-010)
- **Accounts**: 10 checking accounts (CHK-001 to CHK-010)
- **Transactions**: 70 transactions (Oct 20-26, 2025)
- **Beneficiaries**: 90 pre-registered contacts (9 per customer)

---

## Prerequisites

### Required Software

- **Python**: 3.11 or higher
- **Node.js**: 14 or higher
- **npm**: 8 or higher
- **uv**: Python package installer (recommended) - [Install uv](https://github.com/astral-sh/uv)

### Azure Resources (Required)

1. **Azure AI Foundry Project**
   - Project endpoint URL
   - Agent deployment names
   - Azure OpenAI connection

2. **Azure Storage Account**
   - Blob container for invoice/document uploads
   - Connection string or Managed Identity

3. **Azure Document Intelligence**
   - Endpoint URL
   - API key or Managed Identity

4. **Azure Application Insights** (Optional)
   - Connection string for observability

### Azure Resources (For UC2/UC3 - Implementation Ready)

5. **Azure AI Search** (Required for UC2/UC3)
   - Search service endpoint
   - Admin API key
   - Vector indexing enabled
   - Two indexes: bankx-prodinfo-faq (UC2) and bankx-money-coach (UC3)

6. **Azure AI Foundry Content Understanding** (Required for UC3)
   - Endpoint URL for 100% grounding validation
   - Ensures AI Money Coach advice is strictly from book content

7. **Azure Communication Services** (Required for UC2/UC3)
   - Email service for ticket notifications
   - From address configuration

8. **Azure Cosmos DB** (Optional for UC2/UC3)
   - NoSQL database for ticket persistence
   - Currently using mock service for development

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/claude_bank.git
cd claude_bank
```

### 2. Install Python Dependencies

#### Option A: Using uv (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install copilot backend
cd app/copilot
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
uv sync --prerelease=allow

# Install MCP services (repeat for each service)
cd app/business-api/python/account
uv venv
source .venv/bin/activate
uv sync

# Repeat for: transaction, payment, limits, contacts, audit
```

#### Option B: Using pip

```bash
# Install all dependencies from root
pip install -r requirements.txt

# Or install per service
cd app/copilot
pip install -e .
```

### 3. Install Frontend Dependencies

```bash
cd app/frontend
npm install
```

---

## Configuration

### Environment Variables

Create `.env` files in the following locations:

#### 1. Copilot Backend: `app/copilot/.env`

```env
# Application Settings
APP_NAME=BankX Banking Assistant
PROFILE=dev
ENABLE_OTEL=false

# Azure AI Foundry (Required)
AZURE_AI_PROJECT_ENDPOINT=https://your-project.eastus2.inference.ml.azure.com
AZURE_OPENAI_CONNECTION_ID=your-openai-connection-id
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-08-01-preview

# Azure Storage (Required for Invoice Scanning)
AZURE_STORAGE_ACCOUNT_URL=https://yourstorage.blob.core.windows.net
AZURE_STORAGE_CONTAINER_NAME=invoices

# Azure Document Intelligence (Required for Invoice Scanning)
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://yourdocint.cognitiveservices.azure.com
AZURE_DOCUMENT_INTELLIGENCE_API_KEY=your-api-key

# MCP Service URLs (Required)
ACCOUNT_MCP_URL=http://localhost:8070
TRANSACTION_MCP_URL=http://localhost:8071
PAYMENT_MCP_URL=http://localhost:8072
LIMITS_MCP_URL=http://localhost:8073
CONTACTS_MCP_URL=http://localhost:8074
AUDIT_MCP_URL=http://localhost:8075

# Azure Application Insights (Optional)
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=your-key

# UC2/UC3 MCP URLs (Required for UC2/UC3)
PRODINFO_FAQ_MCP_URL=http://localhost:8076
AI_MONEY_COACH_MCP_URL=http://localhost:8077
ESCALATION_COMMS_MCP_URL=http://localhost:8078

# Azure AI Search (Required for UC2/UC3)
AZURE_AI_SEARCH_ENDPOINT=https://yoursearch.search.windows.net
AZURE_AI_SEARCH_KEY=your-search-api-key
AZURE_AI_SEARCH_INDEX_UC2=bankx-prodinfo-faq
AZURE_AI_SEARCH_INDEX_UC3=bankx-money-coach

# Azure Content Understanding (Required for UC3)
AZURE_CONTENT_UNDERSTANDING_ENDPOINT=https://your-ai-foundry.inference.ml.azure.com

# Azure Communication Services (Required for UC2/UC3 Escalation)
AZURE_COMMUNICATION_SERVICES_ENDPOINT=https://youracs.communication.azure.com
AZURE_COMMUNICATION_SERVICES_EMAIL_FROM=support@bankx.com
```

#### 2. Frontend: `app/frontend/.env`

```env
VITE_API_BASE_URL=http://localhost:8080/api
VITE_AZURE_CLIENT_ID=your-azure-ad-client-id
VITE_AZURE_TENANT_ID=your-azure-ad-tenant-id
```

#### 3. MCP Services: Set via shell environment

```bash
# For development (each terminal)
export PROFILE=dev

# For transaction service
export TRANSACTIONS_API_URL=http://localhost:8071
```

---

## Running the Application

### Development Mode (Multiple Terminals)

#### Terminal 1: Account Service (Port 8070)

```bash
cd app/business-api/python/account
uv venv && source .venv/bin/activate
uv sync
export PROFILE=dev
python main.py
```

#### Terminal 2: Transaction Service (Port 8071)

```bash
cd app/business-api/python/transaction
uv venv ; source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
uv sync
export PROFILE=dev  # On Windows PowerShell: $env:PROFILE="dev"
python main.py
```

#### Terminal 3: Payment Service (Port 8072)

```bash
cd app/business-api/python/payment
uv venv ; source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
uv sync
export PROFILE=dev  # On Windows PowerShell: $env:PROFILE="dev"
export TRANSACTIONS_API_URL=http://localhost:8071  # On Windows PowerShell: $env:TRANSACTIONS_API_URL="http://localhost:8071"
python main.py
```

#### Terminal 4: Limits Service (Port 8073)

```bash
cd app/business-api/python/limits
uv venv ; source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
uv sync
export PROFILE=dev  # On Windows PowerShell: $env:PROFILE="dev"
python main.py
```

#### Terminal 5: Contacts Service (Port 8074)

```bash
cd app/business-api/python/contacts
uv venv ; source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
uv sync
export PROFILE=dev  # On Windows PowerShell: $env:PROFILE="dev"
python main.py
```

#### Terminal 6: Audit Service (Port 8075)

```bash
cd app/business-api/python/audit
uv venv ; source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
uv sync
export PROFILE=dev  # On Windows PowerShell: $env:PROFILE="dev"
python main.py
```

#### Terminal 7: ProdInfoFAQ MCP Service (Port 8076) - Optional for UC2

```bash
cd app/business-api/python/prodinfo_faq
uv venv ; source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
uv sync
export PROFILE=dev  # On Windows PowerShell: $env:PROFILE="dev"
# Configure Azure AI Search
export AZURE_AI_SEARCH_ENDPOINT=your-azure-search-endpoint  # On Windows PowerShell: $env:AZURE_AI_SEARCH_ENDPOINT="your-endpoint"
export AZURE_AI_SEARCH_KEY=your-azure-search-key  # On Windows PowerShell: $env:AZURE_AI_SEARCH_KEY="your-key"
python main.py
```

#### Terminal 8: AIMoneyCoach MCP Service (Port 8077) - Optional for UC3

```bash
cd app/business-api/python/ai_money_coach
uv venv ; source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
uv sync
export PROFILE=dev  # On Windows PowerShell: $env:PROFILE="dev"
# Configure Azure AI Search and Content Understanding
export AZURE_AI_SEARCH_ENDPOINT=your-endpoint  # On Windows PowerShell: $env:AZURE_AI_SEARCH_ENDPOINT="your-endpoint"
export AZURE_AI_SEARCH_KEY=your-key  # On Windows PowerShell: $env:AZURE_AI_SEARCH_KEY="your-key"
export AZURE_CONTENT_UNDERSTANDING_ENDPOINT=your-endpoint  # On Windows PowerShell: $env:AZURE_CONTENT_UNDERSTANDING_ENDPOINT="your-endpoint"
python main.py
```

#### Terminal 9: EscalationComms MCP Service (Port 8078) - Optional for UC2/UC3

```bash
cd app/business-api/python/escalation_comms
uv venv ; source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
uv sync
export PROFILE=dev  # On Windows PowerShell: $env:PROFILE="dev"
# Configure Azure Communication Services
export AZURE_COMMUNICATION_SERVICES_ENDPOINT=your-endpoint  # On Windows PowerShell: $env:AZURE_COMMUNICATION_SERVICES_ENDPOINT="your-endpoint"
export AZURE_COMMUNICATION_SERVICES_EMAIL_FROM=support@bankx.com  # On Windows PowerShell: $env:AZURE_COMMUNICATION_SERVICES_EMAIL_FROM="support@bankx.com"
python main.py
```

#### Terminal 10: Copilot Backend (Port 8080)

```bash
cd app/copilot
uv venv ; source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
uv sync --prerelease=allow
export PROFILE=dev  # On Windows PowerShell: $env:PROFILE="dev"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

#### Terminal 11: Frontend (Port 8081)

```bash
cd app/frontend
npm run dev
```

### Access the Application

- **Frontend**: http://localhost:8081
- **Backend API**: http://localhost:8080
- **API Docs**: http://localhost:8080/docs

### Performance Metrics

- **Before MCP Optimization**: 10-15 seconds per message (6-9s MCP overhead + 4-6s LLM)
- **After MCP Optimization**: 2-5 seconds per message (0s MCP overhead + 2-5s LLM)

---

## Project Structure

```
claude_bank/
├── app/
│   ├── business-api/python/          # MCP Microservices
│   │   ├── account/                  # Account Service (Port 8070)
│   │   │   ├── main.py              # Service entry point
│   │   │   ├── mcp_tools.py         # MCP tool definitions
│   │   │   ├── services.py          # Business logic
│   │   │   ├── models.py            # Pydantic models
│   │   │   ├── balance_persistence_service.py
│   │   │   ├── beneficiary_service.py
│   │   │   ├── data_loader_service.py
│   │   │   └── pyproject.toml
│   │   ├── transaction/              # Transaction Service (Port 8071)
│   │   │   ├── main.py
│   │   │   ├── mcp_tools.py
│   │   │   ├── services.py
│   │   │   ├── models.py
│   │   │   ├── routers.py
│   │   │   ├── transaction_persistence_service.py
│   │   │   └── pyproject.toml
│   │   ├── payment/                  # Payment Service (Port 8072)
│   │   │   ├── main.py
│   │   │   ├── mcp_tools.py
│   │   │   ├── services.py
│   │   │   ├── models.py
│   │   │   └── pyproject.toml
│   │   ├── limits/                   # Limits Service (Port 8073)
│   │   │   ├── main.py
│   │   │   ├── mcp_tools.py
│   │   │   ├── services.py
│   │   │   ├── models.py
│   │   │   ├── limits_persistence_service.py
│   │   │   └── pyproject.toml
│   │   ├── contacts/                 # Contacts Service (Port 8074)
│   │   │   ├── main.py
│   │   │   ├── mcp_tools.py
│   │   │   ├── services.py
│   │   │   ├── models.py
│   │   │   └── pyproject.toml
│   │   ├── audit/                    # Audit Service (Port 8075)
│   │   │   ├── main.py
│   │   │   ├── mcp_tools.py
│   │   │   ├── services.py
│   │   │   ├── models.py
│   │   │   ├── audit_persistence_service.py
│   │   │   └── pyproject.toml
│   │   ├── prodinfo_faq/             # ProdInfoFAQ Service (Port 8076)
│   │   │   ├── main.py
│   │   │   ├── mcp_tools.py
│   │   │   ├── services.py
│   │   │   ├── models.py
│   │   │   └── pyproject.toml
│   │   ├── ai_money_coach/           # AIMoneyCoach Service (Port 8077)
│   │   │   ├── main.py
│   │   │   ├── mcp_tools.py
│   │   │   ├── services.py
│   │   │   ├── models.py
│   │   │   └── pyproject.toml
│   │   └── escalation_comms/         # EscalationComms Service (Port 8078)
│   │       ├── main.py
│   │       ├── mcp_tools.py
│   │       ├── services.py
│   │       ├── models.py
│   │       └── pyproject.toml
│   ├── copilot/                      # FastAPI Backend (Port 8080)
│   │   └── app/
│   │       ├── main.py              # Application entry point
│   │       ├── agents/              # Agent Implementations
│   │       │   ├── foundry/         # UC1 Agents (Azure AI Foundry)
│   │       │   │   ├── supervisor_agent_foundry.py
│   │       │   │   ├── account_agent_foundry.py
│   │       │   │   ├── transaction_agent_foundry.py
│   │       │   │   └── payment_agent_foundry.py
│   │       │   └── azure_chat/      # UC2/UC3 Agents (Azure Chat)
│   │       │       ├── supervisor_agent.py
│   │       │       ├── account_agent.py
│   │       │       ├── transaction_agent.py
│   │       │       ├── payment_agent.py
│   │       │       ├── prodinfo_faq_agent.py
│   │       │       ├── ai_money_coach_agent.py
│   │       │       └── escalation_comms_agent.py
│   │       ├── api/                 # REST Endpoints
│   │       │   ├── chat_routers.py  # Chat API
│   │       │   ├── content_routers.py # File upload/download
│   │       │   └── auth_routers.py  # Authentication
│   │       ├── config/              # Configuration
│   │       │   ├── settings.py      # Environment settings
│   │       │   ├── logging.py       # Logging setup
│   │       │   ├── azure_credential.py # Azure auth
│   │       │   ├── container_foundry.py # DI container (UC1)
│   │       │   └── container_azure_chat.py # DI container (UC2/UC3)
│   │       ├── models/              # Data Models
│   │       │   ├── chat.py          # Chat request/response
│   │       │   ├── user.py          # User models
│   │       │   └── financial_schemas.py # Banking schemas
│   │       ├── helpers/             # Utilities
│   │       │   ├── blob_proxy.py    # Blob storage helper
│   │       │   └── document_intelligence_scanner.py
│   │       ├── tools/               # Agent Tools
│   │       │   └── invoice_scanner_plugin.py
│   │       ├── utils/               # Utilities
│   │       │   └── date_normalizer.py
│   │       └── pyproject.toml
│   └── frontend/                    # React Frontend (Port 8081)
│       ├── src/
│       │   ├── components/          # React components
│       │   ├── pages/              # Page components
│       │   ├── services/           # API clients
│       │   ├── hooks/              # Custom React hooks
│       │   ├── utils/              # Utility functions
│       │   └── App.tsx             # Root component
│       ├── package.json
│       └── tsconfig.json
├── schemas/tools-sandbox/
│   └── uc1_synthetic_data/         # CSV Data Files
│       ├── customers.csv           # 10 Thai customers
│       ├── accounts.csv            # 10 checking accounts
│       ├── transactions.csv        # 70 transactions
│       ├── contacts.csv            # 90 beneficiaries
│       └── limits.csv              # Transaction limits
├── data/                           # Runtime Data (JSON)
│   ├── balances.json              # Dynamic balance updates
│   └── beneficiaries.json         # Runtime beneficiary additions
├── docs/                          # Documentation
│   ├── uc2_uc3_correct_implementation.md
│   ├── faq.md
│   ├── troubleshooting.md
│   └── kusto-queries.md
├── requirements.txt               # Python dependencies
├── README.md                     # This file
├── CHANGELOG.md                  # Version history
├── SECURITY.md                   # Security policy
├── azure.yaml                    # Azure deployment config
└── Project.Understanding.txt     # Full specification (90KB)
```

---

## Use Cases

### Use Case 1: Financial Operations

**Test Scenarios**:

```bash
# 1. View Transaction History
"Show me my transactions from last week"

# 2. Transaction Aggregations
"What are my spending patterns this month?"

# 3. Check Balance
"What's my current account balance?"

# 4. Transfer Money
"Transfer 5000 THB to Somchai"

# 5. Transaction Details
"Show me details of transaction TXN-20251020-001"
```

**Supported Customers**: CUST-001 to CUST-010 (use any for testing)

### Use Case 2: Product Info & FAQ (Framework Ready)

**Test Scenarios** (Backend required):

```bash
# 1. Product Query
"What is the interest rate for a 24-month fixed deposit?"

# 2. FAQ Query
"Can I withdraw from my fixed deposit early?"

# 3. Comparison
"Compare savings account vs fixed deposit"

# 4. Unknown Query
"Tell me about mortgage loans"  # Should offer ticket creation

# 5. Out of Scope
"What's the weather today?"  # Should reject and offer ticket
```

### Use Case 3: AI Money Coach (Framework Ready)

**Test Scenarios** (Backend required):

```bash
# 1. Debt Management
"I have 3 credit cards with high interest. How should I prioritize payments?"

# 2. Emergency Situation
"My monthly expenses exceed my income. What should I do?"

# 3. Good vs Bad Debt
"Should I take a loan to buy the latest iPhone?"

# 4. Emergency Fund
"How can I start building an emergency fund when I have no savings?"

# 5. Financial Intelligence
"How can I improve my financial literacy?"
```

---

## API Documentation

### Chat API

**Endpoint**: `POST /api/chat`

**Request**:
```json
{
  "messages": [
    {
      "role": "user",
      "content": "Show me my transactions"
    }
  ],
  "context": {
    "userId": "CUST-001",
    "sessionId": "unique-session-id",
    "timestamp": "2025-10-26T10:00:00+07:00"
  }
}
```

**Response**:
```json
{
  "choices": [
    {
      "messages": [
        {
          "role": "assistant",
          "content": "Here are your recent transactions...",
          "context": {
            "intent": "view_transactions",
            "data_sources": ["transaction_mcp"],
            "citations": [...]
          }
        }
      ]
    }
  ]
}
```

### Content API

**Upload Invoice**: `POST /api/content/upload`
**Download File**: `GET /api/content/download/{blob_name}`

### Authentication

The system supports Azure AD authentication via MSAL. Configure your Azure AD app registration and update the frontend `.env` file with your Client ID and Tenant ID.

---

## Data Model

### Customer Data (CSV)

```csv
customer_id,full_name_th,full_name_en,email,phone
CUST-001,สมชาย ใจดี,Somchai Jaidee,somchai.j@email.com,+66812345678
```

### Account Data (CSV)

```csv
account_id,customer_id,account_type,account_number,currency
CHK-001,CUST-001,Checking,1234567890,THB
```

### Transaction Data (CSV)

```csv
transaction_id,account_id,amount,type,merchant,category,date
TXN-20251020-001,CHK-001,250.00,DEBIT,7-Eleven,Groceries,2025-10-20T08:30:00+07:00
```

### Beneficiary Data (CSV)

```csv
customer_id,beneficiary_account_number,beneficiary_name,relationship,bank_name
CUST-001,9876543210,Areeya Tanaka,Friend,BankX
```

### Limits Data (CSV)

```csv
customer_id,account_id,per_transaction_limit,daily_limit,monthly_limit
CUST-001,CHK-001,50000.00,200000.00,1000000.00
```

---

## Development

### Code Quality

```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

### Adding a New Agent

1. Create agent file in `app/copilot/app/agents/foundry/` or `azure_chat/`
2. Define agent class with tools and instructions
3. Register in DI container (`container_foundry.py` or `container_azure_chat.py`)
4. Update supervisor routing logic
5. Add integration tests

### Adding a New MCP Service

1. Create service directory in `app/business-api/python/`
2. Implement `main.py`, `mcp_tools.py`, `services.py`, `models.py`
3. Create `pyproject.toml` with dependencies
4. Update port assignments (avoid conflicts)
5. Add data files to `schemas/tools-sandbox/uc1_synthetic_data/`
6. Update environment variables in copilot `.env`

---

## Testing

### Unit Tests

```bash
cd app/copilot
pytest tests/unit/
```

### Integration Tests

```bash
cd app/copilot
pytest tests/integration/
```

### End-to-End Tests

```bash
# Start all services first, then run E2E tests
cd app/frontend
npm run test:e2e
```

### Manual Testing

Use the Swagger UI at http://localhost:8080/docs to test individual API endpoints.

---

## Deployment

### Azure Container Apps

The project includes `azure.yaml` for deployment to Azure Container Apps.

```bash
# Install Azure Developer CLI
curl -fsSL https://aka.ms/install-azd.sh | bash

# Login to Azure
azd auth login

# Deploy
azd up
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up -d
```

---

## Troubleshooting

### Common Issues

#### 1. MCP Service Not Starting

**Problem**: Service fails to start on specified port

**Solution**:
- Check if port is already in use: `lsof -i :<port>` (Linux/Mac) or `netstat -ano | findstr :<port>` (Windows)
- Kill conflicting process or change port assignment
- Ensure virtual environment is activated

#### 2. Azure AI Foundry Connection Error

**Problem**: "Unable to connect to Azure AI Foundry"

**Solution**:
- Verify `AZURE_AI_PROJECT_ENDPOINT` is correct
- Check Azure credentials: `az login` and `az account show`
- Ensure Managed Identity has proper role assignments
- Verify firewall rules allow access

#### 3. Agent-Framework-Azure-AI Installation Failure

**Problem**: Package not found during `uv sync`

**Solution**:
- This is a Microsoft private package requiring special access
- Contact Azure AI Foundry support for package registry access
- Alternative: Use public agents framework (requires code changes)

#### 4. Transaction Data Not Found

**Problem**: "No transactions found" despite data existing

**Solution**:
- Check data files in `schemas/tools-sandbox/uc1_synthetic_data/`
- Verify `PROFILE=dev` environment variable is set
- Ensure date queries are within Oct 20-26, 2025 range
- Check timezone is Asia/Bangkok (+07:00)

#### 5. Beneficiary Verification Fails

**Problem**: Account verification always returns "not found"

**Solution**:
- Check `contacts.csv` for registered beneficiaries
- Verify account number format (10 digits)
- Ensure customer has pre-registered contacts
- Check `beneficiaries.json` for runtime additions

#### 6. Balance Not Updating After Transfer

**Problem**: Balance remains unchanged after successful transfer

**Solution**:
- Check `data/balances.json` file permissions
- Verify Payment service has write access to data directory
- Ensure bidirectional transaction creation succeeded
- Check audit logs for transaction details

### Performance Issues

#### Slow Response Times

**Solution**:
- Enable HTTP connection pooling for MCP services
- Use MCP HTTP transport instead of stdio (already implemented)
- Enable Application Insights for bottleneck identification
- Check network latency between services

### Logs

```bash
# View copilot logs
tail -f app/copilot/logs/app.log

# View MCP service logs
tail -f app/business-api/python/account/logs/account.log
```

For more detailed troubleshooting, see `docs/troubleshooting.md`.

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Commit your changes**: `git commit -m "feat: add new feature"`
4. **Push to the branch**: `git push origin feature/your-feature-name`
5. **Open a Pull Request**

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance tasks

---

## License

This project is proprietary and confidential. Unauthorized copying, modification, distribution, or use of this software is strictly prohibited.

---

## Support

For questions or issues:

1. Check the [FAQ](docs/faq.md)
2. Review [Troubleshooting Guide](docs/troubleshooting.md)
3. Open an issue on GitHub
4. Contact the development team

---

## Acknowledgments

- **Azure AI Foundry Team**: For the agent framework and platform support
- **FastMCP Team**: For the Model Context Protocol implementation
- **Microsoft**: For Azure services and infrastructure

---

## Future Releases

This section documents features that have been designed and partially or fully coded, but are not currently deployed or functional in the production system.

### A2A (Agent-to-Agent) Microservices Architecture

**Status**: Code complete, not deployed

**What Exists**:
- ✅ Complete agent microservice implementations in `app/agents/*-agent/`
- ✅ Agent Registry service (`app/agent-registry/`)
- ✅ A2A SDK with registry client, circuit breaker, and retry logic (`app/a2a-sdk/`)
- ✅ Docker Compose configuration (`docker-compose.yml`)
- ✅ Agent handlers for Account, Transaction, Payment, ProdInfo, AIMoneyCoach, EscalationComms

**Architecture** (Planned):
```
┌─────────────────────────────────────────────────────────────┐
│                   SUPERVISOR AGENT                           │
│              (Intent Classification & Routing)               │
│  • Agent Registry Client                                     │
│  • A2A Communication SDK                                     │
│  • Circuit Breaker & Retry Logic                            │
└──────┬────────┬────────┬────────┬────────┬─────────────────┘
       │        │        │        │        │
       │    A2A Protocol (HTTP/JSON)       │
       │        │        │        │        │
    ┌──▼──┐ ┌──▼───┐ ┌──▼───┐ ┌─▼──────┐ │
    ▼     ▼ ▼      ▼ ▼      ▼ ▼        ▼ ▼
┌────────┐ ┌─────────┐ ┌────────┐ ┌──────────┐
│Account │ │Transaction│ │Payment│ │ProdInfo │
│ Agent  │ │  Agent  │ │ Agent │ │   FAQ    │
│Pt: 8100│ │Pt: 8101│ │Pt: 8102│ │Pt: 8103 │
└───┬────┘ └────┬────┘ └───┬────┘ └────┬─────┘
    │           │           │           │
    └───────┬───┴───────────┴───────────┘
            │
      ┌─────┴──────┐
      │            │
   ┌──▼─────────┐ ┌▼──────────────┐
   │ AI Money   │ │ Escalation    │
   │   Coach    │ │    Comms      │
   │ Port: 8104 │ │  Port: 8105   │
   └──────┬─────┘ └───────┬───────┘
          │               │
          │      A2A      │
          └───────┬───────┘
                  │
     ┌────────────┴───────────┐
     │                        │
     ▼                        ▼
┌──────────────┐   ┌────────────────────┐
│AGENT REGISTRY│   │   MCP SERVICES     │
│ Port: 9000   │   │  Account: 8070     │
│              │   │  Transaction: 8071 │
│ Features:    │   │  Payment: 8072     │
│ • Discovery  │   │  Limits: 8073      │
│ • Health     │   │  Contacts: 8074    │
│ • Versioning │   │  Audit: 8075       │
│              │   │  ProdInfoFAQ: 8076 │
│              │   │  AIMoneyCoach: 8077│
│              │   │  Escalation: 8078  │
└──────────────┘   └────────────────────┘
```

**Key Features** (Planned):
- Agent Registry: Centralized service discovery and health monitoring
- Standardized Protocol: HTTP/JSON with authentication (JWT/Entra ID)
- Resilience: Circuit breaker, retry logic, exponential backoff
- Observability: Distributed tracing, metrics, audit logging
- Scalability: Independent agent deployment and horizontal scaling

**Why Not Deployed**:
- Current Azure AI Foundry in-process architecture meets all UC1 requirements
- Microservices architecture adds operational complexity
- Requires container orchestration (Azure Container Apps / Kubernetes)
- Additional infrastructure costs

**To Deploy**:
```bash
# Start all A2A services with Docker Compose
docker-compose up -d

# Or deploy to Azure Container Apps
azd up
```

### Session Memory Caching System

**Status**: Implemented, requires testing

**What's Implemented**:
- Session memory manager with JSON file storage (`memory/` directory)
- MCP data fetcher for cache population
- Periodic cache refresh (every 5 minutes)
- `/api/init-session` endpoint

**What's Needed**:
- End-to-end testing with real user sessions
- Performance validation under load
- Cache eviction policy implementation

**Documentation**: See `IMPLEMENTATION_SUMMARY.md`

### Additional Planned Features

#### Q2 2026
- [ ] Add voice interface support
- [ ] Implement multi-language support (Thai + English)
- [ ] Add sentiment analysis for customer interactions
- [ ] Implement advanced fraud detection

#### Q3 2026
- [ ] Mobile app (iOS/Android)
- [ ] Chatbot widget for website integration
- [ ] Real-time notifications via Azure SignalR
- [ ] Advanced analytics dashboard

---

**Built with ❤️ by the BankX Team**

**Last Updated**: November 18, 2025
**Version**: 1.2.0 - Documentation accuracy update
