"""A2A message handler for AIMoneyCoach Agent."""
import httpx
from typing import Dict, Any
from a2a_sdk.models.message import A2AMessage
from common.observability import get_logger, create_span, add_span_attributes
from config import AgentConfig

logger = get_logger(__name__)

class AIMoneyCoachAgentHandler:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def handle_a2a_message(self, message: A2AMessage) -> Dict[str, Any]:
        intent = message.intent
        payload = message.payload

        with create_span("handle_a2a_message", {"intent": intent, "agent": "ai-money-coach"}):
            if intent in ["coaching.debt_management", "coach.debt"]:
                return await self._handle_debt_management_request(payload)
            elif intent in ["coaching.financial_health", "coach.health"]:
                return await self._handle_financial_health_request(payload)
            elif intent in ["coaching.clarification", "coach.clarify"]:
                return await self._handle_clarification_request(payload)
            else:
                raise ValueError(f"Unsupported intent: {intent}")

    async def _handle_debt_management_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = payload.get("customer_id")
        context = payload.get("context", {})

        if not customer_id:
            raise ValueError("customer_id is required")

        logger.info(f"Providing debt management coaching for customer: {customer_id}")

        with create_span("mcp_get_debt_advice"):
            add_span_attributes(customer_id=customer_id, mcp_tool="getDebtAdvice")

            response = await self.http_client.post(
                f"{self.config.MCP_MONEYCOACH_URL}/mcp/tools/search",
                json={
                    "customer_id": customer_id,
                    "query": "debt management",
                    "context": context,
                },
            )
            response.raise_for_status()
            advice = response.json()

        return {
            "type": "COACHING_CARD",
            "customer_id": customer_id,
            "topic": "debt_management",
            "advice": advice.get("advice", ""),
            "action_items": advice.get("action_items", []),
        }

    async def _handle_financial_health_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = payload.get("customer_id")

        if not customer_id:
            raise ValueError("customer_id is required")

        logger.info(f"Assessing financial health for customer: {customer_id}")

        with create_span("mcp_assess_financial_health"):
            response = await self.http_client.post(
                f"{self.config.MCP_MONEYCOACH_URL}/mcp/tools/search",
                json={
                    "customer_id": customer_id,
                    "query": "financial health assessment",
                },
            )
            response.raise_for_status()
            assessment = response.json()

        return {
            "type": "HEALTH_ASSESSMENT",
            "customer_id": customer_id,
            "status": assessment.get("status", "ORDINARY"),  # ORDINARY or CRITICAL
            "score": assessment.get("score", 0),
            "recommendations": assessment.get("recommendations", []),
        }

    async def _handle_clarification_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = payload.get("customer_id")
        question = payload.get("question")

        if not customer_id:
            raise ValueError("customer_id is required")

        logger.info(f"Processing clarification request for customer: {customer_id}")

        with create_span("mcp_process_clarification"):
            response = await self.http_client.post(
                f"{self.config.MCP_MONEYCOACH_URL}/mcp/tools/search",
                json={
                    "customer_id": customer_id,
                    "query": question or "clarification needed",
                    "type": "clarification",
                },
            )
            response.raise_for_status()
            clarification = response.json()

        return {
            "type": "CLARIFICATION_CARD",
            "customer_id": customer_id,
            "questions": clarification.get("questions", []),
            "context": clarification.get("context", ""),
        }

    async def check_mcp_health(self) -> bool:
        try:
            response = await self.http_client.get(
                f"{self.config.MCP_MONEYCOACH_URL}/health",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return False
