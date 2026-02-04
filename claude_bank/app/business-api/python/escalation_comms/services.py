"""Business logic for EscalationComms MCP server."""

import os
import logging
from typing import List, Optional
from datetime import datetime, timezone
from azure.communication.email import EmailClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import HttpResponseError

from models import EmailMessage, EmailRecipient, EmailSendResult

logger = logging.getLogger(__name__)


class AzureCommunicationEmailService:
    """Service for Azure Communication Services email operations."""

    def __init__(self, endpoint: str, from_email: str):
        """
        Initialize Azure Communication Services Email client.

        Args:
            endpoint: Azure Communication Services endpoint
            from_email: From email address (must be verified domain)
        """
        self.endpoint = endpoint
        self.from_email = from_email
        
        # Get test email for dev mode (all emails will be CC'd to this address)
        self.test_email_recipient = os.getenv("TEST_EMAIL_RECIPIENT")
        self.profile = os.getenv("PROFILE", "prod")

        # Use managed identity for authentication
        credential = DefaultAzureCredential()
        self.client = EmailClient(endpoint, credential)

        logger.info(f"Initialized Azure Communication Services Email client")
        logger.info(f"From email: {from_email}")
        if self.test_email_recipient:
            logger.info(f"All ticket emails will be CC'd to {self.test_email_recipient}")

    async def send_email(self, email: EmailMessage) -> EmailSendResult:
        """
        Send email using Azure Communication Services.

        Args:
            email: Email message to send

        Returns:
            Result of email send operation
        """
        try:
            logger.info(f"Sending email to {len(email.to)} recipient(s): {email.subject}")

            # Build recipients
            to_recipients = [
                {"address": recipient.email, "displayName": recipient.name or recipient.email}
                for recipient in email.to
            ]

            cc_recipients = None
            if email.cc:
                cc_recipients = [
                    {"address": recipient.email, "displayName": recipient.name or recipient.email}
                    for recipient in email.cc
                ]

            bcc_recipients = None
            if email.bcc:
                bcc_recipients = [
                    {"address": recipient.email, "displayName": recipient.name or recipient.email}
                    for recipient in email.bcc
                ]

            # Build message
            message = {
                "senderAddress": self.from_email,
                "recipients": {
                    "to": to_recipients
                },
                "content": {
                    "subject": email.subject,
                }
            }

            # Add body (HTML or plain text)
            if email.is_html:
                message["content"]["html"] = email.body
            else:
                message["content"]["plainText"] = email.body

            # Add CC/BCC if provided
            if cc_recipients:
                message["recipients"]["cc"] = cc_recipients
            if bcc_recipients:
                message["recipients"]["bcc"] = bcc_recipients

            # Send email
            poller = self.client.begin_send(message)
            result = poller.result()

            # Extract message ID from result (can be dict or object)
            message_id = result.get("messageId") if isinstance(result, dict) else result.message_id
            
            logger.info(f"Email sent successfully: {message_id}")

            return EmailSendResult(
                success=True,
                message_id=message_id,
                sent_at=datetime.now(timezone.utc)
            )

        except HttpResponseError as e:
            logger.error(f"HTTP error sending email: {e}")
            return EmailSendResult(
                success=False,
                error=f"HTTP error: {e.message}"
            )

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return EmailSendResult(
                success=False,
                error=str(e)
            )

    async def send_ticket_notification(
        self,
        ticket_id: str,
        customer_email: str,
        customer_name: str,
        query: str,
        category: str
    ) -> EmailSendResult:
        """
        Send support ticket notification email.

        Args:
            ticket_id: Ticket ID
            customer_email: Customer email address
            customer_name: Customer name
            query: Original query
            category: Ticket category

        Returns:
            Result of email send operation
        """
        subject = f"Support Ticket Created: {ticket_id}"

        # Build HTML email body
        body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #0078d4; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f9f9f9; padding: 20px; margin-top: 20px; }}
                .ticket-info {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #0078d4; }}
                .footer {{ text-align: center; color: #666; margin-top: 20px; font-size: 0.9em; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>BankX Support Ticket</h1>
                </div>
                <div class="content">
                    <p>Dear {customer_name},</p>
                    <p>Thank you for contacting BankX support. We have created a support ticket for your inquiry.</p>

                    <div class="ticket-info">
                        <h3>Ticket Details</h3>
                        <p><strong>Ticket ID:</strong> {ticket_id}</p>
                        <p><strong>Category:</strong> {category}</p>
                        <p><strong>Your Question:</strong></p>
                        <p style="background-color: #f0f0f0; padding: 10px; border-radius: 4px;">{query}</p>
                    </div>

                    <p>Our specialist team will review your query and respond within 24 hours.</p>
                    <p>You will receive an email notification when we have an update.</p>

                    <p>Best regards,<br>BankX Support Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message. Please do not reply to this email.</p>
                    <p>&copy; 2025 BankX. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """

        # Create email message
        # Always CC the test email recipient to receive all ticket notifications
        cc_list = None
        if self.test_email_recipient:
            cc_list = [EmailRecipient(email=self.test_email_recipient, name="Support Admin")]
            logger.info(f"Adding CC to {self.test_email_recipient}")
        
        email = EmailMessage(
            to=[EmailRecipient(email=customer_email, name=customer_name)],
            subject=subject,
            body=body,
            cc=cc_list,
            is_html=True
        )

        return await self.send_email(email)
