"""
Balance Persistence Service

Handles loading and updating account balances:
- Load initial balances from CSV (read-only seed data)
- Load current balances from JSON (read-write)
- Update balances when payments occur
- Save updated balances to JSON
"""

import json
import csv
import logging
from pathlib import Path
from typing import Dict
from decimal import Decimal
import sys

# Add common module to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "common"))
from path_utils import get_csv_data_dir, get_dynamic_data_dir

logger = logging.getLogger(__name__)


class BalancePersistenceService:
    def __init__(self, csv_data_path: Path = None, json_data_path: Path = None):
        """
        Initialize the balance persistence service.
        
        Args:
            csv_data_path: Path to CSV data folder (default: schemas/tools-sandbox/uc1_synthetic_data/)
            json_data_path: Path to JSON data folder (default: dynamic_data/)
        """
        if csv_data_path is None:
            # Use environment-aware path resolution
            csv_data_path = get_csv_data_dir()
        
        if json_data_path is None:
            # Use environment-aware path resolution
            json_data_path = get_dynamic_data_dir()
        
        self.csv_data_path = Path(csv_data_path)
        self.json_data_path = Path(json_data_path)
        
        # Ensure JSON directory exists
        self.json_data_path.mkdir(parents=True, exist_ok=True)
        
        # In-memory storage: account_id -> balance (as float)
        self.balances: Dict[str, float] = {}
        
        # Load balances on initialization
        self._load_balances()
    
    def _load_balances(self):
        """Load balances from CSV (initial) and JSON (current)."""
        logger.info("Loading account balances from CSV and JSON...")
        
        # Load from CSV first (initial balances)
        self._load_from_csv()
        
        # Then override with JSON (current balances if exists)
        self._load_from_json()
        
        logger.info(f"✅ Balances loaded for {len(self.balances)} accounts")
    
    def _load_from_csv(self):
        """Load initial balances from CSV file."""
        csv_file = self.csv_data_path / "accounts.csv"
        
        if not csv_file.exists():
            logger.warning(f"accounts.csv not found at {csv_file}")
            return
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    account_id = row['account_id']
                    available_balance = float(row['available_balance'])
                    
                    self.balances[account_id] = available_balance
            
            logger.info(f"✅ Loaded {len(self.balances)} account balances from CSV: {csv_file}")
            
        except Exception as e:
            logger.error(f"❌ Error loading balances from CSV: {e}", exc_info=True)
    
    def _load_from_json(self):
        """Load current balances from JSON file (overrides CSV)."""
        json_file = self.json_data_path / "account_balances.json"
        
        if not json_file.exists():
            logger.info(f"account_balances.json not found at {json_file} (will be created on first save)")
            return
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # JSON structure: { "CHK-001": 102427.94, "CHK-002": 216483.22, ... }
            for account_id, balance in data.items():
                self.balances[account_id] = float(balance)
            
            logger.info(f"✅ Loaded {len(data)} account balances from JSON: {json_file}")
            
        except Exception as e:
            logger.error(f"❌ Error loading balances from JSON: {e}", exc_info=True)
    
    def _save_to_json(self):
        """Save current balances to JSON file."""
        json_file = self.json_data_path / "account_balances.json"
        
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.balances, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Saved {len(self.balances)} account balances to JSON: {json_file}")
            
        except Exception as e:
            logger.error(f"❌ Error saving balances to JSON: {e}", exc_info=True)
            raise
    
    def get_balance(self, account_id: str) -> float:
        """
        Get current balance for an account.
        
        Args:
            account_id: Account ID
        
        Returns:
            Current balance as float (0.0 if account not found)
        """
        return self.balances.get(account_id, 0.0)
    
    def update_balance(self, account_id: str, amount: float, is_credit: bool = True):
        """
        Update account balance (credit or debit).
        
        Args:
            account_id: Account ID
            amount: Amount to add (credit) or subtract (debit)
            is_credit: True to add, False to subtract
        """
        current_balance = self.get_balance(account_id)
        
        if is_credit:
            new_balance = current_balance + amount
            logger.info(f"Credit: {account_id} balance {current_balance:.2f} + {amount:.2f} = {new_balance:.2f}")
        else:
            new_balance = current_balance - amount
            logger.info(f"Debit: {account_id} balance {current_balance:.2f} - {amount:.2f} = {new_balance:.2f}")
        
        self.balances[account_id] = new_balance
        
        # Save to JSON immediately
        self._save_to_json()
    
    def transfer(self, from_account_id: str, to_account_id: str, amount: float):
        """
        Transfer money between accounts (atomic operation).
        
        Args:
            from_account_id: Source account ID
            to_account_id: Destination account ID
            amount: Amount to transfer
        
        Raises:
            ValueError: If insufficient balance
        """
        from_balance = self.get_balance(from_account_id)
        
        if from_balance < amount:
            raise ValueError(
                f"Insufficient balance. Available: {from_balance:.2f} THB, Required: {amount:.2f} THB"
            )
        
        # Debit from source
        self.update_balance(from_account_id, amount, is_credit=False)
        
        # Credit to destination
        self.update_balance(to_account_id, amount, is_credit=True)
        
        logger.info(f"✅ Transfer complete: {from_account_id} -> {to_account_id}, Amount: {amount:.2f} THB")
    
    def has_sufficient_balance(self, account_id: str, amount: float) -> bool:
        """
        Check if account has sufficient balance.
        
        Args:
            account_id: Account ID
            amount: Required amount
        
        Returns:
            True if sufficient balance, False otherwise
        """
        return self.get_balance(account_id) >= amount
