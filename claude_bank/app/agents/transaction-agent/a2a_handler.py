import httpx
from typing import Dict, Any
from a2a_sdk.models.message import A2AMessage
from common.observability import get_logger, create_span, add_span_attributes, get_audit_logger
from config import AgentConfig

logger = get_logger(__name__)
audit_logger = get_audit_logger()

class TransactionAgentHandler:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def handle_a2a_message(self, message: A2AMessage) -> Dict[str, Any]:
        intent = message.intent
        payload = message.payload

        with create_span("handle_a2a_message", {"intent": intent, "agent": "transaction"}):
            if intent in ["transaction.history", "transaction.get_history"]:
                return await self._handle_history_request(payload)
            elif intent in ["transaction.aggregation", "transaction.aggregate"]:
                return await self._handle_aggregation_request(payload)
            elif intent in ["transaction.details", "transaction.get_details"]:
                return await self._handle_details_request(payload)
            else:
                raise ValueError(f"Unsupported intent: {intent}")

    async def _handle_history_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = payload.get("customer_id")
        account_id = payload.get("account_id")
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")
        limit = payload.get("limit", 100)
        thread_id = payload.get("thread_id")

        if not customer_id:
            raise ValueError("customer_id is required")

        logger.info(f"Fetching transaction history for customer: {customer_id}")

        # Audit MCP tool invocation
        with audit_logger.audit_operation(
            operation_type="READ",
            mcp_server="transaction",
            tool_name="searchTransactions",
            user_id=customer_id,
            thread_id=thread_id,
            parameters={
                "customer_id": customer_id,
                "account_id": account_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit
            }
        ) as audit:
            with create_span("mcp_search_transactions"):
                add_span_attributes(customer_id=customer_id, mcp_tool="searchTransactions")

                response = await self.http_client.post(
                    f"{self.config.MCP_TRANSACTION_URL}/mcp/tools/searchTransactions",
                    json={
                        "customer_id": customer_id,
                        "account_id": account_id,
                        "start_date": start_date,
                        "end_date": end_date,
                        "limit": limit,
                    },
                )
                response.raise_for_status()
                transactions = response.json()
                
                # Track audit information
                tx_ids = [tx.get("transaction_id") for tx in transactions if tx.get("transaction_id")]
                audit.set_data_accessed(tx_ids)
                audit.set_data_scope("transaction_history")
                audit.set_result("success", f"Retrieved {len(transactions)} transaction(s)")
                audit.add_compliance_flag("GDPR_PERSONAL_DATA")  # Financial data

        return {
            "type": "TXN_TABLE",
            "customer_id": customer_id,
            "account_id": account_id,
            "transactions": transactions,
            "count": len(transactions),
        }

    async def _handle_aggregation_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = payload.get("customer_id")
        aggregation_type = payload.get("aggregation_type", "SUM")
        thread_id = payload.get("thread_id")

        logger.info(f"Aggregating transactions for customer: {customer_id}")

        # Audit MCP tool invocation
        with audit_logger.audit_operation(
            operation_type="READ",
            mcp_server="transaction",
            tool_name="aggregateTransactions",
            user_id=customer_id,
            thread_id=thread_id,
            parameters={"customer_id": customer_id, "aggregation_type": aggregation_type}
        ) as audit:
            with create_span("mcp_aggregate_transactions"):
                response = await self.http_client.post(
                    f"{self.config.MCP_TRANSACTION_URL}/mcp/tools/aggregateTransactions",
                    json={
                        "customer_id": customer_id,
                        "aggregation_type": aggregation_type,
                    },
                )
                response.raise_for_status()
                aggregation = response.json()
                
                # Track audit information
                audit.set_data_scope("transaction_aggregation")
                audit.set_result("success", f"Aggregation type: {aggregation_type}")
                audit.add_compliance_flag("GDPR_PERSONAL_DATA")

        return {
            "type": "INSIGHTS_CARD",
            "customer_id": customer_id,
            "aggregation_type": aggregation_type,
            "result": aggregation,
        }

    async def _handle_details_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        transaction_id = payload.get("transaction_id")

        if not transaction_id:
            raise ValueError("transaction_id is required")

        logger.info(f"Fetching transaction details: {transaction_id}")

        with create_span("mcp_get_transaction_details"):
            response = await self.http_client.post(
                f"{self.config.MCP_TRANSACTION_URL}/mcp/tools/getTransactionDetails",
                json={"transaction_id": transaction_id},
            )
            response.raise_for_status()
            transaction = response.json()

        return {
            "type": "TXN_DETAIL",
            "transaction": transaction,
        }

    async def check_mcp_health(self) -> bool:
        try:
            response = await self.http_client.get(
                f"{self.config.MCP_TRANSACTION_URL}/health",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return False
