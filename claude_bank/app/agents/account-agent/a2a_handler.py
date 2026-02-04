"""
A2A message handler for Account Agent.

This module handles A2A messages and routes them to the appropriate MCP tools.
"""

import httpx
from typing import Dict, Any

from a2a_sdk.models.message import A2AMessage
from common.observability import get_logger, create_span, add_span_attributes, get_audit_logger
from config import AgentConfig

logger = get_logger(__name__)
audit_logger = get_audit_logger()


class AccountAgentHandler:
    """Handle A2A messages for Account Agent."""

    def __init__(self, config: AgentConfig):
        """Initialize handler with configuration."""
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def handle_a2a_message(self, message: A2AMessage) -> Dict[str, Any]:
        """
        Route A2A message to appropriate handler based on intent.

        Args:
            message: A2A message from supervisor or another agent

        Returns:
            Response payload

        Raises:
            ValueError: If intent is not supported
        """
        intent = message.intent
        payload = message.payload

        with create_span(
            "handle_a2a_message", {"intent": intent, "agent": "account"}
        ):
            if intent == "account.get_balance" or intent == "account.balance":
                return await self._handle_balance_request(payload)
            elif intent == "account.get_limits" or intent == "account.limits":
                return await self._handle_limits_request(payload)
            elif (
                intent == "account.disambiguation"
                or intent == "account.disambiguate"
            ):
                return await self._handle_disambiguation_request(payload)
            else:
                raise ValueError(f"Unsupported intent: {intent}")

    async def _handle_balance_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account balance request."""
        customer_id = payload.get("customer_id")
        account_id = payload.get("account_id")
        thread_id = payload.get("thread_id")  # Extract thread_id from payload

        if not customer_id:
            raise ValueError("customer_id is required")

        logger.info(f"Fetching balance for customer: {customer_id}")

        # Audit MCP tool invocation
        with audit_logger.audit_operation(
            operation_type="READ",
            mcp_server="account",
            tool_name="getCustomerAccounts",
            user_id=customer_id,
            thread_id=thread_id,
            parameters={"customer_id": customer_id}
        ) as audit:
            with create_span("mcp_get_customer_accounts"):
                add_span_attributes(customer_id=customer_id, mcp_tool="getCustomerAccounts")

                # Call MCP Account service to get accounts
                response = await self.http_client.post(
                    f"{self.config.MCP_ACCOUNT_URL}/mcp/tools/getCustomerAccounts",
                    json={"customer_id": customer_id},
                )
                response.raise_for_status()
                accounts = response.json()
                
                # Track audit information
                account_ids = [acc["account_id"] for acc in accounts]
                audit.set_data_accessed(account_ids)
                audit.set_data_scope("account_details")
                audit.set_result("success", f"Retrieved {len(accounts)} account(s)")
                
                # Add compliance flags if needed
                if len(accounts) > 0 and accounts[0].get("account_type") == "SAVINGS":
                    audit.add_compliance_flag("PCI_DSS")

        if not accounts or len(accounts) == 0:
            return {
                "type": "ERROR",
                "error": "No accounts found for customer",
            }

        # If account_id specified, find that account
        if account_id:
            account = next(
                (acc for acc in accounts if acc["account_id"] == account_id), None
            )
            if not account:
                return {
                    "type": "ERROR",
                    "error": f"Account {account_id} not found",
                }
        else:
            # Use first account
            account = accounts[0]

        # Return balance card format
        return {
            "type": "BALANCE_CARD",
            "account_id": account["account_id"],
            "account_name": account.get("account_name", "Account"),
            "account_type": account.get("account_type", "CHECKING"),
            "currency": account.get("currency", "USD"),
            "ledger_balance": account.get("ledger_balance", 0.0),
            "available_balance": account.get("available_balance", 0.0),
        }

    async def _handle_limits_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle account limits request."""
        customer_id = payload.get("customer_id")
        account_id = payload.get("account_id")
        thread_id = payload.get("thread_id")

        if not customer_id:
            raise ValueError("customer_id is required")

        logger.info(f"Fetching limits for customer: {customer_id}")

        # Audit MCP tool invocation
        with audit_logger.audit_operation(
            operation_type="READ",
            mcp_server="limits",
            tool_name="getLimits",
            user_id=customer_id,
            thread_id=thread_id,
            parameters={"customer_id": customer_id, "account_id": account_id}
        ) as audit:
            with create_span("mcp_get_limits"):
                add_span_attributes(customer_id=customer_id, mcp_tool="getLimits")

                # Call MCP Limits service
                response = await self.http_client.post(
                    f"{self.config.MCP_LIMITS_URL}/mcp/tools/getLimits",
                    json={"customer_id": customer_id, "account_id": account_id},
                )
                response.raise_for_status()
                limits = response.json()
                
                # Track audit information
                audit.set_data_accessed([account_id] if account_id else [])
                audit.set_data_scope("account_limits")
                audit.set_result("success", "Limits retrieved")
                audit.add_compliance_flag("PCI_DSS")

        # Return limits information
        return {
            "type": "LIMITS_CARD",
            "customer_id": customer_id,
            "account_id": account_id,
            "daily_transfer_limit": limits.get("daily_transfer_limit", 0.0),
            "daily_transfer_used": limits.get("daily_transfer_used", 0.0),
            "per_transaction_limit": limits.get("per_transaction_limit", 0.0),
            "currency": limits.get("currency", "USD"),
        }

    async def _handle_disambiguation_request(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle account disambiguation when customer has multiple accounts."""
        customer_id = payload.get("customer_id")

        if not customer_id:
            raise ValueError("customer_id is required")

        logger.info(f"Disambiguating accounts for customer: {customer_id}")

        with create_span("mcp_get_customer_accounts"):
            add_span_attributes(customer_id=customer_id, mcp_tool="getCustomerAccounts")

            # Call MCP Account service to get all accounts
            response = await self.http_client.post(
                f"{self.config.MCP_ACCOUNT_URL}/mcp/tools/getCustomerAccounts",
                json={"customer_id": customer_id},
            )
            response.raise_for_status()
            accounts = response.json()

        if not accounts or len(accounts) == 0:
            return {
                "type": "ERROR",
                "error": "No accounts found for customer",
            }

        # Return account picker format
        return {
            "type": "ACCOUNT_PICKER",
            "customer_id": customer_id,
            "accounts": [
                {
                    "account_id": acc["account_id"],
                    "account_name": acc.get("account_name", "Account"),
                    "account_type": acc.get("account_type", "CHECKING"),
                    "balance": acc.get("ledger_balance", 0.0),
                    "currency": acc.get("currency", "USD"),
                }
                for acc in accounts
            ],
        }

    async def check_mcp_health(self) -> bool:
        """Check if MCP services are healthy."""
        try:
            # Check Account MCP service
            response = await self.http_client.get(
                f"{self.config.MCP_ACCOUNT_URL}/health",
                timeout=5.0,
            )
            if response.status_code != 200:
                return False

            # Check Limits MCP service
            response = await self.http_client.get(
                f"{self.config.MCP_LIMITS_URL}/health",
                timeout=5.0,
            )
            if response.status_code != 200:
                return False

            return True
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return False

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
