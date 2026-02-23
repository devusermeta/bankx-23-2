"""
Unified Payment MCP Server - Business Services

Centralized service for handling transfers, limit checks, and validations.
Uses StateManager for all JSON file operations.
"""

import logging
import sys
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime
from difflib import SequenceMatcher

# Add parent directories to path for app.common imports
current_dir = Path(__file__).parent
claude_bank_dir = current_dir.parent.parent.parent.parent
if str(claude_bank_dir) not in sys.path:
    sys.path.insert(0, str(claude_bank_dir))

from app.common.state_manager import StateManager

from models import (
    Account,
    Beneficiary,
    LimitsCheckResult,
    AccountLimits,
    TransferValidationResult,
    TransferExecutionResult,
    TransactionRecord
)

logger = logging.getLogger(__name__)


class TransferService:
    """Unified service for processing transfers"""
    
    def __init__(self):
        self.state_manager = StateManager()
    
    # =========================================================================
    # Account Operations
    # =========================================================================
    
    def get_accounts_by_username(self, username: str) -> List[Account]:
        """
        Get all accounts for a customer by username (BankX email).
        
        Args:
            username: Customer's BankX email
            
        Returns:
            List of Account objects
        """
        try:
            print(f"\n{'='*80}")
            print(f"🔍 [GET_ACCOUNTS] Looking up accounts for username: {username}")
            print(f"{'='*80}")
            
            # Get customer by email
            customer = self.state_manager.get_customer_by_email(username)
            
            if not customer:
                print(f"❌ [GET_ACCOUNTS] No customer found for username: {username}")
                logger.warning(f"No customer found for username: {username}")
                return []
            
            customer_id = customer["customer_id"]
            print(f"✅ [GET_ACCOUNTS] Found customer: {customer['full_name']} (ID: {customer_id})")
            
            # Get accounts for this customer
            all_accounts = self.state_manager.get_accounts()
            print(f"📊 [GET_ACCOUNTS] Total accounts in system: {len(all_accounts)}")
            
            customer_accounts = [
                Account(**acct) for acct in all_accounts 
                if acct.get("customer_id") == customer_id
            ]
            
            print(f"✅ [GET_ACCOUNTS] Found {len(customer_accounts)} accounts for customer {customer_id}")
            for acc in customer_accounts:
                print(f"   💳 {acc.account_id} - {acc.account_no} - Balance: {acc.available_balance:,.2f} {acc.currency}")
            print(f"{'='*80}\n")
            
            return customer_accounts
            
        except Exception as e:
            print(f"❌ [GET_ACCOUNTS] ERROR: {e}")
            logger.error(f"Error fetching accounts for {username}: {e}", exc_info=True)
            return []
    
    def get_account_details(self, account_id: str) -> Optional[dict]:
        """
        Get detailed account information including balance and limits.
        
        Args:
            account_id: Account ID
            
        Returns:
            Dictionary with account details or None if not found
        """
        try:
            print(f"\n🔍 [GET_ACCOUNT_DETAILS] Fetching details for account: {account_id}")
            
            account = self.state_manager.get_account_by_id(account_id)
            if not account:
                print(f"❌ [GET_ACCOUNT_DETAILS] Account not found: {account_id}")
                return None
            
            print(f"✅ [GET_ACCOUNT_DETAILS] Found account: {account['cust_name']}")
            print(f"   💰 Balance: {account['available_balance']:,.2f} {account['currency']}")
            
            # Get limits
            limits = self.state_manager.get_limit_by_account(account_id)
            if limits:
                print(f"   📊 Limits: Per-txn: {limits['per_txn_limit']:,.2f}, Daily remaining: {limits['remaining_today']:,.2f}")
            
            return {
                "id": account["account_id"],
                "accountHolderFullName": account["cust_name"],
                "accountNumber": account["account_no"],
                "currency": account["currency"],
                "balance": account["available_balance"],
                "ledgerBalance": account["ledger_balance"],
                "status": "ACTIVE",
                "limits": limits if limits else None
            }
            
        except Exception as e:
            print(f"❌ [GET_ACCOUNT_DETAILS] ERROR: {e}")
            logger.error(f"Error fetching account details for {account_id}: {e}", exc_info=True)
            return None
    
    # =========================================================================
    # Beneficiary Operations
    # =========================================================================
    
    def get_registered_beneficiaries(self, customer_id: str) -> List[Beneficiary]:
        """
        Get all registered beneficiaries/contacts for a customer.
        
        Args:
            customer_id: Customer ID
            
        Returns:
            List of Beneficiary objects
        """
        try:
            print(f"\n🔍 [GET_BENEFICIARIES] Fetching beneficiaries for customer: {customer_id}")
            
            contacts = self.state_manager.get_contacts(customer_id)
            
            if not contacts:
                print(f"⚠️  [GET_BENEFICIARIES] No contacts found for customer: {customer_id}")
                return []
            
            print(f"✅ [GET_BENEFICIARIES] Found {len(contacts)} contacts for customer {customer_id}")
            
            # Convert to Beneficiary objects
            beneficiaries = [
                Beneficiary(
                    name=contact["name"],
                    account_number=contact.get("account_no", contact.get("account_number", "")),
                    alias=contact.get("alias"),
                    added_date=contact.get("added_date")
                )
                for contact in contacts
            ]
            
            for ben in beneficiaries:
                print(f"   👤 {ben.alias} - {ben.name} - {ben.account_number}")
            
            return beneficiaries
            
        except Exception as e:
            print(f"❌ [GET_BENEFICIARIES] ERROR: {e}")
            logger.error(f"Error fetching beneficiaries for {customer_id}: {e}", exc_info=True)
            return []
    
    def lookup_recipient_account(
        self, 
        account_number: str, 
        recipient_name: Optional[str] = None
    ) -> Optional[dict]:
        """
        Lookup recipient account by account number (and optionally name).
        
        Args:
            account_number: Recipient's account number
            recipient_name: Optional recipient name for verification
            
        Returns:
            Account dict if found and verified, None otherwise
        """
        try:
            print(f"\n🔍 [LOOKUP_RECIPIENT] Searching for account: {account_number}")
            if recipient_name:
                print(f"   With name verification: {recipient_name}")
            
            accounts = self.state_manager.get_accounts()
            
            # Find account by number
            recipient_account = next(
                (a for a in accounts if a.get("account_no") == account_number),
                None
            )
            
            if not recipient_account:
                print(f"❌ [LOOKUP_RECIPIENT] Recipient account not found: {account_number}")
                logger.warning(f"Recipient account not found: {account_number}")
                return None
            
            print(f"✅ [LOOKUP_RECIPIENT] Found account: {recipient_account['account_id']} - {recipient_account['cust_name']}")
            
            # If name provided, verify it matches
            if recipient_name:
                account_name = recipient_account.get("cust_name", "").lower()
                provided_name = recipient_name.lower()
                
                if account_name != provided_name:
                    print(f"❌ [LOOKUP_RECIPIENT] Name mismatch! Account: '{account_name}', Provided: '{provided_name}'")
                    logger.warning(
                        f"Recipient name mismatch. Expected: {account_name}, "
                        f"Got: {provided_name}"
                    )
                    return None
                
                print(f"✅ [LOOKUP_RECIPIENT] Name verified: {recipient_name}")
            
            return recipient_account
            
        except Exception as e:
            print(f"❌ [LOOKUP_RECIPIENT] ERROR: {e}")
            logger.error(f"Error looking up recipient account: {e}", exc_info=True)
            return None
    
    # =========================================================================
    # Limits Checking
    # =========================================================================
    
    def check_limits(
        self, 
        account_id: str, 
        amount: float
    ) -> LimitsCheckResult:
        """
        Check if a transaction is within all limits (balance, per-txn, daily).
        Should be called TWICE: before approval request and before execution.
        
        Args:
            account_id: Sender's account ID
            amount: Transaction amount
            
        Returns:
            LimitsCheckResult with validation details
        """
        try:
            print(f"\n{'='*80}")
            print(f"💰 [CHECK_LIMITS] Validating transaction: {amount:,.2f} THB for account {account_id}")
            print(f"{'='*80}")
            
            # Check and reset daily limits if needed
            self.state_manager.check_and_reset_daily_limits()
            
            # Get account balance
            account = self.state_manager.get_account_by_id(account_id)
            if not account:
                print(f"❌ [CHECK_LIMITS] Account {account_id} not found!")
                return LimitsCheckResult(
                    sufficient_balance=False,
                    within_per_txn_limit=False,
                    within_daily_limit=False,
                    remaining_after=0,
                    daily_limit_remaining_after=0,
                    error_message=f"Account {account_id} not found"
                )
            
            current_balance = account["available_balance"]
            print(f"📊 [CHECK_LIMITS] Current balance: {current_balance:,.2f} THB")
            
            # Get limits
            limits = self.state_manager.get_limit_by_account(account_id)
            if not limits:
                print(f"❌ [CHECK_LIMITS] No limits configured for account {account_id}!")
                return LimitsCheckResult(
                    sufficient_balance=False,
                    within_per_txn_limit=False,
                    within_daily_limit=False,
                    remaining_after=0,
                    daily_limit_remaining_after=0,
                    current_balance=current_balance,
                    error_message=f"No limits configured for account {account_id}"
                )
            
            per_txn_limit = limits["per_txn_limit"]
            daily_limit = limits["daily_limit"]
            remaining_today = limits["remaining_today"]
            
            print(f"📋 [CHECK_LIMITS] Limits Configuration:")
            print(f"   ├─ Per-transaction limit: {per_txn_limit:,.2f} THB")
            print(f"   ├─ Daily limit (total): {daily_limit:,.2f} THB")
            print(f"   └─ Daily remaining: {remaining_today:,.2f} THB")
            
            # Perform checks
            sufficient_balance = current_balance >= amount
            within_per_txn_limit = amount <= per_txn_limit
            within_daily_limit = amount <= remaining_today
            
            remaining_after = current_balance - amount
            daily_limit_remaining_after = remaining_today - amount
            
            print(f"\n🔍 [CHECK_LIMITS] Validation Results:")
            print(f"   ├─ Balance check: {'✅ PASS' if sufficient_balance else '❌ FAIL'} (Need: {amount:,.2f}, Have: {current_balance:,.2f})")
            print(f"   ├─ Per-txn limit: {'✅ PASS' if within_per_txn_limit else '❌ FAIL'} (Amount: {amount:,.2f}, Limit: {per_txn_limit:,.2f})")
            print(f"   └─ Daily limit: {'✅ PASS' if within_daily_limit else '❌ FAIL'} (Amount: {amount:,.2f}, Remaining: {remaining_today:,.2f})")
            
            # Build error message if any check fails
            error_parts = []
            if not sufficient_balance:
                error_parts.append(
                    f"Insufficient balance (available: {current_balance:,.2f} THB)"
                )
            if not within_per_txn_limit:
                error_parts.append(
                    f"Exceeds per-transaction limit ({per_txn_limit:,.2f} THB)"
                )
            if not within_daily_limit:
                error_parts.append(
                    f"Exceeds daily remaining limit ({remaining_today:,.2f} THB)"
                )
            
            error_message = "; ".join(error_parts) if error_parts else None
            
            if error_message:
                print(f"\n❌ [CHECK_LIMITS] VALIDATION FAILED: {error_message}")
            else:
                print(f"\n✅ [CHECK_LIMITS] ALL CHECKS PASSED!")
                print(f"   ├─ Balance after: {remaining_after:,.2f} THB")
                print(f"   └─ Daily limit remaining after: {daily_limit_remaining_after:,.2f} THB")
            
            print(f"{'='*80}\n")
            
            return LimitsCheckResult(
                sufficient_balance=sufficient_balance,
                within_per_txn_limit=within_per_txn_limit,
                within_daily_limit=within_daily_limit,
                remaining_after=remaining_after,
                daily_limit_remaining_after=daily_limit_remaining_after,
                current_balance=current_balance,
                error_message=error_message
            )
            
        except Exception as e:
            print(f"❌ [CHECK_LIMITS] EXCEPTION: {e}")
            logger.error(f"Error checking limits: {e}", exc_info=True)
            return LimitsCheckResult(
                sufficient_balance=False,
                within_per_txn_limit=False,
                within_daily_limit=False,
                remaining_after=0,
                daily_limit_remaining_after=0,
                error_message=f"Error checking limits: {str(e)}"
            )
    
    # =========================================================================
    # Transfer Validation (Pre-execution)
    # =========================================================================
    
    def validate_transfer(
        self,
        sender_account_id: str,
        recipient_identifier: str,
        amount: float,
        recipient_name: Optional[str] = None
    ) -> TransferValidationResult:
        """
        Validate a transfer request BEFORE showing the approval request.
        Checks all limits and validates recipient.
        
        Args:
            sender_account_id: Sender's account ID
            recipient_identifier: Account number or beneficiary alias
            amount: Transfer amount
            recipient_name: Optional recipient name for verification
            
        Returns:
            TransferValidationResult with all validation details
        """
        try:
            print(f"\n{'='*80}")
            print(f"🔍 [VALIDATE_TRANSFER] Starting validation")
            print(f"{'='*80}")
            print(f"   Sender: {sender_account_id}")
            print(f"   Recipient identifier: {recipient_identifier}")
            print(f"   Amount: {amount:,.2f} THB")
            if recipient_name:
                print(f"   Recipient name (for verification): {recipient_name}")
            print(f"{'='*80}\n")
            
            # Get sender account
            sender_account = self.state_manager.get_account_by_id(sender_account_id)
            if not sender_account:
                print(f"❌ [VALIDATE_TRANSFER] Sender account {sender_account_id} not found!")
                return TransferValidationResult(
                    valid=False,
                    sender_account_id=sender_account_id,
                    sender_name="Unknown",
                    sender_balance=0,
                    amount=amount,
                    currency="THB",
                    checks=LimitsCheckResult(
                        sufficient_balance=False,
                        within_per_txn_limit=False,
                        within_daily_limit=False,
                        remaining_after=0,
                        daily_limit_remaining_after=0
                    ),
                    error_message=f"Sender account {sender_account_id} not found"
                )
            
            sender_name = sender_account["cust_name"]
            sender_balance = sender_account["available_balance"]
            currency = sender_account.get("currency", "THB")
            
            print(f"✅ [VALIDATE_TRANSFER] Sender account found: {sender_name}")
            print(f"   Balance: {sender_balance:,.2f} {currency}\n")
            
            # Check limits
            limits_check = self.check_limits(sender_account_id, amount)
            
            # Lookup recipient
            recipient_account = self.lookup_recipient_account(
                recipient_identifier, 
                recipient_name
            )
            
            if not recipient_account:
                # Try to find as beneficiary (by alias, account number, OR name)
                print(f"⚠️  [VALIDATE_TRANSFER] Not found as account number, trying as beneficiary...")
                customer_id = sender_account["customer_id"]
                beneficiaries = self.get_registered_beneficiaries(customer_id)
                
                # Check by alias, account_number, or name
                recipient_lower = recipient_identifier.lower()
                beneficiary = None
                best_match_score = 0.0
                best_match = None
                
                # First, try exact matches by alias or account number
                for b in beneficiaries:
                    if (b.alias and b.alias.lower() == recipient_lower) or \
                       (b.account_number and b.account_number.lower() == recipient_lower):
                        beneficiary = b
                        print(f"✅ [VALIDATE_TRANSFER] Found beneficiary by exact alias/account: {b.name} ({b.account_number})")
                        break
                
                # If not found, try exact name match
                if not beneficiary:
                    for b in beneficiaries:
                        if b.name and b.name.lower() == recipient_lower:
                            beneficiary = b
                            print(f"✅ [VALIDATE_TRANSFER] Found beneficiary by exact name: {b.name} ({b.account_number})")
                            break
                
                # If still not found, try fuzzy matching with similarity threshold
                if not beneficiary:
                    print(f"🔍 [VALIDATE_TRANSFER] Trying fuzzy name matching...")
                    for b in beneficiaries:
                        if b.name:
                            # Use SequenceMatcher to get similarity ratio
                            similarity = SequenceMatcher(None, recipient_lower, b.name.lower()).ratio()
                            print(f"   Comparing '{recipient_identifier}' with '{b.name}': {similarity:.2%} similar")
                            
                            # Keep track of best match (threshold >= 80%)
                            if similarity > best_match_score and similarity >= 0.80:
                                best_match_score = similarity
                                best_match = b
                    
                    if best_match:
                        beneficiary = best_match
                        print(f"✅ [VALIDATE_TRANSFER] Found beneficiary by fuzzy match ({best_match_score:.2%}): {beneficiary.name} ({beneficiary.account_number})")
                    else:
                        print(f"❌ [VALIDATE_TRANSFER] No fuzzy match found (best score: {best_match_score:.2%}, threshold: 80%)")
                
                if beneficiary:
                    # Re-lookup by account number
                    recipient_account = self.lookup_recipient_account(
                        beneficiary.account_number
                    )
                
                if not recipient_account:
                    print(f"❌ [VALIDATE_TRANSFER] Recipient not found: {recipient_identifier}")
                    return TransferValidationResult(
                        valid=False,
                        sender_account_id=sender_account_id,
                        sender_name=sender_name,
                        sender_balance=sender_balance,
                        amount=amount,
                        currency=currency,
                        checks=limits_check,
                        error_message=f"Recipient account not found: {recipient_identifier}"
                    )
            
            recipient_account_id = recipient_account["account_id"]
            recipient_name_found = recipient_account["cust_name"]
            recipient_account_no = recipient_account["account_no"]
            
            print(f"✅ [VALIDATE_TRANSFER] Recipient account found: {recipient_name_found}")
            print(f"   Account: {recipient_account_no} ({recipient_account_id})\n")
            
            # Check if all validations pass
            all_checks_pass = (
                limits_check.sufficient_balance and
                limits_check.within_per_txn_limit and
                limits_check.within_daily_limit
            )
            
            if all_checks_pass:
                print(f"{'='*80}")
                print(f"✅ [VALIDATE_TRANSFER] VALIDATION PASSED!")
                print(f"{'='*80}")
                print(f"   Transfer: {sender_name} → {recipient_name_found}")
                print(f"   Amount: {amount:,.2f} {currency}")
                print(f"   Sender balance after: {limits_check.remaining_after:,.2f} {currency}")
                print(f"   Daily limit remaining after: {limits_check.daily_limit_remaining_after:,.2f} {currency}")
                print(f"{'='*80}\n")
            else:
                print(f"{'='*80}")
                print(f"❌ [VALIDATE_TRANSFER] VALIDATION FAILED!")
                print(f"{'='*80}")
                print(f"   Reason: {limits_check.error_message}")
                print(f"{'='*80}\n")
            
            return TransferValidationResult(
                valid=all_checks_pass,
                sender_account_id=sender_account_id,
                sender_name=sender_name,
                sender_balance=sender_balance,
                recipient_account_id=recipient_account_id,
                recipient_name=recipient_name_found,
                recipient_account_no=recipient_account_no,
                amount=amount,
                currency=currency,
                checks=limits_check,
                error_message=limits_check.error_message if not all_checks_pass else None
            )
            
        except Exception as e:
            print(f"❌ [VALIDATE_TRANSFER] EXCEPTION: {e}")
            logger.error(f"Error validating transfer: {e}", exc_info=True)
            return TransferValidationResult(
                valid=False,
                sender_account_id=sender_account_id,
                sender_name="Unknown",
                sender_balance=0,
                amount=amount,
                currency="THB",
                checks=LimitsCheckResult(
                    sufficient_balance=False,
                    within_per_txn_limit=False,
                    within_daily_limit=False,
                    remaining_after=0,
                    daily_limit_remaining_after=0
                ),
                error_message=f"Validation error: {str(e)}"
            )
    
    # =========================================================================
    # Transfer Execution
    # =========================================================================
    
    def execute_transfer(
        self,
        sender_account_id: str,
        recipient_account_id: str,
        amount: float,
        description: str = "Transfer"
    ) -> TransferExecutionResult:
        """
        Execute a transfer AFTER user approval.
        Performs final limit check, updates balances, creates transactions.
        
        IMPORTANT: This must be called AFTER user approval, and should
        re-check limits before execution.
        
        Args:
            sender_account_id: Sender's account ID
            recipient_account_id: Recipient's account ID
            amount: Transfer amount
            description: Transaction description
            
        Returns:
            TransferExecutionResult with execution details
        """
        try:
            print(f"\n{'='*80}")
            print(f"🚀 [EXECUTE_TRANSFER] Starting transfer execution")
            print(f"{'='*80}")
            print(f"   From: {sender_account_id}")
            print(f"   To: {recipient_account_id}")
            print(f"   Amount: {amount:,.2f} THB")
            print(f"   Description: {description}")
            print(f"{'='*80}\n")
            
            # CRITICAL: Re-check limits before execution (things may have changed)
            print(f"🔍 [EXECUTE_TRANSFER] Step 1: Re-checking limits (final validation)...")
            limits_check = self.check_limits(sender_account_id, amount)
            
            if not (limits_check.sufficient_balance and 
                    limits_check.within_per_txn_limit and 
                    limits_check.within_daily_limit):
                print(f"❌ [EXECUTE_TRANSFER] Final limits check failed!")
                return TransferExecutionResult(
                    success=False,
                    sender_new_balance=limits_check.current_balance or 0,
                    daily_limit_remaining=limits_check.daily_limit_remaining_after,
                    error_message=f"Limits check failed: {limits_check.error_message}"
                )
            
            print(f"✅ [EXECUTE_TRANSFER] Limits check passed!\n")
            
            # Get both accounts
            print(f"🔍 [EXECUTE_TRANSFER] Step 2: Fetching account details...")
            sender_account = self.state_manager.get_account_by_id(sender_account_id)
            recipient_account = self.state_manager.get_account_by_id(recipient_account_id)
            
            if not sender_account or not recipient_account:
                print(f"❌ [EXECUTE_TRANSFER] Account not found!")
                return TransferExecutionResult(
                    success=False,
                    sender_new_balance=0,
                    daily_limit_remaining=0,
                    error_message="One or both accounts not found"
                )
            
            sender_name = sender_account["cust_name"]
            recipient_name = recipient_account["cust_name"]
            sender_balance_before = sender_account["available_balance"]
            recipient_balance_before = recipient_account["available_balance"]
            
            print(f"   Sender: {sender_name} (Balance: {sender_balance_before:,.2f} THB)")
            print(f"   Recipient: {recipient_name} (Balance: {recipient_balance_before:,.2f} THB)")
            print(f"✅ [EXECUTE_TRANSFER] Accounts fetched!\n")
            
            # Generate transaction ID
            timestamp_iso = datetime.now().isoformat()
            timestamp_short = datetime.now().strftime("%Y%m%d%H%M%S")
            txn_id = f"TXN-{timestamp_short}-{sender_account_id[:4]}"
            
            print(f"📋 [EXECUTE_TRANSFER] Step 3: Generated transaction ID: {txn_id}\n")
            
            # Update sender balance (debit)
            print(f"💸 [EXECUTE_TRANSFER] Step 4: Debiting sender account...")
            print(f"   Deducting {amount:,.2f} THB from {sender_name}")
            new_sender_balance = sender_balance_before - amount
            self.state_manager.update_account_balance(
                sender_account_id,
                new_sender_balance
            )
            print(f"✅ [EXECUTE_TRANSFER] Sender account debited!")
            print(f"   {sender_name}: {sender_balance_before:,.2f} → {new_sender_balance:,.2f} THB\n")
            
            # Update recipient balance (credit)
            print(f"💰 [EXECUTE_TRANSFER] Step 5: Crediting recipient account...")
            print(f"   Adding {amount:,.2f} THB to {recipient_name}")
            new_recipient_balance = recipient_balance_before + amount
            self.state_manager.update_account_balance(
                recipient_account_id,
                new_recipient_balance
            )
            print(f"✅ [EXECUTE_TRANSFER] Recipient account credited!")
            print(f"   {recipient_name}: {recipient_balance_before:,.2f} → {new_recipient_balance:,.2f} THB\n")
            # Update sender's daily limit
            print(f"📊 [EXECUTE_TRANSFER] Step 6: Updating daily limit...")
            limits = self.state_manager.get_limit_by_account(sender_account_id)
            old_remaining = limits["remaining_today"]
            new_remaining = old_remaining - amount
            self.state_manager.update_remaining_limit(sender_account_id, new_remaining)
            print(f"✅ [EXECUTE_TRANSFER] Daily limit updated!")
            print(f"   Daily remaining: {old_remaining:,.2f} → {new_remaining:,.2f} THB\n")
            
            # Create transaction records
            print(f"📝 [EXECUTE_TRANSFER] Step 7: Creating transaction records...")
            
            # Sender's outgoing transaction
            sender_txn_dict = {
                "account_id": sender_account_id,
                "timestamp": timestamp_iso,
                "amount": -amount,  # Negative for debit
                "type": "outcome",
                "description": description,
                "category": "Transfer",
                "status": "POSTED",
                "counterparty_name": recipient_account["cust_name"],
                "counterparty_account_no": recipient_account["account_no"],
                "currency": sender_account.get("currency", "THB")
            }
            
            # Recipient's incoming transaction
            recipient_txn_dict = {
                "account_id": recipient_account_id,
                "timestamp": timestamp_iso,
                "amount": amount,  # Positive for credit
                "type": "income",
                "description": f"Transfer from {sender_account['cust_name']}",
                "category": "Transfer",
                "status": "POSTED",
                "counterparty_name": sender_account["cust_name"],
                "counterparty_account_no": sender_account["account_no"],
                "currency": recipient_account.get("currency", "THB")
            }
            
            # Add transactions using StateManager
            sender_txn_id = self.state_manager.add_transaction(sender_txn_dict)
            recipient_txn_id = self.state_manager.add_transaction(recipient_txn_dict)
            
            print(f"✅ [EXECUTE_TRANSFER] Transaction records created!")
            print(f"   Sender transaction ID: {sender_txn_id}")
            print(f"   Recipient transaction ID: {recipient_txn_id}\n")
            
            # Get updated balances
            sender_account = self.state_manager.get_account_by_id(sender_account_id)
            recipient_account = self.state_manager.get_account_by_id(recipient_account_id)
            
            print(f"{'='*80}")
            print(f"✅ [EXECUTE_TRANSFER] TRANSFER COMPLETED SUCCESSFULLY!")
            print(f"{'='*80}")
            print(f"   Transaction ID: {sender_txn_id}")
            print(f"   {sender_name}: {sender_balance_before:,.2f} → {sender_account['available_balance']:,.2f} THB")
            print(f"   {recipient_name}: {recipient_balance_before:,.2f} → {recipient_account['available_balance']:,.2f} THB")
            print(f"   Daily limit remaining: {new_remaining:,.2f} THB")
            print(f"{'='*80}\n")
            
            return TransferExecutionResult(
                success=True,
                transaction_id=sender_txn_id,
                sender_new_balance=sender_account["available_balance"],
                recipient_new_balance=recipient_account["available_balance"],
                daily_limit_remaining=new_remaining,
                error_message=None
            )
            
        except Exception as e:
            print(f"\n❌ [EXECUTE_TRANSFER] EXCEPTION OCCURRED!")
            print(f"   Error: {e}")
            print(f"   Type: {type(e).__name__}")
            logger.error(f"Error executing transfer: {e}", exc_info=True)
            return TransferExecutionResult(
                success=False,
                sender_new_balance=0,
                daily_limit_remaining=0,
                error_message=f"Execution error: {str(e)}"
            )
    
    # =========================================================================
    # Helper Methods - Note: Most helper methods are now using StateManager directly
    # =========================================================================
