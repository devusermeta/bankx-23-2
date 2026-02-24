# BankX Banking Platform - Project Overview

> A multi-agent conversational banking system using Azure AI Foundry, A2A Protocol, FastMCP, and Copilot Studio

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Frontend                           │
│                     (React + TypeScript)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Copilot (Supervisor)                          │
│              - Dynamic routing & orchestration                   │
│              - Conversation state management                     │
│              - FastAPI backend (Port: App)                       │
└───────┬──────────────────────────────────────────────────────────┘
        │
        │ Routes to specialized agents via A2A Protocol
        │
        ├─────────────┬──────────────┬──────────────┬──────────────┐
        ▼             ▼              ▼              ▼              ▼
   ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌────────────┐
   │ Account │  │Transaction│  │ Payment │  │ ProdInfo │  │AI Coach    │
   │ Agent   │  │  Agent    │  │  Agent  │  │FAQ Agent │  │Agent       │
   │:9001    │  │  :9002    │  │  :9003  │  │  :9004   │  │:9005       │
   └────┬────┘  └─────┬─────┘  └────┬────┘  └─────┬────┘  └──────┬─────┘
        │             │              │             │              │
        │ Uses MCP    │ MCP          │ MCP         │ Knowledge    │ Knowledge
        │ Tools       │ Tools        │ Tools       │ Base (RAG)   │ Base (RAG)
        │             │              │             │              │
        ▼             ▼              ▼             │              │
   ┌─────────┐  ┌──────────┐  ┌─────────┐        │              │
   │Account  │  │Transaction│  │Payment  │        │              │
   │MCP      │  │MCP        │  │MCP      │        │              │
   │:8070    │  │:8071      │  │:8072    │        ▼              ▼
   └─────────┘  └──────────┘  └─────────┘   [Azure AI Search] [Vector Store]
   
   ┌─────────┐  ┌──────────┐
   │Limits   │  │Contacts  │
   │MCP      │  │MCP       │
   │:8073    │  │:8074     │
   └─────────┘  └──────────┘
   
        │
        │ If agent cannot answer
        │
        ▼
   ┌───────────────────────────┐
   │ Escalation Copilot Bridge │
   │         :9006             │
   │  (Power Automate + Graph) │
   └─────────────┬─────────────┘
                 │
                 ├────► Excel (OneDrive/SharePoint)
                 └────► Outlook (Send Emails)
```

## 📦 Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend Framework** | FastAPI |
| **MCP Servers** | FastMCP (Model Context Protocol) |
| **Agent Protocol** | A2A (Agent-to-Agent) |
| **AI Platform** | Azure AI Foundry (Agents & Orchestration) |
| **Agent Studio** | Copilot Studio (Escalation workflows) |
| **Workflow Automation** | Power Automate |
| **Frontend** | React + TypeScript |
| **Authentication** | Microsoft Entra ID (Azure AD) |
| **Storage** | Azure Storage, SharePoint/OneDrive |
| **Search** | Azure AI Search |
| **Observability** | Application Insights, OpenTelemetry |

## 🤖 Agent Architecture

### 1. **Copilot (Supervisor Agent)**
**Location:** `claude_bank/app/copilot/`

**Role:** Central orchestrator that dynamically routes user queries to specialized agents

**How it works:**
- Receives user messages from the React frontend
- Analyzes intent using conversation context and routing rules
- Makes **intelligent routing decisions** based on query type
- Routes to appropriate specialist agent via **A2A protocol**
- Manages conversation state and handles confirmations
- Returns aggregated responses to the user

**Key Features:**
- Smart context-aware routing
- Payment confirmation handling
- Ticket creation coordination
- Multi-turn conversation management

**Configuration:** `.env` file contains:
- Agent names/versions
- MCP server URLs (deployed to Azure Container Apps)
- Azure AI Foundry connection strings

---

### 2. **Specialist A2A Agents** (Azure AI Foundry)

All specialist agents follow the **same A2A pattern**:

#### **Account Agent** (`account-agent-a2a`) - Port 9001
**Purpose:** Handle account-related queries

**Capabilities:**
- Account balance inquiries
- Account details and information
- Payment method listing
- Daily transaction limits

**MCP Tools Used:**
- Account MCP (`:8070`) - Account data operations
- Limits MCP (`:8073`) - Transaction limit checks

**How it works:**
1. Receives A2A request from supervisor with customer context
2. Connects to MCP tools with customer_id
3. Agent (hosted in Azure AI Foundry) processes query
4. Calls appropriate MCP tool functions
5. Returns structured response via A2A protocol

---

#### **Transaction Agent** (`transaction-agent-a2a`) - Port 9002
**Purpose:** Transaction history and movement tracking

**Capabilities:**
- View transaction history
- Filter transactions by date/type
- Search specific transactions
- Transaction summaries

**MCP Tools Used:**
- Transaction MCP (`:8071`) - Transaction data

---

#### **Payment Agent** (`payment-agent-v3-a2a`) - Port 9003
**Purpose:** Payment processing and management

**Capabilities:**
- Initiate money transfers
- Manage beneficiaries
- Payment confirmations (mandatory)
- Bill/invoice payment processing

**MCP Tools Used:**
- Payment Unified MCP (`:8072`) - Payment operations
- Contacts MCP (`:8074`) - Beneficiary management

**Critical Flow:**
1. User requests payment
2. Agent collects payment details
3. **MANDATORY:** Agent asks for explicit confirmation
4. Supervisor detects confirmation response
5. Routes back to Payment Agent with confirmation flag
6. Agent processes payment only after confirmation

---

#### **ProdInfo FAQ Agent** (`prodinfo-faq-agent-a2a`) - Port 9004
**Purpose:** Answer product and banking questions

**Capabilities:**
- Product information (accounts, loans, deposits)
- Interest rates and fees
- Eligibility criteria
- Account comparison

**Knowledge Source:**
- **Azure AI Search RAG** - Bank product documentation indexed
- Vector Store (optional) for semantic search

**How it works:**
1. User asks about products (e.g., "What are savings account rates?")
2. Agent queries Azure AI Search index
3. Retrieves relevant documentation
4. Generates answer based on retrieved context
5. If cannot answer → offers to create escalation ticket

---

#### **AI Money Coach Agent** (`ai-money-coach-agent-a2a`) - Port 9005
**Purpose:** Personal finance advice and coaching

**Capabilities:**
- Debt management strategies
- Budgeting advice
- Savings recommendations
- Investment guidance
- Good vs bad debt education

**Knowledge Source:**
- **Vector Store** - Financial coaching book/knowledge base
- Stored in Azure AI Foundry vector store

**How it works:**
1. User asks financial advice (e.g., "How to pay off credit card debt?")
2. Agent searches vector store for relevant passages
3. Provides personalized advice based on knowledge
4. If cannot answer → offers escalation ticket

---

### 3. **Escalation Copilot Bridge** - Port 9006

**Location:** `claude_bank/app/agents/escalation-copilot-bridge/`

**Purpose:** Creates support tickets when agents cannot answer user questions

**Architecture:**
```
Agent (cannot answer)
    │
    ▼
Asks user: "Would you like me to create a support ticket?"
    │
    ▼ (user confirms: "yes")
Supervisor generates ticket ID (TKT-YYYY-HHMMSS)
    │
    ▼
Escalation Bridge receives A2A request
    │
    ▼
Calls Power Automate Flow (HTTP)
    │
    ▼
Power Automate triggers Copilot Studio
    │
    ├──► Writes to Excel (SharePoint/OneDrive): tickets.xlsx
    │
    └──► Sends email via Outlook
    │
    ▼
Returns confirmation to Supervisor
    │
    ▼
User receives: "Ticket TKT-2026-123456 created successfully"
```

**How It Works Internally:**

1. **Trigger Conditions:**
   - ProdInfo/AI Coach agent cannot find answer
   - Agent explicitly offers: "Would you like me to create a support ticket?"
   - User confirms: "yes", "sure", "please", "confirm"

2. **Ticket Creation Flow:**
   ```python
   # Supervisor detects confirmation
   if user_confirms_ticket:
       ticket_id = generate_ticket_id()  # TKT-2026-123456
       
       # Route to Escalation Bridge via A2A
       response = await escalation_bridge.invoke({
           "ticket_id": ticket_id,
           "subject": extracted_from_conversation,
           "description": conversation_summary,
           "priority": "medium",
           "customer_id": authenticated_user_id
       })
   ```

3. **Power Automate Integration:**
   - Bridge calls HTTP endpoint: `POWER_AUTOMATE_FLOW_URL`
   - Flow format: POST with JSON body
   - Power Automate receives and triggers Copilot Studio bot
   - Bot has two output paths:
     - Write row to Excel (TicketsTable)
     - Send email to support team

4. **Configuration Required:**
   - Azure AD App Registration (Graph API permissions)
   - Power Automate Flow URL (from `.env`)
   - Copilot Studio bot configured
   - Excel file: `tickets.xlsx` on SharePoint/OneDrive
   - Table: `TicketsTable` with 8 columns

**Why This Architecture?**
- **Separation of concerns:** Ticket storage (Excel) separate from AI logic
- **Integration:** Leverages existing Microsoft 365 infrastructure
- **Reliability:** Power Automate handles retries and delivery
- **Visibility:** Tickets stored in familiar Excel format

---

## 🔧 MCP Servers (Business Logic Layer)

### What are MCP Servers?

**MCP (Model Context Protocol)** servers expose business logic as **tools** that agents can call. They act as the **data access layer** between AI agents and databases/external systems.

**Pattern:**
```python
# MCP Server exposes tools
@mcp.tool()
def get_account_balance(customer_id: str) -> dict:
    """Fetch account balance from database"""
    return database.query(customer_id)

# Agent calls tool
result = await account_mcp_tool.call_tool(
    "get_account_balance",
    {"customer_id": "C001"}
)
```

### Deployed MCP Servers

All MCP servers are deployed to **Azure Container Apps**:

#### 1. **Account MCP** (`:8070`)
**Location:** `claude_bank/app/business-api/python/account/`

**Tools:**
- `get_account_balance` - Fetch current balance
- `get_account_details` - Account information
- `list_payment_methods` - Cards and payment options

---

#### 2. **Transaction MCP** (`:8071`)
**Location:** `claude_bank/app/business-api/python/transaction/`

**Tools:**
- `get_transactions` - Transaction history with filters
- `get_transaction_by_id` - Single transaction details
- `search_transactions` - Search by criteria

---

#### 3. **Payment Unified MCP** (`:8072`)
**Location:** `claude_bank/app/business-api/python/payment-unified/`

**Tools:**
- `initiate_transfer` - Create money transfer
- `get_transfer_status` - Check payment status
- `list_beneficiaries` - Get saved recipients
- `add_beneficiary` - Add new recipient

---

#### 4. **Limits MCP** (`:8073`)
**Location:** `claude_bank/app/business-api/python/limits/`

**Tools:**
- `get_daily_limit` - Daily transaction limit
- `get_transfer_limit` - Single transfer maximum
- `check_limit_availability` - Remaining limit check

---

#### 5. **Contacts MCP** (`:8074`)
**Location:** `claude_bank/app/business-api/python/contacts/`

**Tools:**
- `list_contacts` - Get beneficiary list
- `add_contact` - Create new contact
- `get_contact_by_id` - Fetch contact details

---

### MCP Server Deployment

All servers are:
- Built as **Docker containers**
- Deployed to **Azure Container Apps**
- Exposed via **HTTPS endpoints**
- URLs configured in Copilot `.env` file

Example URLs:
```
ACCOUNT_MCP_URL=https://account-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io
PAYMENT_MCP_URL=https://payment-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io
```

---

## 🔄 Request Flow Examples

### Example 1: Check Account Balance

```
1. User → Frontend
   "What is my account balance?"

2. Frontend → Copilot (POST /api/chat)
   POST http://localhost:5000/api/chat
   Body: { messages: [...], customer_id: "C001" }

3. Copilot → Supervisor Agent (Azure AI Foundry)
   - Analyzes query intent
   - Routing Decision: Account-related → Account Agent

4. Supervisor → Account Agent (A2A Protocol)
   POST http://localhost:9001/a2a/invoke
   Body: { messages: [...], customer_id: "C001", thread_id: "abc123" }

5. Account Agent → Account MCP Tool
   - Agent hosted in Azure AI Foundry
   - Calls tool: get_account_balance
   - MCP client sends HTTP request to MCP server

6. Account MCP Server → Database
   GET https://account-mcp.../mcp
   Tool: get_account_balance(customer_id="C001")
   Returns: { balance: 50000.00, currency: "THB" }

7. Account Agent → Supervisor (A2A Response)
   { role: "assistant", content: "Your account balance is ฿50,000.00" }

8. Supervisor → Frontend
   { choices: [{ message: { content: "Your balance is ฿50,000.00" }}]}

9. Frontend → User
   Displays: "Your account balance is ฿50,000.00"
```

---

### Example 2: Escalation Flow (Ticket Creation)

```
1. User → "What are the best investment options?"

2. Copilot → AI Money Coach Agent
   (Routes based on "investment" keyword)

3. AI Money Coach searches knowledge base
   - Query doesn't match existing content
   - Cannot provide confident answer

4. AI Money Coach → Supervisor
   "I don't have specific information about that. 
    Would you like me to create a support ticket?"

5. Supervisor → User
   (Passes through the question)

6. User → "Yes, please create a ticket"

7. Supervisor detects ticket confirmation
   - Generates ticket_id: TKT-2026-020915
   - Extracts subject: "Investment options inquiry"
   - Compiles conversation as description

8. Supervisor → Escalation Bridge (A2A)
   POST http://localhost:9006/a2a/invoke
   Body: {
     messages: [{
       role: "user",
       content: "create_ticket: Investment options inquiry"
     }],
     customer_id: "C001",
     thread_id: "xyz789"
   }

9. Escalation Bridge parses request
   - Extracts: ticket_id, subject, description, customer info

10. Bridge → Power Automate Flow
    POST https://prod-xx.eastus.logic.azure.com:443/workflows/...
    Body: {
      ticket_id: "TKT-2026-020915",
      customer_email: "user@example.com",
      subject: "Investment options inquiry",
      description: "...",
      priority: "medium"
    }

11. Power Automate → Copilot Studio
    - Triggers bot conversation
    - Bot configured with 2 actions:
      a) Write to Excel (Add row to TicketsTable)
      b) Send email to support team

12. Copilot Studio executes:
    a) Microsoft Graph API → SharePoint
       - Opens tickets.xlsx
       - Appends row to TicketsTable
    
    b) Microsoft Graph API → Outlook
       - Sends email to support team
       - Subject: "New ticket: TKT-2026-020915"

13. Power Automate → Escalation Bridge
    { status: "success", ticket_id: "TKT-2026-020915" }

14. Escalation Bridge → Supervisor
    "Ticket TKT-2026-020915 created successfully. 
     You'll receive an email confirmation shortly."

15. Supervisor → User
    (Displays confirmation message)
```

---

## 🎯 Use Cases

### UC1: Financial Operations
**Agents:** Account, Transaction, Payment
**MCP Servers:** Account, Transaction, Payment, Limits, Contacts

**Flows:**
- Check account balance
- View transaction history
- Transfer money (with confirmation)
- Manage beneficiaries
- Check daily limits

---

### UC2: Product Information
**Agent:** ProdInfo FAQ Agent
**Data Source:** Azure AI Search (RAG)

**Flows:**
- Ask about savings accounts
- Compare loan products
- Check interest rates
- Learn about account features

**Knowledge Base:** Bank product documentation indexed in Azure AI Search

---

### UC3: Financial Coaching
**Agent:** AI Money Coach Agent
**Data Source:** Vector Store (Azure AI Foundry)

**Flows:**
- Get debt management advice
- Learn budgeting strategies
- Understand good vs bad debt
- Investment guidance

**Knowledge Base:** Personal finance book stored as embeddings

---

### UC4: Escalation & Support
**Agent:** Escalation Copilot Bridge
**Integration:** Power Automate + Copilot Studio

**Flows:**
- Agent cannot answer query
- Offer ticket creation
- Create ticket in Excel
- Send email notification
- Confirm to user

**Triggers:** When ProdInfo or AI Coach agents reach knowledge limits

---

## 🚀 Running the Project

### Prerequisites
- Python 3.11+
- Node.js 18+
- Azure CLI (authenticated)
- Azure AI Foundry project
- Power Automate flow
- Copilot Studio bot

### Start All Services

```powershell
# 1. Start MCP Servers (already deployed to Azure Container Apps)
# URLs configured in copilot/.env

# 2. Start A2A Agents (local development)
# Terminal 1 - Account Agent
cd claude_bank/app/agents/account-agent-a2a
python main.py  # Port 9001

# Terminal 2 - Transaction Agent
cd claude_bank/app/agents/transaction-agent-a2a
python main.py  # Port 9002

# Terminal 3 - Payment Agent
cd claude_bank/app/agents/payment-agent-v3-a2a
python main.py  # Port 9003

# Terminal 4 - ProdInfo FAQ Agent
cd claude_bank/app/agents/prodinfo-faq-agent-a2a
python main.py  # Port 9004

# Terminal 5 - AI Money Coach Agent
cd claude_bank/app/agents/ai-money-coach-agent-a2a
python main.py  # Port 9005

# Terminal 6 - Escalation Bridge
cd claude_bank/app/agents/escalation-copilot-bridge
python main.py  # Port 9006

# 3. Start Copilot (Supervisor)
cd claude_bank/app/copilot
uvicorn app.main:app --reload  # Port 5000

# 4. Start Frontend
cd claude_bank/app/frontend
npm install
npm run dev  # Port 3000
```

### Access
- **Frontend:** http://localhost:3000
- **Copilot API:** http://localhost:5000
- **Agent Health Checks:** http://localhost:900X/health

---

## 📁 Project Structure

```
claude_bank/
├── app/
│   ├── copilot/               # Supervisor agent & API
│   │   ├── app/api/           # FastAPI routers
│   │   ├── app/agents/        # Agent orchestration logic
│   │   └── .env               # Central configuration
│   │
│   ├── agents/                # A2A Specialist Agents
│   │   ├── account-agent-a2a/
│   │   ├── transaction-agent-a2a/
│   │   ├── payment-agent-v3-a2a/
│   │   ├── prodinfo-faq-agent-a2a/
│   │   ├── ai-money-coach-agent-a2a/
│   │   └── escalation-copilot-bridge/
│   │
│   ├── business-api/python/   # MCP Servers
│   │   ├── account/           # Account MCP
│   │   ├── transaction/       # Transaction MCP
│   │   ├── payment-unified/   # Payment MCP
│   │   ├── limits/            # Limits MCP
│   │   └── contacts/          # Contacts MCP
│   │
│   └── frontend/              # React UI
│       ├── src/
│       └── public/
│
└── InitialData/               # Sample banking data
```

---

## 🔑 Key Configuration Files

### 1. Copilot `.env`
**Location:** `claude_bank/app/copilot/.env`

**Critical Settings:**
```env
# Azure AI Foundry
FOUNDRY_PROJECT_ENDPOINT=https://banking-new-resources...
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=gpt-4.1-mini

# MCP Server URLs (deployed)
ACCOUNT_MCP_URL=https://account-mcp...
TRANSACTION_MCP_URL=https://transaction...
PAYMENT_MCP_URL=https://payment-mcp...
LIMITS_MCP_URL=https://limits-mcp...
CONTACTS_MCP_URL=https://contacts-mcp...

# Agent Names (Azure AI Foundry)
SUPERVISOR_AGENT_NAME=supervisor-a2a
ACCOUNT_AGENT_NAME=account-a2a
TRANSACTION_AGENT_NAME=transaction-a2a
PAYMENT_AGENT_NAME=payment-a2a
PRODINFO_FAQ_AGENT_NAME=prodinfo-faq-a2a
AI_MONEY_COACH_AGENT_NAME=ai-money-coach-a2a

# Escalation
ESCALATION_AGENT_A2A_URL=http://localhost:9006
```

### 2. Agent `.env` Files
Each A2A agent has its own `.env`:
- `account-agent-a2a/.env`
- `transaction-agent-a2a/.env`
- `payment-agent-v3-a2a/.env`
- etc.

**Common pattern:**
```env
AZURE_AI_PROJECT_ENDPOINT=...
ACCOUNT_MCP_SERVER_URL=https://account-mcp...
A2A_SERVER_PORT=9001
```

### 3. Escalation Bridge `.env`
**Location:** `escalation-copilot-bridge/.env`

**Required:**
```env
POWER_AUTOMATE_FLOW_URL=https://prod-xx.eastus.logic.azure.com/...
COPILOT_BOT_NAME=BankX Support Bot
A2A_SERVER_PORT=9006
```

---

## 🧠 How Dynamic Routing Works

### Supervisor Routing Logic

The Copilot (Supervisor) uses **intelligent intent detection** to route queries:

**Routing Rules** (from `supervisor_agent_foundry.py`):

```python
# Account operations
if query_about("balance", "account", "limits"):
    route_to(AccountAgent)

# Transactions
if query_about("transactions", "history", "movements"):
    route_to(TransactionAgent)

# Payments (with confirmation detection)
if query_about("transfer", "payment", "send money"):
    route_to(PaymentAgent)
if user_confirms_payment():
    route_to(PaymentAgent, confirmation=True)

# Product info
if query_about("interest rate", "account features", "products"):
    route_to(ProdInfoFAQAgent)

# Financial advice
if query_about("debt", "save money", "investment", "advice"):
    route_to(AIMoneyCoachAgent)

# Escalation
if agent_cannot_answer() and user_confirms_ticket():
    route_to(EscalationBridge)
```

**Context Awareness:**
- Tracks active conversations per customer
- Retains conversation history
- Detects confirmation responses ("yes", "confirm")
- Routes confirmations back to the requesting agent

---

## 🎭 Agent Communication (A2A Protocol)

### A2A Request Format

```python
POST http://localhost:9001/a2a/invoke
Content-Type: application/json

{
    "messages": [
        {"role": "user", "content": "What is my balance?"}
    ],
    "thread_id": "thread_abc123",
    "customer_id": "C001",
    "stream": true
}
```

### A2A Response Format

```python
{
    "role": "assistant",
    "content": "Your account balance is ฿50,000.00",
    "agent": "account-a2a"
}
```

### Agent Card (Discovery)

Each agent exposes a discovery endpoint:

```python
GET http://localhost:9001/

Response:
{
    "name": "Account Agent",
    "agent_id": "account-a2a",
    "version": "1.0.0",
    "capabilities": [
        "account_balance",
        "account_details",
        "payment_methods"
    ],
    "endpoints": {
        "chat": "http://localhost:9001/a2a/invoke",
        "health": "http://localhost:9001/health"
    },
    "mcp_servers": ["account", "limits"]
}
```

---

## 📊 Data Flow Summary

```
User Input
   ↓
Frontend (React)
   ↓
Copilot API (FastAPI)
   ↓
Supervisor Agent (Azure AI Foundry)
   ↓
[Dynamic Routing Decision]
   ↓
Specialist Agent (A2A) - Hosted locally, referenced in Foundry
   ↓
MCP Tool Call
   ↓
MCP Server (FastMCP) - Deployed to Azure Container Apps
   ↓
Database / External System
   ↓
[Response flows back up]
   ↓
User sees result
```

---

## 🎓 Key Concepts Explained

### 1. **A2A Protocol (Agent-to-Agent)**
- Standard for agents to communicate
- JSON-based message format
- Enables multi-agent orchestration
- Allows supervisor to delegate to specialists

### 2. **MCP (Model Context Protocol)**
- Exposes business logic as "tools"
- Agents call tools instead of hallucinating
- Ensures factual, verifiable responses
- Separates AI logic from data access

### 3. **Azure AI Foundry Agents**
- Agents hosted/registered in Azure AI Foundry
- Configurable via portal or API
- Support tool calling (MCP tools)
- Handle conversation threading

### 4. **Dynamic Routing**
- Supervisor analyzes user intent
- Routes to appropriate specialist
- Handles multi-turn context
- Manages confirmations and state

### 5. **Escalation Pattern**
- Agent recognizes knowledge limit
- Offers ticket creation (no assumption)
- Waits for explicit user confirmation
- Creates ticket via Copilot Studio + Power Automate
- Stores in Excel, sends email notification

---

## 🔒 Security & Auth

- **Authentication:** Microsoft Entra ID (Azure AD)
- **Authorization:** Customer ID scoped to authenticated user
- **MCP Security:** Tools validate customer_id before data access
- **Sensitive Data:** Agents reject password/PIN queries
- **Audit Trail:** All tool calls logged for compliance

---

## 📈 Observability

- **Application Insights:** Request tracing, performance metrics
- **OpenTelemetry:** Distributed tracing across agents and MCP servers
- **Logging:** Structured logs for debugging
- **Health Checks:** Each service exposes `/health` endpoint

---

## 🎉 Summary

**BankX** is a production-grade multi-agent banking platform that demonstrates:

✅ **Intelligent Routing** - Supervisor dynamically routes queries  
✅ **Zero Hallucination** - All data from MCP tools, never invented  
✅ **Multi-Agent Orchestration** - 6 specialist agents via A2A protocol  
✅ **Scalable Architecture** - MCP servers deployed to Azure Container Apps  
✅ **Enterprise Integration** - Power Automate, Copilot Studio, Microsoft Graph  
✅ **User-Friendly Escalation** - Seamless ticket creation when agents can't answer  
✅ **Modern Tech Stack** - FastAPI, React, Azure AI Foundry, FastMCP  

**Perfect for:** Learning multi-agent systems, MCP protocol, Azure AI integration, and enterprise chatbot architecture.

---

## 📞 Questions?

- **Routing issues?** Check [chat_routers.py](claude_bank/app/copilot/app/api/chat_routers.py) and [supervisor_agent_foundry.py](claude_bank/app/copilot/app/agents/foundry/supervisor_agent_foundry.py)
- **Agent not responding?** Verify `.env` files and check agent health endpoints
- **MCP connection failed?** Ensure MCP URLs in copilot `.env` are correct
- **Escalation not working?** Check Power Automate flow URL and Copilot Studio bot

---

**Built with ❤️ using Azure AI, FastAPI, and FastMCP**
