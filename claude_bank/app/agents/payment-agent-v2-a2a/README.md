# Payment Agent v2 - Simplified Transfer Agent

Reimagined payment agent with a streamlined **validate → approve → execute** flow.

## Overview

Payment Agent v2 **replaces** the existing `payment-agent-a2a` with a much simpler implementation:

**What Changed**:
- ✅ Single MCP server connection (payment-unified) instead of 4-5 servers
- ✅ Simplified flow: no beneficiary questions, no account verification retries
- ✅ Same port 9003 - no supervisor changes needed
- ✅ Same A2A protocol - fully compatible

**What Stayed the Same**:
- ✅ Azure AI Foundry V2 agent framework
- ✅ A2A protocol for supervisor communication
- ✅ Frontend approval card detection
- ✅ Audit logging and compliance tracking

## Architecture

```
┌─────────────────────────────┐
│  Copilot Supervisor         │
│  (Port 8080)                │
│  route_to_payment_agent()   │
└──────────┬──────────────────┘
           │
           │ A2A Protocol (JSON-RPC)
           │
           ▼
┌─────────────────────────────┐
│  Payment Agent v2           │
│  Port 9003 (UNCHANGED)      │  ◄── REPLACES old payment-agent-a2a
│  A2A Server                 │
└──────────┬──────────────────┘
           │
           │ Single MCP Connection
           │
           ▼
┌─────────────────────────────┐
│  Unified Payment MCP Server │
│  Port 8076 (dev/ngrok)      │
│  6 Consolidated Tools       │
└─────────────────────────────┘
```

## The Simplified Flow

### Old Flow (Complex):
1. Ask which account
2. Get beneficiaries
3. Ask about beneficiary management
4. Validate recipient
5. Retry if account not found
6. Check limits
7. Ask for approval
8. Execute

### New Flow (Simple):
1. **Validate**: Call `validateTransfer()` once
2. **Approve**: Show ONE approval request
3. **Execute**: Call `executeTransfer()` once

**That's it!** No extra questions, no retries.

## Installation

### Prerequisites

- Python 3.11+
- Azure AI Foundry project
- Azure OpenAI deployment
- Unified Payment MCP Server running (port 8076 or ngrok)

### 1. Install Dependencies

```bash
cd claude_bank/app/agents/payment-agent-v2-a2a
pip install -r requirements.txt
```

### 2. Configure Environment

Copy .env.example to .env:

```bash
cp .env.example .env
```

Edit .env with your configuration:

```bash
# Required
AZURE_PROJECT_ENDPOINT=<your-endpoint>
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini

# MCP Server URL (choose one):
# Local development:
PAYMENT_UNIFIED_MCP_URL=http://localhost:8076/mcp
# Ngrok (for testing):
# PAYMENT_UNIFIED_MCP_URL=https://abc123.ngrok.io/mcp
# Azure (production):
# PAYMENT_UNIFIED_MCP_URL=https://payment-unified-mcp.azurecontainerapps.io/mcp
```

### 3. Run the Agent

```bash
python main.py
```

Server will start on port **9003** (same as old payment agent).

## Development Setup with Ngrok

### Scenario: Test locally before Azure deployment

#### Step 1: Start MCP Server
```bash
cd claude_bank/app/business-api/python/payment-unified
python main.py
# Running on http://localhost:8076
```

#### Step 2: Expose MCP with Ngrok
```bash
ngrok http 8076
# Note the URL: https://abc123.ngrok.io
```

#### Step 3: Configure Agent
```bash
cd claude_bank/app/agents/payment-agent-v2-a2a
# Edit .env:
export PAYMENT_UNIFIED_MCP_URL=https://abc123.ngrok.io/mcp
```

#### Step 4: Start Agent
```bash
python main.py
# Running on http://localhost:9003
```

#### Step 5: Test
```bash
curl -X POST http://localhost:9003/a2a/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Transfer 5000 THB to account 1234567890"}
    ],
    "customer_id": "CUST-001",
    "user_email": "john@bankx.com"
  }'
```

## Agent Instructions

The agent follows instructions in `prompts/payment_agent.md`:

**Key Rules**:
- ✅ Call `validateTransfer()` ONCE before approval
- ✅ Show exactly ONE approval request
- ✅ Use pattern "TRANSFER CONFIRMATION REQUIRED" (frontend detection)
- ❌ NO questions about adding beneficiaries
- ❌ NO retry if recipient not found
- ❌ NO multiple approval requests

## API Endpoints

### Agent Card Discovery
```bash
GET /.well-known/agent.json
```

Returns agent metadata for A2A discovery.

### Chat Invocation
```bash
POST /a2a/invoke
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "Transfer 5000 THB to John"}
  ],
  "customer_id": "CUST-001",
  "user_email": "user@bankx.com",
  "thread_id": "optional-thread-id"
}
```

Returns:
```json
{
  "messages": [
    {"role": "user", "content": "Transfer 5000 THB to John"},
    {"role": "assistant", "content": "TRANSFER CONFIRMATION REQUIRED\n\nFrom: ..."}
  ],
  "thread_id": "thread-123",
  "agent": "payment-agent-v2",
  "version": "2.0.0"
}
```

### Health Check
```bash
GET /health
```

Returns agent status and configuration.

## Frontend Integration

The frontend already has approval card detection!

**Pattern Detection**:
```typescript
// frontend/src/components/HumanInLoopConfirmation/
// Detects: "TRANSFER CONFIRMATION REQUIRED"
// Extracts: amount, recipient, account
// Shows: [Approve] [Cancel] buttons
```

**Agent Output Format**:
```
TRANSFER CONFIRMATION REQUIRED

From: John Smith (CHK-001)
To: Jane Doe (1234567890)
Amount: 5,000.00 THB

New balance after transfer: 45,000.00 THB
Daily limit remaining: 195,000.00 THB

Do you want to approve this transfer?
```

Frontend automatically:
1. Detects pattern
2. Parses details
3. Shows approval card
4. Sends "Yes" or "No" back to agent

## MCP Tools Used

The agent has access to 6 tools from payment-unified MCP:

1. **getAccountsByUserName** - List customer accounts
2. **getAccountDetails** - Get account details
3. **getRegisteredBeneficiaries** - Get saved recipients
4. **checkLimits** - Validate limits (called by validateTransfer)
5. **validateTransfer** - Primary validation (before approval)
6. **executeTransfer** - Execute after approval

See: `claude_bank/app/business-api/python/payment-unified/README.md`

## Example Conversations

### Successful Transfer
```
User: Transfer 5000 THB to account 1234567890

Agent: [Calls validateTransfer()]

Agent: 
TRANSFER CONFIRMATION REQUIRED

From: John Smith (CHK-001)
To: Jane Doe (1234567890)
Amount: 5,000.00 THB

New balance after transfer: 45,000.00 THB
Daily limit remaining: 195,000.00 THB

Do you want to approve this transfer?

User: Yes

Agent: [Calls executeTransfer()]

Agent:
✅ Transfer completed successfully!

Transaction ID: TXN-20240115103045-CHK0
Your new balance: 45,000.00 THB
Daily limit remaining: 195,000.00 THB
```

### Insufficient Balance
```
User: Transfer 100000 THB to account 1234567890

Agent: [Calls validateTransfer()]

Agent:
❌ Transfer cannot proceed: Insufficient balance
Your available balance: 50,000.00 THB
Transfer amount: 100,000.00 THB
```

### Recipient Not Found
```
User: Transfer 5000 THB to account 9999999999

Agent: [Calls validateTransfer()]

Agent:
❌ Transfer cannot proceed: Recipient account not found
Account number: 9999999999

Please verify the account number with the recipient.
```

## Migration from Old Payment Agent

### What to Change:

**1. Stop Old Agent**:
```bash
# Find process on port 9003
lsof -i :9003  # macOS/Linux
netstat -ano | findstr :9003  # Windows

# Kill the process
kill -9 <PID>
```

**2. Start New Agent**:
```bash
cd claude_bank/app/agents/payment-agent-v2-a2a
python main.py
```

**3. No Supervisor Changes Needed!**
- Same port 9003
- Same A2A protocol
- Same `route_to_payment_agent()` call

### What to Keep:

- ✅ Supervisor configuration (unchanged)
- ✅ Frontend approval cards (work automatically)
- ✅ Audit logging (same format)
- ✅ Customer mapping (same customer_id/email)

## Troubleshooting

### Agent Won't Start

**Check Azure credentials**:
```bash
az login
az account show
```

**Check environment variables**:
```bash
echo $AZURE_PROJECT_ENDPOINT
echo $PAYMENT_UNIFIED_MCP_URL
```

**Check port**:
```bash
# Port 9003 must be free
lsof -i :9003  # macOS/Linux
netstat -ano | findstr :9003  # Windows
```

### MCP Connection Fails

**Verify MCP server is running**:
```bash
curl http://localhost:8076/health
# Or ngrok URL:
curl https://abc123.ngrok.io/health
```

**Check MCP URL**:
```bash
# Should end with /mcp
echo $PAYMENT_UNIFIED_MCP_URL
# ✅ http://localhost:8076/mcp
# ❌ http://localhost:8076 (missing /mcp)
```

### Agent Initialization Error

**Check Azure AI project**:
```bash
# Verify deployment exists
az ml online-deployment list \
  --resource-group <your-rg> \
  --workspace-name <your-workspace>
```

**Check deployment name**:
```bash
echo $AZURE_OPENAI_DEPLOYMENT
# Should be: gpt-4o-mini (or your deployment name)
```

### Approval Card Not Showing

**Check agent output format**:
- Must include EXACTLY: `TRANSFER CONFIRMATION REQUIRED`
- Must be in format expected by frontend

**Check frontend logs**:
```bash
# Browser console should show:
# "Detected approval pattern: TRANSFER CONFIRMATION REQUIRED"
```

## Testing

### Unit Testing

Test agent handler directly:

```python
import asyncio
from agent_handler import PaymentAgentHandler

async def test():
    handler = PaymentAgentHandler(
        customer_id="CUST-001",
        user_email="john@bankx.com"
    )
    
    await handler.initialize_agent()
    
    result = await handler.handle_message(
        "Transfer 5000 THB to account 1234567890"
    )
    
    print(result["response"])

asyncio.run(test())
```

### Integration Testing

Test via A2A endpoint:

```bash
curl -X POST http://localhost:9003/a2a/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Transfer 5000 THB to account 1234567890"}
    ],
    "customer_id": "CUST-001",
    "user_email": "john@bankx.com"
  }' | jq
```

### End-to-End Testing

Test with frontend:

1. Start MCP server: `python payment-unified/main.py`
2. Start agent: `python payment-agent-v2-a2a/main.py`
3. Start copilot: `cd app/copilot && python app/main.py`
4. Start frontend: `cd app/frontend && npm start`
5. Open browser: `http://localhost:8081`
6. Login and request transfer

## Deployment

### Prerequisites
- Azure AI Foundry project
- Azure Container Apps (or AKS)
- Unified Payment MCP deployed to Azure

### Option 1: Azure Container Apps

```bash
# Build and push image
docker build -t payment-agent-v2:latest .
docker tag payment-agent-v2:latest <your-registry>/payment-agent-v2:latest
docker push <your-registry>/payment-agent-v2:latest

# Deploy
az containerapp create \
  --name payment-agent-v2 \
  --resource-group <your-rg> \
  --environment <your-env> \
  --image <your-registry>/payment-agent-v2:latest \
  --target-port 9003 \
  --env-vars \
    AZURE_PROJECT_ENDPOINT=<endpoint> \
    PAYMENT_UNIFIED_MCP_URL=<mcp-url> \
    AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
```

### Option 2: Azure Kubernetes Service

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: payment-agent-v2
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: payment-agent
        image: <your-registry>/payment-agent-v2:latest
        ports:
        - containerPort: 9003
        env:
        - name: AZURE_PROJECT_ENDPOINT
          value: <endpoint>
        - name: PAYMENT_UNIFIED_MCP_URL
          value: <mcp-url>
```

## Comparison: Old vs New

| Feature | Old Payment Agent | Payment Agent v2 |
|---------|------------------|------------------|
| MCP Servers | 4-5 connections | 1 connection |
| Approval Flow | Multiple questions | One approval |
| Beneficiary Mgmt | Interactive | Passive lookup only |
| Account Retry | Yes (complex) | No (fail fast) |
| Lines of Code | ~1500 | ~600 |
| Complexity | High | Low |
| Port | 9003 | 9003 (same) |
| Protocol | A2A | A2A (same) |
| Frontend Compat | Yes | Yes (same) |

## Support

For issues:
1. Check logs (console output)
2. Verify MCP server is running
3. Test health endpoints
4. Check Azure credentials

## License

Part of the BankX platform.
