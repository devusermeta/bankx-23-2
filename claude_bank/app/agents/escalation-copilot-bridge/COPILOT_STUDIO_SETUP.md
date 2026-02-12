# Copilot Studio A2A Bridge - Setup Guide

## Overview

This bridge agent allows your local A2A agent system to call your **Copilot Studio agent** for escalations. The Copilot Studio agent handles email sending (via Outlook connector) and Excel storage.

## Architecture

```
Local A2A System
    ↓
Escalation Bridge (Port 9006) - FastAPI Server
    ↓
Direct Line API (Bot Framework)
    ↓
Copilot Studio Agent (Cloud) → Outlook Connector → Excel
```

---

## Prerequisites

### 1. Copilot Studio Agent

You should have already created your Copilot Studio agent with:
- ✅ Outlook connector configured for sending emails
- ✅ Excel connector configured for storing ticket data
- ✅ Agent published and active

### 2. Required Information from Copilot Studio

You need to gather these credentials from your Copilot Studio agent.

---

## Step-by-Step: Get Copilot Studio Credentials

### Step 1: Open Your Copilot Studio Agent

1. Go to [Copilot Studio](https://copilotstudio.microsoft.com/)
2. Sign in with your **metakaal.com** tenant account
3. Select your **environment** (the one where you created the escalation agent)
4. Open your **Escalation Agent**

### Step 2: Enable Direct Line Channel

The Direct Line channel allows external applications to communicate with your Copilot Studio agent.

1. In your agent, go to **Settings** → **Channels**
2. Find **Direct Line** in the list of channels
3. Click **Turn on** or **Enable**
4. You'll see the Direct Line configuration page

### Step 3: Get Direct Line Secret Key

1. On the Direct Line channel page, you'll see **Secret keys**
2. There will be two keys: **Key 1** and **Key 2** (either works)
3. Click **Show** next to Key 1
4. **Copy the entire key** - it's a long string like:
   ```
   abc123XYZ...very-long-string...xyz789
   ```
5. ⚠️ **Save this securely** - you'll need it for the `.env` file

### Step 4: Note Other Information

While in Copilot Studio, note down:

- **Agent/Bot Name**: The name of your agent (e.g., "EscalationAgent")
- **Environment ID**: 
  - In Copilot Studio, look at the URL
  - It will contain your environment ID: `https://copilotstudio.microsoft.com/environments/{environment-id}/...`
  - Copy the GUID from the URL
  
### Step 5: Get Azure Tenant ID (metakaal.com)

1. Go to [Azure Portal](https://portal.azure.com)
2. Sign in with your **metakaal.com** account (where resources are created)
3. Click on **Azure Active Directory** or **Microsoft Entra ID**
4. In the overview page, you'll see **Tenant ID** - copy this

---

## Configuration

### Step 1: Copy Environment Template

```powershell
cd d:\Metakaal\Updated_BankX\claude_bank\app\agents\escalation-copilot-bridge
cp .env.example .env
```

### Step 2: Edit `.env` File

Open the `.env` file and fill in your values:

```dotenv
# ==========================================
# Copilot Studio Configuration (REQUIRED)
# ==========================================

# Paste the Direct Line secret key you copied from Copilot Studio
COPILOT_DIRECT_LINE_SECRET=your-secret-key-here

# This is usually the default endpoint
COPILOT_DIRECT_LINE_ENDPOINT=https://directline.botframework.com/v3/directline

# Your agent's name
COPILOT_BOT_NAME=EscalationAgent

# Optional: Bot ID and Environment ID for reference
COPILOT_BOT_ID=your-bot-id (optional)
COPILOT_ENVIRONMENT_ID=your-environment-guid (optional)

# Timeout settings (how long to wait for Copilot Studio response)
COPILOT_TIMEOUT_SECONDS=30
COPILOT_MAX_RESPONSE_WAIT=30

# ==========================================
# Azure Tenant Configuration (REQUIRED)
# ==========================================

# Your metakaal.com tenant ID
AZURE_TENANT_ID=your-metakaal-tenant-id

# ==========================================
# Service Configuration
# ==========================================

# Port for A2A server (default: 9006)
A2A_SERVER_PORT=9006

# Agent Registry URL (if you have one)
AGENT_REGISTRY_URL=http://localhost:9000

# Log level
LOG_LEVEL=INFO
```

### Step 3: Save the File

Save the `.env` file with your actual values.

---

## Installation

### Step 1: Install Dependencies

```powershell
cd d:\Metakaal\Updated_BankX\claude_bank\app\agents\escalation-copilot-bridge
pip install -r requirements.txt
```

### Step 2: Verify Configuration

Run the configuration check:

```powershell
python -c "from config import settings, validate_settings; is_valid, errors = validate_settings(); print('Valid:', is_valid); print('Errors:', errors)"
```

You should see:
```
Valid: True
Errors: []
```

If you see errors, fix them in your `.env` file.

---

## Testing

### Step 1: Start the Bridge Service

```powershell
python main.py
```

You should see output like:
```
[2026-02-12 10:00:00] [INFO] Starting EscalationCopilotBridge v1.0.0
[2026-02-12 10:00:00] [INFO] Port: 9006
[2026-02-12 10:00:00] [INFO] Configuration validated successfully
[2026-02-12 10:00:01] [INFO] Copilot Studio client initialized
[2026-02-12 10:00:01] [INFO] Bot Name: EscalationAgent
[2026-02-12 10:00:02] [INFO] ✓ Successfully connected to Copilot Studio agent
[2026-02-12 10:00:02] [INFO] EscalationCopilotBridge started successfully
INFO:     Uvicorn running on http://0.0.0.0:9006
```

### Step 2: Test Health Endpoint

In another terminal:

```powershell
curl http://localhost:9006/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "EscalationCopilotBridge",
  "version": "1.0.0",
  "copilot_studio": "configured",
  "bot_name": "EscalationAgent"
}
```

### Step 3: Test Configuration Status

```powershell
curl http://localhost:9006/config/status
```

You should see:
```json
{
  "valid": true,
  "errors": [],
  "settings": {
    "service_name": "EscalationCopilotBridge",
    "version": "1.0.0",
    "port": 9006,
    "agent_name": "EscalationAgent",
    "copilot_configured": true,
    "copilot_bot_name": "EscalationAgent",
    ...
  }
}
```

### Step 4: Test Copilot Studio Connection

Send a test message to your Copilot Studio agent:

```powershell
curl -X POST "http://localhost:9006/test/copilot?message=Hello%20from%20A2A%20Bridge"
```

Expected response:
```json
{
  "success": true,
  "message": "Received response from Copilot Studio",
  "response": "Hello! I'm the Escalation Agent. How can I help you?"
}
```

### Step 5: Test Escalation Creation

Create a test escalation ticket:

```powershell
curl -X POST http://localhost:9006/test/escalation
```

Expected response:
```json
{
  "success": true,
  "ticket_id": "TKT-2026-021210305",
  "response": "...",
  "timestamp": "2026-02-12T10:30:05Z"
}
```

This will:
1. Call your Copilot Studio agent
2. Copilot Studio will send an email via Outlook connector
3. Copilot Studio will store the ticket in Excel
4. Response will be returned to the bridge

### Step 6: Test Full A2A Protocol

Use the A2A test script (see below) to test like other agents will call it.

---

## A2A Protocol Testing

### Create Test Script

Save this as `test_a2a_escalation.py`:

```python
import httpx
import asyncio
import json

async def test_a2a_escalation():
    """Test the escalation bridge using A2A protocol"""
    
    url = "http://localhost:9006/a2a/invoke"
    
    # Simulate request from another agent (like ProdInfo)
    request_payload = {
        "messages": [
            {
                "role": "user",
                "content": (
                    "Create escalation ticket: "
                    "Customer is unable to access their account. "
                    "Customer Email: john.doe@example.com, "
                    "Customer Name: John Doe"
                )
            }
        ],
        "customer_id": "CUST-12345",
        "thread_id": "test-thread-001"
    }
    
    print("=" * 60)
    print("Testing A2A Escalation Bridge")
    print("=" * 60)
    print("\nRequest:")
    print(json.dumps(request_payload, indent=2))
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(url, json=request_payload)
            response.raise_for_status()
            
            result = response.json()
            
            print("\n" + "=" * 60)
            print("Response:")
            print("=" * 60)
            print(json.dumps(result, indent=2))
            print("\n✓ Escalation successful!")
            
        except Exception as e:
            print(f"\n✗ Error: {e}")
            if hasattr(e, 'response'):
                print(f"Response: {e.response.text}")

if __name__ == "__main__":
    asyncio.run(test_a2a_escalation())
```

### Run Test

```powershell
python test_a2a_escalation.py
```

Expected output:
```
============================================================
Testing A2A Escalation Bridge
============================================================

Request:
{
  "messages": [...],
  "customer_id": "CUST-12345",
  ...
}

============================================================
Response:
============================================================
{
  "role": "assistant",
  "content": "Support ticket TKT-2026-021210352 created successfully. Email notification sent to customer. Our support team will contact the customer within 24 business hours.",
  "agent": "EscalationAgent"
}

✓ Escalation successful!
```

---

## Troubleshooting

### Issue: "COPILOT_DIRECT_LINE_SECRET is not set"

**Solution**: 
- Make sure you created the `.env` file from `.env.example`
- Check that you pasted the Direct Line secret key correctly
- No extra spaces or quotes around the key

### Issue: "Failed to start conversation with Copilot Studio"

**Possible causes**:
1. **Wrong secret key** - Go back to Copilot Studio and copy the key again
2. **Agent not published** - Make sure your Copilot Studio agent is published
3. **Direct Line channel not enabled** - Check that Direct Line is turned on
4. **Network issues** - Check internet connectivity

**Solution**:
```powershell
# Test Direct Line manually using curl
curl -X POST "https://directline.botframework.com/v3/directline/conversations" `
  -H "Authorization: Bearer YOUR_SECRET_KEY"
```

You should get a conversation ID back.

### Issue: "No response from Copilot Studio (timeout)"

**Possible causes**:
- Copilot Studio agent is slow to respond
- Your agent has complex logic that takes time
- Network latency

**Solution**:
- Increase timeout in `.env`:
  ```dotenv
  COPILOT_TIMEOUT_SECONDS=60
  COPILOT_MAX_RESPONSE_WAIT=60
  ```

### Issue: Agent responds but doesn't create ticket

**Possible causes**:
- Your Copilot Studio agent's trigger/topic doesn't match the message format
- Outlook or Excel connectors not properly configured in Copilot Studio

**Solution**:
- Go to Copilot Studio and test your agent directly
- Make sure it understands messages like:
  ```
  Create escalation ticket:
  Customer ID: CUST-123
  Customer Email: test@example.com
  Customer Name: Test User
  Priority: Medium
  Description: Test issue
  ```
- Adjust the message format in `copilot_studio_client.py` if needed

---

## Integration with Other Agents

Once testing is successful, other agents can call the escalation bridge using standard A2A protocol:

```python
# In another agent (e.g., ProdInfo Agent)
async def escalate_to_support(customer_info: dict, issue: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:9006/a2a/invoke",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": f"Create escalation ticket: {issue}. "
                                   f"Customer Email: {customer_info['email']}, "
                                   f"Customer Name: {customer_info['name']}"
                    }
                ],
                "customer_id": customer_info["customer_id"]
            }
        )
        return response.json()
```

---

## Next Steps

1. ✅ Get Copilot Studio credentials (Direct Line secret)
2. ✅ Configure `.env` file
3. ✅ Install dependencies
4. ✅ Test the bridge
5. ⏭️ Integrate with other agents
6. ⏭️ Deploy to production (optional)

---

## Support

If you encounter issues:

1. Check logs: The bridge server logs everything to stdout
2. Test Copilot Studio directly in the Copilot Studio portal
3. Verify Direct Line channel is properly enabled
4. Use the `/test/copilot` endpoint to isolate connection issues
5. Check the message format matches your Copilot Studio agent's expectations

---

## Summary

**What you need from Copilot Studio:**
1. ✅ Direct Line Secret Key (from Settings → Channels → Direct Line)
2. ✅ Bot/Agent Name
3. ✅ Azure Tenant ID (metakaal.com)

**What the bridge does:**
- Receives A2A requests from local agents
- Translates to Direct Line API calls
- Sends to your Copilot Studio agent (cloud)
- Your Copilot Studio agent handles Outlook + Excel
- Returns response back through A2A protocol

**Result:**
- Local agents think they're calling a local escalation agent
- Actually calling cloud Copilot Studio agent
- Seamless integration! 🎉
