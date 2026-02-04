"""
Audit Service

Business logic for audit logging and decision ledger operations.
"""

import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from models import DecisionLedgerEntry, AgentInteractionLog, DecisionAuditTrail, AuditSearchResult
from audit_persistence_service import audit_persistence_service

logger = logging.getLogger(__name__)


class AuditService:
    """
    Audit Service - Handles decision ledger and governance logging.

    Key responsibilities:
    1. Log agent decisions (US 1.A1)
    2. Log decision rationale (US 1.A2)
    3. Record policy evaluations (US 1.A3)
    4. Provide teller dashboard queries (US 1.T1-1.T5)
    """

    def __init__(self):
        """Initialize Audit Service."""
        logger.info("AuditService initialized")


    def log_decision(
        self,
        conversation_id: str,
        customer_id: str,
        agent_name: str,
        action: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        rationale: str,
        policy_evaluation: Optional[Dict] = None,
        approval: Optional[Dict] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Log a decision to the Decision Ledger.

        This is the PRIMARY function for US 1.A1-1.A3.

        Called by agents after every significant action to create complete audit trail.

        Args:
            conversation_id: Conversation identifier
            customer_id: Customer ID (hashed in production)
            agent_name: Agent that performed action
            action: Action type (e.g., "VIEW_TRANSACTIONS", "TRANSFER")
            input_data: Sanitized input parameters
            output_data: Output summary (structured output schema)
            rationale: Human-readable decision rationale
            policy_evaluation: Optional policy check results
            approval: Optional approval metadata
            metadata: Optional metadata (latency, request_id, etc.)

        Returns:
            ledger_id of the created entry
        """
        logger.info(f"Logging decision: action={action}, customer={customer_id}, agent={agent_name}")

        # Generate unique ledger ID
        ledger_id = f"LEDGER-{uuid.uuid4().hex[:16].upper()}"

        # Get current timestamp (Asia/Bangkok)
        timestamp = datetime.now().astimezone().isoformat()

        # Create ledger entry
        entry = DecisionLedgerEntry(
            ledger_id=ledger_id,
            conversation_id=conversation_id,
            customer_id=customer_id,
            agent_name=agent_name,
            action=action,
            timestamp=timestamp,
            input=input_data,
            output=output_data,
            policy_evaluation=policy_evaluation,
            approval=approval,
            metadata=metadata or {},
            rationale=rationale
        )

        # Persist to storage
        audit_persistence_service.add_ledger_entry(entry)

        logger.info(f"Decision logged: {ledger_id}")
        return ledger_id


    def get_ledger_entry(self, ledger_id: str) -> Optional[DecisionLedgerEntry]:
        """
        Get a specific ledger entry.

        Args:
            ledger_id: Ledger entry ID

        Returns:
            DecisionLedgerEntry or None
        """
        entry_dict = audit_persistence_service.get_ledger_entry(ledger_id)
        if entry_dict:
            return DecisionLedgerEntry(**entry_dict)
        return None


    def get_customer_audit_history(
        self,
        customer_id: str,
        limit: int = 50
    ) -> List[DecisionLedgerEntry]:
        """
        Get audit history for a customer.

        Used by teller dashboard for US 1.T1-1.T5.

        Args:
            customer_id: Customer ID
            limit: Maximum number of entries

        Returns:
            List of DecisionLedgerEntry (most recent first)
        """
        logger.info(f"Getting audit history for customer {customer_id}")

        entries = audit_persistence_service.get_entries_by_customer(customer_id, limit)
        return [DecisionLedgerEntry(**e) for e in entries]


    def get_agent_interactions(
        self,
        customer_id: str,
        limit: int = 50
    ) -> List[AgentInteractionLog]:
        """
        Get agent interaction logs for teller dashboard (US 1.T3).

        Args:
            customer_id: Customer ID
            limit: Maximum number of interactions

        Returns:
            List of AgentInteractionLog models
        """
        logger.info(f"Getting agent interactions for customer {customer_id}")
        return audit_persistence_service.get_agent_interactions(customer_id, limit)


    def get_decision_audit_trail(
        self,
        customer_id: str,
        limit: int = 50
    ) -> List[DecisionAuditTrail]:
        """
        Get decision audit trail for teller dashboard (US 1.T4).

        Args:
            customer_id: Customer ID
            limit: Maximum number of decisions

        Returns:
            List of DecisionAuditTrail models
        """
        logger.info(f"Getting decision audit trail for customer {customer_id}")
        return audit_persistence_service.get_decision_audit_trail(customer_id, limit)


    def search_audit_logs(
        self,
        customer_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        action: Optional[str] = None,
        from_timestamp: Optional[str] = None,
        to_timestamp: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> AuditSearchResult:
        """
        Search audit logs with filters (US 1.T5).

        Args:
            customer_id: Filter by customer
            agent_name: Filter by agent
            action: Filter by action
            from_timestamp: Start date/time
            to_timestamp: End date/time
            page: Page number (1-indexed)
            page_size: Results per page

        Returns:
            AuditSearchResult with paginated results
        """
        logger.info(f"Searching audit logs: customer={customer_id}, agent={agent_name}, action={action}")

        # Get all matching entries
        entries = audit_persistence_service.search_entries(
            customer_id=customer_id,
            agent_name=agent_name,
            action=action,
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            limit=page_size * 10  # Get more for pagination
        )

        # Paginate
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_entries = entries[start_idx:end_idx]

        # Convert to models
        ledger_entries = [DecisionLedgerEntry(**e) for e in paginated_entries]

        return AuditSearchResult(
            total_count=len(entries),
            results=ledger_entries,
            page=page,
            page_size=page_size
        )


    def get_conversation_history(self, conversation_id: str) -> List[DecisionLedgerEntry]:
        """
        Get all decisions in a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of DecisionLedgerEntry (chronological order)
        """
        logger.info(f"Getting conversation history: {conversation_id}")

        entries = audit_persistence_service.get_entries_by_conversation(conversation_id)
        return [DecisionLedgerEntry(**e) for e in entries]
