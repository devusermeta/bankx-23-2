"""
Limits Service

Business logic for checking and managing transaction limits.
"""

import sys
from pathlib import Path
from typing import Optional
import logging

from models import AccountLimits, LimitsCheckResult

# Add common directory to path for StateManager
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "common"))
from state_manager import get_state_manager

logger = logging.getLogger(__name__)


class LimitsService:
    """
    Limits Service - Handles transaction limit checks and validation.

    Key responsibilities:
    1. Check if transaction is within per-transaction limit
    2. Check if transaction is within daily limit
    3. Check if account has sufficient balance
    4. Provide detailed validation results for Policy Gate (US 1.4)
    """

    def __init__(self):
        """Initialize Limits Service with StateManager."""
        self.state = get_state_manager()
        logger.info("LimitsService initialized with StateManager")


    def get_account_limits(self, account_id: str) -> AccountLimits:
        """
        Get limits for an account.

        Args:
            account_id: Account ID (e.g., "CHK-001")

        Returns:
            AccountLimits model with current limits
        """
        # Get limits from StateManager
        limits_data = self.state.get_limit_by_account(account_id)
        
        if not limits_data:
            # Return default limits if not found
            logger.warning(f"No limits found for {account_id}, using defaults")
            limits_data = {
                "account_id": account_id,
                "per_txn_limit": 50000.0,
                "daily_limit": 200000.0,
                "remaining_today": 200000.0,
                "last_reset_date": "2025-11-07"
            }

        limits = AccountLimits(**limits_data)
        limits.calculate_daily_used()

        return limits


    def check_limits(
        self,
        account_id: str,
        amount: float,
        currency: str = "THB"
    ) -> LimitsCheckResult:
        """
        Check if a transaction is within all limits (Policy Gate validation).

        This is the KEY function for US 1.4 (Transfer Approval).

        Validation checks:
        1. Sufficient balance (from BalancePersistenceService)
        2. Within per-transaction limit
        3. Within daily limit (remaining today)

        Args:
            account_id: Account ID
            amount: Transaction amount
            currency: Currency code (default: THB)

        Returns:
            LimitsCheckResult with detailed validation results
        """
        logger.info(f"Checking limits for account {account_id}, amount {amount}")

        # Get current balance from StateManager
        account_data = self.state.get_account_by_id(account_id)
        current_balance = account_data.get('ledger_balance', 0) if account_data else 0

        # Get current limits
        limits = self.get_account_limits(account_id)

        # Perform checks
        sufficient_balance = current_balance >= amount
        within_per_txn_limit = amount <= limits.per_txn_limit
        within_daily_limit = amount <= limits.remaining_today

        # Calculate remaining after transaction
        remaining_after = current_balance - amount if sufficient_balance else current_balance
        daily_limit_remaining_after = limits.remaining_today - amount if within_daily_limit else limits.remaining_today

        # Build result
        result = LimitsCheckResult(
            sufficient_balance=sufficient_balance,
            within_per_txn_limit=within_per_txn_limit,
            within_daily_limit=within_daily_limit,
            remaining_after=remaining_after,
            daily_limit_remaining_after=daily_limit_remaining_after,
            current_balance=current_balance
        )

        # Add error message if any check fails
        if not sufficient_balance:
            result.error_message = f"Insufficient balance. Available: {current_balance} {currency}, Required: {amount} {currency}"
        elif not within_per_txn_limit:
            result.error_message = f"Exceeds per-transaction limit of {limits.per_txn_limit} {currency}"
        elif not within_daily_limit:
            result.error_message = f"Exceeds daily limit. Remaining today: {limits.remaining_today} {currency}"

        logger.info(f"Limits check result: balance={sufficient_balance}, per_txn={within_per_txn_limit}, daily={within_daily_limit}")

        return result


    def get_limits_info(self, account_id: str) -> dict:
        """
        Get comprehensive limits information for an account.

        Used by Account Agent for US 1.3 (BALANCE_CARD).

        Returns:
            Dict with limits information including utilization
        """
        limits = self.get_account_limits(account_id)

        return {
            'per_transaction_limit': limits.per_txn_limit,
            'daily_limit': limits.daily_limit,
            'remaining_today': limits.remaining_today,
            'daily_used': limits.calculate_daily_used(),
            'utilization_percent': limits.calculate_utilization_percent(),
            'currency': limits.currency
        }


    def update_limits_after_transaction(self, account_id: str, amount: float):
        """
        Update daily limits after a successful transaction.

        Called by Payment Service after payment execution.

        Args:
            account_id: Account ID
            amount: Transaction amount (positive value)
        """
        logger.info(f"Updating limits after transaction: account={account_id}, amount={amount}")
        self.state.update_remaining_limit(account_id, amount)
