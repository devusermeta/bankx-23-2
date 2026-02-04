"""
Create AIMoneyCoach Agent programmatically using Azure AI SDK.
This will create an agent with a proper asst_* ID that works with the current SDK.
"""
from azure.ai.projects import AIProjectClient
from azure.identity import AzureCliCredential, DefaultAzureCredential
from app.config.settings import settings
import os

def create_ai_money_coach_agent():
    """Create AIMoneyCoach agent with SDK (gets asst_* ID)"""
    
    print("=" * 80)
    print("Creating AIMoneyCoach Agent via SDK")
    print("=" * 80)
    
    # Use synchronous credential
    try:
        credential = AzureCliCredential()
    except:
        credential = DefaultAzureCredential()
    
    client = AIProjectClient(
        credential=credential,
        endpoint=settings.FOUNDRY_PROJECT_ENDPOINT
    )
    
    print(f"\nProject Endpoint: {settings.FOUNDRY_PROJECT_ENDPOINT}")
    print(f"Model: {settings.FOUNDRY_MODEL_DEPLOYMENT_NAME}")
    
    # Vector store IDs (if any)
    vector_store_ids = []
    if settings.AI_MONEY_COACH_VECTOR_STORE_IDS:
        vector_store_ids = [v.strip() for v in settings.AI_MONEY_COACH_VECTOR_STORE_IDS.split(",")]
    
    print(f"Vector Stores: {vector_store_ids or 'None (will use portal config)'}\n")
    
    # Agent configuration
    instructions = """You are the AIMoneyCoach Agent for BankX. Follow these instructions exactly.

**Core Role and Knowledge Source**
- Provide personalized financial advice based **exclusively** on the book "Debt-Free to Financial Freedom".
- Use only information retrieved from the uploaded copy of this book via file search.
- Do not use general financial knowledge or any external sources.

**CRITICAL: STRICT BOOK-ONLY RESPONSES**
- Answer only using content grounded in "Debt-Free to Financial Freedom".
- Never provide generic financial advice based on your own knowledge.
- If the book does not cover the topic, offer to create a support ticket.

**CRITICAL: CONCISE RESPONSES**
- Keep answers to 2-3 lines (40-60 words) by default.
- Provide detailed explanations only when explicitly requested.
"""
    
    # Create agent with file_search tool
    print("🔧 Creating agent...")
    
    agent_config = {
        "model": settings.FOUNDRY_MODEL_DEPLOYMENT_NAME,
        "name": "AIMoneyCoachAgent",
        "description": "Personal finance coach providing advice grounded in uploaded financial guidance materials",
        "instructions": instructions,
        "tools": [{"type": "file_search"}],  # Enable file search
    }
    
    # Add tool_resources if vector stores specified
    if vector_store_ids:
        agent_config["tool_resources"] = {
            "file_search": {
                "vector_store_ids": vector_store_ids
            }
        }
        print(f"✅ Will attach vector stores: {vector_store_ids}")
    
    try:
        agent = client.agents.create_agent(**agent_config)
        
        print("\n" + "=" * 80)
        print("✅ SUCCESS! Agent created")
        print("=" * 80)
        print(f"\nAgent Name: {agent.name}")
        print(f"Agent ID: {agent.id}")
        print(f"Model: {agent.model}")
        print(f"Tools: {[tool.type for tool in agent.tools] if hasattr(agent, 'tools') else 'N/A'}")
        print("\n" + "=" * 80)
        print("📋 NEXT STEPS:")
        print("=" * 80)
        print(f"\n1. Copy this agent ID: {agent.id}")
        print("\n2. Update container_foundry.py:")
        print(f'   agent_id="{agent.id}"')
        print("\n3. Restart copilot backend")
        print("\n" + "=" * 80)
        
        return agent.id
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nThis might mean:")
        print("- Agent already exists (try listing agents)")
        print("- Permissions issue")
        print("- Invalid configuration")
        return None

if __name__ == "__main__":
    create_ai_money_coach_agent()
