"""
Unified Payment MCP Server - Data Models

Pydantic models for the simplified payment/transfer system.
All models used by the unified MCP tools.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================================
# Account Models
# ============================================================================

class Account(BaseModel):
    """Account information model"""
    account_id: str
    customer_id: str
    account_no: str
    cust_name: str
    bankx_email: Optional[str] = None
    acc_type: str
    currency: str
    ledger_balance: float
    available_balance: float


class PaymentMethod(BaseModel):
    """Payment method details"""
    id: str
    type: str
    name: str
    available_balance: float


class AccountDetails(BaseModel):
    """Detailed account information with payment methods"""
    id: str
    accountHolderFullName: str
    accountNumber: str
    currency: str
    balance: float
    activationDate: str
    status: str = "ACTIVE"
    paymentMethods: List[PaymentMethod] = []


# ============================================================================
# Beneficiary/Contact Models
# ============================================================================

class Beneficiary(BaseModel):
    """Registered beneficiary/contact"""
    name: str
    account_number: str
    alias: Optional[str] = None
    added_date: Optional[str] = None


# ============================================================================
# Limits Models
# ============================================================================

class LimitsCheckResult(BaseModel):
    """Result of checking if a transaction is within limits"""
    sufficient_balance: bool
    within_per_txn_limit: bool
    within_daily_limit: bool
    remaining_after: float
    daily_limit_remaining_after: float
    current_balance: Optional[float] = None
    error_message: Optional[str] = None


class AccountLimits(BaseModel):
    """Account transaction limits"""
    account_id: str
    per_txn_limit: float
    daily_limit: float
    remaining_today: float
    currency: str = "THB"


# ============================================================================
# Transfer Models
# ============================================================================

class TransferValidationResult(BaseModel):
    """Result of transfer validation (before execution)"""
    valid: bool
    sender_account_id: str
    sender_name: str
    sender_balance: float
    recipient_account_id: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_account_no: Optional[str] = None
    amount: float
    currency: str
    checks: LimitsCheckResult
    error_message: Optional[str] = None


class TransferExecutionResult(BaseModel):
    """Result of transfer execution"""
    success: bool
    transaction_id: Optional[str] = None
    sender_new_balance: float
    recipient_new_balance: Optional[float] = None
    daily_limit_remaining: float
    error_message: Optional[str] = None


class TransactionRecord(BaseModel):
    """Transaction record for JSON storage"""
    txn_id: str
    account_id: str
    timestamp: str
    amount: float
    type: str  # "income" or "outcome"
    description: str
    category: str = "Transfer"
    status: str = "POSTED"
    counterparty_name: str
    counterparty_account_no: str
    currency: str = "THB"
