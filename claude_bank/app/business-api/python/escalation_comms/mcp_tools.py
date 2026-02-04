"""MCP tools for EscalationComms agent."""

import logging
from typing import Dict, Any, Optional, List

from fastmcp import FastMCP
from models import EmailMessage, EmailRecipient
from services import AzureCommunicationEmailService
from ticket_service import TicketService

logger = logging.getLogger(__name__)


def register_tools(mcp: FastMCP, email_service: AzureCommunicationEmailService, ticket_service: TicketService):
    """Register all MCP tools for EscalationComms agent."""

    @mcp.tool()
    async def send_email(
        to_emails: str,
        subject: str,
        body: str,
        to_names: Optional[str] = None,
        cc_emails: Optional[str] = None,
        is_html: bool = True
    ) -> Dict[str, Any]:
        """
        Send email via Azure Communication Services.

        Args:
            to_emails: Comma-separated list of recipient email addresses
            subject: Email subject
            body: Email body (HTML or plain text)
            to_names: Optional comma-separated list of recipient names (must match to_emails order)
            cc_emails: Optional comma-separated list of CC email addresses
            is_html: Whether body is HTML (default: True)

        Returns:
            Email send result with success status and message ID
        """
        logger.info(f"[MCP Tool] send_email: subject='{subject}', to={to_emails}")

        try:
            # Parse recipients
            to_email_list = [email.strip() for email in to_emails.split(",")]
            to_name_list = []
            if to_names:
                to_name_list = [name.strip() for name in to_names.split(",")]

            # Build recipient list
            recipients = []
            for idx, email in enumerate(to_email_list):
                name = to_name_list[idx] if idx < len(to_name_list) else None
                recipients.append(EmailRecipient(email=email, name=name))

            # Parse CC if provided
            cc_recipients = None
            if cc_emails:
                cc_email_list = [email.strip() for email in cc_emails.split(",")]
                cc_recipients = [EmailRecipient(email=email) for email in cc_email_list]

            # Create email message
            email_message = EmailMessage(
                to=recipients,
                subject=subject,
                body=body,
                cc=cc_recipients,
                is_html=is_html
            )

            # Send email
            result = await email_service.send_email(email_message)

            return {
                "success": result.success,
                "message_id": result.message_id,
                "error": result.error,
                "sent_at": result.sent_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Error in send_email: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def send_ticket_notification(
        ticket_id: str,
        customer_email: str,
        customer_name: str,
        query: str,
        category: str = "general"
    ) -> Dict[str, Any]:
        """
        Send support ticket notification email to customer.

        This is a convenience tool for sending formatted ticket notifications.

        Args:
            ticket_id: Ticket ID (e.g., TKT-2025-001234)
            customer_email: Customer email address
            customer_name: Customer name
            query: Original customer query
            category: Ticket category (default: "general")

        Returns:
            Email send result
        """
        logger.info(f"[MCP Tool] send_ticket_notification: ticket={ticket_id}, customer={customer_email}")

        try:
            result = await email_service.send_ticket_notification(
                ticket_id=ticket_id,
                customer_email=customer_email,
                customer_name=customer_name,
                query=query,
                category=category
            )

            return {
                "success": result.success,
                "message_id": result.message_id,
                "error": result.error,
                "sent_at": result.sent_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Error in send_ticket_notification: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def get_tickets(
        customer_id: str,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get support tickets for a customer.

        Args:
            customer_id: Customer ID
            status: Optional status filter (open, in_progress, resolved, closed)

        Returns:
            List of tickets with basic information
        """
        logger.info(f"[MCP Tool] get_tickets: customer_id='{customer_id}', status='{status}'")

        try:
            tickets = ticket_service.get_tickets(customer_id=customer_id, status=status)
            
            tickets_list = [{
                "ticket_id": t.ticket_id,
                "description": t.description,
                "status": t.status,
                "priority": t.priority,
                "category": t.category,
                "created_at": t.created_at,
                "updated_at": t.updated_at
            } for t in tickets]

            return {
                "success": True,
                "count": len(tickets_list),
                "tickets": tickets_list
            }

        except Exception as e:
            logger.error(f"Error in get_tickets: {e}")
            return {
                "success": False,
                "error": str(e),
                "tickets": []
            }

    @mcp.tool()
    async def create_ticket(
        customer_id: str,
        description: str,
        priority: str = "normal",
        category: str = "general",
        customer_email: Optional[str] = None,
        customer_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new support ticket for a customer.

        Args:
            customer_id: Customer ID
            description: Issue description
            priority: Priority level (low, normal, high, urgent) - default: normal
            category: Ticket category - default: general
            customer_email: Customer email (for confirmation notification)
            customer_name: Customer name (for personalized confirmation)

        Returns:
            Created ticket details
        """
        logger.info(f"[MCP Tool] create_ticket: customer_id='{customer_id}', priority='{priority}'")

        try:
            # Create ticket
            ticket = ticket_service.create_ticket(
                customer_id=customer_id,
                description=description,
                priority=priority,
                category=category
            )

            # Send confirmation email if customer_email provided
            if customer_email and email_service:
                try:
                    await email_service.send_ticket_notification(
                        ticket_id=ticket.ticket_id,
                        customer_email=customer_email,
                        customer_name=customer_name or "Customer",
                        query=description,
                        category=category
                    )
                    logger.info(f"Sent ticket creation notification to {customer_email}")
                except Exception as email_error:
                    logger.warning(f"Failed to send ticket notification email: {email_error}")

            return {
                "success": True,
                "ticket": {
                    "ticket_id": ticket.ticket_id,
                    "customer_id": ticket.customer_id,
                    "description": ticket.description,
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "category": ticket.category,
                    "created_at": ticket.created_at
                }
            }

        except Exception as e:
            logger.error(f"Error in create_ticket: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def get_ticket_details(ticket_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific ticket including history.

        Args:
            ticket_id: Ticket ID (e.g., TKT-2026-000001)

        Returns:
            Detailed ticket information including update history
        """
        logger.info(f"[MCP Tool] get_ticket_details: ticket_id='{ticket_id}'")

        try:
            ticket = ticket_service.get_ticket_details(ticket_id)
            
            if not ticket:
                return {
                    "success": False,
                    "error": f"Ticket {ticket_id} not found"
                }

            return {
                "success": True,
                "ticket": {
                    "ticket_id": ticket.ticket_id,
                    "customer_id": ticket.customer_id,
                    "description": ticket.description,
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "category": ticket.category,
                    "created_at": ticket.created_at,
                    "updated_at": ticket.updated_at,
                    "updates": ticket.updates,
                    "assigned_to": ticket.assigned_to
                }
            }

        except Exception as e:
            logger.error(f"Error in get_ticket_details: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def update_ticket(
        ticket_id: str,
        status: Optional[str] = None,
        notes: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing support ticket.

        Args:
            ticket_id: Ticket ID
            status: New status (open, in_progress, resolved, closed)
            notes: Notes to add to the ticket
            priority: New priority (low, normal, high, urgent)

        Returns:
            Updated ticket information
        """
        logger.info(f"[MCP Tool] update_ticket: ticket_id='{ticket_id}', status='{status}'")

        try:
            ticket = ticket_service.update_ticket(
                ticket_id=ticket_id,
                status=status,
                notes=notes,
                priority=priority
            )

            return {
                "success": True,
                "ticket": {
                    "ticket_id": ticket.ticket_id,
                    "status": ticket.status,
                    "priority": ticket.priority,
                    "updated_at": ticket.updated_at
                }
            }

        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error in update_ticket: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def close_ticket(ticket_id: str) -> Dict[str, Any]:
        """
        Close a support ticket.

        Args:
            ticket_id: Ticket ID

        Returns:
            Closed ticket information
        """
        logger.info(f"[MCP Tool] close_ticket: ticket_id='{ticket_id}'")

        try:
            ticket = ticket_service.close_ticket(ticket_id)

            return {
                "success": True,
                "ticket": {
                    "ticket_id": ticket.ticket_id,
                    "status": ticket.status,
                    "closed_at": ticket.updated_at
                }
            }

        except ValueError as e:
            return {
                "success": False,
                "error": str(e)
            }
        except Exception as e:
            logger.error(f"Error in close_ticket: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    logger.info("Registered 7 MCP tools for EscalationComms agent (2 email + 5 ticket management)")
