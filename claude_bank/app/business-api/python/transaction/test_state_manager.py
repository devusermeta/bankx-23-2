import sys
from pathlib import Path

# Add common directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "common"))

from services import TransactionService

print("Testing Transaction Service with StateManager...")

svc = TransactionService()

# Test get_last_transactions with limit=1
print("\n=== Test 1: Get last 1 transaction ===")
txns = svc.get_last_transactions('CHK-001', limit=1)
print(f"✓ Got {len(txns)} transaction")
if txns:
    print(f"  ID: {txns[0].id}")
    print(f"  Description: {txns[0].description}")
    print(f"  Recipient: {txns[0].recipientName}")
    print(f"  Amount: {txns[0].amount} THB")
    print(f"  Type: {txns[0].type}")

# Test get_last_transactions with limit=5
print("\n=== Test 2: Get last 5 transactions ===")
txns5 = svc.get_last_transactions('CHK-001', limit=5)
print(f"✓ Got {len(txns5)} transactions")
for i, txn in enumerate(txns5, 1):
    print(f"  {i}. {txn.id} - {txn.description} - {txn.amount} THB")

print("\n=== Transaction MCP ready for testing ===")
