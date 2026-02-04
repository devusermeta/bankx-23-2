"""Ticket management service for Escalation MCP server."""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class TicketStatus(str, Enum):
    """Ticket status values."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    """Ticket priority values."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class TicketUpdate:
    """Ticket update/history entry."""
    timestamp: str
    update_type: str
    content: str
    updated_by: str = "system"


@dataclass
class Ticket:
    """Support ticket model."""
    ticket_id: str
    customer_id: str
    description: str
    status: str
    priority: str
    created_at: str
    updated_at: str
    category: str = "general"
    updates: List[Dict[str, Any]] = None
    assigned_to: Optional[str] = None
    
    def __post_init__(self):
        if self.updates is None:
            self.updates = []


class TicketService:
    """
    Service for managing support tickets.
    
    Uses JSON file storage for simplicity. In production, this would use a database.
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize ticket service.
        
        Args:
            data_dir: Directory for storing ticket data (defaults to ./data)
        """
        if data_dir is None:
            data_dir = Path(__file__).parent / "data"
        
        self.data_dir = data_dir
        self.data_dir.mkdir(exist_ok=True)
        self.tickets_file = self.data_dir / "tickets.json"
        
        # Load existing tickets or initialize empty dict
        if self.tickets_file.exists():
            with open(self.tickets_file, 'r') as f:
                self.tickets = json.load(f)
            logger.info(f"Loaded {len(self.tickets)} existing tickets")
        else:
            self.tickets = {}
            self._save_tickets()
            logger.info("Initialized new ticket storage")
    
    def _save_tickets(self):
        """Save tickets to file."""
        with open(self.tickets_file, 'w') as f:
            json.dump(self.tickets, f, indent=2)
    
    def _generate_ticket_id(self) -> str:
        """Generate unique ticket ID in format TKT-YYYY-NNNNNN."""
        now = datetime.now(timezone.utc)
        year = now.year
        
        # Count tickets for this year
        year_prefix = f"TKT-{year}-"
        existing_tickets = [tid for tid in self.tickets.keys() if tid.startswith(year_prefix)]
        next_number = len(existing_tickets) + 1
        
        return f"TKT-{year}-{next_number:06d}"
    
    def create_ticket(
        self,
        customer_id: str,
        description: str,
        priority: str = "normal",
        category: str = "general"
    ) -> Ticket:
        """
        Create a new support ticket.
        
        Args:
            customer_id: Customer ID
            description: Issue description
            priority: Priority level (low/normal/high/urgent)
            category: Ticket category
        
        Returns:
            Created ticket
        """
        now = datetime.now(timezone.utc).isoformat()
        ticket_id = self._generate_ticket_id()
        
        ticket = Ticket(
            ticket_id=ticket_id,
            customer_id=customer_id,
            description=description,
            status=TicketStatus.OPEN,
            priority=priority,
            created_at=now,
            updated_at=now,
            category=category,
            updates=[{
                "timestamp": now,
                "update_type": "created",
                "content": "Ticket created",
                "updated_by": "system"
            }]
        )
        
        self.tickets[ticket_id] = asdict(ticket)
        self._save_tickets()
        
        logger.info(f"Created ticket {ticket_id} for customer {customer_id}")
        return ticket
    
    def get_tickets(
        self,
        customer_id: str,
        status: Optional[str] = None
    ) -> List[Ticket]:
        """
        Get tickets for a customer.
        
        Args:
            customer_id: Customer ID
            status: Optional status filter (open/in_progress/resolved/closed)
        
        Returns:
            List of tickets
        """
        tickets = []
        for ticket_data in self.tickets.values():
            if ticket_data["customer_id"] == customer_id:
                if status is None or ticket_data["status"] == status:
                    tickets.append(Ticket(**ticket_data))
        
        # Sort by created_at descending (newest first)
        tickets.sort(key=lambda t: t.created_at, reverse=True)
        
        logger.info(f"Found {len(tickets)} tickets for customer {customer_id}")
        return tickets
    
    def get_ticket_details(self, ticket_id: str) -> Optional[Ticket]:
        """
        Get detailed information about a specific ticket.
        
        Args:
            ticket_id: Ticket ID
        
        Returns:
            Ticket or None if not found
        """
        ticket_data = self.tickets.get(ticket_id)
        if ticket_data:
            return Ticket(**ticket_data)
        return None
    
    def update_ticket(
        self,
        ticket_id: str,
        status: Optional[str] = None,
        notes: Optional[str] = None,
        priority: Optional[str] = None
    ) -> Ticket:
        """
        Update an existing ticket.
        
        Args:
            ticket_id: Ticket ID
            status: New status (optional)
            notes: Notes to add (optional)
            priority: New priority (optional)
        
        Returns:
            Updated ticket
        
        Raises:
            ValueError: If ticket not found
        """
        if ticket_id not in self.tickets:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        ticket_data = self.tickets[ticket_id]
        now = datetime.now(timezone.utc).isoformat()
        
        # Add update entry
        update = {
            "timestamp": now,
            "update_type": "updated",
            "content": "",
            "updated_by": "system"
        }
        
        updates = []
        if status and status != ticket_data["status"]:
            ticket_data["status"] = status
            updates.append(f"Status changed to {status}")
        
        if priority and priority != ticket_data["priority"]:
            ticket_data["priority"] = priority
            updates.append(f"Priority changed to {priority}")
        
        if notes:
            updates.append(f"Notes: {notes}")
        
        update["content"] = "; ".join(updates) if updates else "Ticket updated"
        ticket_data["updates"].append(update)
        ticket_data["updated_at"] = now
        
        self._save_tickets()
        
        logger.info(f"Updated ticket {ticket_id}: {update['content']}")
        return Ticket(**ticket_data)
    
    def close_ticket(self, ticket_id: str) -> Ticket:
        """
        Close a ticket.
        
        Args:
            ticket_id: Ticket ID
        
        Returns:
            Closed ticket
        
        Raises:
            ValueError: If ticket not found
        """
        return self.update_ticket(ticket_id, status=TicketStatus.CLOSED, notes="Ticket closed")
