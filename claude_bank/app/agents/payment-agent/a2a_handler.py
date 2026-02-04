import httpx
from typing import Dict, Any
from a2a_sdk.models.message import A2AMessage
from common.observability import get_logger, create_span, add_span_attributes, get_audit_logger
from config import AgentConfig

logger = get_logger(__name__)
audit_logger = get_audit_logger()

class PaymentAgentHandler:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def handle_a2a_message(self, message: A2AMessage) -> Dict[str, Any]:
        intent = message.intent
        payload = message.payload

        with create_span("handle_a2a_message", {"intent": intent, "agent": "payment"}):
            if intent in ["payment.transfer", "payment.create_transfer"]:
                return await self._handle_transfer_request(payload)
            elif intent in ["payment.validate", "payment.validate_transfer"]:
                return await self._handle_validate_request(payload)
            else:
                raise ValueError(f"Unsupported intent: {intent}")

    async def _handle_transfer_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        from_account_id = payload.get("from_account_id")
        to_account_id = payload.get("to_account_id")
        amount = payload.get("amount")
        currency = payload.get("currency", "USD")
        customer_id = payload.get("customer_id")
        thread_id = payload.get("thread_id")

        if not all([from_account_id, to_account_id, amount]):
            raise ValueError("from_account_id, to_account_id, and amount are required")

        logger.info(f"Processing transfer: {amount} {currency} from {from_account_id} to {to_account_id}")

        # Validate against limits first - Audit READ operation
        with audit_logger.audit_operation(
            operation_type="READ",
            mcp_server="limits",
            tool_name="checkLimits",
            user_id=customer_id,
            thread_id=thread_id,
            parameters={"account_id": from_account_id, "amount": amount}
        ) as audit:
            with create_span("mcp_check_limits"):
                response = await self.http_client.post(
                    f"{self.config.MCP_LIMITS_URL}/mcp/tools/checkLimits",
                    json={"account_id": from_account_id, "amount": amount},
                )
                response.raise_for_status()
                limits_check = response.json()
                
                # Track audit information
                audit.set_data_accessed([from_account_id])
                audit.set_data_scope("payment_limits_check")
                allowed = limits_check.get("allowed", False)
                audit.set_result("success" if allowed else "rejected", 
                               f"Limit check: {'allowed' if allowed else 'rejected'}")
                audit.add_compliance_flag("PCI_DSS")

        if not limits_check.get("allowed", False):
            return {
                "type": "TRANSFER_REJECTED",
                "reason": limits_check.get("reason", "Limit exceeded"),
            }

        # Submit payment - Audit WRITE operation
        with audit_logger.audit_operation(
            operation_type="WRITE",
            mcp_server="payment",
            tool_name="submitPayment",
            user_id=customer_id,
            thread_id=thread_id,
            parameters={
                "from_account_id": from_account_id,
                "to_account_id": to_account_id,
                "amount": amount,
                "currency": currency
            }
        ) as audit:
            with create_span("mcp_submit_payment"):
                response = await self.http_client.post(
                    f"{self.config.MCP_PAYMENT_URL}/mcp/tools/submitPayment",
                    json={
                        "from_account_id": from_account_id,
                        "to_account_id": to_account_id,
                        "amount": amount,
                        "currency": currency,
                    },
                )
                response.raise_for_status()
                payment_result = response.json()
                
                # Track audit information
                tx_id = payment_result.get("transaction_id")
                audit.set_data_accessed([from_account_id, to_account_id, tx_id] if tx_id else [from_account_id, to_account_id])
                audit.set_data_scope("payment_execution")
                audit.set_result("success", f"Payment initiated: {tx_id}")
                audit.add_compliance_flag("PCI_DSS")
                if float(amount) > 10000:  # High value transaction threshold
                    audit.add_compliance_flag("HIGH_VALUE_TRANSACTION")

        return {
            "type": "TRANSFER_RESULT",
            "transaction_id": payment_result.get("transaction_id"),
            "status": payment_result.get("status", "SUCCESS"),
            "amount": amount,
            "currency": currency,
        }

    async def _handle_validate_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        from_account_id = payload.get("from_account_id")
        amount = payload.get("amount")

        with create_span("mcp_validate_transfer"):
            response = await self.http_client.post(
                f"{self.config.MCP_PAYMENT_URL}/mcp/tools/validateTransfer",
                json={"from_account_id": from_account_id, "amount": amount},
            )
            response.raise_for_status()
            validation = response.json()

        return {
            "type": "VALIDATION_RESULT",
            "valid": validation.get("valid", False),
            "errors": validation.get("errors", []),
        }

    async def check_mcp_health(self) -> bool:
        try:
            response = await self.http_client.get(f"{self.config.MCP_PAYMENT_URL}/health", timeout=5.0)
            if response.status_code != 200:
                return False
            response = await self.http_client.get(f"{self.config.MCP_LIMITS_URL}/health", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return False
