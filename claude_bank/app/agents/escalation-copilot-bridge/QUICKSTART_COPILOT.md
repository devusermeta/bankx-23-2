# Escalation Copilot Bridge - Quick Start

## What is This?

This is an **A2A-compatible bridge** that allows your local agent system to call your **Copilot Studio agent** for escalations. 

- Your Copilot Studio agent handles **Outlook email** and **Excel storage**
- The bridge translates between **A2A protocol** (local) and **Direct Line API** (Copilot Studio)
- Other agents call the bridge like any A2A agent (port 9006)

## What You Need

From your Copilot Studio agent:

1. **Direct Line Secret** (Settings → Channels → Direct Line → Show Key)
2. **Bot Name** (your agent's name)
3. **Azure Tenant ID** (metakaal.com tenant)

## Quick Setup (5 Minutes)

### 1. Configure Environment

```powershell
cd d:\Metakaal\Updated_BankX\claude_bank\app\agents\escalation-copilot-bridge
cp .env.example .env
notepad .env
```

Fill in:
```dotenv
COPILOT_DIRECT_LINE_SECRET=your-secret-key-from-copilot-studio
COPILOT_BOT_NAME=EscalationAgent
AZURE_TENANT_ID=your-metakaal-tenant-id
```

### 2. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 3. Start the Bridge

```powershell
python main.py
```

You should see:
```
✓ Successfully connected to Copilot Studio agent
INFO:     Uvicorn running on http://0.0.0.0:9006
```

### 4. Test It

In another terminal:

```powershell
# Test health
curl http://localhost:9006/health

# Test Copilot connection
curl -X POST "http://localhost:9006/test/copilot?message=Hello"

# Test A2A escalation
python test_a2a_escalation.py
```

## How Other Agents Will Use It

```python
# In ProdInfo Agent or any other agent
import httpx

async def escalate_issue(customer_id, customer_email, customer_name, issue):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:9006/a2a/invoke",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": f"Create escalation ticket: {issue}. "
                                   f"Customer Email: {customer_email}, "
                                   f"Customer Name: {customer_name}"
                    }
                ],
                "customer_id": customer_id
            }
        )
        return response.json()
```

## Architecture

```
ProdInfo Agent (Local)
   ↓ A2A Protocol
Escalation Bridge (Port 9006, Local)
   ↓ Direct Line API (HTTPS)
Copilot Studio Agent (Cloud)
   ↓ Outlook Connector + Excel Connector
Email Sent + Ticket Stored
```

## Files Created

| File | Purpose |
|------|---------|
| `copilot_studio_client.py` | Direct Line API client for calling Copilot Studio |
| `config.py` | Configuration with Copilot Studio settings |
| `a2a_handler.py` | A2A protocol handler (updated to use Copilot Studio) |
| `main.py` | FastAPI server with A2A endpoints |
| `models.py` | Data models for A2A protocol |
| `.env.example` | Environment template |
| `test_a2a_escalation.py` | Test script for A2A protocol |
| `COPILOT_STUDIO_SETUP.md` | Detailed setup guide |

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/a2a/invoke` | POST | Main A2A escalation endpoint |
| `/.well-known/agent.json` | GET | Agent discovery card |
| `/test/copilot` | POST | Test Copilot Studio connection |
| `/test/escalation` | POST | Test ticket creation |
| `/config/status` | GET | Check configuration |

## Troubleshooting

### "Configuration validation failed"
→ Check your `.env` file has `COPILOT_DIRECT_LINE_SECRET` and `AZURE_TENANT_ID`

### "Failed to start conversation"
→ Verify Direct Line channel is enabled in Copilot Studio
→ Check secret key is correct (no extra spaces)

### "No response from Copilot Studio (timeout)"
→ Increase timeout: `COPILOT_MAX_RESPONSE_WAIT=60`
→ Test your Copilot Studio agent directly in portal

### "Port 9006 already in use"
→ Change port in `.env`: `A2A_SERVER_PORT=9007`

## Next Steps

1. ✅ Get Direct Line secret from Copilot Studio
2. ✅ Configure `.env` file
3. ✅ Run `python main.py`
4. ✅ Test with `test_a2a_escalation.py`
5. ⏭️ Integrate with other agents
6. ⏭️ Deploy to production

## Key Points

- ✅ **Same Excel file** as Copilot Studio uses (in your SharePoint/OneDrive)
- ✅ **Same Outlook account** as Copilot Studio uses (via connector)
- ✅ **No code changes needed** in Copilot Studio agent
- ✅ **No resource duplication** - bridge just calls your existing agent
- ✅ **A2A compatible** - other agents don't know it's calling cloud service
- ✅ **Fast setup** - 5 minutes if you have the credentials

## Authentication Flow

```
User → Frontend (bankxthb auth for natta@bankxthb.onmicrosoft.com)
  ↓
Local Agents (A2A, metakaal tenant resources)
  ↓
Escalation Bridge (Direct Line Secret, no user context)
  ↓
Copilot Studio Agent (metakaal environment)
  ↓
Outlook/Excel (metakaal tenant resources)
```

The bridge uses **service-to-service** authentication (Direct Line Secret), not user authentication. This is perfect for your scenario:

- Frontend: bankxthb tenant (user auth)
- Resources: metakaal tenant (service auth)
- Bridge: connects the two seamlessly

## Summary

**You asked:** Can I get my Copilot Studio agent to work with local A2A agents?

**Answer:** Yes! This bridge makes it possible:
- Copilot Studio agent stays in cloud (metakaal environment)
- Bridge runs locally on port 9006
- Other agents call bridge using A2A protocol
- Bridge forwards to Copilot Studio via Direct Line API
- Copilot Studio handles Outlook + Excel
- Response comes back through bridge

**Result:** Seamless integration! 🎉
