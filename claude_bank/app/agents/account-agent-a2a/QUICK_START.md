# AccountAgent A2A - Quick Start Guide

This guide shows how to set up and run the AccountAgent as an A2A microservice using agent-framework patterns.

## Architecture

```
Azure AI Foundry (Cloud)
    │
    └── AccountAgent (Created in Foundry)
            │
            ▼
    Agent Framework SDK (Python)
            │
            ├── AzureAIClient (Wraps Foundry agent)
            ├── ChatAgent (Adds MCP tools)
            └── MCPStreamableHTTPTool (Connects to MCP servers)
                    │
                    ├── Account MCP (localhost:8001)
                    └── Limits MCP (localhost:8002)
```

## Prerequisites

1. **Azure AI Foundry Project**:
   - Go to https://ai.azure.com
   - Create a new project
   - Deploy a GPT-4 model

2. **Azure CLI Authentication**:
   ```powershell
   az login
   ```

3. **Environment Variables**:
   Create `.env` file with:
   ```
   AZURE_AI_PROJECT_ENDPOINT=https://your-project.cognitiveservices.azure.com
   AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4
   ACCOUNT_MCP_SERVER_URL=http://localhost:8001
   LIMITS_MCP_SERVER_URL=http://localhost:8002
   A2A_SERVER_PORT=9001
   A2A_SERVER_HOST=0.0.0.0
   ```

## Step 1: Create Agent in Azure AI Foundry

Run this ONCE to create the AccountAgent in Foundry:

```powershell
cd d:\Metakaal\Bank_01-01-2026\Bank_v3\claude_bank\app\agents\account-agent-a2a
uv run python create_account_agent_in_foundry.py
```

This will:
- Create "AccountAgent" in your Foundry project
- Display agent name and version
- Show you what to add to `.env`

Example output:
```
✅ Agent Created Successfully!
  Name: AccountAgent
  Version: 1
  ID: agents/AccountAgent/versions/1

=== Next Steps ===
1. Update your .env file with:
   ACCOUNT_AGENT_NAME=AccountAgent
   ACCOUNT_AGENT_VERSION=1
```

## Step 2: Update .env File

Add the agent details from Step 1 to `.env`:

```
ACCOUNT_AGENT_NAME=AccountAgent
ACCOUNT_AGENT_VERSION=1
```

## Step 3: Start MCP Servers

**Terminal 1 - Account MCP**:
```powershell
cd d:\Metakaal\Bank_01-01-2026\Bank_v3\claude_bank\app\business-api\python\account
uv run python main.py
```

**Terminal 2 - Limits MCP**:
```powershell
cd d:\Metakaal\Bank_01-01-2026\Bank_v3\claude_bank\app\business-api\python\limits
uv run python main.py
```

## Step 4: Start A2A Service

**Terminal 3 - AccountAgent A2A**:
```powershell
cd d:\Metakaal\Bank_01-01-2026\Bank_v3\claude_bank\app\agents\account-agent-a2a
uv run python main.py
```

Expected output:
```
[INFO] AccountAgentHandler initialized (Agent Framework + Foundry V2)
[INFO] ✅ Azure credential created (AzureCliCredential)
[INFO] ✅ Agent instructions loaded
[INFO] A2A server running on http://0.0.0.0:9001
```

## Step 5: Test the A2A Service

**Test 1 - Agent Card**:
```powershell
curl http://localhost:9001/agent-card
```

Expected response:
```json
{
  "name": "AccountAgent",
  "description": "Account management specialist",
  "version": "1.0.0",
  "url": "http://localhost:9001"
}
```

**Test 2 - Chat Request**:
```powershell
curl -X POST http://localhost:9001/chat ^
  -H "Content-Type: application/json" ^
  -d "{\"messages\": [{\"role\": \"user\", \"content\": \"What is my account balance?\"}], \"customer_id\": \"CUST001\", \"stream\": false}"
```

## Step 6: Enable in Supervisor

Edit `claude_bank/.env`:
```
USE_A2A_FOR_ACCOUNT_AGENT=true
ACCOUNT_AGENT_A2A_URL=http://localhost:9001
```

Now the supervisor will route account queries to the A2A service!

## Troubleshooting

### "Azure credential error"
- Run `az login` to authenticate
- Check that your account has access to the Foundry project

### "Agent not found"
- Make sure you ran `create_account_agent_in_foundry.py`
- Check `.env` has correct `ACCOUNT_AGENT_NAME` and `ACCOUNT_AGENT_VERSION`

### "MCP connection failed"
- Ensure MCP servers are running (Step 3)
- Check MCP_SERVER_URL values in `.env`

### "Import Error: agent_framework"
- Run `uv sync` to install agent-framework packages
- Verify pyproject.toml has agent-framework-* dependencies

## Architecture Notes

- **Agent Creation**: Done ONCE in Azure AI Foundry (cloud service)
- **Agent Framework**: Python SDK that wraps the Foundry agent
- **MCP Tools**: Connect agent to business logic microservices
- **A2A Protocol**: Enables HTTP communication with supervisor
- **Caching**: Agents are cached per thread for performance

## Next Steps

1. Test standalone A2A service (Steps 1-5)
2. Enable in supervisor (Step 6)
3. Test end-to-end integration
4. Monitor logs for debugging
