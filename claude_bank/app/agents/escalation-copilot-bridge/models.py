"""
Data models for Escalation Copilot Bridge.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# A2A Protocol Models
class AgentIdentifier(BaseModel):
    """Agent identifier in A2A protocol."""
    agent_id: str
    agent_name: str


class A2AMetadata(BaseModel):
    """Metadata for A2A messages."""
    timeout_seconds: Optional[int] = 30
    retry_count: Optional[int] = 0
    trace_id: Optional[str] = None


class A2AMessage(BaseModel):
    """A2A message format."""
    message_id: Optional[str] = None
    correlation_id: Optional[str] = None
    protocol_version: str = "1.0"
    timestamp: Optional[str] = None
    source: Optional[AgentIdentifier] = None
    target: Optional[AgentIdentifier] = None
    intent: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    metadata: Optional[A2AMetadata] = None


class A2AResponse(BaseModel):
    """A2A response format."""
    message_id: str
    correlation_id: Optional[str] = None
    status: str  # success, error, timeout
    response: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


# Chat Request/Response Models (Compatible with current agents)
class ChatMessage(BaseModel):
    """Single chat message."""
    role: str  # user, assistant, system
    content: str


class ChatRequest(BaseModel):
    """Chat request format used by ProdInfo and other agents."""
    messages: List[ChatMessage]
    customer_id: Optional[str] = None
    thread_id: Optional[str] = None
    stream: bool = False


class ChatResponse(BaseModel):
    """Chat response format."""
    role: str = "assistant"
    content: str
    agent: str = "EscalationAgent"


# Ticket Models
class TicketData(BaseModel):
    """Parsed ticket information from A2A message."""
    ticket_id: str
    customer_id: str
    customer_email: str
    customer_name: str
    description: str
    priority: str = "normal"
    status: str = "Open"
    created_date: str


class TicketCreationResult(BaseModel):
    """Result of ticket creation."""
    success: bool
    ticket_id: Optional[str] = None
    error: Optional[str] = None
    email_sent: bool = False
    excel_updated: bool = False
    copilot_response: Optional[str] = None  # Response from Copilot Studio agent


# Agent Card Model
class AgentEndpoints(BaseModel):
    """Agent endpoints for registry."""
    http: str
    health: str
    a2a: str


class AgentCard(BaseModel):
    """Agent card for A2A discovery."""
    agent_name: str
    agent_type: str
    version: str
    description: str
    capabilities: List[str]
    endpoints: AgentEndpoints
    status: str = "active"


# Excel Models
class ExcelRow(BaseModel):
    """Excel row data for ticket storage."""
    ticket_id: str = Field(alias="Ticket ID")
    customer_id: str = Field(alias="Customer ID")
    customer_email: str = Field(alias="Customer Email")
    customer_name: str = Field(alias="Customer Name")
    description: str = Field(alias="Description")
    priority: str = Field(alias="Priority")
    status: str = Field(alias="Status")
    created_date: str = Field(alias="Created Date")
    
    class Config:
        populate_by_name = True


# Email Models
class EmailRecipient(BaseModel):
    """Email recipient."""
    email_address: str
    name: Optional[str] = None


class EmailContent(BaseModel):
    """Email content structure."""
    subject: str
    body_html: str
    to_recipients: List[EmailRecipient]
