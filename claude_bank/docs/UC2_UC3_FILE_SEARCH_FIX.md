# URGENT FIX: UC2 & UC3 File Search Tool Issue

## Problem Identified
❌ **Error**: `KeyError: "No tool or function named 'msearch'"`

## Root Cause
When building ChatAgent locally with `agent_id`, we were passing `instructions` parameter which **overrides** the portal configuration. This prevented the agent from accessing its portal-configured `file_search` tool.

## Solution Applied
✅ **Removed `instructions` parameter** from ChatAgent initialization in both agents:
- `ai_money_coach_agent_knowledge_base_foundry.py`
- `prodinfo_faq_agent_knowledge_base_foundry.py`

### Code Change:
```python
# BEFORE (WRONG):
chat_agent = ChatAgent(
    name=...,
    chat_client=AzureAIAgentClient(...),
    instructions=Agent.instructions,  # ❌ This overrides portal config!
    tools=tools_list
)

# AFTER (CORRECT):
chat_agent = ChatAgent(
    name=...,
    chat_client=AzureAIAgentClient(...),
    # instructions=Agent.instructions,  # ✅ Commented out - use portal config
    tools=tools_list  # ✅ Only add our MCP tools
)
```

## What This Means
1. **Portal instructions are now used** - agents will follow instructions configured in Azure AI Foundry portal
2. **File search tool works** - agents can use their portal-configured `file_search` or `msearch` tool
3. **MCP tools still added** - EscalationComms MCP for ticket creation still works

## Next Steps

### 1. Restart the Application
The changes have been made to the code. You need to restart the uvicorn server:
```powershell
# Press Ctrl+C in the uvicorn terminal
# Then restart:
python -m app.copilot.app.main
```

### 2. Verify Portal Instructions (IMPORTANT!)
Go to Azure AI Foundry portal and verify both agents have proper instructions:

#### UC2 - ProdInfoFAQ Agent (`asst_65oOm3oxeYt2oNEZK5oAGLHw`)
Should have instructions similar to those in `prodinfo_faq_agent_knowledge_base_foundry.py` lines 41-136

#### UC3 - AIMoneyCoach Agent (`asst_7iSDqfE2OA2xJDdcYq5ajcy9`)
Should have instructions similar to those in `ai_money_coach_agent_knowledge_base_foundry.py` lines 40-138

### 3. Test Again
After restart, test the question:
- "When is borrowing money acceptable?" → Should route to AIMoneyCoach and answer from knowledge base

## Technical Notes
- When `agent_id` is provided to AzureAIAgentClient, the agent uses its **portal configuration**
- Local `instructions` parameter should be omitted to allow portal config to take effect
- Portal-configured tools (like `file_search`) are automatically available
- Locally added tools (like MCP) are merged with portal tools

## If Portal Instructions Are Missing
If the agents don't have instructions in the portal, you'll need to either:
1. **Add instructions in portal** (recommended)
2. **Or** uncomment the `instructions` parameter but verify the portal's file_search tool is properly configured

## Test Results Expected
✅ Supervisor routes to AIMoneyCoach (already working)
✅ AIMoneyCoach accesses file_search tool (should work after restart)
✅ Agent answers from "Debt-Free to Financial Freedom" book with citations
