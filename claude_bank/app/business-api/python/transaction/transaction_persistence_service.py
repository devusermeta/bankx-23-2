"""
Transaction Persistence Service

Handles loading and saving transactions:
- Load historical transactions from CSV (read-only)
- Load dynamic transactions from JSON (read-write)
- Save new transactions to JSON
- Merge both sources for complete history
"""

import json
import csv
import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from models import Transaction

logger = logging.getLogger(__name__)


class TransactionPersistenceService:
    def __init__(self, csv_data_path: Path = None, json_data_path: Path = None):
        """
        Initialize the transaction persistence service.
        
        Args:
            csv_data_path: Path to CSV data folder (default: schemas/tools-sandbox/uc1_synthetic_data/)
            json_data_path: Path to JSON data folder (default: dynamic_data/)
        """
        # Add common module to path if not already
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "common"))
        from path_utils import get_csv_data_dir, get_dynamic_data_dir
        
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
        
        # In-memory storage: account_id -> List[Transaction]
        self.transactions: Dict[str, List[Transaction]] = {}
        
        # Track last transaction ID for sequence generation
        self.last_transaction_id = 0
        
        # Load transactions on initialization
        self._load_transactions()
    
    def _load_transactions(self):
        """Load transactions from CSV (historical) and JSON (dynamic)."""
        logger.info("Loading transactions from CSV and JSON...")
        
        # Load from CSV first (historical data)
        self._load_from_csv()
        
        # Then load from JSON (runtime additions)
        self._load_from_json()
        
        logger.info(f"✅ Transactions loaded. Total accounts: {len(self.transactions)}")
        for account_id, txns in self.transactions.items():
            logger.info(f"   {account_id}: {len(txns)} transactions")
    
    def _load_from_csv(self):
        """Load historical transactions from CSV file."""
        csv_file = self.csv_data_path / "transactions.csv"
        
        if not csv_file.exists():
            logger.warning(f"transactions.csv not found at {csv_file}")
            return
        
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    account_id = row['account_id']
                    
                    # Parse transaction
                    transaction = Transaction(
                        id=row['txn_id'],
                        description=row['description'],
                        type=row['type'],  # 'income' or 'outcome'
                        recipientName=row['counterparty_name'],
                        recipientBankReference=row['counterparty_account_no'],
                        accountId=account_id,
                        paymentType=row['category'],
                        amount=float(row['amount']),
                        timestamp=row['timestamp']
                    )
                    
                    # Add to in-memory storage
                    if account_id not in self.transactions:
                        self.transactions[account_id] = []
                    
                    self.transactions[account_id].append(transaction)
                    
                    # Track max transaction ID for sequence
                    # Extract numeric part from T000123 -> 123
                    try:
                        txn_num = int(row['txn_id'][1:])  # Remove 'T' prefix
                        if txn_num > self.last_transaction_id:
                            self.last_transaction_id = txn_num
                    except ValueError:
                        pass
            
            logger.info(f"✅ Loaded transactions from CSV: {csv_file}")
            
        except Exception as e:
            logger.error(f"❌ Error loading transactions from CSV: {e}", exc_info=True)
    
    def _load_from_json(self):
        """Load dynamic transactions from JSON file."""
        json_file = self.json_data_path / "transactions.json"
        
        if not json_file.exists():
            logger.info(f"transactions.json not found at {json_file} (will be created on first save)")
            return
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle new JSON structure: { "_metadata": {...}, "transactions": [...] }
            if "transactions" in data and isinstance(data["transactions"], list):
                # New format: array of transactions with account_id field
                logger.info(f"Loading transactions from new JSON format (array structure)")
                for txn_dict in data["transactions"]:
                    account_id = txn_dict.get("account_id")
                    if not account_id:
                        continue
                    
                    if account_id not in self.transactions:
                        self.transactions[account_id] = []
                    
                    # Map JSON fields to Transaction model
                    transaction = Transaction(
                        id=txn_dict['txn_id'],
                        description=txn_dict.get('description', ''),
                        type=txn_dict.get('type', ''),
                        recipientName=txn_dict.get('counterparty_name', ''),
                        recipientBankReference=txn_dict.get('counterparty_account_no', ''),
                        accountId=txn_dict['account_id'],
                        paymentType=txn_dict.get('category', ''),
                        amount=float(txn_dict.get('amount', 0)),
                        timestamp=txn_dict.get('timestamp', '')
                    )
                    self.transactions[account_id].append(transaction)
                    
                    # Track max transaction ID
                    try:
                        txn_num = int(transaction.id[1:])  # Remove 'T' prefix
                        if txn_num > self.last_transaction_id:
                            self.last_transaction_id = txn_num
                    except ValueError:
                        pass
                
                # Update last_txn_id from metadata if available
                if "_metadata" in data and "last_txn_id" in data["_metadata"]:
                    try:
                        last_id = data["_metadata"]["last_txn_id"]
                        txn_num = int(last_id[1:])  # Remove 'T' prefix
                        if txn_num > self.last_transaction_id:
                            self.last_transaction_id = txn_num
                    except (ValueError, IndexError):
                        pass
            else:
                # Old format: { "CHK-001": [...transactions...], "CHK-002": [...] }
                logger.info(f"Loading transactions from old JSON format (per-account structure)")
                for account_id, txn_list in data.items():
                    if account_id.startswith("_"):  # Skip metadata keys
                        continue
                    
                    if account_id not in self.transactions:
                        self.transactions[account_id] = []
                    
                    for txn_data in txn_list:
                        transaction = Transaction(**txn_data)
                        self.transactions[account_id].append(transaction)
                        
                        # Track max transaction ID
                        try:
                            txn_num = int(transaction.id[1:])  # Remove 'T' prefix
                            if txn_num > self.last_transaction_id:
                                self.last_transaction_id = txn_num
                        except ValueError:
                            pass
            
            logger.info(f"✅ Loaded transactions from JSON: {json_file}")
            
        except Exception as e:
            logger.error(f"❌ Error loading transactions from JSON: {e}", exc_info=True)
    
    def _save_to_json(self):
        """Save dynamic transactions (new ones) to JSON file."""
        json_file = self.json_data_path / "transactions.json"
        
        try:
            # Load existing JSON transactions first
            existing_json_transactions = {}
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    existing_json_transactions = json.load(f)
            
            # Prepare data for JSON (only transactions not in CSV)
            json_data = {}
            
            # For now, save all transactions to JSON for simplicity
            # In production, you might want to only save new ones
            for account_id, txns in self.transactions.items():
                json_data[account_id] = [txn.model_dump() for txn in txns]
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Saved transactions to JSON: {json_file}")
            
        except Exception as e:
            logger.error(f"❌ Error saving transactions to JSON: {e}", exc_info=True)
            raise
    
    def generate_transaction_id(self) -> str:
        """Generate next transaction ID in sequence (T000496, T000497, etc.)."""
        self.last_transaction_id += 1
        return f"T{self.last_transaction_id:06d}"
    
    def add_transaction(self, transaction: Transaction):
        """
        Add a new transaction and save to JSON.
        
        Args:
            transaction: Transaction object to add
        """
        account_id = transaction.accountId
        
        if account_id not in self.transactions:
            self.transactions[account_id] = []
        
        self.transactions[account_id].append(transaction)
        
        # Save to JSON immediately
        self._save_to_json()
        
        logger.info(f"✅ Added transaction {transaction.id} for account {account_id}")
    
    def get_transactions(self, account_id: str, limit: int = None) -> List[Transaction]:
        """
        Get all transactions for an account (merged CSV + JSON).
        
        Args:
            account_id: Account ID
            limit: Maximum number of transactions to return (most recent first)
        
        Returns:
            List of Transaction objects, sorted by timestamp descending
        """
        if account_id not in self.transactions:
            return []
        
        # Sort by timestamp descending (most recent first)
        sorted_txns = sorted(
            self.transactions[account_id],
            key=lambda t: t.timestamp,
            reverse=True
        )
        
        if limit:
            return sorted_txns[:limit]
        
        return sorted_txns
    
    def get_transactions_by_recipient(self, account_id: str, recipient_name: str) -> List[Transaction]:
        """
        Get transactions for a specific recipient.
        
        Args:
            account_id: Account ID
            recipient_name: Recipient name to filter by
        
        Returns:
            List of Transaction objects matching the recipient
        """
        if account_id not in self.transactions:
            return []
        
        # Filter by recipient name (case-insensitive)
        filtered = [
            txn for txn in self.transactions[account_id]
            if recipient_name.lower() in txn.recipientName.lower()
        ]
        
        # Sort by timestamp descending
        return sorted(filtered, key=lambda t: t.timestamp, reverse=True)
