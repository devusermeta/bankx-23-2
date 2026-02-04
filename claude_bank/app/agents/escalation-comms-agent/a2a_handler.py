"""
A2A message handler for EscalationComms Agent.

This module handles A2A messages for email notifications via Azure Communication Services.
"""

import httpx
from typing import Dict, Any
from datetime import datetime

from a2a_sdk.models.message import A2AMessage
from common.observability import get_logger, create_span, add_span_attributes
from config import AgentConfig

logger = get_logger(__name__)


class EscalationCommsAgentHandler:
    """Handle A2A messages for EscalationComms Agent."""

    def __init__(self, config: AgentConfig):
        """Initialize handler with configuration."""
        self.config = config
        self.http_client = httpx.AsyncClient(timeout=30.0)

    async def handle_a2a_message(self, message: A2AMessage) -> Dict[str, Any]:
        """
        Route A2A message to appropriate handler based on intent.

        Args:
            message: A2A message from ProdInfoFAQ or AIMoneyCoach agent

        Returns:
            Response payload

        Raises:
            ValueError: If intent is not supported
        """
        intent = message.intent
        payload = message.payload

        with create_span(
            "handle_a2a_message", {"intent": intent, "agent": "escalation-comms"}
        ):
            if intent in ["escalation.send_email", "email.send", "notification.send"]:
                return await self._handle_send_email_request(payload)
            elif intent in ["escalation.send_ticket_email", "ticket.notify"]:
                return await self._handle_send_ticket_email_request(payload)
            else:
                raise ValueError(f"Unsupported intent: {intent}")

    async def _handle_send_email_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle generic email sending request.

        Args:
            payload: Contains recipient_email, subject, body, priority (optional)

        Returns:
            Email confirmation with delivery status
        """
        recipient_email = payload.get("recipient_email")
        subject = payload.get("subject")
        body = payload.get("body")
        priority = payload.get("priority", "normal")

        if not all([recipient_email, subject, body]):
            raise ValueError("recipient_email, subject, and body are required")

        logger.info(f"Sending email to: {recipient_email}")

        with create_span("mcp_send_email"):
            add_span_attributes(
                recipient=recipient_email,
                subject=subject,
                priority=priority,
                mcp_tool="sendemail"
            )

            # Call MCP EscalationComms service to send email
            response = await self.http_client.post(
                f"{self.config.MCP_ESCALATION_COMMS_URL}/mcp/tools/sendemail",
                json={
                    "recipient_email": recipient_email,
                    "subject": subject,
                    "body": body,
                    "priority": priority,
                },
            )
            response.raise_for_status()
            email_result = response.json()

        # Return confirmation
        return {
            "type": "EMAIL_CONFIRMATION",
            "email_sent": email_result.get("sent", True),
            "recipient": recipient_email,
            "subject": subject,
            "timestamp": datetime.now().isoformat(),
            "message_id": email_result.get("message_id", ""),
        }

    async def _handle_send_ticket_email_request(
        self, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle ticket notification email request.

        This sends emails to both customer and bank employees when a support ticket is created.

        Args:
            payload: Contains ticket_id, customer_email, customer_name, query, category, priority

        Returns:
            Email confirmation with delivery status for both recipients
        """
        ticket_id = payload.get("ticket_id")
        customer_email = payload.get("customer_email")
        customer_name = payload.get("customer_name", "Customer")
        customer_id = payload.get("customer_id")
        query = payload.get("query")
        category = payload.get("category", "general")
        priority = payload.get("priority", "normal")
        bank_support_email = payload.get("bank_support_email", "support@bankx.com")

        if not all([ticket_id, customer_email, query]):
            raise ValueError("ticket_id, customer_email, and query are required")

        logger.info(f"Sending ticket notification emails for ticket: {ticket_id}")

        # Build customer email
        customer_subject = f"Support Ticket Created - {ticket_id}"
        customer_body = f"""
Dear {customer_name},

Thank you for contacting BankX support. Your support ticket has been created successfully.

Ticket ID: {ticket_id}
Category: {category}
Priority: {priority}

Your Query:
{query}

Expected Response Time: 24 hours

Our support team will review your query and respond as soon as possible. You can reference the ticket ID {ticket_id} in any follow-up communications.

If you have any urgent concerns, please contact our customer service hotline.

Best regards,
BankX Support Team
"""

        # Build bank employee email
        employee_subject = f"New Support Ticket - {ticket_id} - {category.upper()}"
        employee_body = f"""
New Support Ticket Created

Ticket ID: {ticket_id}
Priority: {priority}
Category: {category}
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Customer Information:
- Customer ID: {customer_id}
- Name: {customer_name}
- Email: {customer_email}

Customer Query:
{query}

Action Required:
Please review and respond to this ticket within 24 hours. Use ticket ID {ticket_id} for tracking.

---
BankX Ticketing System
"""

        emails_sent = []

        with create_span("mcp_send_ticket_emails"):
            add_span_attributes(
                ticket_id=ticket_id,
                customer_email=customer_email,
                category=category,
                priority=priority,
                mcp_tool="sendemail"
            )

            # Send customer email
            try:
                customer_response = await self.http_client.post(
                    f"{self.config.MCP_ESCALATION_COMMS_URL}/mcp/tools/sendemail",
                    json={
                        "recipient_email": customer_email,
                        "subject": customer_subject,
                        "body": customer_body,
                        "priority": priority,
                        "ticket_id": ticket_id,
                    },
                )
                customer_response.raise_for_status()
                emails_sent.append({
                    "recipient": customer_email,
                    "type": "customer",
                    "sent": True,
                })
                logger.info(f"Customer email sent successfully to {customer_email}")
            except Exception as e:
                logger.error(f"Failed to send customer email: {e}")
                emails_sent.append({
                    "recipient": customer_email,
                    "type": "customer",
                    "sent": False,
                    "error": str(e),
                })

            # Send bank employee email
            try:
                employee_response = await self.http_client.post(
                    f"{self.config.MCP_ESCALATION_COMMS_URL}/mcp/tools/sendemail",
                    json={
                        "recipient_email": bank_support_email,
                        "subject": employee_subject,
                        "body": employee_body,
                        "priority": priority,
                        "ticket_id": ticket_id,
                    },
                )
                employee_response.raise_for_status()
                emails_sent.append({
                    "recipient": bank_support_email,
                    "type": "bank_employee",
                    "sent": True,
                })
                logger.info(f"Bank employee email sent successfully to {bank_support_email}")
            except Exception as e:
                logger.error(f"Failed to send bank employee email: {e}")
                emails_sent.append({
                    "recipient": bank_support_email,
                    "type": "bank_employee",
                    "sent": False,
                    "error": str(e),
                })

        # Return comprehensive confirmation
        return {
            "type": "TICKET_EMAIL_CONFIRMATION",
            "ticket_id": ticket_id,
            "emails_sent": emails_sent,
            "recipients": [customer_email, bank_support_email],
            "timestamp": datetime.now().isoformat(),
            "all_sent": all(email.get("sent", False) for email in emails_sent),
        }

    async def check_mcp_health(self) -> bool:
        """Check if MCP EscalationComms service is healthy."""
        try:
            response = await self.http_client.get(
                f"{self.config.MCP_ESCALATION_COMMS_URL}/health",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"MCP health check failed: {e}")
            return False

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
