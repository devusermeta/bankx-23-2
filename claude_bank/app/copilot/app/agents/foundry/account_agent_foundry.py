from azure.core.credentials import TokenCredential
from agent_framework.azure import AzureAIClient
from azure.ai.projects import AIProjectClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from app.config.azure_credential import get_azure_credential_async
from app.tools.audited_mcp_tool import AuditedMCPTool

import os
import logging


def get_or_reuse_agent(agent_name: str, agent_id: str | None = None):
    """
    NEW APPROACH (v2): Always prefer pre-configured agent IDs from .env
    If agent_id is provided in .env, use it. Don't create new agents.
    Fresh MCP tools are attached every request in build_af_agent().
    
    This ensures:
    - ✅ Pre-built agents in Azure are reused (no duplication)
    - ✅ Fresh MCP connections per request (tools work)
    - ✅ No SDK create_agent() dependency
    - ✅ Works in both local and Azure environments
    """
    if agent_id:
        print(f"✅ Using pre-configured agent ID for {agent_name}: {agent_id}")
        return agent_id
    
    raise ValueError(
        f"❌ Agent ID required for {agent_name}. "
        f"Please configure {agent_name.upper()}_ID in .env file. "
        f"Example: ACCOUNT_AGENT_ID=asst_xxxxx"
    )


# LEGACY CODE (v1) - COMMENTED OUT FOR REFERENCE
# def get_or_create_agent(foundry_client, agent_name: str, agent_description: str, model_deployment: str, agent_id: str | None = None):
#     """Check if agent exists, if not create it. Returns the agent object (or agent_id string in Docker mode)."""
#     # Check if we're in Docker mode (use pre-configured agents only)
#     use_prebuilt_only = os.getenv('USE_PREBUILT_AGENTS_ONLY', 'false').lower() == 'true'
#     
#     if use_prebuilt_only:
#         # Docker mode: Use pre-configured agent ID only (SDK may not support agent creation)
#         if agent_id:
#             print(f"✅ [DOCKER MODE] Using pre-configured agent ID for {agent_name}: {agent_id}")
#             return agent_id
#         raise ValueError(
#             f"❌ Docker mode requires pre-configured agent. No agent_id configured for {agent_name}. "
#             f"Please create the agent in Azure AI Foundry portal and configure its ID in the .env file."
#         )
#     
#     # Local dev mode: Full agent management with Azure AI SDK
#     try:
#         # If agent_id provided, try to get that specific agent
#         if agent_id:
#             try:
#                 agent = foundry_client.agents.get_agent(agent_id)
#                 print(f"✅ Found existing {agent_name} by ID: {agent.id}")
#                 return agent
#             except Exception as e:
#                 print(f"⚠️ Could not find agent with ID {agent_id}: {e}")
#                 print(f"   Will search by name or create new agent...")
#
#         # Try to list existing agents and find matching one by name
#         agents = foundry_client.agents.list_agents()
#
#         # Look for agent with matching name
#         for agent in agents:
#             if hasattr(agent, 'name') and agent.name == agent_name:
#                 print(f"✅ Found existing {agent_name} by name: (ID: {agent.id})")
#                 return agent
#
#         # Agent not found, create new one
#         print(f"🚀 Creating new {agent_name}")
#         new_agent = foundry_client.agents.create_agent(
#             model=model_deployment,
#             name=agent_name,
#             description=agent_description
#         )
#         print(f"✅ Created new {agent_name}: (ID: {new_agent.id})")
#         return new_agent
#
#     except Exception as e:
#         print(f"⚠️ Error checking for existing {agent_name}, creating new one: {e}")
#         # Fallback to creating new agent
#         return foundry_client.agents.create_agent(
#             model=model_deployment,
#             name=agent_name,
#             description=agent_description
#         )


logger = logging.getLogger(__name__)

class AccountAgent :
    instructions = """
    You are a personal financial advisor who helps users with their bank account information.
    
    CRITICAL RESPONSE RULES:
    - Answer ONLY what the user asks - be concise and direct
    - If asked for balance: provide ONLY the balance amount
    - If asked for account details: provide ONLY the requested details
    - If asked for payment methods: provide ONLY payment method info
    - If asked for limits (daily limit, transaction limit, transfer limit): use Limits MCP tools to get current limits
    - Do NOT provide extra information unless specifically asked
    - Do NOT ask follow-up questions like "Is there anything else?" or "Would you like to know more?"
    - Do NOT offer additional help or suggestions
    - Just answer the question and STOP
    
    CRITICAL: NO HALLUCINATIONS
    - ONLY use data returned by MCP tools
    - If a tool fails or returns error, say "I couldn't retrieve that information right now"
    - NEVER make up account numbers, balances, transaction amounts, dates, or names
    - If you don't have the information, say "I don't have that information"
    
    Always use the below logged user details to retrieve account info:
    {user_mail}
    
    Examples:
    - User: "What is my account balance?" → You: "Your balance is 99,650.00 THB"
    - User: "Show me my account details" → You: "Account ID: CHK-001, Account Holder: Somchai Rattanakorn, Currency: THB, Balance: 99,650.00 THB"
    - User: "What is my daily transfer limit?" → You: "Your per-transaction limit is 50,000 THB and your daily limit is 200,000 THB. You have 200,000 THB remaining today"
    """
    name = "AccountAgent"
    description = "This agent manages user accounts related information such as balance, credit cards, and transaction limits."

    def __init__(self, foundry_project_client: AIProjectClient, 
                 chat_deployment_name:str,
                 account_mcp_server_url: str,
                 limits_mcp_server_url: str,
                 foundry_endpoint: str,
                 agent_id: str | None = None,
                 agent_name: str | None = None,
                 agent_version: str | None = None):
        self.foundry_project_client = foundry_project_client
        self.chat_deployment_name = chat_deployment_name
        self.account_mcp_server_url = account_mcp_server_url
        self.limits_mcp_server_url = limits_mcp_server_url
        self.foundry_endpoint = foundry_endpoint
        
        # Support both old agent_id and new name:version format
        if agent_name and agent_version:
            # V2 format: separate name and version
            self.agent_name = agent_name
            self.agent_version = agent_version
            logger.info(f"✅ Using V2 format: {agent_name}:{agent_version}")
        elif agent_id:
            # Try to parse agent_id in format "name:version"
            if ":" in agent_id:
                parts = agent_id.split(":", 1)
                self.agent_name = parts[0]
                self.agent_version = parts[1]
                logger.info(f"✅ Parsed V2 format from agent_id: {self.agent_name}:{self.agent_version}")
            else:
                # Old asst_* format - not supported
                raise ValueError(f"Old agent_id format '{agent_id}' not supported. Use agent_name and agent_version instead.")
        else:
            raise ValueError("Either (agent_name + agent_version) or agent_id must be provided")
        
        # LEGACY: Old approach stored created_agent object, now we just store the ID string
        # self.created_agent = get_or_create_agent(
        #     foundry_project_client, AccountAgent.name, AccountAgent.description, chat_deployment_name, agent_id=agent_id
        # )
        
        # ChatAgent caching to avoid rebuilding on every request
        self._cached_chat_agent = None
        self._cached_thread_id = None
        


    async def _create_mcp_tools(self, customer_id: str = None, thread_id: str = None):
        """Create fresh MCP tool instances for each request with audit logging"""
        logger.info("Creating fresh MCP connections for Account and Limits services...")
        
        # Use AuditedMCPTool for compliance tracking
        account_mcp_server = AuditedMCPTool(
            name="Account MCP server client",
            url=self.account_mcp_server_url,
            customer_id=customer_id,
            thread_id=thread_id,
            mcp_server_name="account"
        )
        await account_mcp_server.connect()
        logger.info("✅ Account MCP connection established (with audit logging)")
        
        limits_mcp_server = AuditedMCPTool(
            name="Limits MCP server client",
            url=self.limits_mcp_server_url,
            customer_id=customer_id,
            thread_id=thread_id,
            mcp_server_name="limits"
        )
        await limits_mcp_server.connect()
        logger.info("✅ Limits MCP connection established (with audit logging)")
        
        return account_mcp_server, limits_mcp_server

    async def build_af_agent(self, thread_id: str | None, customer_id: str = None, user_email: str = None) -> ChatAgent:
        """Build agent for this request with fresh MCP connection
        
        Args:
            thread_id: Thread ID for conversation continuity
            customer_id: Customer ID for audit logging (e.g., CUST-002)
            user_email: User's email/UPN from access token (e.g., nattaporn.suksawat@example.com)
        """
        # Check cache first
        if self._cached_chat_agent is not None and self._cached_thread_id == thread_id:
            logger.info(f"⚡ [CACHE HIT] Reusing cached AccountAgent for thread={thread_id}")
            print(f"⚡ [CACHE HIT] Reusing cached AccountAgent")
            return self._cached_chat_agent
        
        logger.info(f"Building AccountAgent for thread={thread_id}, customer={customer_id}, email={user_email}")
        
        # Create fresh MCP connections for this request with audit tracking
        account_mcp_server, limits_mcp_server = await self._create_mcp_tools(
            customer_id=customer_id,
            thread_id=thread_id
        )

        # Use provided user_email (UPN from token) or lookup from customer_id
        if user_email:
            user_mail = user_email
            print(f"📧 [ACCOUNT_AGENT] Using provided email: {user_mail}")
        else:
            # Fallback: lookup email from customer_id
            from app.auth.user_mapper import get_user_mapper
            
            try:
                user_mapper = get_user_mapper()
                customer_info = user_mapper.get_customer_info(customer_id)
                
                if customer_info:
                    user_mail = customer_info.get("email")
                    print(f"📧 [ACCOUNT_AGENT] Looked up email for {customer_id}: {user_mail}")
                else:
                    user_mail = "somchai.rattanakorn@example.com"
                    print(f"⚠️ [ACCOUNT_AGENT] No customer found for {customer_id}, using default")
            except Exception as e:
                print(f"❌ [ACCOUNT_AGENT] Error looking up customer: {e}")
                user_mail = "somchai.rattanakorn@example.com"
                print(f"⚠️ [ACCOUNT_AGENT] Using default email due to error")
        
        full_instruction = AccountAgent.instructions.format(user_mail=user_mail)

        credential = await get_azure_credential_async()

        # Create AzureAIClient with agent name and version
        chat_client = AzureAIClient(
            project_client=self.foundry_project_client,
            agent_name=self.agent_name,
            agent_version=self.agent_version
        )
        
        # Create ChatAgent using create_agent() method with tools
        chat_agent = chat_client.create_agent(
            name=AccountAgent.name,
            instructions=full_instruction,
            tools=[account_mcp_server, limits_mcp_server]
        )
        
        # Store reference to MCP tools so we can update thread context later
        chat_agent._mcp_tools = [account_mcp_server, limits_mcp_server]
        
        # Cache the agent for future requests
        self._cached_chat_agent = chat_agent
        self._cached_thread_id = thread_id
        logger.info(f"💾 [CACHE STORED] AccountAgent cached for thread={thread_id}")
        print(f"💾 [CACHE STORED] AccountAgent cached")
        
        return chat_agent