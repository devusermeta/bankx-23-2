"""
EscalationComms Agent - Azure AI Foundry Implementation
Purpose: Email notifications for support tickets and escalations
"""

import os
import logging
from typing import Any
from azure.ai.projects import AIProjectClient
from agent_framework.azure import AzureAIClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from app.config.azure_credential import get_azure_credential_async

logger = logging.getLogger(__name__)


def get_or_create_agent(foundry_client, agent_name: str, agent_description: str, model_deployment: str, agent_id: str | None = None):
    """Check if agent exists, if not create it. Returns the agent object (or agent_id string in Docker mode)."""
    # Check if we're in Docker mode (use pre-configured agents only)
    use_prebuilt_only = os.getenv('USE_PREBUILT_AGENTS_ONLY', 'false').lower() == 'true'
    
    if use_prebuilt_only:
        # Docker mode: Use pre-configured agent ID only (SDK may not support agent creation)
        if agent_id:
            print(f"✅ [DOCKER MODE] Using pre-configured agent ID for {agent_name}: {agent_id}")
            return agent_id
        raise ValueError(
            f"❌ Docker mode requires pre-configured agent. No agent_id configured for {agent_name}. "
            f"Please create the agent in Azure AI Foundry portal and configure its ID in the .env file."
        )
    
    # Local dev mode: Use NEW Azure AI Foundry V2 format (name:version)
    # Agents must already exist in Azure AI Foundry portal
    # No need to create/check - just use the reference
    print(f"✅ Using agent name (V2 format): {agent_name}:v1")
    
    class AgentReference:
        """Simple agent reference for V2 format"""
        def __init__(self, name):
            self.id = f"{name}:v1"  # V2 format: name:version
            self.name = name
    
    return AgentReference(agent_name)


class EscalationCommsAgent:
    """
    EscalationComms Agent for email notifications via Azure Communication Services
    
    Provides email notification capabilities for:
    - Support ticket notifications (UC2 - ProdInfoFAQ)
    - Financial advisory escalations (UC3 - AIMoneyCoach)
    
    Architecture:
    - Uses Azure AI Foundry Agent SDK
    - Connects to EscalationComms MCP Server (port 8078)
    - MCP tools: send_email, send_ticket_notification
    """
    
    name = "EscalationCommsAgent"
    description = "Sends email notifications for support tickets and escalations via Azure Communication Services"
    
    instructions = """You are the EscalationComms Agent for BankX, specialized in sending email notifications for support tickets and customer escalations.

**Your Core Responsibilities:**
1. Send email notifications when support tickets are created
2. Send ticket confirmation emails to customers
3. Ensure all notifications are properly formatted and delivered
4. Handle email sending with appropriate error handling

**Available Tools:**
1. **send_email**: Send a generic email
   - Use for custom email scenarios
   - Requires: recipient email, subject, body, optional CC/BCC
   
2. **send_ticket_notification**: Send formatted support ticket notification
   - Use when a support ticket is created
   - Automatically formats email with ticket details
   - Requires: ticket_id, customer_email, customer_name, query, category
   - Sends confirmation to customer with ticket ID and details

**Email Sending Guidelines:**
- ALWAYS validate email addresses before sending
- Include clear ticket IDs in subject lines
- Format emails professionally with proper HTML structure
- Handle errors gracefully and report failures clearly
- Confirm successful sends with message IDs
**Example Flow:**
User: "Send ticket notification for TKT-20251112-000001"
1. Call send_ticket_notification with ticket details
2. Confirm email sent successfully
3. Report message ID if available

**Important:**
- All emails are sent via Azure Communication Services
- Emails are automatically CC'd to support team in dev/test mode
- Always confirm receipt or report errors clearly
"""

    def __init__(
        self,
        foundry_project_client: AIProjectClient,
        chat_deployment_name: str,
        escalation_comms_mcp_server_url: str = None,
        foundry_endpoint: str = None,
        agent_id: str = None,
        agent_name: str = None,
        agent_version: str = None
    ):
        """
        Initialize EscalationComms Agent with Azure AI Foundry.
        
        Args:
            foundry_project_client: Azure AI Foundry project client
            chat_deployment_name: Chat model deployment name
            escalation_comms_mcp_server_url: EscalationComms MCP server URL (port 8078)
            foundry_endpoint: Azure AI Foundry endpoint
            agent_id: Pre-existing agent ID (deprecated)
            agent_name: Agent name for V2 format
            agent_version: Agent version for V2 format
        """
        self.foundry_project_client = foundry_project_client
        self.chat_deployment_name = chat_deployment_name
        self.escalation_comms_mcp_server_url = escalation_comms_mcp_server_url
        self.foundry_endpoint = foundry_endpoint
        
        # Support both old agent_id and new name:version format
        if agent_name and agent_version:
            self.agent_name = agent_name
            self.agent_version = agent_version
            logger.info(f"✅ Using V2 format: {agent_name}:{agent_version}")
        elif agent_id:
            if ":" in agent_id:
                parts = agent_id.split(":", 1)
                self.agent_name = parts[0]
                self.agent_version = parts[1]
                logger.info(f"✅ Parsed V2 format from agent_id: {self.agent_name}:{self.agent_version}")
            else:
                raise ValueError(f"Old agent_id format '{agent_id}' not supported. Use agent_name and agent_version instead.")
        else:
            raise ValueError("Either (agent_name + agent_version) or agent_id must be provided")
        
        logger.info("EscalationCommsAgent initialized with Azure AI Foundry")
        logger.info(f"  EscalationComms MCP Server: {escalation_comms_mcp_server_url}")
        logger.info(f"  Agent: {self.agent_name}:{self.agent_version}")
        
        # ChatAgent caching to avoid rebuilding on every request
        self._cached_chat_agent = None
        self._cached_thread_id = None

    async def build_af_agent(self, thread_id: str | None) -> ChatAgent:
        """Build agent for this request with fresh MCP connection"""
        # Check cache first
        if self._cached_chat_agent is not None and self._cached_thread_id == thread_id:
            logger.info(f"⚡ [CACHE HIT] Reusing cached EscalationCommsAgent for thread={thread_id}")
            print(f"⚡ [CACHE HIT] Reusing cached EscalationCommsAgent")
            return self._cached_chat_agent
        
        logger.info("Building EscalationCommsAgent for thread")
        
        # Create MCP connection for EscalationComms server
        tools_list = []
        
        if self.escalation_comms_mcp_server_url:
            logger.info(f"Connecting to EscalationComms MCP server: {self.escalation_comms_mcp_server_url}")
            escalation_mcp_server = MCPStreamableHTTPTool(
                name="EscalationComms MCP server client",
                url=self.escalation_comms_mcp_server_url
            )
            await escalation_mcp_server.connect()
            tools_list.append(escalation_mcp_server)
            logger.info("✅ EscalationComms MCP connection established")
        else:
            logger.warning("⚠️  No EscalationComms MCP server URL provided")
        
        credential = await get_azure_credential_async()
        
        # Create AzureAIClient with agent name and version
        chat_client = AzureAIClient(
            project_client=self.foundry_project_client,
            agent_name=self.agent_name,
            agent_version=self.agent_version
        )
        
        # Create ChatAgent using create_agent() method with tools
        chat_agent = chat_client.create_agent(
            name=EscalationCommsAgent.name,
            instructions=EscalationCommsAgent.instructions,
            tools=tools_list
        )
        
        # Cache the agent for future requests
        self._cached_chat_agent = chat_agent
        self._cached_thread_id = thread_id
        logger.info(f"💾 [CACHE STORED] EscalationCommsAgent cached for thread={thread_id}")
        print(f"💾 [CACHE STORED] EscalationCommsAgent cached")
        
        return chat_agent
