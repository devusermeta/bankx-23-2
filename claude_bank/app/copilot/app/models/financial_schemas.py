"""
Pydantic models for BankX Financial Operations structured outputs.
These schemas ensure zero-hallucination by enforcing strict output formats.

Timezone: All timestamps in Asia/Bangkok (+07:00)
Currency: Thai Baht (THB) only
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from decimal import Decimal


# ============================================================================
# USE CASE 1.1 & 1.5: TRANSACTION SCHEMAS
# ============================================================================

class TransactionRow(BaseModel):
    """Single transaction row for TXN_TABLE"""
    txn_id: str = Field(..., description="Transaction ID (e.g., T000044)")
    date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    time: str = Field(..., description="Transaction time (HH:MM:SS)")
    amount: float = Field(..., description="Transaction amount")
    direction: Literal["IN", "OUT"] = Field(..., description="Direction of money flow")
    description: str = Field(..., description="Transaction description")
    category: str = Field(..., description="Transaction category (e.g., Transfer)")
    status: str = Field(..., description="Transaction status (e.g., POSTED)")
    counterparty_name: str = Field(..., description="Other party's name")
    counterparty_account_no: str = Field(..., description="Other party's account (masked)")
    currency: str = Field(default="THB", description="Currency code")


class TransactionSummary(BaseModel):
    """Summary statistics for transaction list"""
    total_in: float = Field(..., description="Total inbound amount")
    total_out: float = Field(..., description="Total outbound amount")
    net: float = Field(..., description="Net cash flow (in - out)")


class PeriodInfo(BaseModel):
    """Time period information"""
    from_date: str = Field(..., alias="from", description="Start date (YYYY-MM-DD)")
    to_date: str = Field(..., alias="to", description="End date (YYYY-MM-DD)")
    description: Optional[str] = Field(None, description="Human-readable period description")

    class Config:
        populate_by_name = True


class TXN_TABLE(BaseModel):
    """US 1.1: Transaction history table - structured output with no conversational filler"""
    type: Literal["TXN_TABLE"] = "TXN_TABLE"
    account_id: str = Field(..., description="Account ID (e.g., CHK-001)")
    account_name: str = Field(..., description="Account display name")
    currency: str = Field(default="THB", description="Currency code")
    period: PeriodInfo = Field(..., description="Query period")
    rows: List[TransactionRow] = Field(default_factory=list, description="Transaction rows")
    total_count: int = Field(..., description="Total number of transactions")
    summary: TransactionSummary = Field(..., description="Summary statistics")


class CounterpartyInfo(BaseModel):
    """Counterparty details for transaction"""
    name: str = Field(..., description="Counterparty name")
    account_no: str = Field(..., description="Account number (masked)")
    full_account_no: Optional[str] = Field(None, description="Full account number (for authorized views)")


class TransactionMetadata(BaseModel):
    """Transaction metadata"""
    posted_date: str = Field(..., description="Date transaction was posted")
    timezone: str = Field(default="Asia/Bangkok", description="Timezone for timestamps")
    retrieval_time: Optional[str] = Field(None, description="When details were retrieved")


class TXN_DETAIL(BaseModel):
    """US 1.5: Single transaction details"""
    type: Literal["TXN_DETAIL"] = "TXN_DETAIL"

    class Transaction(BaseModel):
        txn_id: str
        account_id: str
        account_name: str
        timestamp: str = Field(..., description="ISO 8601 with +07:00")
        date: str
        time: str
        amount: float
        direction: Literal["IN", "OUT"]
        description: str
        category: str
        status: str
        currency: str = "THB"
        counterparty: CounterpartyInfo
        balance_after: float

    transaction: Transaction
    metadata: TransactionMetadata


# ============================================================================
# USE CASE 1.2: TRANSACTION AGGREGATION SCHEMAS
# ============================================================================

class AggregationDetails(BaseModel):
    """Breakdown details for aggregation"""
    total_transactions: int
    inbound_transactions: int
    outbound_transactions: int
    sum_in: Optional[float] = None
    sum_out: Optional[float] = None
    net: Optional[float] = None


class INSIGHTS_CARD(BaseModel):
    """US 1.2: Transaction aggregation insights"""
    type: Literal["INSIGHTS_CARD"] = "INSIGHTS_CARD"
    metric_type: Literal["COUNT", "SUM_IN", "SUM_OUT", "NET"] = Field(..., description="Type of aggregation")
    value: float = Field(..., description="Computed metric value")
    currency: str = Field(default="THB", description="Currency code")
    period: PeriodInfo = Field(..., description="Aggregation period")
    account_id: str
    account_name: str
    details: Optional[AggregationDetails] = Field(None, description="Detailed breakdown")


# ============================================================================
# USE CASE 1.3: BALANCE & LIMITS SCHEMAS
# ============================================================================

class BalanceInfo(BaseModel):
    """Account balance information"""
    ledger_balance: float = Field(..., description="Total balance on record")
    available_balance: float = Field(..., description="Balance available for use")
    pending_amount: float = Field(default=0.0, description="Pending/hold amount")


class LimitsInfo(BaseModel):
    """Transaction limits information"""
    per_transaction_limit: float = Field(..., description="Maximum per single transaction")
    daily_limit: float = Field(..., description="Maximum daily total")
    remaining_today: float = Field(..., description="Daily limit remaining")
    daily_used: float = Field(..., description="Daily limit already used")
    utilization_percent: float = Field(..., description="Daily limit utilization %")


class BALANCE_CARD(BaseModel):
    """US 1.3: Account balance and limits"""
    type: Literal["BALANCE_CARD"] = "BALANCE_CARD"
    account_id: str
    account_no: str = Field(..., description="Account number (partially masked)")
    account_name: str
    account_type: str = Field(..., description="Account type (e.g., CHK)")
    currency: str = "THB"
    balance: BalanceInfo
    limits: LimitsInfo
    last_updated: str = Field(..., description="ISO 8601 timestamp +07:00")
    advisory: Optional[str] = Field(None, description="Optional advisory message")


# ============================================================================
# USE CASE 1.4: TRANSFER APPROVAL & RESULT SCHEMAS
# ============================================================================

class AccountInfo(BaseModel):
    """Account information for transfers"""
    account_id: str
    account_no: str = Field(..., description="Masked account number")
    account_name: str
    available_balance: Optional[float] = None


class BeneficiaryInfo(BaseModel):
    """Beneficiary information"""
    name: str
    account_no: str = Field(..., description="Masked account number")
    full_account_no: Optional[str] = Field(None, description="Full account for execution")


class TransferItem(BaseModel):
    """Single transfer in a batch"""
    to: BeneficiaryInfo
    amount: float
    schedule: str = Field(default="NOW", description="When to execute (NOW, SCHEDULED)")


class ValidationResult(BaseModel):
    """Policy gate validation results"""
    sufficient_balance: bool
    within_per_txn_limit: bool
    within_daily_limit: bool
    remaining_after: float = Field(..., description="Balance after transfer")
    daily_limit_remaining_after: float = Field(..., description="Daily limit remaining after")


class ApprovalButton(BaseModel):
    """Button for user approval action"""
    action: Literal["APPROVE", "REJECT"]
    request_id: str = Field(..., description="Idempotent request ID")
    label: str = Field(..., description="Button label text")


class TRANSFER_APPROVAL(BaseModel):
    """US 1.4: Transfer approval card - requires explicit user confirmation"""
    type: Literal["TRANSFER_APPROVAL"] = "TRANSFER_APPROVAL"
    request_id: str = Field(..., description="Unique idempotent request ID")
    from_account: AccountInfo
    currency: str = "THB"
    transfers: List[TransferItem] = Field(..., description="List of transfers to approve")
    total_amount: float = Field(..., description="Total amount across all transfers")
    validation: ValidationResult = Field(..., description="Policy gate results")
    buttons: List[ApprovalButton] = Field(..., description="Approve/Reject actions")


class TransferResultItem(BaseModel):
    """Result for single transfer"""
    to: BeneficiaryInfo
    amount: float
    status: Literal["SUCCESS", "FAILED"]
    payment_id: Optional[str] = Field(None, description="Payment ID if successful")
    error_message: Optional[str] = Field(None, description="Error if failed")
    timestamp: str = Field(..., description="Execution timestamp +07:00")


class TRANSFER_RESULT(BaseModel):
    """US 1.4: Transfer execution result"""
    type: Literal["TRANSFER_RESULT"] = "TRANSFER_RESULT"
    request_id: str = Field(..., description="Original request ID")
    status: Literal["SUCCESS", "PARTIAL_SUCCESS", "FAILED"]
    results: List[TransferResultItem]
    new_balance: Optional[float] = Field(None, description="Updated balance after transfers")
    daily_limit_remaining: Optional[float] = Field(None, description="Remaining daily limit")
    confirmation_message: Optional[str] = Field(None, description="Human-readable confirmation")


# ============================================================================
# ERROR HANDLING SCHEMAS
# ============================================================================

class ErrorDetails(BaseModel):
    """Detailed error information"""
    requested_amount: Optional[float] = None
    available_balance: Optional[float] = None
    per_txn_limit: Optional[float] = None
    daily_limit_remaining: Optional[float] = None


class ERROR_CARD(BaseModel):
    """Structured error response with remediation"""
    type: Literal["ERROR_CARD"] = "ERROR_CARD"
    error_code: str = Field(..., description="Error code (e.g., INSUFFICIENT_BALANCE)")
    cause: str = Field(..., description="Human-readable explanation")
    remedy: str = Field(..., description="Suggested action to resolve")
    details: Optional[ErrorDetails] = Field(None, description="Additional error context")


# ============================================================================
# USE CASE 1.A: DECISION LEDGER SCHEMAS (GOVERNANCE)
# ============================================================================

class ToolCallMetadata(BaseModel):
    """Single tool call metadata"""
    tool: str = Field(..., description="Tool name (e.g., Reporting.searchTransactions)")
    latency_ms: int
    status: Literal["success", "failure"] = "success"
    error_message: Optional[str] = None


class PolicyCheck(BaseModel):
    """Single policy check result"""
    check_name: str
    required: Optional[float] = None
    available: Optional[float] = None
    passed: bool
    details: Optional[str] = None


class PolicyEvaluation(BaseModel):
    """Complete policy evaluation snapshot"""
    snapshot_time: str = Field(..., description="ISO 8601 +07:00")
    available_balance: float
    per_txn_limit: float
    daily_limit: float
    daily_remaining: float
    checks: List[PolicyCheck]
    decision: Literal["APPROVED", "REJECTED"]
    failure_reason: Optional[str] = None


class ApprovalMetadata(BaseModel):
    """User approval metadata"""
    presented_time: str
    approved_time: Optional[str] = None
    approval_latency_ms: Optional[int] = None
    approval_actor: str = Field(..., description="Customer ID who approved")
    approval_action: Literal["APPROVE", "REJECT"]
    approval_channel: str = Field(default="web_chat")


class DecisionLedgerEntry(BaseModel):
    """US 1.A1-1.A3: Complete decision ledger entry for Cosmos DB"""
    ledger_id: str = Field(..., description="Unique ledger entry ID")
    conversation_id: str
    customer_id: str = Field(..., description="Hashed customer ID")
    agent_name: str
    action: str = Field(..., description="Action performed")
    timestamp: str = Field(..., description="ISO 8601 +07:00")

    input: Dict[str, Any] = Field(..., description="Sanitized input parameters")
    output: Dict[str, Any] = Field(..., description="Output summary")

    policy_evaluation: Optional[PolicyEvaluation] = Field(None, description="Policy checks if applicable")
    approval: Optional[ApprovalMetadata] = Field(None, description="Approval metadata if applicable")

    metadata: Dict[str, Any] = Field(..., description="Latency, request_id, etc.")
    rationale: str = Field(..., description="Human-readable decision rationale")


# ============================================================================
# USE CASE 1.T: TELLER DASHBOARD SCHEMAS (AUDIT)
# ============================================================================

class CustomerProfile(BaseModel):
    """US 1.T1: Customer profile for teller view"""
    customer_id: str
    full_name: str
    email: str
    phone: str
    status: str = "ACTIVE"
    joined_date: Optional[str] = None
    last_login: Optional[str] = None


class TellerAccountInfo(BaseModel):
    """Account info for teller view"""
    account_id: str
    account_no: str
    account_name: str
    type: str
    currency: str = "THB"
    ledger_balance: float
    available_balance: float
    status: str = "ACTIVE"
    opened_date: Optional[str] = None


class RegisteredBeneficiary(BaseModel):
    """Beneficiary for teller view"""
    name: str
    account_no: str


class CUSTOMER_PROFILE_CARD(BaseModel):
    """US 1.T1: Complete customer profile"""
    type: Literal["CUSTOMER_PROFILE_CARD"] = "CUSTOMER_PROFILE_CARD"
    customer: CustomerProfile
    accounts: List[TellerAccountInfo]
    limits: LimitsInfo
    registered_beneficiaries: List[RegisteredBeneficiary]


class AgentInteraction(BaseModel):
    """US 1.T3: Single agent interaction"""
    sequence: int
    timestamp: str
    agent_name: str
    action: str
    input: Dict[str, Any]
    output: Dict[str, Any]
    latency_ms: int
    success: bool
    request_id: str
    tool_calls: Optional[List[ToolCallMetadata]] = None


class AGENT_INTERACTION_LOG(BaseModel):
    """US 1.T3: Agent interaction log"""
    type: Literal["AGENT_INTERACTION_LOG"] = "AGENT_INTERACTION_LOG"
    conversation_id: str
    customer_id: str
    customer_name: str
    period: Dict[str, str] = Field(..., description="start and end timestamps")
    interactions: List[AgentInteraction]
    summary: Dict[str, Any]


class AuditStage(BaseModel):
    """US 1.T4: Single audit trail stage"""
    stage: str = Field(..., description="Stage name (e.g., '1. Intent Classification')")
    timestamp: str
    agent: str
    decision: str
    rationale: str
    confidence: Optional[float] = None
    policy_snapshot: Optional[Dict[str, Any]] = None
    checks: Optional[Dict[str, PolicyCheck]] = None
    approval_metadata: Optional[ApprovalMetadata] = None
    tool_call: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None


class DECISION_AUDIT_TRAIL(BaseModel):
    """US 1.T4: Complete decision audit trail"""
    type: Literal["DECISION_AUDIT_TRAIL"] = "DECISION_AUDIT_TRAIL"
    payment_id: Optional[str] = None
    request_id: str
    customer_id: str
    customer_name: str
    audit_entries: List[AuditStage]
    summary: Dict[str, Any]
    compliance_flags: Dict[str, bool] = Field(..., description="Compliance check results")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_error_card(
    error_code: str,
    cause: str,
    remedy: str,
    details: Optional[Dict[str, Any]] = None
) -> ERROR_CARD:
    """Helper to create ERROR_CARD instances"""
    error_details = ErrorDetails(**details) if details else None
    return ERROR_CARD(
        error_code=error_code,
        cause=cause,
        remedy=remedy,
        details=error_details
    )


def generate_request_id() -> str:
    """Generate idempotent request ID"""
    from datetime import datetime
    import uuid
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    short_uuid = str(uuid.uuid4())[:8].upper()
    return f"REQ-{timestamp}-{short_uuid}"


def generate_ledger_id() -> str:
    """Generate Decision Ledger entry ID"""
    from datetime import datetime
    import uuid
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    short_uuid = str(uuid.uuid4())[:8].upper()
    return f"DL-{timestamp}-{short_uuid}"
