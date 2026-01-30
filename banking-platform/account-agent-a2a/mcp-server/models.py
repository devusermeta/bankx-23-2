"""
Data models for Account MCP Server
"""

from typing import List, Optional
from pydantic import BaseModel


class PaymentMethodSummary(BaseModel):
    """Payment method summary in account details"""
    id: str
    type: str
    activationDate: Optional[str] = None
    expirationDate: Optional[str] = None


class PaymentMethod(BaseModel):
    """Full payment method details with balance"""
    id: str
    type: str
    activationDate: Optional[str] = None
    expirationDate: Optional[str] = None
    availableBalance: Optional[str] = None
    cardNumber: Optional[str] = None


class Account(BaseModel):
    """Account details with balance and payment methods"""
    id: str
    userName: str
    accountHolderFullName: str
    currency: str
    activationDate: Optional[str] = None
    balance: Optional[str] = None
    paymentMethods: Optional[List[PaymentMethodSummary]] = None


class AccountLimits(BaseModel):
    """Account transaction limits"""
    account_id: str
    per_txn_limit: float
    daily_limit: float
    remaining_today: float
    currency: str = "THB"
    daily_used: Optional[float] = None

    def calculate_daily_used(self) -> float:
        """Calculate how much of the daily limit has been used"""
        self.daily_used = self.daily_limit - self.remaining_today
        return self.daily_used

    def calculate_utilization_percent(self) -> float:
        """Calculate daily limit utilization percentage"""
        if self.daily_limit == 0:
            return 0.0
        return (self.calculate_daily_used() / self.daily_limit) * 100


class LimitsCheckResult(BaseModel):
    """Result of checking if a transaction is within limits"""
    sufficient_balance: bool
    within_per_txn_limit: bool
    within_daily_limit: bool
    remaining_after: float
    daily_limit_remaining_after: float
    current_balance: Optional[float] = None
    error_message: Optional[str] = None
