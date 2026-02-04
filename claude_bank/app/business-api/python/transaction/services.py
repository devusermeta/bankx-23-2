from typing import List, Optional, Literal, Dict
from models import Transaction
import logging
import sys
from pathlib import Path

# Add path to common directory for StateManager
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "common"))
from state_manager import get_state_manager

logger = logging.getLogger(__name__)


class TransactionService:
    def __init__(self):
        # Use StateManager instead of TransactionPersistenceService
        self.state = get_state_manager()
        
        # For backward compatibility with old dummy data (account 1010)
        self._add_dummy_data_for_legacy_accounts()
    
    def _add_dummy_data_for_legacy_accounts(self):
        """Add dummy data for legacy account 1010 (backward compatibility)."""
        # Skip dummy data - we're using real CSV/JSON data now
        pass

    def get_transactions_by_recipient_name(self, account_id: str, name: str) -> List[Transaction]:
        logger.info("get_transactions_by_recipient_name called with account_id=%s, name=%s", account_id, name)
        if not account_id:
            raise ValueError("AccountId is empty or null")
        
        # Use StateManager to get all transactions for account
        all_txns = self.state.get_transactions(account_id)
        
        # Filter by recipient name (case-insensitive partial match)
        filtered = []
        for txn in all_txns:
            if name.lower() in txn.get('counterparty_name', '').lower():
                transaction = Transaction(
                    id=txn['txn_id'],
                    description=txn.get('description', ''),
                    type=txn.get('type', ''),
                    recipientName=txn.get('counterparty_name', ''),
                    recipientBankReference=txn.get('counterparty_account_no', ''),
                    accountId=txn['account_id'],
                    paymentType=txn.get('category', ''),
                    amount=float(txn.get('amount', 0)),
                    timestamp=txn.get('timestamp', '')
                )
                filtered.append(transaction)
        
        return filtered

    def get_last_transactions(self, account_id: str, limit: int = 5) -> List[Transaction]:
        logger.info("get_last_transactions called with account_id=%s, limit=%s", account_id, limit)
        if not account_id:
            raise ValueError("AccountId is empty or null")
        
        # Use StateManager to get transactions (sorted by timestamp desc)
        all_txns = self.state.get_transactions(account_id)
        
        # Convert JSON format to Transaction model format
        transactions = []
        for txn in all_txns[:limit]:
            transaction = Transaction(
                id=txn['txn_id'],
                description=txn.get('description', ''),
                type=txn.get('type', ''),
                recipientName=txn.get('counterparty_name', ''),
                recipientBankReference=txn.get('counterparty_account_no', ''),
                accountId=txn['account_id'],
                paymentType=txn.get('category', ''),
                amount=float(txn.get('amount', 0)),
                timestamp=txn.get('timestamp', '')
            )
            transactions.append(transaction)
        
        return transactions

    def notify_transaction(self, account_id: str, transaction: Transaction) -> None:
        logger.info("notify_transaction called with account_id=%s, transaction=%s", account_id, transaction)
        if not account_id:
            raise ValueError("AccountId is empty or null")

        # Use StateManager to add transaction (automatically saves to JSON)
        txn_data = {
            'txn_id': transaction.id,
            'account_id': account_id,
            'timestamp': transaction.timestamp,
            'type': transaction.type,
            'amount': transaction.amount,
            'currency': 'THB',
            'counterparty_name': transaction.recipientName,
            'counterparty_account_no': transaction.recipientBankReference,
            'category': transaction.paymentType,
            'description': transaction.description,
            'status': 'completed'
        }
        self.state.add_transaction(txn_data)

    def search_transactions(
        self,
        account_id: str,
        from_date: str,
        to_date: str
    ) -> List[Transaction]:
        """
        Search transactions by date range.

        Args:
            account_id: Account ID to search
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of transactions in the date range
        """
        logger.info(
            "search_transactions called with account_id=%s, from_date=%s, to_date=%s",
            account_id, from_date, to_date
        )

        if not account_id:
            raise ValueError("AccountId is empty or null")

        # Use StateManager to get all transactions for account
        all_txns = self.state.get_transactions(account_id)
        
        # Filter by date range in Python
        transactions = []
        for txn in all_txns:
            try:
                # Parse transaction timestamp - extract date part
                txn_timestamp = txn.get('timestamp', '')
                if 'T' in txn_timestamp:
                    txn_date = txn_timestamp.split('T')[0]  # Get YYYY-MM-DD
                else:
                    txn_date = txn_timestamp
                
                # Check if in date range
                if from_date <= txn_date <= to_date:
                    transaction = Transaction(
                        id=txn['txn_id'],
                        description=txn.get('description', ''),
                        type=txn.get('type', ''),
                        recipientName=txn.get('counterparty_name', ''),
                        recipientBankReference=txn.get('counterparty_account_no', ''),
                        accountId=txn['account_id'],
                        paymentType=txn.get('category', ''),
                        amount=float(txn.get('amount', 0)),
                        timestamp=txn.get('timestamp', '')
                    )
                    transactions.append(transaction)
            except Exception as e:
                logger.warning(f"Error parsing transaction {txn.get('txn_id')}: {e}")
                continue

        logger.info(f"Found {len(transactions)} transactions in date range")
        return transactions

    def get_transaction_details(self, account_id: str, txn_id: str) -> Optional[Transaction]:
        """
        Get details for a specific transaction.

        Args:
            account_id: Account ID (for authorization)
            txn_id: Transaction ID to retrieve

        Returns:
            Transaction object or None if not found
        """
        logger.info(
            "get_transaction_details called with account_id=%s, txn_id=%s",
            account_id, txn_id
        )

        if not account_id:
            raise ValueError("AccountId is empty or null")

        # Get all transactions for account using StateManager
        all_txns = self.state.get_transactions(account_id)

        # Find transaction by ID and convert to Transaction model
        for txn in all_txns:
            if txn.get('txn_id') == txn_id:
                logger.info(f"Found transaction {txn_id}")
                transaction = Transaction(
                    id=txn['txn_id'],
                    description=txn.get('description', ''),
                    type=txn.get('type', ''),
                    recipientName=txn.get('counterparty_name', ''),
                    recipientBankReference=txn.get('counterparty_account_no', ''),
                    accountId=txn['account_id'],
                    paymentType=txn.get('category', ''),
                    amount=float(txn.get('amount', 0)),
                    timestamp=txn.get('timestamp', '')
                )
                return transaction

        logger.warning(f"Transaction {txn_id} not found for account {account_id}")
        return None

    def aggregate_transactions(
        self,
        account_id: str,
        from_date: str,
        to_date: str,
        metric_type: Literal["COUNT", "SUM_IN", "SUM_OUT", "NET"]
    ) -> Dict:
        """
        Aggregate transactions by metric type.

        Args:
            account_id: Account ID
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            metric_type: Type of aggregation (COUNT, SUM_IN, SUM_OUT, NET)

        Returns:
            Dict with aggregation results
        """
        logger.info(
            "aggregate_transactions called with account_id=%s, from_date=%s, to_date=%s, metric_type=%s",
            account_id, from_date, to_date, metric_type
        )

        # Get transactions in date range
        transactions = self.search_transactions(account_id, from_date, to_date)

        # Calculate metrics
        total_count = len(transactions)
        inbound_transactions = [t for t in transactions if t.type == "income"]
        outbound_transactions = [t for t in transactions if t.type == "outcome"]

        sum_in = sum(t.amount for t in inbound_transactions)
        sum_out = sum(t.amount for t in outbound_transactions)
        net = sum_in - sum_out

        # Determine value based on metric type
        value_map = {
            "COUNT": total_count,
            "SUM_IN": sum_in,
            "SUM_OUT": sum_out,
            "NET": net
        }

        value = value_map.get(metric_type, 0)

        result = {
            "metric_type": metric_type,
            "value": value,
            "total_transactions": total_count,
            "inbound_transactions": len(inbound_transactions),
            "outbound_transactions": len(outbound_transactions),
            "sum_in": sum_in,
            "sum_out": sum_out,
            "net": net,
            "transactions": [t.id for t in transactions]  # Transaction IDs for reference
        }

        logger.info(f"Aggregation result: {metric_type} = {value}")
        return result

# create a single service instance (in-memory sample data lives here)
transaction_service_singleton = TransactionService()