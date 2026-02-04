import logging
import os
from typing import Optional
import uuid
import requests
from pathlib import Path
from datetime import datetime
import sys

from models import Payment, Transaction

# Add common directory to path for StateManager
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "common"))
from state_manager import get_state_manager

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, transaction_api_url: Optional[str] = None):
        # Prefer explicit constructor param. If not provided, read from env.
        env_url = os.environ.get("TRANSACTIONS_API_SERVER_URL") or os.environ.get("TRANSACTIONS_API_URL")
        if transaction_api_url:
            self.transaction_api_url = transaction_api_url
        elif env_url:
            self.transaction_api_url = env_url
        else:
            # Defensive: fail fast if the transaction API URL isn't configured.
            raise ValueError(
                "Transaction API URL is not configured. Provide `transaction_api_url` to PaymentService or set the TRANSACTIONS_API_SERVER_URL (or legacy TRANSACTIONS_API_URL) environment variable."
            )

        # Use StateManager instead of individual services
        self.state = get_state_manager()

    def process_payment(self, payment: Payment):
        # Check and reset daily limits if it's a new day (fallback mechanism)
        logger.info("🔍 Checking if daily limits need reset...")
        self.state.check_and_reset_daily_limits()
        
        # validations
        if not payment.accountId:
            raise ValueError("AccountId is empty or null")
        
        # UPDATED: Accept both numeric (old) and alphanumeric (new CSV format like CHK-001) account IDs
        # No longer requiring isdigit() validation
        
        if (payment.paymentType or "").lower() != "transfer" and (not payment.paymentMethodId):
            raise ValueError("paymentMethodId is empty or null")

        # UPDATED: Accept both numeric and alphanumeric payment method IDs (e.g., PM-CHK-001)
        # No longer requiring isdigit() validation for payment method ID

        # Pydantic v2: `json()` is deprecated. Use `model_dump_json()` instead.
        logger.info("Payment successful for: %s", payment.model_dump_json())

        # STEP 1: Get recipient account ID from account number
        logger.info(f"Looking up recipient account number: {payment.recipientBankCode}")
        accounts = self.state.get_accounts()
        recipient_account = None
        
        for acc_data in accounts:
            if acc_data.get('account_no') == payment.recipientBankCode:
                recipient_account = acc_data
                break
        
        if not recipient_account:
            logger.error(f"❌ Recipient account not found for account number: {payment.recipientBankCode}")
            raise ValueError(f"Recipient account not found: {payment.recipientBankCode}")
        
        recipient_account_id = recipient_account['account_id']
        logger.info(f"Found recipient account: {recipient_account_id} ({recipient_account.get('cust_name')})")
        
        # STEP 2: Get sender account for balance check
        sender_account = self.state.get_account_by_id(payment.accountId)
        if not sender_account:
            logger.error(f"❌ Sender account not found: {payment.accountId}")
            raise ValueError(f"Sender account not found: {payment.accountId}")
        
        sender_balance = sender_account.get('ledger_balance', 0)
        recipient_balance = recipient_account.get('ledger_balance', 0)
        
        logger.info(f"Current balances: Sender {payment.accountId}={sender_balance:.2f} THB, Recipient {recipient_account_id}={recipient_balance:.2f} THB")
        
        # STEP 3: Update balances (atomic operations)
        new_sender_balance = sender_balance - payment.amount
        new_recipient_balance = recipient_balance + payment.amount
        
        logger.info(f"Processing balance transfer: {payment.accountId} -> {recipient_account_id}, Amount: {payment.amount} THB")
        self.state.update_account_balance(payment.accountId, new_sender_balance)
        self.state.update_account_balance(recipient_account_id, new_recipient_balance)
        
        logger.info(f"✅ Balance updated: {payment.accountId}={new_sender_balance:.2f} THB, {recipient_account_id}={new_recipient_balance:.2f} THB")
        
        # STEP 4: Create OUT transaction for sender
        out_txn_dict = {
            "description": payment.description,
            "type": "outcome",
            "counterparty_name": payment.recipientName,
            "counterparty_account_no": payment.recipientBankCode,
            "account_id": payment.accountId,
            "category": payment.paymentType or "transfer",
            "amount": payment.amount,
            "timestamp": payment.timestamp or datetime.now().isoformat()
        }
        
        out_txn_id = self.state.add_transaction(out_txn_dict)
        logger.info(f"✅ Saved OUT transaction: {out_txn_id} for {payment.accountId}")
        
        # STEP 5: Create IN transaction for recipient
        sender_account_no = sender_account.get('account_no', payment.accountId)
        sender_name = sender_account.get('cust_name', 'Unknown')
        
        in_txn_dict = {
            "description": f"Transfer from {sender_name}",
            "type": "income",
            "counterparty_name": sender_name,
            "counterparty_account_no": sender_account_no,
            "account_id": recipient_account_id,
            "category": payment.paymentType or "transfer",
            "amount": payment.amount,
            "timestamp": payment.timestamp or datetime.now().isoformat()
        }
        
        in_txn_id = self.state.add_transaction(in_txn_dict)
        logger.info(f"✅ Saved IN transaction: {in_txn_id} for {recipient_account_id}")
        
        logger.info(f"✅ Bidirectional transactions created: OUT ({out_txn_id}) and IN ({in_txn_id})")
        
        # STEP 6: Update daily limits (deduct amount from remaining)
        sender_limit = self.state.get_limit_by_account(payment.accountId)
        new_remaining = sender_limit['remaining_today'] - payment.amount
        logger.info(f"Updating daily limits for {payment.accountId}: {sender_limit['remaining_today']:.2f} - {payment.amount:.2f} = {new_remaining:.2f} THB")
        self.state.update_remaining_limit(payment.accountId, new_remaining)
        logger.info(f"✅ Daily limits updated for {payment.accountId}")

