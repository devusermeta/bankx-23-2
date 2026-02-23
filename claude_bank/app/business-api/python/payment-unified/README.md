# Unified Payment MCP Server

Consolidated MCP server for payment/transfer operations in BankX.

## Overview

This unified MCP server **replaces** 4-5 separate MCP servers with a single consolidated server handling:
- Account lookups
- Beneficiary management  
- Limits checking
- Transfer validation
- Transfer execution

## Architecture

```
┌─────────────────────────────┐
│  Payment Agent v2 (A2A)     │
│  Port 9003                  │
└──────────┬──────────────────┘
           │
           │ Single Connection
           │
           ▼
┌─────────────────────────────┐
│  Unified Payment MCP Server │
│  Port 8076 (dev)            │
│  Port 8072 (production)     │
└──────────┬──────────────────┘
           │
           │ StateManager
           │
           ▼
┌─────────────────────────────┐
│  JSON Data Files            │
│  - accounts.json            │
│  - limits.json              │
│  - transactions.json        │
│  - contacts.json            │
│  - customers.json           │
└─────────────────────────────┘
```

## Available MCP Tools

The server exposes 6 MCP tools:

### 1. getAccountsByUserName(username: str)
Get all accounts for a customer by their BankX email.

**Usage**: First call to list available accounts for transfer.

### 2. getAccountDetails(account_id: str)
Get detailed account information including balance and limits.

**Usage**: Get specific account details when needed.

### 3. getRegisteredBeneficiaries(customer_id: str)
Get saved recipients/beneficiaries for a customer.

**Usage**: When user wants to transfer to a saved contact.

### 4. checkLimits(account_id: str, amount: float)
Check if transaction is within balance, per-txn (50K), and daily (200K) limits.

**Usage**: Called by validateTransfer (don't call separately).

### 5. validateTransfer(sender_account_id: str, recipient_identifier: str, amount: float, recipient_name: str | None)
**PRIMARY VALIDATION TOOL** - Complete pre-execution validation.

Validates:
- Sender account exists
- Recipient found (by account number or beneficiary alias)
- All limits checks pass

**Usage**: ALWAYS call before requesting approval.

### 6. executeTransfer(sender_account_id: str, recipient_account_id: str, amount: float, description: str)
Execute the transfer AFTER user approval.

**What it does**:
- Re-checks all limits
- Debits sender account
- Credits recipient account
- Updates daily limit remaining
- Creates transaction records

**Usage**: ONLY after user approves the validated transfer.

## Installation

### 1. Install Dependencies

```bash
cd claude_bank/app/business-api/python/payment-unified
pip install -r requirements.txt
```

### 2. Configure Environment

Copy .env.example to .env:

```bash
cp .env.example .env
```

Edit .env as needed (defaults should work for local development).

### 3. Run the Server

**Development (port 8076)**:
```bash
python -m app.business-api.python.payment-unified.main
```

Or with uvicorn:
```bash
uvicorn app.business-api.python.payment-unified.main:app --port 8076 --reload
```

**Production (port 8072)**:
```bash
export PAYMENT_UNIFIED_MCP_PORT=8072
uvicorn app.business-api.python.payment-unified.main:app --port 8072
```

## Development with Ngrok

For testing with the Payment Agent v2 before Azure deployment:

### 1. Start MCP Server Locally
```bash
python -m app.business-api.python.payment-unified.main
# Server running on http://localhost:8076
```

### 2. Expose with Ngrok
```bash
ngrok http 8076
# Note the HTTPS URL: https://abc123.ngrok.io
```

### 3. Configure Agent
Set environment variable for Payment Agent v2:

```bash
export PAYMENT_UNIFIED_MCP_URL=https://abc123.ngrok.io/mcp
```

Now the agent can connect to the MCP server through ngrok!

## Endpoints

- **Health Check**: `GET /health`
- **Root**: `GET /`
- **MCP**: `/mcp` (MCP protocol endpoint)

Example:
```bash
# Health check
curl http://localhost:8076/health

# Root info
curl http://localhost:8076/
```

## Data Files

The server uses StateManager to access JSON files in `dynamic_data/`:

- `accounts.json` - Account balances and details
- `limits.json` - Transaction limits and daily tracking
- `transactions.json` - Transaction history
- `contacts.json` - Beneficiary/contact lists
- `customers.json` - Customer information

All file operations are **thread-safe** using FileLock.

## Transaction Limits

Limits are **stored in limits.json** and are **account-specific**. Current configuration:

- **Per-Transaction**: Typically 50,000 THB (varies by account)
- **Daily**: Typically 200,000 THB (resets at midnight automatically, varies by account)
- **Currency**: THB

Limits are retrieved dynamically from `dynamic_data/limits.json` for each account. The system supports different limits per account. only

The server automatically:
- Checks limits before transactions
- Updates remaining daily limit
- Resets daily limits at midnight

## Validation Flow

### Standard Transfer Flow:
```
1. validateTransfer()
   ├─ Verify sender account
   ├─ Lookup recipient (account # or alias)
   ├─ Check balance
   ├─ Check per-txn limit (50K)
   ├─ Check daily limit (200K)
   └─ Return complete validation

2. [User Approval Required]

3. executeTransfer()
   ├─ RE-CHECK all limits
   ├─ Debit sender
   ├─ Credit recipient
   ├─ Update daily limit
   ├─ Create transaction records
   └─ Return transaction ID
```

## Error Handling

The server returns detailed error messages:

**Insufficient Balance**:
```json
{
  "success": false,
  "error_message": "Insufficient balance (available: 1,000.00 THB)"
}
```

**Exceeds Limit**:
```json
{
  "success": false,
  "error_message": "Exceeds per-transaction limit (50,000.00 THB)"
}
```

**Recipient Not Found**:
```json
{
  "success": false,
  "error_message": "Recipient account not found: 1234567890"
}
```

## Testing

### Manual Tool Testing

You can test individual tools using curl or Python:

```bash
# Test health check
curl http://localhost:8076/health

# Test MCP tools (requires MCP client)
# See: https://modelcontextprotocol.io/docs
```

### Integration Testing

Test with Payment Agent v2:

```bash
# Start MCP server
python -m app.business-api.python.payment-unified.main

# In another terminal, start Payment Agent v2
cd claude_bank/app/agents/payment-agent-v2-a2a
python main.py

# Send test request via A2A protocol
curl -X POST http://localhost:9003/a2a/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Transfer 5000 THB to account 1234567890"}],
    "customer_id": "CUST-001",
    "user_email": "user@bankx.com"
  }'
```

## Deployment to Azure

### Option 1: Azure Container Apps

1. Build Docker image:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8072"]
```

2. Deploy to Azure Container Apps:
```bash
az containerapp create \
  --name payment-unified-mcp \
  --resource-group <your-rg> \
  --environment <your-env> \
  --image <your-image> \
  --target-port 8072
```

### Option 2: Azure MCP Hosting

Deploy using Azure AI Foundry MCP hosting (recommended for production).

See: [Azure MCP Documentation](https://learn.microsoft.com/azure/ai-foundry/)

## Troubleshooting

### Server Won't Start

**Check ports**:
```bash
# See what's using port 8076
lsof -i :8076  # macOS/Linux
netstat -ano | findstr :8076  # Windows
```

**Check logs**:
```bash
# Increase log level
export LOG_LEVEL=DEBUG
python -m app.business-api.python.payment-unified.main
```

### MCP Connection Fails

**Verify server is running**:
```bash
curl http://localhost:8076/health
```

**Check MCP URL in agent config**:
```bash
echo $PAYMENT_UNIFIED_MCP_URL
# Should be: http://localhost:8076/mcp
# Or ngrok URL: https://abc123.ngrok.io/mcp
```

### Data File Errors

**Check file paths**:
```bash
# Ensure dynamic_data/ exists and has JSON files
ls -la claude_bank/dynamic_data/
```

**Check permissions**:
```bash
# Server needs read/write access
chmod 644 claude_bank/dynamic_data/*.json
```

## Migration from Old MCP Servers

This server **replaces**:
- `account` MCP (port 8070)
- `transaction` MCP (port 8071)
- `payment` MCP (port 8072)
- `contacts` MCP (port 8074)
- `limits` MCP (port 8073)

**No migration needed** - just use the new unified server:

**Before** (5 connections):
```python
account_mcp = MCPTool("http://localhost:8070/mcp")
transaction_mcp = MCPTool("http://localhost:8071/mcp")
payment_mcp = MCPTool("http://localhost:8072/mcp")
limits_mcp = MCPTool("http://localhost:8073/mcp")
contacts_mcp = MCPTool("http://localhost:8074/mcp")
```

**After** (1 connection):
```python
payment_mcp = MCPTool("http://localhost:8076/mcp")
# All tools available from single server!
```

## Support

For issues or questions:
1. Check logs for detailed error messages
2. Verify all environment variables are set
3. Ensure data files are present and accessible
4. Test health endpoint first

## License

Part of the BankX platform.
