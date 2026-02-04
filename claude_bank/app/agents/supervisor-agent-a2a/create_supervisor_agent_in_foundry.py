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
AGENT_NAME = os.getenv("SUPERVISOR_AGENT_NAME", "SupervisorAgent")
AGENT_MODEL = os.getenv("SUPERVISOR_AGENT_MODEL_DEPLOYMENT", "gpt-4.1-mini")

# Load agent instructions
prompts_dir = Path(__file__).parent / "prompts"
instructions_file = prompts_dir / "supervisor_agent.md"

if not instructions_file.exists():
    print(f"❌ Error: Instructions file not found: {instructions_file}")
    sys.exit(1)

with open(instructions_file, "r", encoding="utf-8") as f:
    AGENT_INSTRUCTIONS = f.read()

# Clean instructions to ensure proper encoding
AGENT_INSTRUCTIONS = AGENT_INSTRUCTIONS.strip()

# Validate configuration
if not AZURE_AI_PROJECT_ENDPOINT:
    print("❌ Error: AZURE_AI_PROJECT_ENDPOINT not set in .env file")
    sys.exit(1)


async def create_supervisor_agent():
    """Create Supervisor Agent in Azure AI Foundry"""
    
    print("=" * 70)
    print("  Creating Supervisor Agent in Azure AI Foundry")
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
            print("1. Update supervisor-agent-a2a/.env file:")
            print(f"   SUPERVISOR_AGENT_NAME={agent.name}")
            print(f"   SUPERVISOR_AGENT_VERSION={agent.version}")
            print(f"   SUPERVISOR_AGENT_MODEL_DEPLOYMENT={AGENT_MODEL}")
            print()
            print("2. Restart the supervisor agent:")
            print("   cd app/agents/supervisor-agent-a2a")
            print("   uv run --prerelease=allow python main.py")
            print()
            print("3. Verify thread tracking in Azure AI Foundry portal:")
            print(f"   {AZURE_AI_PROJECT_ENDPOINT}")
            print()
            print("🎉 Supervisor Agent will now have:")
            print("   - Thread tracking and history")
            print("   - Governance and compliance monitoring")
            print("   - Agent versioning capabilities")
            print("   - Full observability in Azure AI Foundry")
            print()
            
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_supervisor_agent())
