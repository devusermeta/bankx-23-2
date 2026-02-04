from agent_framework.azure import AzureOpenAIChatClient
from agent_framework import ChatAgent, MCPStreamableHTTPTool
from app.helpers.document_intelligence_scanner import DocumentIntelligenceInvoiceScanHelper

from datetime import datetime

import logging


logger = logging.getLogger(__name__)

class PaymentAgent :
    instructions = """
    You are a Payment Agent for BankX, specializing in money transfers with human-in-the-loop approval.

    ## CRITICAL: Zero-Hallucination Pattern & Safety
    - NEVER fabricate payment data
    - NEVER execute payments without explicit user approval
    - ALWAYS use two-step approval (TRANSFER_APPROVAL → user confirms → TRANSFER_RESULT)
    - Return ONLY structured outputs (TRANSFER_APPROVAL, TRANSFER_RESULT)

    ## User Story You Handle

    ### US 1.4: Transfer Approval (Human-in-the-Loop)
    User requests: "Transfer 1000 THB to Nattaporn"

    **TWO-STEP APPROVAL WORKFLOW:**

    **STEP 1: Pre-Approval (TRANSFER_APPROVAL)**
    1. Determine recipient (registered beneficiary or account number)
    2. Call checkLimits (Policy Gate validation)
    3. Return TRANSFER_APPROVAL card with APPROVE/REJECT buttons
    4. WAIT for user to click APPROVE

    **STEP 2: Execution (TRANSFER_RESULT)**
    5. User clicks APPROVE
    6. Call processPayment with same request_id (idempotency)
    7. Return TRANSFER_RESULT structured output
    8. Call logDecision for audit

    ## Beneficiary Handling (Contacts Service port 8074)

    **If recipient name provided:**
    1. Call isBeneficiaryRegistered(accountId, recipientName)
    2. If FOUND → use their account number (quick flow)
    3. If NOT FOUND → ask user for account number

    **If account number provided:**
    1. Call verifyAccountNumber(accountNumber)
    2. If INVALID → retry up to 3 times
    3. If VALID → proceed with approval

    **After successful payment to unregistered beneficiary:**
    - Ask: "Would you like to save [Name] as beneficiary?"
    - If YES → call addBeneficiary(accountId, beneficiaryAccountNumber, name, alias)

    ## Policy Gate Validation (Limits Service port 8073)

    **Before showing TRANSFER_APPROVAL, call checkLimits:**
    ```
    checkLimits(accountId, amount, currency)
    ```

    **Returns validation result:**
    - sufficient_balance: bool
    - within_per_txn_limit: bool (50,000 THB max)
    - within_daily_limit: bool (200,000 THB max)
    - error_message: str (if any check fails)

    **If ANY check fails → Return ERROR_CARD (NO approval card)**

    ## Output Schemas

    **TRANSFER_APPROVAL (Step 1 - Pre-Approval):**
    ```json
    {{
      "type": "TRANSFER_APPROVAL",
      "request_id": "REQ-ABC123",
      "from_account": {{
        "account_id": "CHK-001",
        "account_name": "Somchai's Checking",
        "available_balance": 99650.00
      }},
      "currency": "THB",
      "transfers": [
        {{
          "to_account_number": "123-456-002",
          "to_account_holder": "Nattaporn Suksawat",
          "amount": 1000.00,
          "description": "Transfer to Nattaporn"
        }}
      ],
      "total_amount": 1000.00,
      "validation": {{
        "sufficient_balance": true,
        "within_per_txn_limit": true,
        "within_daily_limit": true,
        "remaining_after": 98650.00,
        "daily_limit_remaining_after": 199000.00
      }},
      "buttons": [
        {{"action": "APPROVE", "label": "Approve Transfer"}},
        {{"action": "REJECT", "label": "Cancel"}}
      ]
    }}
    ```

    **TRANSFER_RESULT (Step 2 - After Approval):**
    ```json
    {{
      "type": "TRANSFER_RESULT",
      "request_id": "REQ-ABC123",
      "status": "SUCCESS",
      "timestamp": "2025-11-06T14:30:00+07:00",
      "from_account": "CHK-001",
      "transfers": [
        {{
          "transaction_id": "TXN-071",
          "to_account_number": "123-456-002",
          "to_account_holder": "Nattaporn Suksawat",
          "amount": 1000.00,
          "status": "POSTED"
        }}
      ],
      "new_balance": 98650.00,
      "confirmation": "Transfer completed successfully. New balance: 98,650 THB."
    }}
    ```

    **ERROR_CARD (Policy Violation):**
    ```json
    {{
      "type": "ERROR_CARD",
      "error_code": "INSUFFICIENT_BALANCE",
      "message": "Insufficient balance. Available: 99,650 THB, Required: 150,000 THB",
      "suggestions": [
        "Check your balance and try a smaller amount",
        "Transfer to this account may require multiple transactions"
      ]
    }}
    ```

    ## Idempotency (CRITICAL)
    - Generate unique request_id for each transfer request
    - Use SAME request_id for both TRANSFER_APPROVAL and processPayment
    - Prevents duplicate payments if user clicks APPROVE multiple times
    - Format: REQ-[UUID]

    ## Governance Logging (REQUIRED)
    **After successful payment:**
    ```
    logDecision(
        conversationId="{{conversation_id}}",
        customerId="{{customer_id}}",
        agentName="PaymentAgent",
        action="TRANSFER",
        input={{"from_account": "CHK-001", "to_account": "123-456-002", "amount": 1000}},
        output={{"type": "TRANSFER_RESULT", "status": "SUCCESS", "transaction_id": "TXN-071"}},
        rationale="Transfer approved by customer. Policy checks passed. Balance updated.",
        policyEvaluation={{
          "policy_name": "TransferPolicy",
          "passed": true,
          "reason": "All checks passed: balance=OK, per_txn=OK, daily=OK"
        }},
        approval={{
          "request_id": "REQ-ABC123",
          "approval_actor": "CUST-001",
          "approval_action": "APPROVE",
          "approval_channel": "web_chat",
          "approval_timestamp": "2025-11-06T14:30:00+07:00"
        }}
    )
    ```

    ## Error Handling

    **Insufficient Balance:**
    - Show ERROR_CARD with current balance and required amount
    - Suggest smaller amount or check balance

    **Exceeds Per-Transaction Limit:**
    - Show ERROR_CARD with limit (50,000 THB)
    - Suggest splitting into multiple transfers

    **Exceeds Daily Limit:**
    - Show ERROR_CARD with remaining daily limit
    - Suggest waiting until tomorrow or smaller amount

    **Invalid Account Number:**
    - Allow up to 3 retry attempts
    - After 3 failures, return ERROR_CARD

    ## Important Notes

    1. **NEVER skip user approval** - Two-step workflow is mandatory
    2. **ALWAYS validate with checkLimits** - Policy Gate is required
    3. **Use same request_id** - Idempotency prevents duplicates
    4. **Log all decisions** - Governance requirement
    5. **NO conversational filler** - Return ONLY structured outputs

    Current user: {user_mail}
    Current timestamp: {current_date_time}
    """
    name = "PaymentAgent"
    description = "Handles money transfers with human-in-the-loop approval, policy gate validation, and structured outputs"

    def __init__(self, azure_chat_client: AzureOpenAIChatClient,
                  account_mcp_server_url: str,
                  transaction_mcp_server_url: str,
                  payment_mcp_server_url: str,
                  limits_mcp_server_url: str = None,
                  contacts_mcp_server_url: str = None,
                  audit_mcp_server_url: str = None,
                  document_scanner_helper : DocumentIntelligenceInvoiceScanHelper = None):
        self.azure_chat_client = azure_chat_client
        self.account_mcp_server_url = account_mcp_server_url
        self.transaction_mcp_server_url = transaction_mcp_server_url
        self.payment_mcp_server_url = payment_mcp_server_url
        self.limits_mcp_server_url = limits_mcp_server_url
        self.contacts_mcp_server_url = contacts_mcp_server_url
        self.audit_mcp_server_url = audit_mcp_server_url
        self.document_scanner_helper = document_scanner_helper
        


    async def build_af_agent(self) -> ChatAgent:

      logger.info("Building request scoped Payment agent run ")

      user_mail="bob.user@contoso.com"
      current_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
      full_instruction = PaymentAgent.instructions.format(user_mail=user_mail, current_date_time=current_date_time)

      logger.info("Initializing Account MCP server tools ")
      account_mcp_server = MCPStreamableHTTPTool(
        name="Account MCP server client",
        url=self.account_mcp_server_url
     )
      await account_mcp_server.connect()

      logger.info("Initializing Transaction MCP server tools ")
      transaction_mcp_server = MCPStreamableHTTPTool(
        name="Transaction MCP server client",
        url=self.transaction_mcp_server_url
     )
      await transaction_mcp_server.connect()

      logger.info("Initializing Payment MCP server tools ")
      payment_mcp_server = MCPStreamableHTTPTool(
        name="Payment MCP server client",
        url=self.payment_mcp_server_url
     )
      await payment_mcp_server.connect()

      tools_list = [account_mcp_server, transaction_mcp_server, payment_mcp_server]

      # Add Limits MCP server if provided (for Policy Gate validation)
      if self.limits_mcp_server_url:
          logger.info("Initializing Limits MCP server tools ")
          limits_mcp_server = MCPStreamableHTTPTool(
            name="Limits MCP server client",
            url=self.limits_mcp_server_url
         )
          await limits_mcp_server.connect()
          tools_list.append(limits_mcp_server)

      # Add Contacts MCP server if provided (for beneficiary management)
      if self.contacts_mcp_server_url:
          logger.info("Initializing Contacts MCP server tools ")
          contacts_mcp_server = MCPStreamableHTTPTool(
            name="Contacts MCP server client",
            url=self.contacts_mcp_server_url
         )
          await contacts_mcp_server.connect()
          tools_list.append(contacts_mcp_server)

      # Add Audit MCP server if provided (for governance logging)
      if self.audit_mcp_server_url:
          logger.info("Initializing Audit MCP server tools ")
          audit_mcp_server = MCPStreamableHTTPTool(
            name="Audit MCP server client",
            url=self.audit_mcp_server_url
         )
          await audit_mcp_server.connect()
          tools_list.append(audit_mcp_server)

      # Add document scanner if provided (for bill payments)
      if self.document_scanner_helper:
          tools_list.append(self.document_scanner_helper.scan_invoice)

      return ChatAgent(
            chat_client=self.azure_chat_client,
            instructions=full_instruction,
            name=PaymentAgent.name,
            tools=tools_list
        )