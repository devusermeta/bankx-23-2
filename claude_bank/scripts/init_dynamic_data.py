"""
Initialize dynamic_data JSON files from CSV seed data

Run this once to populate transactions.json and other files
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.common.state_manager import get_state_manager

def main():
    print("=" * 60)
    print("Initializing UC1 Dynamic Data from CSV")
    print("=" * 60)
    
    sm = get_state_manager()
    
    # Force regeneration of all files
    print("\n1. Regenerating accounts.json...")
    sm._regenerate_accounts()
    
    print("\n2. Regenerating limits.json...")
    sm._regenerate_limits()
    
    print("\n3. Regenerating transactions.json...")
    sm._regenerate_transactions()
    
    print("\n4. Regenerating contacts.json...")
    sm._regenerate_contacts()
    
    print("\n5. Regenerating customers.json...")
    sm._regenerate_customers()
    
    print("\n" + "=" * 60)
    print("✅ Initialization complete!")
    print("=" * 60)
    
    # Print summary
    print("\nSummary:")
    print(f"  Accounts: {len(sm.get_accounts())}")
    print(f"  Limits: {len(sm.get_limits())}")
    print(f"  Transactions: {len(sm.get_transactions())}")
    print(f"  Customers: {len(sm.get_customers())}")
    print(f"  Contacts (CUST-001): {len(sm.get_contacts('CUST-001'))}")
    
    print("\nFiles created in: dynamic_data/")
    print("  - accounts.json")
    print("  - limits.json")
    print("  - transactions.json")
    print("  - contacts.json")
    print("  - customers.json")

if __name__ == "__main__":
    main()
