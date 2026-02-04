"""
Limits Service Models

Defines data models for account transaction limits.
"""

from pydantic import BaseModel
from typing import Optional


class AccountLimits(BaseModel):
    """
    Account transaction limits model.

    Attributes:
        account_id: Account identifier (e.g., "CHK-001")
        per_txn_limit: Maximum amount per single transaction
        daily_limit: Maximum total amount per day
        remaining_today: Remaining daily limit available
        currency: Currency code (e.g., "THB")
        daily_used: Amount already used today (calculated field)
    """
    account_id: str
    per_txn_limit: float
    daily_limit: float
    remaining_today: float
    currency: str = "THB"
    daily_used: Optional[float] = None

    def calculate_daily_used(self):
        """Calculate how much of the daily limit has been used."""
        self.daily_used = self.daily_limit - self.remaining_today
        return self.daily_used

    def calculate_utilization_percent(self) -> float:
        """Calculate daily limit utilization percentage."""
        if self.daily_limit == 0:
            return 0.0
        return (self.calculate_daily_used() / self.daily_limit) * 100


class LimitsCheckResult(BaseModel):
    """
    Result of checking if a transaction is within limits.

    Used by Payment Agent to validate transfers before approval.
    """
    sufficient_balance: bool
    within_per_txn_limit: bool
    within_daily_limit: bool
    remaining_after: float
    daily_limit_remaining_after: float
    current_balance: Optional[float] = None
    error_message: Optional[str] = None
