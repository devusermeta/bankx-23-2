import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity.aio import AzureCliCredential

# Load environment variables
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Configuration
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")
AGENT_NAME = os.getenv("AI_MONEY_COACH_AGENT_NAME", "AIMoneyCoachAgent")
# Use the same model variable name as working account agent
AGENT_MODEL = os.getenv("AZURE_AI_MODEL_DEPLOYMENT_NAME") or os.getenv("AI_MONEY_COACH_AGENT_MODEL_DEPLOYMENT", "gpt-4.1-mini")

# Load agent instructions
prompts_dir = Path(__file__).parent / "prompts"
instructions_file = prompts_dir / "ai_money_coach_agent.md"

if not instructions_file.exists():
    print(f"❌ Error: Instructions file not found: {instructions_file}")
    sys.exit(1)

# Read instructions with encoding fallback
try:
    with open(instructions_file, "r", encoding="utf-8-sig") as f:
        AGENT_INSTRUCTIONS = f.read()
except UnicodeDecodeError:
    print("⚠️ UTF-8 decoding failed, trying latin-1...")
    with open(instructions_file, "r", encoding="latin-1") as f:
        AGENT_INSTRUCTIONS = f.read()

# Clean instructions to ensure proper encoding
AGENT_INSTRUCTIONS = AGENT_INSTRUCTIONS.strip()

# Validate configuration
if not AZURE_AI_PROJECT_ENDPOINT:
    print("❌ Error: AZURE_AI_PROJECT_ENDPOINT not set in .env file")
    sys.exit(1)


async def create_ai_money_coach_agent():
    """Create AIMoneyCoach Agent in Azure AI Foundry"""
    
    print("=" * 70)
    print("  Creating AIMoneyCoach Agent in Azure AI Foundry")
    print("=" * 70)
    print()
    
    try:
        # Initialize Azure AI Project Client
        print(f"📡 Connecting to Azure AI Project...")
        print(f"   Endpoint: {AZURE_AI_PROJECT_ENDPOINT}")
        print()
        
        # Create agent
        print(f"🔨 Creating {AGENT_NAME}...")
        print(f"   Model: {AGENT_MODEL}")
        print(f"   Instructions: {len(AGENT_INSTRUCTIONS)} characters")
        print()
        
        async with (
            AzureCliCredential() as credential,
            AIProjectClient(endpoint=AZURE_AI_PROJECT_ENDPOINT, credential=credential) as project_client,
        ):
            # Try to list existing agents first to check if it already exists
            try:
                print("🔍 Checking for existing agents...")
                agents_list = project_client.agents.list_agents()
                existing_agents = [agent async for agent in agents_list]
                existing_names = [agent.name for agent in existing_agents if hasattr(agent, 'name')]
                print(f"   Found {len(existing_agents)} existing agents: {existing_names}")
                
                if AGENT_NAME in existing_names:
                    print(f"⚠️  Agent '{AGENT_NAME}' already exists!")
                    print("   Use Azure AI Foundry portal to view or update it.")
                    return None
            except Exception as list_error:
                print(f"⚠️  Could not list agents: {list_error}")
                print("   Continuing with creation...")
            
            print()
            agent = await project_client.agents.create_version(
                agent_name=AGENT_NAME,
                definition=PromptAgentDefinition(
                    model=AGENT_MODEL,
                    instructions=AGENT_INSTRUCTIONS,
                ),
            )
            
            print("✅ Agent Created Successfully!")
            print()
            print(f"   Name: {agent.name}")
            print(f"   Version: {agent.version}")
            print(f"   ID: {agent.id}")
            print()
            
            print("=" * 70)
            print("  NEXT STEPS - IMPORTANT!")
            print("=" * 70)
            print()
            print("1. Go to Azure AI Foundry portal:")
            print(f"   {AZURE_AI_PROJECT_ENDPOINT}")
            print()
            print("2. Find your agent: AIMoneyCoachAgent")
            print()
            print("3. Upload the book to vector store:")
            print("   - 'Debt-Free to Financial Freedom' (PDF/DOCX)")
            print()
            print("4. Enable 'file_search' tool for the agent")
            print()
            print("5. Update ai-money-coach-agent-a2a/.env file:")
            print(f"   AI_MONEY_COACH_AGENT_NAME={agent.name}")
            print(f"   AI_MONEY_COACH_AGENT_VERSION={agent.version}")
            print()
            print("6. Update main claude_bank/.env file:")
            print(f"   AI_MONEY_COACH_AGENT_ID={agent.id}")
            print()
            print("7. Start A2A service: cd ai-money-coach-agent-a2a; uv run --prerelease=allow python main.py")
            print()
            print("8. Test: curl http://localhost:9005/.well-known/agent.json")
            print()
            print("9. Test in Foundry portal first:")
            print("   - Ask: 'How do I pay off debt effectively?'")
            print("   - Verify it uses ONLY the book content")
            print()
            
            return agent
            
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_ai_money_coach_agent())
