"""
Limits Persistence Service

Manages loading and persisting account transaction limits.
Supports both CSV-based initial data and JSON-based runtime updates.
"""

import csv
import json
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class LimitsPersistenceService:
    """
    Manages account limits data with persistence.

    Data flow:
    1. Load initial limits from CSV (limits.csv)
    2. Load runtime updates from JSON (data/limits_updates.json)
    3. Merge CSV + JSON (JSON overrides CSV)
    4. Save updates to JSON when limits change (e.g., after transactions)

    This mirrors the pattern used in BalancePersistenceService.
    """

    def __init__(self):
        """Initialize persistence service and load data."""
        # Add common module to path
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "common"))
        from path_utils import get_csv_data_dir
        
        # Use environment-aware path resolution
        self.data_path = get_csv_data_dir()
        self.limits_csv_path = self.data_path / "limits.csv"

        # Path to runtime updates
        self.runtime_data_path = Path(__file__).parent / "data"
        self.limits_json_path = self.runtime_data_path / "limits_updates.json"

        # In-memory storage: account_id -> limits dict
        self.limits: Dict[str, Dict] = {}

        # Default limits (fallback if no CSV data)
        self.default_per_txn_limit = 50000.00
        self.default_daily_limit = 200000.00

        # Load data
        self._load_from_csv()
        self._load_from_json()

        logger.info(f"LimitsPersistenceService initialized: {len(self.limits)} accounts with limits")


    def _load_from_csv(self):
        """
        Load initial limits from CSV.

        CSV format: account_id,per_txn_limit,daily_limit,remaining_today,currency
        """
        if not self.limits_csv_path.exists():
            logger.warning(f"limits.csv not found at {self.limits_csv_path}. Using defaults.")
            return

        try:
            with open(self.limits_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    account_id = row['account_id']
                    self.limits[account_id] = {
                        'account_id': account_id,
                        'per_txn_limit': float(row['per_txn_limit']),
                        'daily_limit': float(row['daily_limit']),
                        'remaining_today': float(row['remaining_today']),
                        'currency': row.get('currency', 'THB')
                    }

            logger.info(f"Loaded limits for {len(self.limits)} accounts from CSV")

        except Exception as e:
            logger.error(f"Error loading limits from CSV: {e}")


    def _load_from_json(self):
        """
        Load runtime updates from JSON.

        JSON overrides CSV data for accounts that have updates.
        """
        if not self.limits_json_path.exists():
            logger.info("No runtime limits updates found (limits_updates.json)")
            return

        try:
            with open(self.limits_json_path, 'r', encoding='utf-8') as f:
                updates = json.load(f)

            # Merge updates into limits
            for account_id, limit_data in updates.items():
                self.limits[account_id] = limit_data

            logger.info(f"Loaded {len(updates)} runtime limit updates from JSON")

        except Exception as e:
            logger.error(f"Error loading limits from JSON: {e}")


    def _save_to_json(self):
        """
        Save current limits to JSON.

        Only saves accounts that differ from CSV (i.e., have been updated).
        """
        # Ensure data directory exists
        self.runtime_data_path.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.limits_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.limits, f, indent=2)

            logger.info(f"Saved limits for {len(self.limits)} accounts to JSON")

        except Exception as e:
            logger.error(f"Error saving limits to JSON: {e}")


    def get_limits(self, account_id: str) -> Optional[Dict]:
        """
        Get limits for an account.

        Args:
            account_id: Account ID (e.g., "CHK-001")

        Returns:
            Limits dict or None if not found (will use defaults)
        """
        return self.limits.get(account_id)


    def get_limits_or_default(self, account_id: str, currency: str = "THB") -> Dict:
        """
        Get limits for an account, or return default limits if not found.

        Args:
            account_id: Account ID
            currency: Currency code (default: THB)

        Returns:
            Limits dict (never None)
        """
        limits = self.get_limits(account_id)

        if limits:
            return limits

        # Return default limits
        logger.info(f"Using default limits for account {account_id}")
        return {
            'account_id': account_id,
            'per_txn_limit': self.default_per_txn_limit,
            'daily_limit': self.default_daily_limit,
            'remaining_today': self.default_daily_limit,
            'currency': currency
        }


    def update_remaining_limit(self, account_id: str, amount: float):
        """
        Update remaining daily limit after a transaction.

        Called by Payment Service after successful payment.

        Args:
            account_id: Account ID
            amount: Transaction amount (positive value)
        """
        limits = self.get_limits_or_default(account_id)

        # Deduct from remaining
        limits['remaining_today'] = max(0, limits['remaining_today'] - amount)

        # Update in memory
        self.limits[account_id] = limits

        # Persist to JSON
        self._save_to_json()

        logger.info(f"Updated limits for {account_id}: remaining={limits['remaining_today']}")


    def reset_daily_limits(self):
        """
        Reset all daily limits to full amount.

        This would be called by a scheduled job at midnight (not implemented yet).
        For now, limits persist across sessions.
        """
        for account_id, limits in self.limits.items():
            limits['remaining_today'] = limits['daily_limit']

        self._save_to_json()
        logger.info("Reset all daily limits")


# Singleton instance
limits_persistence_service = LimitsPersistenceService()
