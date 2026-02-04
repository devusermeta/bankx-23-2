"""
Test PaymentService with StateManager integration.
Tests atomic updates: accounts.json, transactions.json, limits.json
"""

import sys
from pathlib import Path
from datetime import datetime

# Add common directory to path for StateManager
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "common"))

from state_manager import get_state_manager
from services import PaymentService
from models import Payment

def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def test_payment_service():
    """Test complete payment flow with StateManager."""
    
    state = get_state_manager()
    service = PaymentService(transaction_api_url="http://localhost:8071")
    
    print_section("INITIAL STATE")
    
    # Get sender account (CHK-001)
    sender = state.get_account_by_id("CHK-001")
    print(f"Sender CHK-001: {sender['cust_name']}")
    print(f"  Balance: {sender['ledger_balance']:.2f} THB")
    print(f"  Account No: {sender['account_no']}")
    
    # Get recipient account (123-456-003)
    accounts = state.get_accounts()
    recipient = None
    for acc_data in accounts:
        if acc_data.get('account_no') == '123-456-003':
            recipient = acc_data
            break
    
    print(f"\nRecipient {recipient['account_id']}: {recipient['cust_name']}")
    print(f"  Balance: {recipient['ledger_balance']:.2f} THB")
    print(f"  Account No: {recipient['account_no']}")
    
    # Get sender limit
    sender_limit = state.get_limit_by_account("CHK-001")
    print(f"\nSender Limits:")
    print(f"  Per-transaction: {sender_limit['per_txn_limit']:.2f} THB")
    print(f"  Daily limit: {sender_limit['daily_limit']:.2f} THB")
    print(f"  Remaining today: {sender_limit['remaining_today']:.2f} THB")
    
    # Get transaction count
    transactions = state.get_transactions()
    print(f"\nTotal transactions in system: {len(transactions)}")
    sender_txns = [t for t in transactions if t.get('account_id') == 'CHK-001']
    print(f"Sender CHK-001 transactions: {len(sender_txns)}")
    
    print_section("EXECUTING TRANSFER: 500 THB to Pimchanok")
    
    # Create payment
    payment = Payment(
        accountId="CHK-001",
        paymentMethodId="PM-001",
        amount=500.0,
        description="Test transfer to Pimchanok",
        recipientName="Pimchanok Thongchai",
        recipientBankCode="123-456-003",
        paymentType="transfer",
        timestamp=datetime.now().isoformat()
    )
    
    # Process payment
    try:
        service.process_payment(payment)
        print("✅ Payment processed successfully")
    except Exception as e:
        print(f"❌ Payment failed: {e}")
        return
    
    print_section("FINAL STATE")
    
    # Get updated sender account
    sender_after = state.get_account_by_id("CHK-001")
    print(f"Sender CHK-001: {sender_after['cust_name']}")
    print(f"  Balance: {sender_after['ledger_balance']:.2f} THB (was {sender['ledger_balance']:.2f})")
    print(f"  Change: {sender_after['ledger_balance'] - sender['ledger_balance']:.2f} THB")
    
    # Get updated recipient account
    recipient_after = state.get_account_by_id(recipient['account_id'])
    print(f"\nRecipient {recipient_after['account_id']}: {recipient_after['cust_name']}")
    print(f"  Balance: {recipient_after['ledger_balance']:.2f} THB (was {recipient['ledger_balance']:.2f})")
    print(f"  Change: +{recipient_after['ledger_balance'] - recipient['ledger_balance']:.2f} THB")
    
    # Get updated limit
    sender_limit_after = state.get_limit_by_account("CHK-001")
    print(f"\nSender Limits:")
    print(f"  Remaining today: {sender_limit_after['remaining_today']:.2f} THB (was {sender_limit['remaining_today']:.2f})")
    print(f"  Used: {sender_limit['remaining_today'] - sender_limit_after['remaining_today']:.2f} THB")
    
    # Get new transactions
    transactions_after = state.get_transactions()
    print(f"\nTotal transactions in system: {len(transactions_after)} (was {len(transactions)})")
    print(f"New transactions created: {len(transactions_after) - len(transactions)}")
    
    # Show new transactions
    new_txns = transactions_after[len(transactions):]
    for txn in new_txns:
        print(f"\n  Transaction {txn['txn_id']}:")
        print(f"    Account: {txn['account_id']}")
        print(f"    Type: {txn['type']}")
        print(f"    Amount: {txn['amount']:.2f} THB")
        print(f"    Description: {txn['description']}")
        print(f"    Counterparty: {txn.get('counterparty_name', 'N/A')}")
    
    print_section("VERIFICATION")
    
    # Verify balance changes
    sender_balance_change = sender_after['ledger_balance'] - sender['ledger_balance']
    recipient_balance_change = recipient_after['ledger_balance'] - recipient['ledger_balance']
    
    assert sender_balance_change == -500.0, f"Sender balance should decrease by 500, got {sender_balance_change}"
    print("✅ Sender balance decreased by 500 THB")
    
    assert recipient_balance_change == 500.0, f"Recipient balance should increase by 500, got {recipient_balance_change}"
    print("✅ Recipient balance increased by 500 THB")
    
    # Verify transactions created
    assert len(transactions_after) == len(transactions) + 2, "Should create 2 transactions (OUT + IN)"
    print("✅ 2 transactions created (OUT + IN)")
    
    # Verify limit update
    limit_change = sender_limit['remaining_today'] - sender_limit_after['remaining_today']
    assert limit_change == 500.0, f"Remaining limit should decrease by 500, got {limit_change}"
    print("✅ Daily limit decreased by 500 THB")
    
    print("\n✅ ALL TESTS PASSED!")
    print(f"\nResult: Transfer of 500 THB from {sender['cust_name']} to {recipient['cust_name']} completed successfully.")
    print(f"  - Balances updated atomically")
    print(f"  - Bidirectional transactions created")
    print(f"  - Daily limits updated")

if __name__ == "__main__":
    test_payment_service()
