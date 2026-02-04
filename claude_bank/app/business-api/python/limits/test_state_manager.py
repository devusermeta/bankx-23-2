import sys
from pathlib import Path

# Add common directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "common"))

from services import LimitsService

print("Testing Limits Service with StateManager...")

svc = LimitsService()

# Test get_account_limits
print("\n=== Test 1: Get account limits ===")
limits = svc.get_account_limits('CHK-001')
print(f"✓ Account CHK-001 limits:")
print(f"  Per-txn limit: {limits.per_txn_limit} THB")
print(f"  Daily limit: {limits.daily_limit} THB")
print(f"  Remaining today: {limits.remaining_today} THB")

# Test check_limits
print("\n=== Test 2: Check limits for 5000 THB transaction ===")
result = svc.check_limits('CHK-001', 5000)
print(f"✓ Sufficient balance: {result.sufficient_balance}")
print(f"✓ Within per-txn limit: {result.within_per_txn_limit}")
print(f"✓ Within daily limit: {result.within_daily_limit}")
approved = result.sufficient_balance and result.within_per_txn_limit and result.within_daily_limit
print(f"✓ All checks passed: {approved}")

# Test check_limits with large amount (should fail per-txn limit)
print("\n=== Test 3: Check limits for 60000 THB transaction (exceeds 50K limit) ===")
result = svc.check_limits('CHK-001', 60000)
print(f"✓ Within per-txn limit: {result.within_per_txn_limit}")
approved = result.sufficient_balance and result.within_per_txn_limit and result.within_daily_limit
print(f"✓ All checks passed: {approved}")
if not approved:
    print(f"✓ Error message: {result.error_message}")

print("\n=== Limits MCP ready for testing ===")
