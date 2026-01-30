"""
Services for Account MCP Server

Provides business logic for account and limits operations.
Ported from Classic Claude with simplified structure.
"""

import logging
from typing import List, Optional
from models import Account, PaymentMethod, PaymentMethodSummary, AccountLimits, LimitsCheckResult
from data_loader_service import DataLoaderService

logger = logging.getLogger(__name__)


class AccountService:
    """
    Account Service - Handles account operations.
    
    Provides:
    - Get account details with balance
    - Get payment method details
    - Get accounts by user email
    """
    
    def __init__(self, data_loader: DataLoaderService):
        self.data_loader = data_loader
        logger.info("AccountService initialized")
    
    
    def get_accounts_by_user_name(self, user_name: str) -> List[dict]:
        """
        Get all accounts for a user by their email (userName).
        
        Args:
            user_name: User's email address
        
        Returns:
            List of account dicts with basic info
        """
        logger.info(f"Getting accounts for user: {user_name}")
        
        accounts = self.data_loader.get_accounts_by_email(user_name)
        
        if not accounts:
            logger.warning(f"No accounts found for user: {user_name}")
            return []
        
        # Return simplified account list
        result = []
        for account in accounts:
            result.append({
                "account_id": account["account_id"],
                "account_no": account["account_no"],
                "account_type": account["acc_type"],
                "currency": account["currency"],
                "balance": account["ledger_balance"]
            })
        
        logger.info(f"Found {len(result)} accounts for {user_name}")
        return result
    
    
    def get_account_details(self, account_id: str) -> Optional[Account]:
        """
        Get detailed account information including balance and payment methods.
        
        Args:
            account_id: Account ID (e.g., "CHK-001")
        
        Returns:
            Account model with full details
        """
        logger.info(f"Getting account details for: {account_id}")
        
        if not account_id:
            raise ValueError("AccountId is empty or null")
        
        # Get account from data loader
        account_data = self.data_loader.get_account_by_id(account_id)
        if not account_data:
            logger.warning(f"Account not found: {account_id}")
            return None
        
        # Get customer details
        customer = self.data_loader.get_customer_by_id(account_data["customer_id"])
        if not customer:
            logger.warning(f"Customer not found for account: {account_id}")
            return None
        
        # Build Account model
        return Account(
            id=account_data["account_id"],
            userName=customer["email"],
            accountHolderFullName=customer["full_name"],
            currency=account_data["currency"],
            activationDate="2025-09-01",
            balance=str(account_data["ledger_balance"]),
            paymentMethods=[
                PaymentMethodSummary(
                    id=f"PM-{account_data['account_id']}",
                    type="BankTransfer",
                    activationDate="2025-09-01",
                    expirationDate="9999-12-31"
                )
            ]
        )
    
    
    def get_payment_method_details(self, payment_method_id: str) -> Optional[PaymentMethod]:
        """
        Get payment method details with available balance.
        
        Args:
            payment_method_id: Payment method ID (format: "PM-CHK-001")
        
        Returns:
            PaymentMethod model with balance
        """
        logger.info(f"Getting payment method details for: {payment_method_id}")
        
        if not payment_method_id:
            raise ValueError("PaymentMethodId is empty or null")
        
        # Extract account_id from payment method ID
        if payment_method_id.startswith("PM-"):
            account_id = payment_method_id[3:]  # Remove "PM-" prefix
            account_data = self.data_loader.get_account_by_id(account_id)
            
            if account_data:
                return PaymentMethod(
                    id=payment_method_id,
                    type="BankTransfer",
                    activationDate="2025-09-01",
                    expirationDate="9999-12-31",
                    availableBalance=str(account_data["available_balance"]),
                    cardNumber=None
                )
        
        logger.warning(f"Payment method not found: {payment_method_id}")
        return None


class LimitsService:
    """
    Limits Service - Handles transaction limit checks and validation.
    
    Provides:
    - Check if transaction is within limits
    - Get account limits info
    - Update limits after transaction
    """
    
    def __init__(self, data_loader: DataLoaderService):
        self.data_loader = data_loader
        logger.info("LimitsService initialized")
    
    
    def get_account_limits(self, account_id: str) -> AccountLimits:
        """
        Get limits for an account.
        
        Args:
            account_id: Account ID (e.g., "CHK-001")
        
        Returns:
            AccountLimits model
        """
        limits_data = self.data_loader.get_limit_by_account(account_id)
        
        if not limits_data:
            logger.warning(f"No limits found for {account_id}, using defaults")
            limits_data = {
                "account_id": account_id,
                "per_txn_limit": 50000.0,
                "daily_limit": 200000.0,
                "remaining_today": 200000.0,
                "currency": "THB"
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
        Check if a transaction is within all limits.
        
        Validates:
        1. Sufficient balance
        2. Within per-transaction limit
        3. Within daily limit
        
        Args:
            account_id: Account ID
            amount: Transaction amount
            currency: Currency code
        
        Returns:
            LimitsCheckResult with validation details
        """
        logger.info(f"Checking limits for account {account_id}, amount {amount}")
        
        # Get current balance
        account_data = self.data_loader.get_account_by_id(account_id)
        current_balance = account_data.get("ledger_balance", 0) if account_data else 0
        
        # Get limits
        limits = self.get_account_limits(account_id)
        
        # Perform checks
        sufficient_balance = current_balance >= amount
        within_per_txn_limit = amount <= limits.per_txn_limit
        within_daily_limit = amount <= limits.remaining_today
        
        # Calculate remaining after
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
        
        Args:
            account_id: Account ID
        
        Returns:
            Dict with limits info and utilization
        """
        limits = self.get_account_limits(account_id)
        
        return {
            "per_transaction_limit": limits.per_txn_limit,
            "daily_limit": limits.daily_limit,
            "remaining_today": limits.remaining_today,
            "daily_used": limits.calculate_daily_used(),
            "utilization_percent": limits.calculate_utilization_percent(),
            "currency": limits.currency
        }
    
    
    def update_limits_after_transaction(self, account_id: str, amount: float) -> dict:
        """
        Update daily limits after a successful transaction.
        
        Args:
            account_id: Account ID
            amount: Transaction amount
        
        Returns:
            Status message
        """
        logger.info(f"Updating limits after transaction: account={account_id}, amount={amount}")
        self.data_loader.update_remaining_limit(account_id, amount)
        
        return {
            "status": "success",
            "message": f"Daily limit updated for account {account_id}"
        }
