"""Data models for ProdInfoFAQ MCP server."""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime, timezone


class SearchResult(BaseModel):
    """Search result from Azure AI Search."""
    document_id: str = Field(default="unknown", description="Document identifier")
    content: str = Field(default="", description="Document content chunk")
    title: str = Field(default="", description="Document title")
    section: Optional[str] = Field(default=None, description="Document section")
    confidence: float = Field(default=0.0, description="Search confidence score (0-1)")
    source: str = Field(default="unknown", description="Source document name")
    url: Optional[str] = Field(default=None, description="Source URL if available")


class GroundingValidationResult(BaseModel):
    """Result of grounding validation using Content Understanding."""
    is_grounded: bool = Field(description="Whether the answer is grounded in source documents")
    confidence: float = Field(description="Grounding confidence score (0-1)")
    validated_answer: Optional[str] = Field(default=None, description="Validated and synthesized answer")
    citations: List[str] = Field(default_factory=list, description="Source citations")
    reason: Optional[str] = Field(default=None, description="Reason if not grounded")


class SupportTicket(BaseModel):
    """Support ticket for escalation."""
    ticket_id: str = Field(description="Unique ticket ID (TKT-YYYY-NNNNNN)")
    customer_id: str = Field(description="Customer identifier")
    query: str = Field(description="Original customer question")
    category: str = Field(description="Ticket category")
    priority: Literal["normal", "high", "urgent"] = Field(default="normal")
    status: Literal["created", "pending", "resolved"] = Field(default="created")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Optional[dict] = Field(default_factory=dict)


class CachedQuery(BaseModel):
    """Cached query result."""
    query_hash: str = Field(description="Hash of the query")
    query: str = Field(description="Original query")
    answer: str = Field(description="Cached answer")
    sources: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    hit_count: int = Field(default=1, description="Number of times this was retrieved")
