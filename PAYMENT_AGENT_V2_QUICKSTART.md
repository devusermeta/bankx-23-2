# Payment Agent v2 - Quick Start Guide

Simplified payment/transfer system with unified MCP server.

## What Was Implemented

### ✅ Complete Implementation

Two new components that **replace** the existing complex payment agent:

1. **Unified Payment MCP Server** (`claude_bank/app/business-api/python/payment-unified/`)
   - Consolidates 4-5 MCP servers into ONE
   - 6 tools for transfers: accounts, beneficiaries, limits, validation, execution
   - Thread-safe JSON operations with StateManager
   - Port 8076 (development) or 8072 (production)

2. **Payment Agent v2** (`claude_bank/app/agents/payment-agent-v2-a2a/`)
   - Simplified agent: validate → approve → execute
   - Single MCP connection (vs 4-5 in old agent)
   - Same port 9003 (no supervisor changes!)
   - Same A2A protocol (fully compatible)

## File Structure

```
claude_bank/
├── app/
│   ├── business-api/python/payment-unified/    ← NEW Unified MCP Server
│   │   ├── __init__.py
│   │   ├── models.py                           ← Pydantic data models
│   │   ├── services.py                         ← TransferService business logic
│   │   ├── mcp_tools.py                        ← 6 MCP tools
│   │   ├── main.py                             ← FastAPI server
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── README.md                           ← Detailed MCP docs
│   │
│   └── agents/payment-agent-v2-a2a/            ← NEW Payment Agent v2
│       ├── __init__.py
│       ├── audited_mcp_tool.py                 ← Compliance wrapper
│       ├── agent_handler.py                    ← Agent logic
│       ├── main.py                             ← A2A server
│       ├── prompts/payment_agent.md            ← Agent instructions
│       ├── requirements.txt
│       ├── .env.example
│       └── README.md                           ← Detailed agent docs
```

## Quick Start (5 Minutes)

### Step 1: Install Dependencies

```powershell
# Unified MCP Server
cd claude_bank\app\business-api\python\payment-unified
pip install -r requirements.txt

# Payment Agent v2
cd ..\..\..\..\agents\payment-agent-v2-a2a
pip install -r requirements.txt
```

### Step 2: Configure

**MCP Server** (payment-unified/.env):
```bash
# Copy example
cp .env.example .env

# Edit if needed (defaults work for local dev)
PAYMENT_UNIFIED_MCP_PORT=8076
```

**Agent** (payment-agent-v2-a2a/.env):
```bash
# Copy example
cp .env.example .env

# REQUIRED: Set Azure credentials
AZURE_PROJECT_ENDPOINT=<your-azure-ai-project-endpoint>
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini

# MCP URL (local development)
PAYMENT_UNIFIED_MCP_URL=http://localhost:8076/mcp
```

### Step 3: Run

**Terminal 1 - Start MCP Server**:
```powershell
cd claude_bank\app\business-api\python\payment-unified
python main.py

# Should see:
# ✅ Connected to Azure AI Project
# ✅ Payment Unified MCP Server started on port 8076
```

**Terminal 2 - Start Agent**:
```powershell
cd claude_bank\app\agents\payment-agent-v2-a2a
python main.py

# Should see:
# ✅ Payment Agent v2 A2A Server ready on 0.0.0.0:9003
```

### Step 4: Test

```powershell
# Health check
curl http://localhost:8076/health
curl http://localhost:9003/health

# Test transfer via A2A
curl -X POST http://localhost:9003/a2a/invoke `
  -H "Content-Type: application/json" `
  -d '{
    "messages": [
      {"role": "user", "content": "Transfer 5000 THB to account 1234567890"}
    ],
    "customer_id": "CUST-001",
    "user_email": "john@bankx.com"
  }'
```

## Development with Ngrok

To test before deploying MCP server to Azure:

### Step 1: Start MCP Server Locally
```powershell
cd claude_bank\app\business-api\python\payment-unified
python main.py
```

### Step 2: Expose with Ngrok
```powershell
ngrok http 8076
# Note the HTTPS URL: https://abc123.ngrok.io
```

### Step 3: Update Agent Config
```powershell
# Edit payment-agent-v2-a2a/.env
PAYMENT_UNIFIED_MCP_URL=https://abc123.ngrok.io/mcp
```

### Step 4: Start Agent
```powershell
cd claude_bank\app\agents\payment-agent-v2-a2a
python main.py
```

Now the agent connects to MCP server through ngrok!

## Integration with Existing System

### No Changes Required!

✅ **Supervisor** (`app/copilot/app/agents/foundry/supervisor_agent_foundry.py`)
- No changes needed
- Still calls `route_to_payment_agent()` 
- Same port 9003

✅ **Frontend** (`app/frontend/src/components/HumanInLoopConfirmation/`)
- No changes needed
- Detects "TRANSFER CONFIRMATION REQUIRED" pattern
- Shows [Approve][Cancel] buttons automatically

✅ **Data Files** (`dynamic_data/*.json`)
- No changes needed
- Same StateManager for thread-safe operations

### Migration Steps

1. **Stop old payment agent** (port 9003)
2. **Start new agent** (same port 9003)
3. **Done!**

## How It Works

### The Simplified Flow

**User Request**: "Transfer 5000 THB to John"

**Agent Actions**:
1. `getAccountsByUserName("john@bankx.com")` → Get sender's accounts
2. `validateTransfer("CHK-001", "John", 5000)` → Validate everything
3. Show approval request (ONE question only):
   ```
   TRANSFER CONFIRMATION REQUIRED
   
   From: John Smith (CHK-001)
   To: Jane Doe (1234567890)
   Amount: 5,000.00 THB
   
   Do you want to approve this transfer?
   ```
4. User: "Yes"
5. `executeTransfer("CHK-001", "SAV-005", 5000, "Transfer")` → Execute
6. Confirm: "✅ Transfer completed! Transaction ID: TXN-xxx"

### MCP Tools Available

From unified payment-unified MCP server:

1. **getAccountsByUserName**(username) - List accounts
2. **getAccountDetails**(account_id) - Account info
3. **getRegisteredBeneficiaries**(customer_id) - Saved recipients
4. **checkLimits**(account_id, amount) - Validate limits
5. **validateTransfer**(sender, recipient, amount) - Pre-execution validation
6. **executeTransfer**(sender, recipient, amount, desc) - Execute transfer

## Transaction Limits

Limits are **stored in dynamic_data/limits.json** and **vary by account**:

- **Per-Transaction Limit**: Account-specific (commonly 50,000 THB)
- **Daily Limit**: Account-specific (commonly 200,000 THB, resets at midnight)
- **Currency**: THB only

Limits checked **twice**:
1. Before approval (validation)
2. Before execution (safety check)

Each account can have different limits configured in the limits.json file.

## Example Conversations

### ✅ Successful Transfer

```
User: Transfer 5000 THB to account 1234567890

Agent: TRANSFER CONFIRMATION REQUIRED

From: John Smith (CHK-001)
To: Jane Doe (1234567890)
Amount: 5,000.00 THB

New balance after transfer: 45,000.00 THB
Daily limit remaining: 195,000.00 THB

Do you want to approve this transfer?

User: Yes

Agent: ✅ Transfer completed successfully!

Transaction ID: TXN-20240115103045-CHK0
Your new balance: 45,000.00 THB
Daily limit remaining: 195,000.00 THB
```

### ❌ Insufficient Balance

```
User: Transfer 100000 THB to account 1234567890

Agent: ❌ Transfer cannot proceed: Insufficient balance
Your available balance: 50,000.00 THB
Transfer amount: 100,000.00 THB
```

### ❌ Exceeds Limit

```
User: Transfer 60000 THB to account 1234567890

Agent: ❌ Transfer cannot proceed: Amount exceeds per-transaction limit
Your limit: 50,000.00 THB
Requested amount: 60,000.00 THB
```

## Troubleshooting

### MCP Server Won't Start

```powershell
# Check if port 8076 is in use
netstat -ano | findstr :8076

# Check data files exist
ls claude_bank\dynamic_data\*.json

# Increase logging
$env:LOG_LEVEL = "DEBUG"
python main.py
```

### Agent Won't Start

```powershell
# Check Azure credentials
az login
az account show

# Check environment variables
echo $env:AZURE_PROJECT_ENDPOINT
echo $env:PAYMENT_UNIFIED_MCP_URL

# Check if port 9003 is free
netstat -ano | findstr :9003
```

### Agent Can't Connect to MCP

```powershell
# Verify MCP server is running
curl http://localhost:8076/health

# Check URL has /mcp suffix
echo $env:PAYMENT_UNIFIED_MCP_URL
# Should be: http://localhost:8076/mcp
# Not: http://localhost:8076
```

### Approval Card Not Showing

Check agent output includes:
- Exact phrase: `TRANSFER CONFIRMATION REQUIRED`
- Proper format (see examples above)

Check browser console for:
```
"Detected approval pattern: TRANSFER CONFIRMATION REQUIRED"
```

## Next Steps

### 1. Testing
- Test various transfer amounts
- Test with different accounts
- Test limit scenarios
- Test approval/cancellation

### 2. Deploy MCP Server to Azure
- Build Docker image
- Deploy to Azure Container Apps
- Update agent's PAYMENT_UNIFIED_MCP_URL

### 3. Deploy Agent to Azure
- Build Docker image  
- Deploy to Azure Container Apps on port 9003
- Update supervisor to point to new agent

### 4. Retire Old Agent
- Stop old payment-agent-a2a
- Archive code
- Monitor logs

## Documentation

Detailed documentation available:

- **MCP Server**: `claude_bank/app/business-api/python/payment-unified/README.md`
- **Agent**: `claude_bank/app/agents/payment-agent-v2-a2a/README.md`

## What's Different from Old Agent

| Feature | Old Agent | New Agent v2 |
|---------|-----------|--------------|
| MCP Servers | 4-5 connections | 1 connection |
| Flow Steps | 8+ steps | 3 steps |
| Questions | Multiple | One approval |
| Beneficiary Mgmt | Interactive | Passive |
| Retries | Yes | No (fail fast) |
| Code Lines | ~1500 | ~600 |
| Complexity | High | Low |

## Benefits

✅ **Faster**: Single MCP connection, fewer round-trips
✅ **Simpler**: 3-step flow vs 8+ steps
✅ **Clearer**: One approval, no confusing questions
✅ **Safer**: Limits checked twice (validation + execution)
✅ **Compatible**: Same port, same protocol, no migration
✅ **Maintainable**: 60% less code, better organized

## Support

For issues:
1. Check logs (console output)
2. Verify both servers running
3. Test health endpoints first
4. Check Azure credentials
5. Verify data files present

## Summary

You now have:
- ✅ Unified Payment MCP Server (6 tools, 1 connection)
- ✅ Payment Agent v2 (simplified flow)
- ✅ Complete configuration files
- ✅ Comprehensive documentation
- ✅ Ready for local testing
- ✅ Ready for ngrok development
- ✅ Ready for Azure deployment

**No changes needed to supervisor or frontend!**

Start both servers and test! 🚀
