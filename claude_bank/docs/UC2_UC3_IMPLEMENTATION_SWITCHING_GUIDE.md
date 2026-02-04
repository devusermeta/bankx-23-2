# UC2 & UC3 Implementation Switching Guide

## Current Status
✅ **ACTIVE**: Native file search implementation (Azure AI Foundry vector store)
- Uses `ProdInfoFAQAgentKnowledgeBase` (UC2)
- Uses `AIMoneyCoachKnowledgeBaseAgent` (UC3)
- No MCP RAG servers needed (ports 8076, 8077)
- Files uploaded directly to Azure AI Foundry portal

## How to Switch Between Implementations

### Files Modified with Switch Comments:
1. `app/copilot/app/config/container_foundry.py`
2. `app/copilot/app/agents/foundry/supervisor_agent_foundry.py`

### To Switch BACK to Old Implementation (Azure AI Search RAG):

#### Step 1: Update Imports in `container_foundry.py`
```python
# Comment out ACTIVE VERSION:
# from app.agents.foundry.prodinfo_faq_agent_knowledge_base_foundry import ProdInfoFAQAgentKnowledgeBase
# from app.agents.foundry.ai_money_coach_agent_knowledge_base_foundry import AIMoneyCoachKnowledgeBaseAgent

# Uncomment OLD VERSION:
from app.agents.foundry.prodinfo_faq_agent_foundry import ProdInfoFAQAgent
from app.agents.foundry.ai_money_coach_agent_foundry import AIMoneyCoachAgent
```

#### Step 2: Update Agent Instantiation in `container_foundry.py`
```python
# Comment out ACTIVE VERSION and uncomment OLD VERSION sections for:
# - _foundry_prodinfo_faq_agent (line ~153)
# - _foundry_ai_money_coach_agent (line ~173)
```

#### Step 3: Update Imports in `supervisor_agent_foundry.py`
```python
# Comment out ACTIVE VERSION:
# from app.agents.foundry.prodinfo_faq_agent_knowledge_base_foundry import ProdInfoFAQAgentKnowledgeBase
# from app.agents.foundry.ai_money_coach_agent_knowledge_base_foundry import AIMoneyCoachKnowledgeBaseAgent

# Uncomment OLD VERSION:
from app.agents.foundry.prodinfo_faq_agent_foundry import ProdInfoFAQAgent
from app.agents.foundry.ai_money_coach_agent_foundry import AIMoneyCoachAgent
```

#### Step 4: Update Type Hints in `supervisor_agent_foundry.py` __init__
```python
# Comment out ACTIVE VERSION:
# prodinfo_faq_agent: ProdInfoFAQAgentKnowledgeBase,
# ai_money_coach_agent: AIMoneyCoachKnowledgeBaseAgent,

# Uncomment OLD VERSION:
prodinfo_faq_agent: ProdInfoFAQAgent,
ai_money_coach_agent: AIMoneyCoachAgent,
```

#### Step 5: Start MCP RAG Servers
```bash
# Terminal 1: Start ProdInfoFAQ MCP server (port 8076)
python app/a2a-sdk/agents/prod_info_faq/prod_info_faq_mcp_server.py

# Terminal 2: Start AIMoneyCoach MCP server (port 8077)
python app/a2a-sdk/agents/ai_money_coach/ai_money_coach_mcp_server.py
```

#### Step 6: Update Environment Variables
```bash
# Make sure these are set:
PRODINFO_FAQ_MCP_URL=http://localhost:8076
AI_MONEY_COACH_MCP_URL=http://localhost:8077
```

## Comparison

| Feature | Native File Search (ACTIVE) | Azure AI Search RAG (OLD) |
|---------|----------------------------|---------------------------|
| **Agent Files** | `*_knowledge_base_foundry.py` | `*_foundry.py` |
| **Knowledge Source** | Azure AI Foundry vector store | Azure AI Search indexes |
| **File Upload** | Via Azure AI Foundry portal | Via blob storage + indexing |
| **MCP Servers Needed** | 0 (only EscalationComms) | 2 (ports 8076, 8077) |
| **Complexity** | Lower | Higher |
| **Maintenance** | Simpler | More complex |
| **Testing Status** | ✅ Both tested & working | ✅ Previously working |

## Agent IDs (Same for Both Versions)
- **UC2 (ProdInfoFAQ)**: `asst_65oOm3oxeYt2oNEZK5oAGLHw`
- **UC3 (AIMoneyCoach)**: `asst_7iSDqfE2OA2xJDdcYq5ajcy9`

## Recommendation
✅ **Keep using Native File Search** (current active version) unless specific requirements dictate otherwise. It's simpler, requires less infrastructure, and has been tested successfully.
