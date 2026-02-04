"""A2A message models."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class AgentIdentifier(BaseModel):
    """Agent identifier in A2A messages."""
    agent_id: str = Field(..., description="Unique agent ID")
    agent_name: str = Field(..., description="Human-readable agent name")


class A2AMetadata(BaseModel):
    """Metadata for A2A messages."""
    timeout_seconds: int = Field(default=30, description="Request timeout")
    retry_count: int = Field(default=0, description="Number of retries attempted")
    trace_id: Optional[str] = Field(None, description="Distributed trace ID")
    span_id: Optional[str] = Field(None, description="Trace span ID")
    priority: str = Field(default="normal", description="Message priority: low, normal, high")
    additional_context: Dict[str, Any] = Field(default_factory=dict, description="Additional context data")


class A2AMessage(BaseModel):
    """Agent-to-agent message."""
    message_id: str = Field(default_factory=lambda: f"msg-{uuid4().hex}", description="Unique message ID")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for request-response tracking")
    protocol_version: str = Field(default="1.0", description="A2A protocol version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    source: AgentIdentifier = Field(..., description="Source agent")
    target: AgentIdentifier = Field(..., description="Target agent")
    intent: str = Field(..., description="Intent/capability being invoked")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Message payload")
    metadata: A2AMetadata = Field(default_factory=A2AMetadata, description="Message metadata")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "source": {"agent_id": "supervisor-001", "agent_name": "SupervisorAgent"},
                "target": {"agent_id": "account-001", "agent_name": "AccountAgent"},
                "intent": "account.get_balance",
                "payload": {
                    "customer_id": "CUST-001",
                    "account_id": "CHK-001"
                },
                "metadata": {
                    "timeout_seconds": 30,
                    "trace_id": "trace-abc123"
                }
            }
        }


class A2AResponse(BaseModel):
    """Response from agent-to-agent call."""
    message_id: str = Field(default_factory=lambda: f"msg-{uuid4().hex}", description="Response message ID")
    correlation_id: str = Field(..., description="Original request correlation ID")
    protocol_version: str = Field(default="1.0", description="A2A protocol version")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    source: AgentIdentifier = Field(..., description="Responding agent")
    target: AgentIdentifier = Field(..., description="Original requesting agent")
    status: str = Field(..., description="Response status: success, error, timeout")
    response: Dict[str, Any] = Field(default_factory=dict, description="Response data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details if status is error")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Response metadata")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "correlation_id": "req-uuid-67890",
                "source": {"agent_id": "account-001", "agent_name": "AccountAgent"},
                "target": {"agent_id": "supervisor-001", "agent_name": "SupervisorAgent"},
                "status": "success",
                "response": {
                    "type": "BALANCE_CARD",
                    "account_id": "CHK-001",
                    "balance": 99650.00
                },
                "metadata": {
                    "processing_time_ms": 245
                }
            }
        }


class A2AError(BaseModel):
    """Error information in A2A responses."""
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    retry_after_seconds: Optional[int] = Field(None, description="Suggested retry delay")
