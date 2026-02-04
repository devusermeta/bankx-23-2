"""Data models for AIMoneyCoach MCP server."""

from pydantic import BaseModel, Field
from typing import List, Optional


class MoneyCoachSearchResult(BaseModel):
    """Search result from Money Coach document."""
    chapter: int = Field(description="Chapter number (1-12)")
    chapter_title: str = Field(description="Chapter title")
    content: str = Field(description="Content chunk")
    confidence: float = Field(default=0.5, description="Search confidence score (0-1)")
    page: Optional[int] = Field(default=None, description="Page number if available")


class GroundingValidationResult(BaseModel):
    """Result of grounding validation."""
    is_grounded: bool = Field(description="Whether answer is grounded in book content")
    confidence: float = Field(description="Grounding confidence score (0-1)")
    validated_answer: Optional[str] = Field(default=None, description="Validated answer")
    chapter_references: List[str] = Field(default_factory=list, description="Chapter references")
    reason: Optional[str] = Field(default=None, description="Reason if not grounded")
    contains_non_book_content: bool = Field(default=False, description="Whether answer contains content not from book")
