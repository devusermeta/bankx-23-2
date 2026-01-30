# Account Agent - Banking Platform

Account Agent with unified MCP server providing account information and transaction limits functionality.

## Architecture

```
┌─────────────────────────────────────────┐
│  Client / Frontend                       │
└──────────────┬──────────────────────────┘
               │ HTTP (A2A Protocol)
┌──────────────▼──────────────────────────┐
│  Account A2A Agent (Port 9001)          │
│  - Agent Card: /.well-known/agent.json │
│  - Chat: /a2a/invoke                    │
│  - Azure AI Foundry Hosted              │
└──────────────┬──────────────────────────┘
               │ MCP Protocol
┌──────────────▼──────────────────────────┐
│  Account MCP Server (Port 8070)         │
│  - getAccountsByUserName                │
│  - getAccountDetails                    │
│  - getPaymentMethodDetails              │
│  - checkLimits                          │
│  - getAccountLimits                     │
└─────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│  dynamic_data/ (JSON Files)             │
│  - accounts.json                        │
│  - limits.json                          │
│  - customers.json                       │
└─────────────────────────────────────────┘
```

## Project Structure

```
banking-platform/
├── account-agent-a2a/
│   ├── mcp-server/               # MCP Server (Port 8070)
│   │   ├── main.py               # Entry point
│   │   ├── mcp_tools.py          # Tool definitions
│   │   ├── services.py           # Business logic
│   │   ├── models.py             # Data models
│   │   ├── data_loader_service.py # JSON data access
│   │   ├── logging_config.py     # Logging setup
│   │   ├── start.ps1             # Startup script
│   │   └── pyproject.toml        # Dependencies
│   │
│   ├── a2a-agent/                # A2A Server (Port 9001)
│   │   ├── main.py               # FastAPI server
│   │   ├── agent_handler.py      # Agent lifecycle
│   │   ├── config.py             # Configuration
│   │   ├── create_agent_in_foundry.py  # Agent creation
│   │   ├── .env                  # Environment variables
│   │   └── pyproject.toml        # Dependencies
│   │
│   └── prompts/
│       └── account_agent.md      # Agent instructions
│
├── InitialData/                  # Seed data (CSV)
│   ├── accounts.csv
│   ├── limits.csv
│   └── customers.csv
│
├── dynamic_data/                 # Runtime state (JSON)
│   ├── accounts.json
│   ├── limits.json
│   └── customers.json
│
└── scripts/
    └── init_data.py              # CSV to JSON converter
```

## Setup Instructions

### Prerequisites

- Python 3.11+
- Azure CLI installed and logged in (`az login`)
- Azure AI Foundry project created
- Access to deploy agents in Azure AI Foundry

### Step 1: Install Dependencies

**MCP Server:**
```powershell
cd account-agent-a2a\mcp-server
pip install -e .
```

**A2A Agent:**
```powershell
cd ..\a2a-agent
pip install -e .
```

### Step 2: Initialize Data

Convert CSV seed data to JSON runtime files:

```powershell
cd ..\..\scripts
python init_data.py
```

This creates JSON files in `dynamic_data/`:
- `accounts.json` - Account balances (updated on transactions)
- `limits.json` - Transaction limits (updated on transactions)
- `customers.json` - Customer information

### Step 3: Create Agent in Azure AI Foundry

Run the agent creation script (one-time setup):

```powershell
cd ..\account-agent-a2a\a2a-agent
python create_agent_in_foundry.py
```

This will:
1. Create `AccountAgent` in Azure AI Foundry
2. Configure MCP tool connections
3. Output agent name and version

**Update `.env` file** with the returned values:
```env
ACCOUNT_AGENT_NAME=AccountAgent
ACCOUNT_AGENT_VERSION=1
```

### Step 4: Start MCP Server

```powershell
cd ..\mcp-server
python main.py
```

Or use the PowerShell script:
```powershell
.\start.ps1
```

Server starts on **http://localhost:8070/mcp**

### Step 5: Start A2A Agent Server

```powershell
cd ..\a2a-agent
python main.py
```

Server starts on **http://localhost:9001**

## Testing

### 1. Test Agent Card Discovery

```powershell
curl http://localhost:9001/.well-known/agent.json
```

### 2. Test Health Check

```powershell
curl http://localhost:9001/health
```

### 3. Test Agent Queries

**Get Account Balance:**
```powershell
curl -X POST http://localhost:9001/a2a/invoke `
  -H "Content-Type: application/json" `
  -d '{
    "messages": [
      {"role": "user", "content": "What accounts does somchai.rattanakorn@example.com have?"}
    ]
  }'
```

**Check Transaction Limits:**
```powershell
curl -X POST http://localhost:9001/a2a/invoke `
  -H "Content-Type: application/json" `
  -d '{
    "messages": [
      {"role": "user", "content": "What are my transaction limits for account CHK-001?"}
    ]
  }'
```

**Validate Transaction:**
```powershell
curl -X POST http://localhost:9001/a2a/invoke `
  -H "Content-Type: application/json" `
  -d '{
    "messages": [
      {"role": "user", "content": "Can I transfer 30000 THB from account CHK-001?"}
    ]
  }'
```

### 4. Test MCP Server Directly

```powershell
curl -X POST http://localhost:8070/mcp `
  -H "Content-Type: application/json" `
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "getAccountDetails",
      "arguments": {
        "accountId": "CHK-001"
      }
    }
  }'
```

## MCP Tools

### getAccountsByUserName
Get all accounts for a user by email address.

**Parameters:**
- `userName` (string): User's email address

**Example:**
```json
{
  "userName": "somchai.rattanakorn@example.com"
}
```

### getAccountDetails
Get detailed account information with balance.

**Parameters:**
- `accountId` (string): Account ID (e.g., "CHK-001")

**Returns:** Account details, balance, payment methods

### getPaymentMethodDetails
Get payment method with available balance.

**Parameters:**
- `paymentMethodId` (string): Payment method ID (e.g., "PM-CHK-001")

### checkLimits
Validate if a transaction is within all limits.

**Parameters:**
- `accountId` (string): Account ID
- `amount` (float): Transaction amount
- `currency` (string): Currency code (default: "THB")

**Returns:** Validation results (balance, per-txn limit, daily limit)

### getAccountLimits
Get comprehensive limit information for an account.

**Parameters:**
- `accountId` (string): Account ID

**Returns:** Limits with utilization percentage

## Environment Variables

**a2a-agent/.env:**
```env
# Azure AI Foundry
AZURE_AI_PROJECT_ENDPOINT=https://banking-new-resources.services.ai.azure.com/api/projects/banking-new
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4.1-mini

# Agent Settings
ACCOUNT_AGENT_NAME=AccountAgent
ACCOUNT_AGENT_VERSION=1

# MCP Server
ACCOUNT_MCP_SERVER_URL=http://localhost:8070/mcp

# A2A Server
A2A_SERVER_HOST=0.0.0.0
A2A_SERVER_PORT=9001

# Logging
LOG_LEVEL=INFO
```

## Data Management

### Runtime State (dynamic_data/)

JSON files persist runtime state across restarts:
- **accounts.json**: Current balances (updated by transactions)
- **limits.json**: Daily limit remaining (reset daily)
- **customers.json**: Customer information

### Resetting Data

To reset to initial state:
```powershell
cd scripts
python init_data.py
```

This regenerates JSON files from CSV seed data.

## Architecture Notes

### Singleton Pattern
- Agent handler is created once and reused across requests
- MCP tools are shared for performance
- Thread IDs enable conversation continuity

### Anti-Hallucination
- Agent prompt enforces tool usage for ALL data retrieval
- No manual calculations or estimations allowed
- All responses must be backed by tool calls

### Data Flow
```
User Query → A2A Server → Agent Handler → Azure AI Foundry Agent
                                                    ↓
                                            MCP Tool Call
                                                    ↓
                                            MCP Server
                                                    ↓
                                            Services Layer
                                                    ↓
                                            Data Loader
                                                    ↓
                                            JSON Files
```

## Troubleshooting

### Agent Initialization Fails
- Ensure Azure CLI is logged in: `az login`
- Verify `AZURE_AI_PROJECT_ENDPOINT` in `.env`
- Check agent name/version match Azure AI Foundry

### MCP Server Connection Error
- Verify MCP server is running on port 8070
- Check `ACCOUNT_MCP_SERVER_URL` in `.env`
- Ensure firewall allows localhost connections

### JSON Files Not Found
- Run `python scripts/init_data.py` to initialize data
- Check `dynamic_data/` folder exists
- Verify CSV files are in `InitialData/`

### Tool Calls Not Working
- Check MCP server logs for errors
- Verify tool names match exactly
- Ensure JSON files have correct schema

## Next Steps

After Account Agent is working:
1. Create Payment Agent with payment/transaction tools
2. Create Transaction Agent with transaction history
3. Create Supervisor Agent for routing
4. Add more specialized agents as needed

## License

Internal BankX project
