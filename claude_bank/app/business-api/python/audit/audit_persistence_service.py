"""
Audit Persistence Service

Manages storing and retrieving audit logs and decision ledger entries.
Currently uses JSON for storage, can be upgraded to Cosmos DB for production.
"""

import json
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from models import DecisionLedgerEntry, AgentInteractionLog, DecisionAuditTrail

logger = logging.getLogger(__name__)


class AuditPersistenceService:
    """
    Manages audit logs with persistence.

    Data flow:
    1. Agents log decisions via logDecision MCP tool
    2. Entries stored in JSON (decision_ledger.json)
    3. Teller queries via getTellerDashboard tools
    4. Future: Migrate to Cosmos DB for production

    This provides:
    - Decision Ledger (US 1.A1-1.A3)
    - Teller Dashboard queries (US 1.T1-1.T5)
    """

    def __init__(self):
        """Initialize persistence service."""
        # Path to runtime data
        self.data_path = Path(__file__).parent / "data"
        self.ledger_json_path = self.data_path / "decision_ledger.json"

        # In-memory storage: list of decision ledger entries
        self.ledger_entries: List[Dict] = []

        # Load existing data
        self._load_from_json()

        logger.info(f"AuditPersistenceService initialized: {len(self.ledger_entries)} entries loaded")


    def _load_from_json(self):
        """Load decision ledger entries from JSON."""
        if not self.ledger_json_path.exists():
            logger.info("No existing decision_ledger.json found (will create on first save)")
            return

        try:
            with open(self.ledger_json_path, 'r', encoding='utf-8') as f:
                self.ledger_entries = json.load(f)

            logger.info(f"Loaded {len(self.ledger_entries)} ledger entries from JSON")

        except Exception as e:
            logger.error(f"Error loading ledger from JSON: {e}")


    def _save_to_json(self):
        """Save decision ledger entries to JSON."""
        # Ensure data directory exists
        self.data_path.mkdir(parents=True, exist_ok=True)

        try:
            with open(self.ledger_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.ledger_entries, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(self.ledger_entries)} ledger entries to JSON")

        except Exception as e:
            logger.error(f"Error saving ledger to JSON: {e}")


    def add_ledger_entry(self, entry: DecisionLedgerEntry) -> str:
        """
        Add a new decision ledger entry.

        Args:
            entry: DecisionLedgerEntry to add

        Returns:
            ledger_id of the added entry
        """
        # Convert to dict and add to in-memory storage
        entry_dict = entry.model_dump()
        self.ledger_entries.append(entry_dict)

        # Persist to JSON
        self._save_to_json()

        logger.info(f"Added ledger entry: {entry.ledger_id} ({entry.action})")
        return entry.ledger_id


    def get_ledger_entry(self, ledger_id: str) -> Optional[Dict]:
        """
        Get a specific ledger entry by ID.

        Args:
            ledger_id: Ledger entry ID

        Returns:
            Ledger entry dict or None if not found
        """
        for entry in self.ledger_entries:
            if entry['ledger_id'] == ledger_id:
                return entry
        return None


    def get_entries_by_customer(self, customer_id: str, limit: int = 50) -> List[Dict]:
        """
        Get ledger entries for a specific customer.

        Args:
            customer_id: Customer ID
            limit: Maximum number of entries to return

        Returns:
            List of ledger entries (most recent first)
        """
        customer_entries = [
            entry for entry in self.ledger_entries
            if entry.get('customer_id') == customer_id
        ]

        # Sort by timestamp descending (most recent first)
        customer_entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return customer_entries[:limit]


    def get_entries_by_conversation(self, conversation_id: str) -> List[Dict]:
        """
        Get all ledger entries for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of ledger entries (chronological order)
        """
        conversation_entries = [
            entry for entry in self.ledger_entries
            if entry.get('conversation_id') == conversation_id
        ]

        # Sort by timestamp ascending (chronological order)
        conversation_entries.sort(key=lambda x: x.get('timestamp', ''))

        return conversation_entries


    def get_entries_by_action(self, action: str, limit: int = 50) -> List[Dict]:
        """
        Get ledger entries for a specific action type.

        Args:
            action: Action name (e.g., "TRANSFER", "VIEW_TRANSACTIONS")
            limit: Maximum number of entries to return

        Returns:
            List of ledger entries (most recent first)
        """
        action_entries = [
            entry for entry in self.ledger_entries
            if entry.get('action') == action
        ]

        # Sort by timestamp descending
        action_entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        return action_entries[:limit]


    def search_entries(
        self,
        customer_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        action: Optional[str] = None,
        from_timestamp: Optional[str] = None,
        to_timestamp: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search ledger entries with filters.

        Used by teller dashboard for US 1.T5.

        Args:
            customer_id: Filter by customer
            agent_name: Filter by agent
            action: Filter by action
            from_timestamp: Start date/time (ISO 8601)
            to_timestamp: End date/time (ISO 8601)
            limit: Maximum number of results

        Returns:
            List of matching ledger entries (most recent first)
        """
        results = self.ledger_entries

        # Apply filters
        if customer_id:
            results = [e for e in results if e.get('customer_id') == customer_id]

        if agent_name:
            results = [e for e in results if e.get('agent_name') == agent_name]

        if action:
            results = [e for e in results if e.get('action') == action]

        if from_timestamp:
            results = [e for e in results if e.get('timestamp', '') >= from_timestamp]

        if to_timestamp:
            results = [e for e in results if e.get('timestamp', '') <= to_timestamp]

        # Sort by timestamp descending
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        logger.info(f"Search found {len(results)} entries (returning {min(len(results), limit)})")
        return results[:limit]


    def get_agent_interactions(self, customer_id: str, limit: int = 50) -> List[AgentInteractionLog]:
        """
        Get agent interaction logs for teller dashboard (US 1.T3).

        Args:
            customer_id: Customer ID
            limit: Maximum number of interactions

        Returns:
            List of AgentInteractionLog models
        """
        entries = self.get_entries_by_customer(customer_id, limit)

        interactions = []
        for entry in entries:
            interactions.append(AgentInteractionLog(
                interaction_id=entry.get('ledger_id', ''),
                conversation_id=entry.get('conversation_id', ''),
                customer_id=entry.get('customer_id', ''),
                agent_name=entry.get('agent_name', ''),
                action=entry.get('action', ''),
                timestamp=entry.get('timestamp', ''),
                input_summary=str(entry.get('input', {}))[:200],  # Truncate
                output_summary=str(entry.get('output', {}))[:200],  # Truncate
                success=entry.get('output', {}).get('type') != 'ERROR_CARD',
                error_message=entry.get('output', {}).get('message') if entry.get('output', {}).get('type') == 'ERROR_CARD' else None
            ))

        return interactions


    def get_decision_audit_trail(self, customer_id: str, limit: int = 50) -> List[DecisionAuditTrail]:
        """
        Get decision audit trail for teller dashboard (US 1.T4).

        Args:
            customer_id: Customer ID
            limit: Maximum number of decisions

        Returns:
            List of DecisionAuditTrail models
        """
        entries = self.get_entries_by_customer(customer_id, limit)

        audit_trail = []
        for entry in entries:
            policy_evals = []
            if entry.get('policy_evaluation'):
                policy_evals.append(entry['policy_evaluation'])

            approval_status = None
            if entry.get('approval'):
                approval_status = entry['approval'].get('approval_action')

            audit_trail.append(DecisionAuditTrail(
                ledger_id=entry.get('ledger_id', ''),
                conversation_id=entry.get('conversation_id', ''),
                customer_id=entry.get('customer_id', ''),
                agent_name=entry.get('agent_name', ''),
                action=entry.get('action', ''),
                timestamp=entry.get('timestamp', ''),
                policy_evaluations=policy_evals,
                approval_status=approval_status,
                rationale=entry.get('rationale', '')
            ))

        return audit_trail


# Singleton instance
audit_persistence_service = AuditPersistenceService()
