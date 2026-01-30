"""
Data Loader Service

Handles loading and saving JSON data from dynamic_data folder.
Provides CRUD operations for accounts, limits, and customers.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DataLoaderService:
    """
    Service for loading and persisting data from JSON files.
    
    JSON files are stored in banking-platform/dynamic_data/:
    - accounts.json: Account data with balances
    - limits.json: Transaction limits
    - customers.json: Customer information
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize data loader with path to dynamic_data folder"""
        if data_dir is None:
            # Default: banking-platform/dynamic_data
            self.data_dir = Path(__file__).parent.parent.parent / "dynamic_data"
        else:
            self.data_dir = Path(data_dir)
        
        logger.info(f"DataLoaderService initialized with data_dir: {self.data_dir}")
        
        # Ensure directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.accounts_file = self.data_dir / "accounts.json"
        self.limits_file = self.data_dir / "limits.json"
        self.customers_file = self.data_dir / "customers.json"
        
        # In-memory cache
        self._accounts_cache: Optional[Dict] = None
        self._limits_cache: Optional[Dict] = None
        self._customers_cache: Optional[Dict] = None
    
    
    def _load_json(self, file_path: Path) -> Dict:
        """Load JSON file with error handling"""
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"File not found: {file_path}")
                return {}
        except Exception as e:
            logger.error(f"Error loading {file_path}: {e}")
            return {}
    
    
    def _save_json(self, file_path: Path, data: Dict):
        """Save JSON file with error handling"""
        try:
            # Update metadata timestamp
            if "_metadata" in data:
                data["_metadata"]["last_updated"] = datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved data to {file_path}")
        except Exception as e:
            logger.error(f"Error saving {file_path}: {e}")
    
    
    # ===== Accounts =====
    
    def get_accounts(self) -> List[Dict]:
        """Get all accounts"""
        if self._accounts_cache is None:
            data = self._load_json(self.accounts_file)
            self._accounts_cache = data
        
        return self._accounts_cache.get("accounts", [])
    
    
    def get_account_by_id(self, account_id: str) -> Optional[Dict]:
        """Get account by ID"""
        accounts = self.get_accounts()
        for account in accounts:
            if account.get("account_id") == account_id:
                return account
        return None
    
    
    def get_accounts_by_email(self, email: str) -> List[Dict]:
        """Get accounts by customer email (userName)"""
        accounts = self.get_accounts()
        
        # First find customer by email
        customers = self.get_customers()
        customer_id = None
        for customer in customers:
            if customer.get("email") == email:
                customer_id = customer.get("customer_id")
                break
        
        if not customer_id:
            return []
        
        # Then find accounts for that customer
        result = []
        for account in accounts:
            if account.get("customer_id") == customer_id:
                result.append(account)
        
        return result
    
    
    def update_account_balance(self, account_id: str, new_balance: float):
        """Update account balance"""
        accounts = self.get_accounts()
        
        for account in accounts:
            if account.get("account_id") == account_id:
                account["ledger_balance"] = new_balance
                account["available_balance"] = new_balance
                
                # Save updated data
                if self._accounts_cache:
                    self._accounts_cache["accounts"] = accounts
                    self._save_json(self.accounts_file, self._accounts_cache)
                
                logger.info(f"Updated balance for {account_id}: {new_balance}")
                return
        
        logger.warning(f"Account not found for balance update: {account_id}")
    
    
    # ===== Limits =====
    
    def get_limits(self) -> List[Dict]:
        """Get all limits"""
        if self._limits_cache is None:
            data = self._load_json(self.limits_file)
            self._limits_cache = data
        
        return self._limits_cache.get("limits", [])
    
    
    def get_limit_by_account(self, account_id: str) -> Optional[Dict]:
        """Get limits for specific account"""
        limits = self.get_limits()
        for limit in limits:
            if limit.get("account_id") == account_id:
                return limit
        return None
    
    
    def update_remaining_limit(self, account_id: str, amount: float):
        """Update remaining daily limit after transaction"""
        limits = self.get_limits()
        
        for limit in limits:
            if limit.get("account_id") == account_id:
                current_remaining = limit.get("remaining_today", 0)
                new_remaining = current_remaining - amount
                limit["remaining_today"] = new_remaining
                
                # Save updated data
                if self._limits_cache:
                    self._limits_cache["limits"] = limits
                    self._save_json(self.limits_file, self._limits_cache)
                
                logger.info(f"Updated remaining limit for {account_id}: {new_remaining}")
                return
        
        logger.warning(f"Limits not found for update: {account_id}")
    
    
    # ===== Customers =====
    
    def get_customers(self) -> List[Dict]:
        """Get all customers"""
        if self._customers_cache is None:
            data = self._load_json(self.customers_file)
            self._customers_cache = data
        
        return self._customers_cache.get("customers", [])
    
    
    def get_customer_by_id(self, customer_id: str) -> Optional[Dict]:
        """Get customer by ID"""
        customers = self.get_customers()
        for customer in customers:
            if customer.get("customer_id") == customer_id:
                return customer
        return None
    
    
    def reload_data(self):
        """Reload all data from disk (clears cache)"""
        self._accounts_cache = None
        self._limits_cache = None
        self._customers_cache = None
        logger.info("Data cache cleared, will reload on next access")
