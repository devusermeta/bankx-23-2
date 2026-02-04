"""Data models for EscalationComms MCP server."""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
from datetime import datetime


class EmailRecipient(BaseModel):
    """Email recipient."""
    email: EmailStr = Field(description="Email address")
    name: Optional[str] = Field(default=None, description="Recipient name")


class EmailMessage(BaseModel):
    """Email message to send."""
    to: List[EmailRecipient] = Field(description="List of recipients")
    subject: str = Field(description="Email subject")
    body: str = Field(description="Email body (HTML or plain text)")
    cc: Optional[List[EmailRecipient]] = Field(default=None, description="CC recipients")
    bcc: Optional[List[EmailRecipient]] = Field(default=None, description="BCC recipients")
    is_html: bool = Field(default=True, description="Whether body is HTML")


class EmailSendResult(BaseModel):
    """Result of email send operation."""
    success: bool = Field(description="Whether email was sent successfully")
    message_id: Optional[str] = Field(default=None, description="Message ID if successful")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    sent_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp")
