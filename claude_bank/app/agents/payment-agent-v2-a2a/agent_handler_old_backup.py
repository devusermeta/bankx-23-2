"""
Payment Agent v2 Handler - Simplified Transfer Agent

Handles payment/transfer requests using the unified Payment MCP Server.
Much simpler than the original payment agent - single MCP connection,
streamlined validate → approve → execute flow.
"""

import os
import sys
import logging
from pathlib import Path
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

try:
    from .audited_mcp_tool import AuditedMCPTool
except ImportError:
    from audited_mcp_tool import AuditedMCPTool

logger = logging.getLogger(__name__)


class PaymentAgentHandler:
    """
    Simplified handler for Payment Agent v2.
    
    Uses unified Payment MCP Server for all operations:
    - Account lookup
    - Beneficiary management
    - Limits checking
    - Transfer validation and execution
    """
    
    def __init__(
        self,
        customer_id: str,
        user_email: str,
        thread_id: str | None = None,
        mcp_url: str | None = None
    ):
        """
        Initialize Payment Agent v2 handler.
        
        Args:
            customer_id: Customer ID (e.g., "CUST-001")
            user_email: Customer's BankX email
            thread_id: Conversation thread ID
            mcp_url: URL of unified Payment MCP Server
        """
        self.customer_id = customer_id
        self.user_email = user_email
        self.thread_id = thread_id
        
        # Get MCP URL from env or parameter
        self.mcp_url = mcp_url or os.getenv(
            "PAYMENT_UNIFIED_MCP_URL",
            "http://localhost:8076/mcp"
        )
        
        # Azure AI Project credentials
        self.project_client = None
        self.agent = None
        self.agent_thread = None
        
        logger.info(
            f"[PAYMENT AGENT V2] Initialized handler for {customer_id} "
            f"(email={user_email}, thread={thread_id})"
        )
    
    def _create_mcp_tool(self) -> AuditedMCPTool:
        """
        Create audited MCP tool connection to unified Payment MCP Server.
        
        Returns:
            AuditedMCPTool instance connected to payment-unified MCP server
        """
        logger.info(f"[PAYMENT AGENT V2] Creating MCP tool connection to {self.mcp_url}")
        
        mcp_tool = AuditedMCPTool(
            name="Payment Unified MCP Server",
            url=self.mcp_url,
            customer_id=self.customer_id,
            thread_id=self.thread_id,
            mcp_server_name="payment-unified"
        )
        
        logger.info("[PAYMENT AGENT V2] ✅ MCP tool created")
        return mcp_tool
    
    def _load_instructions(self) -> str:
        """Load agent instructions from prompts/payment_agent.md"""
        prompts_path = Path(__file__).parent / "prompts" / "payment_agent.md"
        
        try:
            with open(prompts_path, "r", encoding="utf-8") as f:
                instructions = f.read()
            
            # Add customer context
            instructions += f"\n\n## Current Customer Context\n\n"
            instructions += f"- **Customer ID**: {self.customer_id}\n"
            instructions += f"- **Username (BankX Email)**: {self.user_email}\n"
            instructions += f"- **Thread ID**: {self.thread_id}\n"
            
            logger.info("[PAYMENT AGENT V2] ✅ Loaded instructions")
            return instructions
            
        except Exception as e:
            logger.error(f"[PAYMENT AGENT V2] ❌ Failed to load instructions: {e}")
            raise
    
    async def initialize_agent(self):
        """
        Initialize Azure AI Foundry agent with unified MCP tool.
        
        Creates:
        - Project client connection
        - Audited MCP tool
        - AI agent with instructions
        - Conversation thread
        """
        logger.info("[PAYMENT AGENT V2] 🚀 Initializing agent...")
        
        try:
            # Get Azure credentials
            project_endpoint = os.getenv("AZURE_PROJECT_ENDPOINT")
            if not project_endpoint:
                raise ValueError("AZURE_PROJECT_ENDPOINT not configured")
            
            # Create project client
            self.project_client = AIProjectClient.from_connection_string(
                credential=DefaultAzureCredential(),
                conn_str=project_endpoint
            )
            
            logger.info("[PAYMENT AGENT V2] ✅ Connected to Azure AI Project")
            
            # Create MCP tool
            mcp_tool = self._create_mcp_tool()
            
            # Load instructions
            instructions = self._load_instructions()
            
            # Get model deployment
            model_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")
            
            # Create agent
            logger.info(f"[PAYMENT AGENT V2] Creating agent with model: {model_deployment}")
            
            self.agent = self.project_client.agents.create_agent(
                model=model_deployment,
                name="payment-agent-v2",
                instructions=instructions,
                tools=[mcp_tool]
            )
            
            logger.info(f"[PAYMENT AGENT V2] ✅ Agent created: {self.agent.id}")
            
            # Create or get thread
            if self.thread_id:
                try:
                    self.agent_thread = self.project_client.agents.get_thread(
                        self.thread_id
                    )
                    logger.info(f"[PAYMENT AGENT V2] ✅ Using existing thread: {self.thread_id}")
                except:
                    logger.info(f"[PAYMENT AGENT V2] Thread {self.thread_id} not found, creating new")
                    self.agent_thread = self.project_client.agents.create_thread()
                    self.thread_id = self.agent_thread.id
            else:
                self.agent_thread = self.project_client.agents.create_thread()
                self.thread_id = self.agent_thread.id
                logger.info(f"[PAYMENT AGENT V2] ✅ Created thread: {self.thread_id}")
            
            logger.info("[PAYMENT AGENT V2] 🎉 Agent fully initialized")
            
        except Exception as e:
            logger.error(f"[PAYMENT AGENT V2] ❌ Initialization failed: {e}")
            raise
    
    async def handle_message(self, user_message: str) -> dict:
        """
        Handle a user message - the main entry point.
        
        Args:
            user_message: User's message text
            
        Returns:
            Dictionary with response and metadata:
            {
                "response": str,
                "thread_id": str,
                "success": bool,
                "error": str | None
            }
        """
        logger.info(f"[PAYMENT AGENT V2] 📨 Handling message: {user_message[:100]}...")
        
        try:
            # Ensure agent is initialized
            if not self.agent:
                await self.initialize_agent()
            
            # Add user message to thread
            self.project_client.agents.create_message(
                thread_id=self.thread_id,
                role="user",
                content=user_message
            )
            
            logger.info(f"[PAYMENT AGENT V2] ▶️  Running agent on thread {self.thread_id}")
            
            # Run agent
            run = self.project_client.agents.create_and_process_run(
                thread_id=self.thread_id,
                assistant_id=self.agent.id
            )
            
            logger.info(f"[PAYMENT AGENT V2] Run status: {run.status}")
            
            # Check run status
            if run.status == "failed":
                error_msg = f"Agent run failed: {run.last_error.message if run.last_error else 'Unknown error'}"
                logger.error(f"[PAYMENT AGENT V2] ❌ {error_msg}")
                return {
                    "response": "I apologize, but I encountered an error processing your request. Please try again.",
                    "thread_id": self.thread_id,
                    "success": False,
                    "error": error_msg
                }
            
            # Get messages from thread
            messages = self.project_client.agents.list_messages(
                thread_id=self.thread_id
            )
            
            # Get latest assistant message
            assistant_messages = [
                msg for msg in messages.data 
                if msg.role == "assistant"
            ]
            
            if not assistant_messages:
                logger.warning("[PAYMENT AGENT V2] ⚠️  No assistant response found")
                return {
                    "response": "I apologize, but I couldn't generate a response. Please try again.",
                    "thread_id": self.thread_id,
                    "success": False,
                    "error": "No assistant response"
                }
            
            # Extract text from latest message
            latest_message = assistant_messages[0]
            response_text = self._extract_message_text(latest_message.content)
            
            logger.info(f"[PAYMENT AGENT V2] ✅ Response generated ({len(response_text)} chars)")
            
            return {
                "response": response_text,
                "thread_id": self.thread_id,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"[PAYMENT AGENT V2] ❌ Error handling message: {e}")
            return {
                "response": "I apologize, but an unexpected error occurred. Please try again.",
                "thread_id": self.thread_id,
                "success": False,
                "error": str(e)
            }
    
    def _extract_message_text(self, content) -> str:
        """
        Extract text from message content.
        
        Args:
            content: List of message content items (dicts or objects)
            
        Returns:
            Combined text string
        """
        text_parts = []
        
        for item in content:
            # Handle both dict and object formats
            if hasattr(item, 'text'):
                # Object format
                text_parts.append(item.text.value if hasattr(item.text, 'value') else str(item.text))
            elif isinstance(item, dict) and 'text' in item:
                # Dict format
                text_parts.append(item['text']['value'] if isinstance(item['text'], dict) else item['text'])
        
        return "\n".join(text_parts)
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("[PAYMENT AGENT V2] 🧹 Cleaning up resources")
        
        try:
            if self.agent and self.project_client:
                # Optionally delete agent (or keep for reuse)
                # self.project_client.agents.delete_agent(self.agent.id)
                pass
            
            logger.info("[PAYMENT AGENT V2] ✅ Cleanup completed")
            
        except Exception as e:
            logger.warning(f"[PAYMENT AGENT V2] ⚠️  Cleanup error: {e}")
    
    def __repr__(self):
        return (
            f"PaymentAgentHandler(customer={self.customer_id}, "
            f"email={self.user_email}, thread={self.thread_id})"
        )
