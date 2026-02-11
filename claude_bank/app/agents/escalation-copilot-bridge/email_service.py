"""
Email service for sending notifications via Microsoft Graph Mail API.
"""

import logging
from typing import Optional
from config import settings
from graph_client import get_graph_client
from models import TicketData, EmailContent, EmailRecipient

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service for sending emails via Microsoft Graph Mail API.
    """
    
    def __init__(self):
        self.sender_address = settings.EMAIL_SENDER_ADDRESS
        self.sender_name = settings.EMAIL_SENDER_NAME
    
    def _build_ticket_email_html(self, ticket: TicketData) -> str:
        """
        Build HTML email body for ticket creation notification.
        
        Args:
            ticket: Ticket data
            
        Returns:
            HTML string
        """
        html = f"""
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
  <h2 style="color: #0066cc;">Support Ticket Created</h2>
  
  <p>Dear <strong>{ticket.customer_name}</strong>,</p>
  
  <p>Your support ticket has been successfully created.</p>
  
  <table style="border-collapse: collapse; width: 100%; max-width: 600px; margin: 20px 0;">
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; background-color: #f5f5f5; width: 150px;"><strong>Ticket ID:</strong></td>
      <td style="padding: 10px; border: 1px solid #ddd;">{ticket.ticket_id}</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; background-color: #f5f5f5;"><strong>Description:</strong></td>
      <td style="padding: 10px; border: 1px solid #ddd;">{ticket.description}</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; background-color: #f5f5f5;"><strong>Priority:</strong></td>
      <td style="padding: 10px; border: 1px solid #ddd;">{ticket.priority}</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; background-color: #f5f5f5;"><strong>Status:</strong></td>
      <td style="padding: 10px; border: 1px solid #ddd;">{ticket.status}</td>
    </tr>
  </table>
  
  <p>Our support team will contact you at <strong>{ticket.customer_email}</strong> within 24 business hours.</p>
  
  <p style="margin-top: 30px;">
    Best regards,<br>
    <strong>{self.sender_name}</strong>
  </p>
  
  <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
  <p style="font-size: 12px; color: #999;">
    This is an automated message. Please do not reply to this email.
  </p>
</body>
</html>
        """
        return html
    
    async def send_ticket_notification(self, ticket: TicketData) -> bool:
        """
        Send ticket creation notification email.
        
        Args:
            ticket: Ticket data
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Build email content
            subject = f"Support Ticket Created - {ticket.ticket_id}"
            body_html = self._build_ticket_email_html(ticket)
            
            email_content = EmailContent(
                subject=subject,
                body_html=body_html,
                to_recipients=[
                    EmailRecipient(
                        email_address=ticket.customer_email,
                        name=ticket.customer_name
                    )
                ]
            )
            
            return await self.send_email(email_content)
        
        except Exception as e:
            logger.error(f"Failed to send ticket notification: {e}")
            return False
    
    async def send_email(self, email: EmailContent) -> bool:
        """
        Send email via Microsoft Graph Mail API.
        
        Args:
            email: Email content
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            graph_client = await get_graph_client()
            
            # Build recipient list
            to_recipients = [
                {
                    "emailAddress": {
                        "address": recipient.email_address,
                        "name": recipient.name or recipient.email_address
                    }
                }
                for recipient in email.to_recipients
            ]
            
            # Build email message
            message = {
                "message": {
                    "subject": email.subject,
                    "body": {
                        "contentType": "HTML",
                        "content": email.body_html
                    },
                    "toRecipients": to_recipients,
                    "from": {
                        "emailAddress": {
                            "address": self.sender_address,
                            "name": self.sender_name
                        }
                    }
                },
                "saveToSentItems": "true"
            }
            
            # Send email using sendMail endpoint
            endpoint = f"users/{self.sender_address}/sendMail"
            
            logger.info(f"Sending email to {[r.email_address for r in email.to_recipients]}")
            logger.debug(f"Email subject: {email.subject}")
            
            await graph_client.post(endpoint, message)
            
            logger.info(f"Successfully sent email: {email.subject}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            logger.error(f"Error details: {type(e).__name__}: {str(e)}")
            return False
    
    async def send_test_email(self, to_address: str) -> bool:
        """
        Send a test email to verify configuration.
        
        Args:
            to_address: Recipient email address
            
        Returns:
            True if sent successfully
        """
        try:
            test_email = EmailContent(
                subject="Test Email from Escalation Bridge",
                body_html="""
<html>
<body>
  <h2>Test Email</h2>
  <p>This is a test email from the Escalation Copilot Bridge.</p>
  <p>If you received this, your email configuration is working correctly!</p>
</body>
</html>
                """,
                to_recipients=[EmailRecipient(email_address=to_address)]
            )
            
            return await self.send_email(test_email)
        
        except Exception as e:
            logger.error(f"Failed to send test email: {e}")
            return False


# Global instance
_email_service: Optional[EmailService] = None


async def get_email_service() -> EmailService:
    """Get or create global email service."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
