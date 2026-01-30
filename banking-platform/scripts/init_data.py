"""
Data Initialization Script

Converts CSV files from InitialData/ to JSON files in dynamic_data/.
Run this once before starting the MCP server for the first time.
"""

import csv
import json
from pathlib import Path
from datetime import datetime


def load_csv(file_path: Path) -> list:
    """Load CSV file and return list of dicts"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    return data


def convert_accounts_csv_to_json(csv_path: Path, json_path: Path):
    """Convert accounts.csv to accounts.json"""
    print(f"Converting {csv_path} to {json_path}...")
    
    rows = load_csv(csv_path)
    
    # Convert to proper types and format
    accounts = []
    for row in rows:
        account = {
            "account_id": row["account_id"],
            "customer_id": row["customer_id"],
            "account_no": row["account_no"],
            "cust_name": row["cust_name"],
            "acc_type": row["acc_type"],
            "currency": row["currency"],
            "ledger_balance": float(row["ledger_balance"]),
            "available_balance": float(row["available_balance"])
        }
        accounts.append(account)
    
    # Create JSON structure with metadata
    data = {
        "_metadata": {
            "last_updated": datetime.now().isoformat(),
            "source": "InitialData/accounts.csv",
            "description": "Runtime account balances - updated on each transfer"
        },
        "accounts": accounts
    }
    
    # Write JSON file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Created {json_path} with {len(accounts)} accounts")


def convert_limits_csv_to_json(csv_path: Path, json_path: Path):
    """Convert limits.csv to limits.json"""
    print(f"Converting {csv_path} to {json_path}...")
    
    rows = load_csv(csv_path)
    
    # Convert to proper types and format
    limits = []
    for row in rows:
        limit = {
            "account_id": row["account_id"],
            "per_txn_limit": float(row["per_txn_limit"]),
            "daily_limit": float(row["daily_limit"]),
            "remaining_today": float(row["remaining_today"]),
            "currency": row["currency"]
        }
        limits.append(limit)
    
    # Create JSON structure with metadata
    data = {
        "_metadata": {
            "last_updated": datetime.now().isoformat(),
            "source": "InitialData/limits.csv",
            "description": "Runtime transfer limits - remaining_today updated on each transfer"
        },
        "limits": limits
    }
    
    # Write JSON file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Created {json_path} with {len(limits)} limits")


def convert_customers_csv_to_json(csv_path: Path, json_path: Path):
    """Convert customers.csv to customers.json"""
    print(f"Converting {csv_path} to {json_path}...")
    
    rows = load_csv(csv_path)
    
    # Convert to proper format
    customers = []
    for row in rows:
        customer = {
            "customer_id": row["customer_id"],
            "full_name": row["full_name"],
            "email": row["email"],
            "phone": row["phone"]
        }
        customers.append(customer)
    
    # Create JSON structure with metadata
    data = {
        "_metadata": {
            "last_updated": datetime.now().isoformat(),
            "source": "InitialData/customers.csv",
            "description": "Customer information"
        },
        "customers": customers
    }
    
    # Write JSON file
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Created {json_path} with {len(customers)} customers")


def main():
    """Main initialization function"""
    print("=" * 60)
    print("Data Initialization Script")
    print("=" * 60)
    print()
    
    # Get paths
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    initial_data_dir = base_dir / "InitialData"
    dynamic_data_dir = base_dir / "dynamic_data"
    
    # Ensure dynamic_data directory exists
    dynamic_data_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if InitialData exists
    if not initial_data_dir.exists():
        print(f"ERROR: InitialData directory not found at {initial_data_dir}")
        return
    
    # Convert CSVs to JSONs
    try:
        # Accounts
        accounts_csv = initial_data_dir / "accounts.csv"
        accounts_json = dynamic_data_dir / "accounts.json"
        if accounts_csv.exists():
            convert_accounts_csv_to_json(accounts_csv, accounts_json)
        else:
            print(f"WARNING: {accounts_csv} not found")
        
        # Limits
        limits_csv = initial_data_dir / "limits.csv"
        limits_json = dynamic_data_dir / "limits.json"
        if limits_csv.exists():
            convert_limits_csv_to_json(limits_csv, limits_json)
        else:
            print(f"WARNING: {limits_csv} not found")
        
        # Customers
        customers_csv = initial_data_dir / "customers.csv"
        customers_json = dynamic_data_dir / "customers.json"
        if customers_csv.exists():
            convert_customers_csv_to_json(customers_csv, customers_json)
        else:
            print(f"WARNING: {customers_csv} not found")
        
        print()
        print("=" * 60)
        print("✓ Data initialization completed successfully!")
        print("=" * 60)
        print()
        print(f"JSON files created in: {dynamic_data_dir}")
        print("You can now start the MCP server.")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
