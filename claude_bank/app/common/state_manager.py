"""
State Manager for UC1 - JSON-based persistent storage

This module provides thread-safe read/write operations for:
- accounts.json
- limits.json  
- transactions.json
- contacts.json
- customers.json

Features:
- File locking for concurrent access
- Atomic read-modify-write operations
- Auto-regeneration from CSV if JSON missing
- Metadata tracking
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import threading
from filelock import FileLock
import csv
import logging

logger = logging.getLogger(__name__)

# Import path utilities for environment-aware path resolution
from .path_utils import get_base_dir, get_dynamic_data_dir, get_csv_data_dir

# Base paths using environment-aware resolution
PROJECT_ROOT = get_base_dir()
DYNAMIC_DATA_DIR = get_dynamic_data_dir()
CSV_SEED_DIR = get_csv_data_dir()

# Ensure dynamic_data directory exists
DYNAMIC_DATA_DIR.mkdir(parents=True, exist_ok=True)

class StateManager:
    """Thread-safe state manager for JSON storage"""
    
    def __init__(self):
        self._locks = {
            "accounts": threading.RLock(),
            "limits": threading.RLock(),
            "transactions": threading.RLock(),
            "contacts": threading.RLock(),
            "customers": threading.RLock(),
        }
    
    def _get_json_path(self, entity: str) -> Path:
        """Get path to JSON file"""
        return DYNAMIC_DATA_DIR / f"{entity}.json"
    
    def _get_lock_path(self, entity: str) -> Path:
        """Get path to lock file"""
        return DYNAMIC_DATA_DIR / f"{entity}.json.lock"
    
    def _read_json(self, entity: str) -> Dict:
        """Read JSON file with locking"""
        json_path = self._get_json_path(entity)
        lock_path = self._get_lock_path(entity)
        
        # Check if JSON exists, if not regenerate from CSV
        if not json_path.exists():
            print(f"⚠️  {entity}.json not found, regenerating from CSV...")
            self._regenerate_from_csv(entity)
        
        with FileLock(str(lock_path), timeout=10):
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    
    def _write_json(self, entity: str, data: Dict):
        """Write JSON file with locking and atomic operation"""
        json_path = self._get_json_path(entity)
        lock_path = self._get_lock_path(entity)
        temp_path = json_path.with_suffix('.tmp')
        
        # Update metadata
        if "_metadata" in data:
            data["_metadata"]["last_updated"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00")
        
        with FileLock(str(lock_path), timeout=10):
            # Write to temp file first
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_path.replace(json_path)
    
    def _regenerate_from_csv(self, entity: str):
        """Regenerate JSON from CSV seed data"""
        print(f"🔄 Regenerating {entity}.json from CSV...")
        
        if entity == "accounts":
            self._regenerate_accounts()
        elif entity == "limits":
            self._regenerate_limits()
        elif entity == "transactions":
            self._regenerate_transactions()
        elif entity == "contacts":
            self._regenerate_contacts()
        elif entity == "customers":
            self._regenerate_customers()
        
        print(f"✅ {entity}.json regenerated successfully")
    
    def _regenerate_accounts(self):
        """Regenerate accounts.json from CSV"""
        csv_path = CSV_SEED_DIR / "accounts.csv"
        accounts = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                accounts.append({
                    "account_id": row["account_id"],
                    "customer_id": row["customer_id"],
                    "account_no": row["account_no"],
                    "cust_name": row["cust_name"],
                    "acc_type": row["acc_type"],
                    "currency": row["currency"],
                    "ledger_balance": float(row["ledger_balance"]),
                    "available_balance": float(row["available_balance"])
                })
        
        data = {
            "_metadata": {
                "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                "source": "uc1_synthetic_data/accounts.csv",
                "description": "Runtime account balances - updated on each transfer"
            },
            "accounts": accounts
        }
        
        self._write_json("accounts", data)
    
    def _regenerate_limits(self):
        """Regenerate limits.json from CSV"""
        csv_path = CSV_SEED_DIR / "limits.csv"
        limits = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                limits.append({
                    "account_id": row["account_id"],
                    "per_txn_limit": float(row["per_txn_limit"]),
                    "daily_limit": float(row["daily_limit"]),
                    "remaining_today": float(row["remaining_today"]),
                    "currency": row["currency"]
                })
        
        data = {
            "_metadata": {
                "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                "source": "uc1_synthetic_data/limits.csv",
                "description": "Runtime transfer limits - remaining_today updated on each transfer"
            },
            "limits": limits
        }
        
        self._write_json("limits", data)
    
    def _regenerate_transactions(self):
        """Regenerate transactions.json from CSV"""
        csv_path = CSV_SEED_DIR / "transactions.csv"
        transactions = []
        last_txn_id = "T000000"
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                transactions.append({
                    "txn_id": row["txn_id"],
                    "account_id": row["account_id"],
                    "timestamp": row["timestamp"],
                    "amount": float(row["amount"]),
                    "type": row["type"],
                    "description": row["description"],
                    "category": row["category"],
                    "status": row["status"],
                    "counterparty_name": row["counterparty_name"],
                    "counterparty_account_no": row["counterparty_account_no"],
                    "currency": row["currency"]
                })
                last_txn_id = row["txn_id"]
        
        # Calculate next transaction ID
        next_num = int(last_txn_id[1:]) + 1
        next_txn_id = f"T{next_num:06d}"
        
        data = {
            "_metadata": {
                "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                "source": "uc1_synthetic_data/transactions.csv",
                "description": "Transaction history - new transactions appended at runtime",
                "last_txn_id": last_txn_id,
                "next_txn_id": next_txn_id
            },
            "transactions": transactions
        }
        
        self._write_json("transactions", data)
    
    def _regenerate_customers(self):
        """Regenerate customers.json from CSV"""
        csv_path = CSV_SEED_DIR / "customers.csv"
        customers = []
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                customers.append({
                    "customer_id": row["customer_id"],
                    "full_name": row["full_name"],
                    "email": row["email"],
                    "phone": row["phone"]
                })
        
        data = {
            "_metadata": {
                "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                "source": "uc1_synthetic_data/customers.csv",
                "description": "Customer master data - read-only"
            },
            "customers": customers
        }
        
        self._write_json("customers", data)
    
    def _regenerate_contacts(self):
        """Regenerate contacts.json from CSV"""
        csv_path = CSV_SEED_DIR / "contacts.csv"
        contacts_dict = {}
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                owner = row["owner_customer_id"]
                if owner not in contacts_dict:
                    contacts_dict[owner] = []
                
                contacts_dict[owner].append({
                    "name": row["name"],
                    "account_no": row["account_no"],
                    "alias": row["alias"]
                })
        
        data = {
            "_metadata": {
                "last_updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+07:00"),
                "source": "uc1_synthetic_data/contacts.csv",
                "description": "Registered beneficiaries - can be extended at runtime"
            },
            "contacts": contacts_dict
        }
        
        self._write_json("contacts", data)
    
    # Public API methods
    
    def get_accounts(self) -> List[Dict]:
        """Get all accounts"""
        data = self._read_json("accounts")
        return data.get("accounts", [])
    
    def get_account_by_id(self, account_id: str) -> Optional[Dict]:
        """Get account by ID"""
        accounts = self.get_accounts()
        for acc in accounts:
            if acc["account_id"] == account_id:
                return acc
        return None
    
    def update_account_balance(self, account_id: str, new_balance: float):
        """Update account balance atomically"""
        data = self._read_json("accounts")
        
        for acc in data["accounts"]:
            if acc["account_id"] == account_id:
                acc["ledger_balance"] = new_balance
                acc["available_balance"] = new_balance
                break
        
        self._write_json("accounts", data)
    
    def get_limits(self) -> List[Dict]:
        """Get all limits (automatically resets daily limits if new day)"""
        # Check and reset daily limits if it's a new day
        self.check_and_reset_daily_limits()
        
        data = self._read_json("limits")
        return data.get("limits", [])
    
    def get_limit_by_account(self, account_id: str) -> Optional[Dict]:
        """Get limit by account ID (automatically resets daily limits if new day)"""
        # Check and reset daily limits if it's a new day
        self.check_and_reset_daily_limits()
        
        limits = self.get_limits()
        for lim in limits:
            if lim["account_id"] == account_id:
                return lim
        return None
    
    def update_remaining_limit(self, account_id: str, new_remaining: float):
        """Update remaining daily limit atomically"""
        data = self._read_json("limits")
        
        for lim in data["limits"]:
            if lim["account_id"] == account_id:
                lim["remaining_today"] = new_remaining
                break
        
        # Update timestamp
        data["_metadata"]["last_updated"] = datetime.now().astimezone().isoformat()
        
        self._write_json("limits", data)
    
    def check_and_reset_daily_limits(self):
        """
        Check if daily limits need to be reset (new day).
        Resets all remaining_today to daily_limit if date has changed.
        
        This method should be called:
        - When limits are read (get_limit_by_account)
        - After any transaction is processed
        """
        data = self._read_json("limits")
        
        # Get last updated date from metadata
        last_updated = data["_metadata"].get("last_updated", "")
        
        try:
            # Parse last updated date (handle timezone-aware ISO format)
            if last_updated:
                last_date = datetime.fromisoformat(last_updated).date()
            else:
                # No last_updated, assume old data
                last_date = None
            
            current_date = datetime.now().date()
            
            # Check if it's a new day
            if last_date is None or current_date > last_date:
                logger.info(f"🔄 [LIMITS RESET] New day detected! Last reset: {last_date}, Current: {current_date}")
                logger.info(f"🔄 [LIMITS RESET] Resetting daily limits for all accounts...")
                
                # Reset all remaining_today to daily_limit
                reset_count = 0
                for lim in data["limits"]:
                    old_remaining = lim.get("remaining_today", 0)
                    lim["remaining_today"] = lim["daily_limit"]
                    reset_count += 1
                    logger.info(f"   ✅ Reset {lim['account_id']}: {old_remaining} → {lim['daily_limit']}")
                
                # Update metadata with current timestamp
                data["_metadata"]["last_updated"] = datetime.now().astimezone().isoformat()
                
                # Write updated data
                self._write_json("limits", data)
                
                logger.info(f"🎉 [LIMITS RESET] Successfully reset {reset_count} account limits!")
                return True
            else:
                logger.debug(f"✅ [LIMITS CHECK] Limits are current. Last reset: {last_date}")
                return False
                
        except Exception as e:
            logger.error(f"❌ [LIMITS RESET] Error checking/resetting limits: {e}")
            return False
    
    def get_transactions(self, account_id: Optional[str] = None) -> List[Dict]:
        """Get all transactions, optionally filtered by account, sorted by timestamp descending (newest first)"""
        data = self._read_json("transactions")
        transactions = data.get("transactions", [])
        
        logger.info(f"📊 StateManager loaded {len(transactions)} total transactions from JSON")
        
        # Filter by account if specified
        if account_id:
            transactions = [txn for txn in transactions if txn["account_id"] == account_id]
            logger.info(f"📊 Filtered to {len(transactions)} transactions for account {account_id}")
            if transactions:
                logger.info(f"📊 Latest transaction for {account_id}: {transactions[0].get('txn_id')} at {transactions[0].get('timestamp')}")
        
        # Sort by timestamp descending (newest first)
        # Handle both ISO format timestamps and simple date strings
        try:
            transactions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        except Exception as e:
            logger.warning(f"Could not sort transactions by timestamp: {e}")
        
        return transactions
    
    def add_transaction(self, transaction: Dict) -> str:
        """Add new transaction and return transaction ID"""
        data = self._read_json("transactions")
        
        # Get next transaction ID
        next_txn_id = data["_metadata"]["next_txn_id"]
        transaction["txn_id"] = next_txn_id
        
        # Add transaction
        data["transactions"].append(transaction)
        
        # Update metadata
        next_num = int(next_txn_id[1:]) + 1
        data["_metadata"]["last_txn_id"] = next_txn_id
        data["_metadata"]["next_txn_id"] = f"T{next_num:06d}"
        
        self._write_json("transactions", data)
        return next_txn_id
    
    def get_contacts(self, customer_id: str) -> List[Dict]:
        """Get contacts for a customer"""
        data = self._read_json("contacts")
        return data.get("contacts", {}).get(customer_id, [])
    
    def get_customers(self) -> List[Dict]:
        """Get all customers"""
        data = self._read_json("customers")
        return data.get("customers", [])
    
    def get_customer_by_email(self, email: str) -> Optional[Dict]:
        """
        Get customer by email.
        Searches both 'email' and 'bankx_email' fields.
        """
        customers = self.get_customers()
        email_lower = email.lower()
        for cust in customers:
            # Check regular email
            if cust["email"].lower() == email_lower:
                return cust
            # Check bankx_email (Entra ID email)
            if "bankx_email" in cust and cust["bankx_email"].lower() == email_lower:
                return cust
        return None


# Global singleton instance
_state_manager = None

def get_state_manager() -> StateManager:
    """Get global StateManager instance"""
    global _state_manager
    if _state_manager is None:
        _state_manager = StateManager()
    return _state_manager
