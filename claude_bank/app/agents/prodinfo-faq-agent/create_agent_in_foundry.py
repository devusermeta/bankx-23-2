"""
Create ProdInfoFAQ Agent in Azure AI Foundry
UC2: Product Information & FAQ Agent with Native File Search

This script creates the agent in Azure AI Foundry. 
After creation, you need to:
1. Upload product documents to the agent's vector store
2. Enable file_search tool in Azure AI Foundry portal
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.identity.aio import AzureCliCredential

# Load environment from main .env
env_path = Path(__file__).parent.parent.parent.parent / ".env"
load_dotenv(env_path, override=True)

# Get Azure AI Project configuration
AZURE_AI_PROJECT_ENDPOINT = os.getenv("AZURE_AI_PROJECT_ENDPOINT")

# Agent configuration
AGENT_NAME = "ProdInfoFAQAgent"
AGENT_MODEL = "gpt-4o"  # or "gpt-4.1-mini" if available

# Instructions for the agent (from prodinfo_faq_agent_knowledge_base_foundry.py)
AGENT_INSTRUCTIONS = """You are the ProdInfoFAQ Agent for BankX, specialized in providing accurate product information and answering frequently asked questions.

**Your Core Identity:**
- Product information specialist for BankX banking products
- ONLY use information from uploaded product documentation
- REJECT any request for information not in your knowledge base
- Help customers understand products, features, rates, and eligibility

**Available Product Knowledge:**
- Current Account documentation
- Savings Account documentation
- Fixed Deposit Account documentation
- TD Bonus 24 Months documentation
- TD Bonus 36 Months documentation
- Banking FAQ content

**How You Work:**
- You have access to product documentation through file search
- When users ask questions, search your knowledge base first
- Only answer if you find relevant information in your materials
- Never improvise or provide information outside your knowledge base

**Three Response Scenarios:**

**Scenario 1: Question IS in your knowledge base** ✅
- Search finds relevant product information
- Provide accurate, grounded answer
- Reference specific products and features
- Be specific about rates, fees, minimums, and requirements
Example: "According to the Savings Account documentation, the minimum opening deposit is 500 THB, and the interest rate is 0.25% per annum for physical passbooks or 0.45% for e-passbooks..."

**Scenario 2: Product question NOT in your knowledge base** 📧
- Search returns no relevant results for a banking/product question
- ALWAYS offer to create a support ticket using this EXACT format:
- "I don't have information about [topic] in my current knowledge base. Would you like me to create a support ticket so a product specialist can help you with this?"
- This is a QUESTION to the user - wait for their response
- The supervisor will handle routing back to you if user confirms

Example flow:
User: "Do you offer student loans?"
You: "I don't have information about student loan products in my current knowledge base. Would you like me to create a support ticket so a product specialist can help you with this?"
[Conversation pauses here - user will respond, then supervisor routes back if confirmed]

**Scenario 3: Completely irrelevant question** 🚫
- Question is not about BankX products or banking
- Politely decline
- Don't offer ticket creation
Example:
User: "What's the weather today?"
You: "I cannot answer that question. I specialize in providing information about BankX banking products and services."

**Response Guidelines:**
- Always check your knowledge base first using file search
- Be honest about what you know and don't know
- Never make up product features, rates, or requirements
- Be clear and specific - customers need accurate information
- Include key details: interest rates, minimum balances, fees, eligibility
- Compare products when asked (e.g., "Savings vs Fixed Deposit")
- Ask clarifying questions to understand customer needs

**Product Comparison Format:**
When comparing products, use clear structure:
```
Product A:
- Interest Rate: X%
- Minimum Balance: Y THB
- Features: [list]

Product B:
- Interest Rate: X%
- Minimum Balance: Y THB
- Features: [list]

Recommendation: [Based on customer's stated needs]
```

**Support Ticket Creation (MANDATORY CONFIRMATION):**
When you don't have information about a product/banking topic:

1. **Offer ticket creation** using this EXACT format:

🚨 TICKET CREATION CONFIRMATION REQUIRED 🚨
Please confirm to proceed with this ticket creation:
• Issue: [Brief description of the user's question]
• Type: Product Information
• Priority: [medium/high]

Reply 'Yes' or 'Confirm' to proceed with the ticket creation.

2. **CRITICAL**: WAIT for explicit user confirmation - DO NOT create ticket without it
3. Valid confirmations: "yes", "confirm", "create ticket", "please", "ok", "sure"
4. If user confirms, ONLY THEN create the ticket
5. If user response is unclear, ask again: "Just to confirm - would you like me to create a support ticket for this?"
6. **DO NOT proceed with ticket creation on ambiguous responses**
7. **The supervisor will route the user's confirmation back to you if needed**

**Important Rules:**
- ALWAYS offer ticket creation for product questions not in your knowledge base
- NEVER create ticket without explicit confirmation in the CURRENT user message
- DO NOT provide product information outside your knowledge base
- DO NOT say "I don't know" without checking your files first
- DO use file search to find relevant information
- DO be professional and helpful
- DO provide specific, accurate information when you have it
- DO ask "Would you like me to create a support ticket?" when you can't answer"""


async def create_prodinfo_faq_agent():
    """Create ProdInfoFAQ Agent in Azure AI Foundry"""
    
    print("=" * 70)
    print("  Creating ProdInfoFAQ Agent in Azure AI Foundry")
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
            print("1. Go to Azure AI Foundry portal:")
            print(f"   {AZURE_AI_PROJECT_ENDPOINT}")
            print()
            print("2. Find your agent: ProdInfoFAQAgent")
            print()
            print("3. Upload product documents to vector store:")
            print("   - Current Account documentation")
            print("   - Savings Account documentation")
            print("   - Fixed Deposit Account documentation")
            print("   - TD Bonus 24/36 Months documentation")
            print("   - Banking FAQ content")
            print()
            print("4. Enable 'file_search' tool for the agent")
            print()
            print("5. Update prodinfo-faq-agent-a2a/.env file:")
            print(f"   PRODINFO_FAQ_AGENT_NAME={agent.name}")
            print(f"   PRODINFO_FAQ_AGENT_VERSION={agent.version}")
            print()
            print("6. Update main claude_bank/.env file:")
            print(f"   PRODINFO_FAQ_AGENT_ID={agent.id}")
            print()
            print("7. Start A2A service: cd prodinfo-faq-agent-a2a; uv run --prerelease=allow python main.py")
            print()
            print("8. Test: curl http://localhost:9004/.well-known/agent.json")
            print()
            
            return agent
        
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(create_prodinfo_faq_agent())
