import sys
from pathlib import Path

# Add common directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "common"))

from state_manager import get_state_manager

print("✓ StateManager import successful")

state = get_state_manager()
print("✓ StateManager initialized")

acc = state.get_account_by_id('CHK-001')
print(f"✓ Account CHK-001 balance: {acc['ledger_balance']} THB")

print("\n=== Account MCP ready for testing ===")
