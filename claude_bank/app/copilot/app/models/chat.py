from pydantic import BaseModel
from typing import List, Optional, Any, Literal
from enum import Enum

class ConfirmationType(str, Enum):
    """Types of confirmations that can be pending"""
    PAYMENT = "payment"
    TICKET_CREATION = "ticket_creation"
    EMAIL_SEND = "email_send"
    BENEFICIARY_ADD = "beneficiary_add"

class PendingConfirmation(BaseModel):
    """Represents a pending user confirmation"""
    type: ConfirmationType
    details: dict  # Stores context like amount, recipient, ticket subject, etc.
    message_id: Optional[str] = None  # ID of message that requested confirmation

class ChatMessage(BaseModel):
    role: str
    content: str
    attachments: Optional[List[Any]] = None
    pending_confirmation: Optional[PendingConfirmation] = None  # Tracks if this message requires confirmation

class ChatAppRequest(BaseModel):
    stream: Optional[bool] = False
    messages: List[ChatMessage]
    attachements: Optional[List[str]] = None
    threadId: Optional[str] = None

class ChatResponseMessage(BaseModel):
    content: str
    role: str
    attachments: List[Any] = []

class ChatContext(BaseModel):
    thoughts: str = ""
    data_points: List[Any] = []
    pending_confirmation: Optional[PendingConfirmation] = None  # Track if agent is waiting for confirmation
    requires_ui_confirmation: bool = False  # Signal to frontend to show confirmation buttons

class ChatDelta(BaseModel):
    content: str
    role: str
    attachments: List[Any] = []

class ChatChoice(BaseModel):
    index: int
    message: ChatResponseMessage
    context: ChatContext
    delta: ChatDelta

class ChatResponse(BaseModel):
    choices: List[ChatChoice]
    threadId: str
