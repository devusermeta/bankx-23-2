# Account Agent A2A Microservice

NEW Azure AI Foundry V2 implementation using A2A protocol for decomposable architecture.

## Features

- **A2A Protocol**: Implements agent-to-agent communication via HTTP/JSON-RPC
- **Agent Discovery**: Exposes `/.well-known/agent.json` for agent card discovery
- **Azure AI Foundry V2**: Uses `azure-ai-projects` (NEW SDK) with `AIProjectClient`
- **MCP Integration**: Connects to Account MCP (8070) and Limits MCP (8073) servers
- **Agent Framework**: Uses `agent-framework` with `ChatAgent` and `MCPStreamableHTTPTool`
- **Streaming Responses**: Supports Server-Sent Events (SSE) for real-time responses

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file from template:

```bash
cp .env.example .env
# Edit .env with your actual Azure credentials
```

**🔒 SECURITY**: Never commit `.env` file! It's already in `.gitignore`. Use `.env.example` for documentation.

Example `.env` content:

```env
# Azure AI Foundry V2
AZURE_AI_PROJECT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
AZURE_AI_PROJECT_API_KEY=your_api_key_here

# Agent Configuration (NEW format: name:version, not asst_xxx)
ACCOUNT_AGENT_NAME=AccountAgent
ACCOUNT_AGENT_VERSION=1

# Model Deployment
ACCOUNT_AGENT_MODEL_DEPLOYMENT=gpt-4o

# MCP Server URLs
ACCOUNT_MCP_SERVER_URL=http://localhost:8070/mcp
LIMITS_MCP_SERVER_URL=http://localhost:8073/mcp

# A2A Server Configuration
A2A_SERVER_PORT=9001
A2A_SERVER_HOST=0.0.0.0
```

### 3. Run the A2A Server

```bash
python main.py
```

The server will start on `http://localhost:9001`

## A2A Endpoints

### Agent Card Discovery
```
GET http://localhost:9001/.well-known/agent.json
```

Returns agent metadata for discovery:
```json
{
  "name": "Account Agent",
  "description": "Specialized banking agent for account management...",
  "capabilities": ["account_balance", "account_details", "payment_methods", "transaction_limits"],
  "endpoints": {
    "chat": "http://localhost:9001/a2a/invoke"
  }
}
```

### Chat Invocation
```
POST http://localhost:9001/a2a/invoke
Content-Type: application/json

{
  "messages": [
    {"role": "user", "content": "What is my account balance?"}
  ],
  "thread_id": "thread_123",
  "customer_id": "customer_456",
  "stream": true
}
```

## Architecture

```
┌─────────────────────────────────────────┐
│   Supervisor Agent (A2A Client)        │
│   - Routes account queries here         │
└───────────────┬─────────────────────────┘
                │ HTTP/JSON-RPC (A2A)
                ▼
┌─────────────────────────────────────────┐
│   Account Agent A2A Server (main.py)   │
│   - FastAPI server                      │
│   - A2A protocol implementation         │
│   - Agent card at /.well-known/         │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│   AccountAgentHandler                   │
│   - Azure AI Foundry V2 integration     │
│   - ChatAgent with agent-framework      │
│   - MCP tools orchestration             │
└───────────────┬─────────────────────────┘
                │
        ┌───────┴───────┐
        ▼               ▼
┌─────────────┐  ┌─────────────┐
│ Account MCP │  │ Limits MCP  │
│   (8070)    │  │   (8073)    │
└─────────────┘  └─────────────┘
```

## Testing

### Test Agent Card Discovery
```bash
curl http://localhost:9001/.well-known/agent.json
```

### Test Chat Endpoint (Non-Streaming)
```bash
curl -X POST http://localhost:9001/a2a/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "What is my balance?"}],
    "thread_id": "test_thread",
    "customer_id": "test_customer",
    "stream": false
  }'
```

### Test Health Check
```bash
curl http://localhost:9001/health
```

## Migration Notes

### Differences from OLD Foundry V1 Implementation

| Aspect | OLD (Foundry V1) | NEW (Foundry V2 + A2A) |
|--------|------------------|------------------------|
| SDK | `azure-ai-agents` | `azure-ai-projects` |
| Client | `AzureAIAgentClient` (OLD) | `AzureAIClient` (NEW) |
| Authentication | Service Principal | API Key (simpler) |
| Agent ID Format | `asst_xxxxx` | `name:version` (e.g., `AccountAgent:1`) |
| Architecture | In-process | A2A microservice |
| Communication | Direct method calls | HTTP/JSON-RPC |
| Discovery | N/A | Agent card at `/.well-known/agent.json` |
| Scaling | Monolithic | Independent microservice |
| Deployment | Single copilot backend | Decomposable services |

### Benefits of A2A Architecture

✅ **Decomposable**: Each agent can scale independently  
✅ **Discoverable**: Agent card enables dynamic service discovery  
✅ **Technology Agnostic**: Agents can be built in any language  
✅ **Fault Isolated**: Agent failures don't crash the entire system  
✅ **Easier Testing**: Test individual agents in isolation  
✅ **Modern**: Follows industry best practices for microservices  

## Troubleshooting

### Agent ID Not Found
Ensure `ACCOUNT_AGENT_ID` is set in `.env` and the agent exists in Azure AI Foundry.

### MCP Connection Errors
Verify MCP servers are running:
```bash
# Check Account MCP
curl http://localhost:8070/health

# Check Limits MCP
curl http://localhost:8073/health
```

### Authentication Errors
Verify Azure credentials:
```bash
az login
az account show
```

## Next Steps

1. Start the Account Agent A2A server: `python main.py`
2. Verify agent card: `curl http://localhost:9001/.well-known/agent.json`
3. Update supervisor to route account queries to A2A endpoint
4. Test end-to-end with supervisor routing
5. Monitor performance and compare with OLD implementation
6. Migrate remaining agents (Transaction, Payment, etc.) using same pattern
