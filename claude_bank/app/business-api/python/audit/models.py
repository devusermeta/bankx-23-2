"""
Audit Service Models

Defines data models for audit logging and decision ledger.
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime


class PolicyEvaluation(BaseModel):
    """Policy evaluation result for governance"""
    policy_name: str
    passed: bool
    reason: Optional[str] = None


class ApprovalMetadata(BaseModel):
    """Approval metadata for transactions"""
    request_id: str
    approval_actor: str = Field(..., description="Customer ID who approved")
    approval_action: Literal["APPROVE", "REJECT"]
    approval_channel: str = Field(default="web_chat")
    approval_timestamp: str


class DecisionLedgerEntry(BaseModel):
    """
    Complete decision ledger entry for governance logging.

    Captures every agent action, decision, and rationale for compliance and audit.
    Implements US 1.A1-1.A3.
    """
    ledger_id: str = Field(..., description="Unique ledger entry ID")
    conversation_id: str
    customer_id: str = Field(..., description="Customer ID (hashed in production)")
    agent_name: str = Field(..., description="Agent that performed action")
    action: str = Field(..., description="Action performed (e.g., VIEW_TRANSACTIONS, TRANSFER)")
    timestamp: str = Field(..., description="ISO 8601 +07:00")

    input: Dict[str, Any] = Field(..., description="Sanitized input parameters")
    output: Dict[str, Any] = Field(..., description="Output summary")

    policy_evaluation: Optional[PolicyEvaluation] = Field(None, description="Policy checks if applicable")
    approval: Optional[ApprovalMetadata] = Field(None, description="Approval metadata if applicable")

    metadata: Dict[str, Any] = Field(default_factory=dict, description="Latency, request_id, etc.")
    rationale: str = Field(..., description="Human-readable decision rationale")


class AgentInteractionLog(BaseModel):
    """
    Agent interaction log for teller dashboard.

    Simplified view of agent-customer interactions for US 1.T3.
    """
    interaction_id: str
    conversation_id: str
    customer_id: str
    agent_name: str
    action: str
    timestamp: str
    input_summary: str
    output_summary: str
    success: bool
    error_message: Optional[str] = None


class DecisionAuditTrail(BaseModel):
    """
    Decision audit trail for teller dashboard.

    Governance view of decisions with policy evaluations for US 1.T4.
    """
    ledger_id: str
    conversation_id: str
    customer_id: str
    agent_name: str
    action: str
    timestamp: str
    policy_evaluations: List[PolicyEvaluation]
    approval_status: Optional[str] = None
    rationale: str


class AuditSearchResult(BaseModel):
    """
    Search results for audit queries.

    Used by teller dashboard for US 1.T5.
    """
    total_count: int
    results: List[DecisionLedgerEntry]
    page: int = 1
    page_size: int = 50
