"""A2A message handler for ProdInfoFAQ Agent."""
import httpx
from typing import Dict, Any
from a2a_sdk.models.message import A2AMessage
from common.observability import get_logger, create_span, add_span_attributes
from config import AgentConfig

logger = get_logger(__name__)

class ProdInfoFAQAgentHandler:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def handle_a2a_message(self, message: A2AMessage) -> Dict[str, Any]:
        intent = message.intent
        payload = message.payload

        with create_span("handle_a2a_message", {"intent": intent, "agent": "prodinfo-faq"}):
            if intent in ["product.info", "product.get_info"]:
                return await self._handle_product_info_request(payload)
            elif intent in ["faq.answer", "faq.get_answer"]:
                return await self._handle_faq_request(payload)
            elif intent in ["ticket.create", "support.create_ticket"]:
                return await self._handle_create_ticket_request(payload)
            else:
                raise ValueError(f"Unsupported intent: {intent}")

    async def _handle_product_info_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        query = payload.get("query")
        product_type = payload.get("product_type")

        if not query:
            raise ValueError("query is required")

        logger.info(f"Searching product info: {query}")

        with create_span("mcp_search_product_info"):
            add_span_attributes(query=query, mcp_tool="searchProductInfo")

            response = await self.http_client.post(
                f"{self.config.MCP_PRODINFO_URL}/mcp/tools/search",
                json={"query": query, "product_type": product_type},
            )
            response.raise_for_status()
            results = response.json()

        return {
            "type": "KNOWLEDGE_CARD",
            "query": query,
            "results": results,
            "count": len(results),
        }

    async def _handle_faq_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        question = payload.get("question")

        if not question:
            raise ValueError("question is required")

        logger.info(f"Searching FAQ: {question}")

        with create_span("mcp_search_faq"):
            add_span_attributes(question=question, mcp_tool="searchFAQ")

            response = await self.http_client.post(
                f"{self.config.MCP_PRODINFO_URL}/mcp/tools/search",
                json={"query": question, "type": "faq"},
            )
            response.raise_for_status()
            results = response.json()

        if not results or len(results) == 0:
            return {
                "type": "FAQ_CARD",
                "question": question,
                "answer": "I couldn't find an answer to your question. Would you like me to create a support ticket?",
                "confidence": 0.0,
            }

        return {
            "type": "FAQ_CARD",
            "question": question,
            "answer": results[0].get("answer", ""),
            "confidence": results[0].get("confidence", 0.0),
        }

    async def _handle_create_ticket_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = payload.get("customer_id")
        subject = payload.get("subject")
        description = payload.get("description")

        if not all([customer_id, subject, description]):
            raise ValueError("customer_id, subject, and description are required")

        logger.info(f"Creating support ticket for customer: {customer_id}")

        with create_span("mcp_create_ticket"):
            response = await self.http_client.post(
                f"{self.config.MCP_PRODINFO_URL}/mcp/tools/createTicket",
                json={
                    "customer_id": customer_id,
                    "subject": subject,
                    "description": description,
                },
            )
            response.raise_for_status()
            ticket = response.json()

        return {
            "type": "TICKET_CARD",
            "ticket_id": ticket.get("ticket_id"),
            "status": "CREATED",
            "subject": subject,
        }

    async def check_mcp_health(self) -> bool:
        try:
            response = await self.http_client.get(
                f"{self.config.MCP_PRODINFO_URL}/health",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return False
