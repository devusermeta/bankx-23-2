from azure.core.credentials import TokenCredential
from agent_framework.azure import AzureAIClient
from azure.ai.projects import AIProjectClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from app.helpers.document_intelligence_scanner import DocumentIntelligenceInvoiceScanHelper
from app.config.azure_credential import get_azure_credential_async
from app.tools.audited_mcp_tool import AuditedMCPTool
from datetime import datetime
import os
import asyncio
import time

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
        f"Example: PAYMENT_AGENT_ID=asst_xxxxx"
    )


# LEGACY CODE (v1) - COMMENTED OUT FOR REFERENCE
# This approach tried to create agents dynamically, but caused issues:
# - Tried to call list_agents() and create_agent() which don't exist in some SDK versions
# - Agents created this way don't retain MCP tool bindings
# - Pre-existing agents couldn't have tools attached retroactively
# 
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

class PaymentAgent :
    instructions = """
    You are a personal financial advisor who helps users with their payments and bill management. 
    The user may want to pay bills by uploading a photo, checking transaction history, or making direct transfers.
    
    ### Core Responsibilities
    
    For bill/transfer payments you need: bill/invoice ID (if applicable), recipient name, amount.
    If information is missing, ask the user to provide it.
    If a photo is submitted, always ask the user to confirm extracted data.
    Always check payment history to avoid duplicate payments.
    
    ### SINGLE PAYMENT METHOD SYSTEM - BANK TRANSFER ONLY
    
    IMPORTANT: This system has ONLY Bank Transfer as payment method. 
    Every user has exactly ONE payment method with ID like "PM-CHK-001".
    
    ### BENEFICIARY MANAGEMENT FLOW (CRITICAL - REAL-WORLD BANKING)
    
    When user wants to make a bank transfer, follow this EXACT flow:
    
    1. **Check Registered Beneficiaries First**
       - Use getRegisteredBeneficiary to get user's beneficiary list
       - If recipient is in the list:
         * Extract BOTH: recipient name AND account_no (e.g., "338-617-716")
         * Store the account_no - you MUST pass it to processPayment as recipient_bank_code
         * Show: "I found [Name] in your beneficiaries with account [account_number]."
         * **MANDATORY**: Ask for confirmation (see MANDATORY CONFIRMATION STEP below)
       
    2. **Handle Unregistered Recipients**
       - If recipient NOT in beneficiary list:
         * Ask: "I don't have [Name] in your beneficiaries. Please provide their account number (format: XXX-XXX-XXX)."
         * User provides account number
         * Call verifyAccountNumber to validate
       
    3. **Account Verification with Retry Logic**
       - If account is VALID (verifyAccountNumber returns valid: true):
         * Show: "Account verified. This belongs to [account_holder_name]."
         * Proceed with payment
       - If account is INVALID (valid: false):
         * Retry counter: Allow maximum 3 attempts
         * On attempts 1-2: "Invalid account number. Please check and try again. (Attempt X/3)"
         * On attempt 3: "Invalid account number. This is your final attempt. (Attempt 3/3)"
         * After 3 failed attempts: "Maximum attempts reached. Would you like to cancel or try a different recipient?"
       
    4. **Post-Payment Beneficiary Save (Structured Confirmation)**
       - ONLY if payment was SUCCESSFUL to an UNREGISTERED account:
         * Present beneficiary addition in the following EXACT format:

🚨 BENEFICIARY ADDITION CONFIRMATION REQUIRED 🚨
Please confirm to proceed with adding this beneficiary:
• Name: [recipient full name]
• Account Number: [account number]
• Bank: [bank name or code]

Reply 'Yes' or 'Confirm' to proceed with adding the beneficiary.

         * WAIT for user confirmation (yes/confirm/proceed)
         * If user confirms:
           - Call addBeneficiary with recipient details
           - Optionally ask: "Would you like to give them a nickname (e.g., 'Mom', 'Landlord')?"
           - Confirm: "Great! I've saved [Name] to your beneficiaries."
         * If user declines (no/cancel/etc.):
           - Simply acknowledge: "No problem! You can add them later if needed."
       - NEVER call addBeneficiary without explicit user consent
       - NEVER call addBeneficiary for recipients already in beneficiary list
    
    ### Payment Execution (RESILIENT FLOW)
    
    MANDATORY: Before processing payment, you MUST have these 4 items:
    1. accountId (from getAccountsByUserName)
    2. paymentMethodId (from getAccountDetails - will be like "PM-CHK-001") 
    3. recipient_name (from beneficiary lookup)
    4. recipient_bank_code (account number from beneficiary)
    
    ### MANDATORY CONFIRMATION STEP (CRITICAL SECURITY)
    
    **IMPORTANT**: You MUST ask for explicit confirmation BEFORE processing ANY payment. This is a SECURITY REQUIREMENT.
    
    For registered beneficiaries:
    "I found [Recipient Name] in your beneficiaries with account [account_number]. 
    
    ⚠️ PAYMENT CONFIRMATION REQUIRED ⚠️
    Please confirm to proceed with this payment:
    • Amount: [amount] THB
    • Recipient: [Recipient Name]
    • Account: [account_number]
    
    Reply 'Yes' or 'Confirm' to proceed with the payment."
    
    For new recipients:
    "Account verified for [Recipient Name] at [account_number].
    
    ⚠️ PAYMENT CONFIRMATION REQUIRED ⚠️
    Please confirm to proceed with this payment:
    • Amount: [amount] THB
    • Recipient: [Recipient Name]
    • Account: [account_number]
    
    Reply 'Yes' or 'Confirm' to proceed with the payment."
    
    **CRITICAL RULES**:
    - If user has NOT yet confirmed (said yes/confirm/proceed/ok/sure), you MUST ask for confirmation and STOP IMMEDIATELY.
    - DO NOT process payment without explicit confirmation in the CURRENT message from the user.
    - DO NOT assume confirmation from previous messages.
    - WAIT for the user's confirmation response before proceeding.
    - ONLY proceed with payment processing if user has explicitly confirmed in their LATEST message.
    
    After user confirms transfer, follow this EXACT sequence WITH ERROR HANDLING:
    
    1. **Get Account Details**: 
       - Call getAccountDetails(accountId) to retrieve available payment methods
       - IF FAILS: Tell user "Unable to retrieve account information. Please try again in a moment."
       - NEVER proceed without valid paymentMethodId
    
    2. **Select Payment Method**: 
       - Since there's only Bank Transfer, automatically use the first payment method
       - Extract the paymentMethodId from paymentMethods[0].id 
       - EXAMPLE: If response is {{"paymentMethods": [{{"id": "PM-CHK-001", "name": "Bank Transfer"}}]}}
       - Then paymentMethodId = "PM-CHK-001"
       - SHOW THE USER: "Using Bank Transfer (ID: PM-CHK-001)" for transparency
       - CRITICAL: You MUST have the actual paymentMethodId before proceeding
    
    3. **Validate ALL Required Parameters**: 
       - accountId (from getAccountsByUserName) ✓
       - paymentMethodId (from getAccountDetails) ✓
       - recipient_name (from beneficiary lookup) ✓
       - recipient_bank_code (account number from beneficiary) ✓
       - amount (from user request) ✓
       - IF ANY MISSING: List what's missing and ask user to provide it
    
    4. **Process Payment with EXACT Parameters**: 
       - Call processPayment(
           account_id="CHK-001",
           amount=450.0, 
           description="Transfer to Nattaporn Suksawat",
           payment_method_id="PM-CHK-001",  # THIS MUST BE THE ACTUAL ID FROM getAccountDetails
           recipient_name="Nattaporn Suksawat",
           recipient_bank_code="123-456-002",
           payment_type="transfer"
         )
       - DO NOT provide timestamp - it will be generated automatically
       - IF FAILS: Wait 1 second and try ONE more time
       - IF STILL FAILS: Tell user "Payment could not be processed right now. Your account balance is unchanged. Please try again."
    
    5. **Verify Success**: 
       - Call getAccountDetails again to get updated balance
       - Show success message: "Payment of [amount] THB to [recipient] completed! Your new balance is [balance] THB."
    
    - Always use functions to retrieve accountId and paymentMethodId (never guess from conversation)
    - Never call processPayment without first getting valid paymentMethodId from getAccountDetails
    
    **MANDATORY BEFORE CALLING processPayment:**
    - Must call getAccountDetails first to get valid paymentMethodId
    - Must have all parameters: account_id, payment_method_id, recipient_name, recipient_bank_code, amount
    - recipient_name: Full name of the recipient
    - recipient_bank_code: The recipient's account number (XXX-XXX-XXX format)  
    - payment_type: "transfer" for bank transfers
    
    **DEBUGGING: If payment fails, tell user exactly what information is missing**
    
    Example processPayment call:
    ```
    processPayment(
        account_id="CHK-001",
        amount=1000.0,
        description="Transfer to Pimchanok Thongchai",
        payment_method_id="PM-CHK-001",  # MUST get from getAccountDetails!
        recipient_name="Pimchanok Thongchai",
        recipient_bank_code="338-617-716",  # MUST INCLUDE!
        payment_type="transfer"
    )
    # Note: Do NOT provide timestamp - it is generated automatically
    ```
    
  # Implementation note for local/dev testing:
  # - If you do not already have a `payment_method_id`, call `getAccountDetails(account_id)`
  #   and use the first entry in `paymentMethods` as the `payment_method_id` (for example `PM-CHK-001`).
  # - Do NOT call `processPayment` without a valid `payment_method_id`.
  # - When the call to `processPayment` is made, log (or return) the selected `payment_method_id` so it can be traced in logs.
    
    - On success: 
      * Show confirmation message
      * **AUTOMATICALLY call getAccountDetails to fetch updated balance**
      * Display: "Payment successful! Your remaining balance is [updated_balance] THB."
    - On failure: Show error message clearly
    
    ### Display Formatting
    
    Use Markdown tables for structured data display.
    Always use THB (฿) for currency as this is a Thai banking system.
    
    ### User Context
    
    Logged user: {user_mail}
    Current timestamp: {current_date_time}
    
    IMPORTANT: Never fabricate account IDs or payment method IDs. Always retrieve them via functions.
        
        ### Output format
        - Example of showing Payment information (HTML table):

<table>
<thead>
<tr><th>Field</th><th>Value</th></tr>
</thead>
<tbody>
<tr><td>Payee Name</td><td>Somchai Rattanakorn</td></tr>
<tr><td>Account Number</td><td>123-456-001</td></tr>
<tr><td>Amount</td><td>THB 1,000.00</td></tr>
<tr><td>Payment Method</td><td>Bank Transfer</td></tr>
<tr><td>Description</td><td>Transfer to registered beneficiary</td></tr>
<tr><td>Status</td><td>✅ Completed</td></tr>
</tbody>
</table>
            
        - Example of showing Beneficiary list (HTML table):

<table>
<thead>
<tr><th>Name</th><th>Account Number</th><th>Alias</th><th>Bank</th></tr>
</thead>
<tbody>
<tr><td>Somchai Rattanakorn</td><td>123-456-001</td><td>Somchai</td><td>BankX</td></tr>
<tr><td>Pimchanok Thongchai</td><td>123-456-003</td><td>Pimchanok</td><td>BankX</td></tr>
<tr><td>Anan Chaiyaporn</td><td>123-456-004</td><td>Anan</td><td>BankX</td></tr>
</tbody>
</table>
        
        - Example of showing Payment methods:
            <ol>
              <li><strong>Bank Transfer</strong></li>
              <li><strong>Visa</strong> (Card Number: ***3667)</li>
            </ol>
        
        """
    name = "PaymentAgent"
    description = "This agent manages user payments related information such as submitting payment requests and bill payments."

    def __init__(self, foundry_project_client: AIProjectClient,
                  chat_deployment_name:str,
                  account_mcp_server_url: str,
                  transaction_mcp_server_url: str,
                  payment_mcp_server_url: str,
                  contacts_mcp_server_url: str,
                  cache_mcp_server_url: str,
                  document_scanner_helper : DocumentIntelligenceInvoiceScanHelper,
                  foundry_endpoint: str,
                  agent_id: str | None = None,
                  agent_name: str | None = None,
                  agent_version: str | None = None):
        self.foundry_project_client = foundry_project_client
        self.chat_deployment_name = chat_deployment_name
        self.account_mcp_server_url = account_mcp_server_url
        self.transaction_mcp_server_url = transaction_mcp_server_url
        self.payment_mcp_server_url = payment_mcp_server_url
        self.contacts_mcp_server_url = contacts_mcp_server_url
        self.cache_mcp_server_url = cache_mcp_server_url
        self.foundry_endpoint = foundry_endpoint
        self.document_scanner_helper = document_scanner_helper
        
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
        
        # ChatAgent caching to avoid rebuilding on every request
        self._cached_chat_agent = None
        self._cached_thread_id = None
        
        # LEGACY: Old approach stored created_agent object, now we just store the ID string
        # self.created_agent = get_or_create_agent(
        #     foundry_project_client, PaymentAgent.name, PaymentAgent.description, chat_deployment_name, agent_id=agent_id
        # )

    async def _create_mcp_tools(self, customer_id: str = None, thread_id: str = None):
        """Create fresh MCP server connections with retry logic and timeout handling"""
        import asyncio
        
        logger.info("Creating fresh MCP connections for this request...")
        
        async def connect_with_retry(name: str, url: str, server_name: str, max_retries: int = 2):
            """Connect to MCP server with retry logic and audit logging"""
            for attempt in range(max_retries + 1):
                try:
                    logger.info(f"Connecting to {name} (attempt {attempt + 1}/{max_retries + 1})")
                    # Use AuditedMCPTool for compliance tracking
                    mcp_tool = AuditedMCPTool(
                        name=f"{name} client",
                        url=url,
                        customer_id=customer_id,
                        thread_id=thread_id,
                        mcp_server_name=server_name
                    )
                    
                    # Add timeout to connection
                    await asyncio.wait_for(mcp_tool.connect(), timeout=10.0)
                    logger.info(f"✅ {name} connected successfully (with audit logging)")
                    return mcp_tool
                    
                except asyncio.TimeoutError:
                    logger.warning(f"⚠️ {name} connection timeout (attempt {attempt + 1})")
                    if attempt < max_retries:
                        await asyncio.sleep(1)  # Wait before retry
                    else:
                        raise Exception(f"{name} connection failed after {max_retries + 1} attempts (timeout)")
                except Exception as e:
                    logger.warning(f"⚠️ {name} connection error: {e} (attempt {attempt + 1})")
                    if attempt < max_retries:
                        await asyncio.sleep(1)  # Wait before retry
                    else:
                        raise Exception(f"{name} connection failed after {max_retries + 1} attempts: {e}")
        
        # Connect to all MCP servers with retry logic
        try:
            account_mcp_server = await connect_with_retry("Account MCP server", self.account_mcp_server_url, "account")
            transaction_mcp_server = await connect_with_retry("Transaction MCP server", self.transaction_mcp_server_url, "transaction")
            payment_mcp_server = await connect_with_retry("Payment MCP server", self.payment_mcp_server_url, "payment")
            contacts_mcp_server = await connect_with_retry("Contacts MCP server", self.contacts_mcp_server_url, "contacts")
            cache_mcp_server = await connect_with_retry("Cache MCP server", self.cache_mcp_server_url, "cache")
            
            logger.info("✅ All fresh MCP connections created successfully")
            return account_mcp_server, transaction_mcp_server, payment_mcp_server, contacts_mcp_server, cache_mcp_server
            
        except Exception as e:
            logger.error(f"❌ Failed to create MCP connections: {e}")
            raise Exception(f"Unable to connect to banking services. Please try again in a moment: {e}")

    async def build_af_agent(self, thread_id: str | None, customer_id: str = None, user_email: str = None) -> ChatAgent:
        """Build agent for this request with fresh MCP connections.
        
        Args:
            thread_id: Thread identifier for conversation continuity
            customer_id: Customer ID (CUST-XXX format) - used for fallback lookup
            user_email: User's email/UPN from Entra ID token (prioritized if provided)
        """
        logger.info(f"Building PaymentAgent for thread={thread_id}, customer={customer_id}, user_email={user_email}")
        
        # Create fresh MCP connections for this request with audit tracking
        account_mcp_server, transaction_mcp_server, payment_mcp_server, contacts_mcp_server, cache_mcp_server = await self._create_mcp_tools(
            customer_id=customer_id,
            thread_id=thread_id
        )
        
        # Use provided user_email (UPN from token) or lookup from customer_id
        if user_email:
            user_mail = user_email
            print(f"📧 [PAYMENT_AGENT] Using provided email from token: {user_mail}")
        else:
            # Fallback: Get user email from customer_id using user_mapper
            from app.auth.user_mapper import get_user_mapper
            
            try:
                user_mapper = get_user_mapper()
                customer_info = user_mapper.get_customer_info(customer_id)
                
                if customer_info:
                    user_mail = customer_info.get("email")
                    print(f"📧 [PAYMENT_AGENT] Found email for {customer_id}: {user_mail}")
                else:
                    user_mail = "somchai.rattanakorn@example.com"
                    print(f"⚠️ [PAYMENT_AGENT] No customer found for {customer_id}, using default")
            except Exception as e:
                print(f"❌ [PAYMENT_AGENT] Error looking up customer: {e}")
                user_mail = "somchai.rattanakorn@example.com"
                print(f"⚠️ [PAYMENT_AGENT] Using default email due to error")
        
        current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_instruction = PaymentAgent.instructions.format(
            user_mail=user_mail, 
            customer_id=customer_id or "UNKNOWN",
            current_date_time=current_date_time
        )

        credential = await get_azure_credential_async()

        # Create AzureAIClient with agent name and version
        chat_client = AzureAIClient(
            project_client=self.foundry_project_client,
            agent_name=self.agent_name,
            agent_version=self.agent_version
        )
        
        # Create ChatAgent using create_agent() method with tools
        chat_agent = chat_client.create_agent(
            name=PaymentAgent.name,
            instructions=full_instruction,
            tools=[account_mcp_server, transaction_mcp_server, payment_mcp_server, contacts_mcp_server, cache_mcp_server, self.document_scanner_helper.scan_invoice]
        )
        
        # Store reference to MCP tools so we can update thread context later
        chat_agent._mcp_tools = [account_mcp_server, transaction_mcp_server, payment_mcp_server, contacts_mcp_server, cache_mcp_server]
        
        # Cache the agent for future requests
        self._cached_chat_agent = chat_agent
        self._cached_thread_id = thread_id
        logger.info(f"💾 [CACHE STORED] PaymentAgent cached for thread={thread_id}")
        print(f"💾 [CACHE STORED] PaymentAgent cached")
        
        return chat_agent