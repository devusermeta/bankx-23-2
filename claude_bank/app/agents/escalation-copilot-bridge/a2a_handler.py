"""
A2A protocol handler for processing escalation requests.
Calls Copilot Studio agent via Power Automate flow.
"""

import re
import logging
import uuid
from datetime import datetime
from typing import Optional, Tuple
from config import settings
from models import ChatRequest, ChatResponse, TicketData, TicketCreationResult
from power_automate_client import get_power_automate_client

logger = logging.getLogger(__name__)


class A2AHandler:
    """
    Handler for processing A2A escalation requests.
    """
    
    def __init__(self):
        self.default_priority = settings.DEFAULT_TICKET_PRIORITY
        self.default_status = settings.DEFAULT_TICKET_STATUS
        self.default_customer_id = settings.DEFAULT_CUSTOMER_ID
    
    def generate_ticket_id(self) -> str:
        """
        Generate unique ticket ID in format: TKT-YYYY-MMDDHHMMSS
        
        Returns:
            Ticket ID string
        """
        now = datetime.now()
        ticket_id = f"TKT-{now.strftime('%Y-%m%d%H%M%S')}"
        return ticket_id
    
    def extract_email(self, text: str) -> Optional[str]:
        """
        Extract email address from text using regex.
        
        Args:
            text: Text to search
            
        Returns:
            Email address or None
        """
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(email_pattern, text)
        return match.group(0) if match else None
    
    def extract_customer_name(self, text: str) -> Optional[str]:
        """
        Extract customer name from text.
        Looks for patterns like:
        - "Customer name: John Doe"
        - "Name: John Doe" 
        - "My name is John Doe"
        - "I am John Doe"
        
        Args:
            text: Text to search
            
        Returns:
            Customer name or None
        """
        # Multiple patterns to catch different formats
        patterns = [
            r'[Cc]ustomer [Nn]ame(?:\s*:?\s*|\s+is\s+)([A-Za-z\s]+?)(?:[,\.]|\s*,|$)',
            r'[Nn]ame(?:\s*:?\s*|\s+is\s+)([A-Za-z\s]+?)(?:[,\.]|\s*,|$)',
            r'[Mm]y name is\s+([A-Za-z\s]+?)(?:[,\.]|\s*,|$)',
            r'I am\s+([A-Za-z\s]+?)(?:[,\.]|\s*,|$)',
            r'[Uu]ser(?:\s*:?\s*|\s+is\s+)([A-Za-z\s]+?)(?:[,\.]|\s*,|$)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # Validate name (should be 2-50 chars, only letters and spaces)
                if 2 <= len(name) <= 50 and re.match(r'^[A-Za-z\s]+$', name):
                    return name
        
        return None
    
    def extract_description(self, text: str) -> str:
        """
        Extract issue description from text.
        Removes email, name, and common prefixes.
        
        Args:
            text: Full message text
            
        Returns:
            Cleaned description
        """
        # Remove "Create escalation ticket:" prefix first
        description = re.sub(r'^Create escalation ticket:\s*', '', text, flags=re.IGNORECASE)
        
        # Remove common prefixes
        prefixes = [
            r'^Create a support ticket for this issue:\s*',
            r'^Create ticket:\s*',
            r'^Issue:\s*',
            r'^Problem:\s*',
            r'^Help with:\s*'
        ]
        
        for prefix in prefixes:
            description = re.sub(prefix, '', description, flags=re.IGNORECASE)
        
        # Extract the actual issue description (everything before Customer Email/Name)
        # Pattern: get everything BEFORE "Customer Email:" or "Customer Name:" or similar
        match = re.search(r'^(.+?)(?:Customer Email:|Customer Name:|Email:|Name:)', description, flags=re.IGNORECASE)
        if match:
            description = match.group(1).strip()
        else:
            # If no match, try to remove email and name patterns at the end
            description = re.sub(r',?\s*Customer email:\s*[^\s,]+', '', description, flags=re.IGNORECASE)
            description = re.sub(r',?\s*Customer name:\s*[A-Za-z\s]+$', '', description, flags=re.IGNORECASE)
            description = re.sub(r',?\s*Email:\s*[^\s,]+', '', description, flags=re.IGNORECASE)
            description = re.sub(r',?\s*Name:\s*[A-Za-z\s]+$', '', description, flags=re.IGNORECASE)
        
        # Clean up whitespace
        description = re.sub(r'\s+', ' ', description).strip()
        description = description.rstrip('.,')
        
        # If description is too short or empty, use a default message
        if len(description) < 10:
            description = "Customer support request - details in ticket"
        
        return description
    
    def parse_ticket_from_message(self, request: ChatRequest) -> Tuple[TicketData, list[str]]:
        """
        Parse ticket information from chat request.
        
        Args:
            request: Chat request from A2A call
            
        Returns:
            Tuple of (TicketData, list of warnings)
        """
        warnings = []
        
        # Get the user message (last message with role=user)
        user_message = None
        for msg in reversed(request.messages):
            if msg.role == "user":
                user_message = msg.content
                break
        
        if not user_message:
            raise ValueError("No user message found in request")
        
        logger.debug(f"Parsing ticket from message: {user_message}")
        
        # Extract components
        email = self.extract_email(user_message)
        name = self.extract_customer_name(user_message)
        description = self.extract_description(user_message)
        
        # Use customer_id from request or default
        customer_id = request.customer_id or self.default_customer_id
        if customer_id == self.default_customer_id:
            warnings.append("customer_id not provided, using default")
        
        # Validate and set defaults
        if not email:
            warnings.append("No email address found in message")
            email = "noreply@bankx.com"
        
        if not name:
            warnings.append("No customer name found in message")
            name = "Customer"
        
        if not description or len(description) < 5:
            warnings.append("Description is too short or missing")
            description = user_message[:200]  # Use first 200 chars of message
        
        # Generate ticket
        ticket_id = self.generate_ticket_id()
        created_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        ticket = TicketData(
            ticket_id=ticket_id,
            customer_id=customer_id,
            customer_email=email,
            customer_name=name,
            description=description,
            priority=self.default_priority,
            status=self.default_status,
            created_date=created_date
        )
        
        logger.info(f"Parsed ticket: {ticket.ticket_id} for {ticket.customer_email}")
        if warnings:
            logger.warning(f"Parsing warnings: {warnings}")
        
        return ticket, warnings
    
    async def create_ticket(self, request: ChatRequest) -> TicketCreationResult:
        """
        Create a support ticket by calling Copilot Studio agent via Power Automate.
        The Copilot Studio agent handles Excel storage and email sending.
        
        Args:
            request: Chat request with ticket information
            
        Returns:
            TicketCreationResult
        """
        try:
            # Parse ticket data from incoming A2A request
            ticket, warnings = self.parse_ticket_from_message(request)
            
            logger.info(f"Creating ticket via Power Automate for customer {ticket.customer_id}")
            if warnings:
                logger.warning(f"Parsing warnings: {warnings}")
            
            # Get Power Automate client
            pa_client = await get_power_automate_client()
            
            # Call Power Automate flow which calls Copilot Studio agent
            result = await pa_client.create_escalation_ticket(
                customer_id=ticket.customer_id,
                customer_email=ticket.customer_email,
                customer_name=ticket.customer_name,
                description=ticket.description,
                priority=ticket.priority
            )
            
            if result.get("success"):
                ticket_id = result.get("ticket_id", ticket.ticket_id)
                logger.info(f"Ticket {ticket_id} created successfully via Power Automate")
                
                return TicketCreationResult(
                    success=True,
                    ticket_id=ticket_id,
                    excel_updated=True,  # Power Automate/Copilot Studio handles this
                    email_sent=True,     # Power Automate/Copilot Studio handles this
                    copilot_response=result.get("response", "")
                )
            else:
                error = result.get("error", "Unknown error from Power Automate")
                logger.error(f"Power Automate failed to create ticket: {error}")
                
                return TicketCreationResult(
                    success=False,
                    error=error,
                    excel_updated=False,
                    email_sent=False
                )
        
        except Exception as e:
            logger.error(f"Error creating ticket via Power Automate: {e}")
            return TicketCreationResult(
                success=False,
                error=str(e),
                excel_updated=False,
                email_sent=False
            )
    
    async def process_request(self, request: ChatRequest) -> ChatResponse:
        """
        Process A2A chat request and return formatted response.
        
        Args:
            request: Chat request
            
        Returns:
            Chat response
        """
        try:
            # Create ticket
            result = await self.create_ticket(request)
            
            if result.success:
                # Build success message
                content = f"Support ticket {result.ticket_id} created successfully."
                
                if result.email_sent:
                    content += " Email notification sent to customer."
                else:
                    content += " Note: Email notification failed to send."
                
                content += " Our support team will contact the customer within 24 business hours."
                
                return ChatResponse(
                    role="assistant",
                    content=content,
                    agent="EscalationAgent"
                )
            else:
                # Return error response
                content = f"Failed to create support ticket: {result.error}"
                return ChatResponse(
                    role="assistant",
                    content=content,
                    agent="EscalationAgent"
                )
        
        except Exception as e:
            logger.error(f"Error processing A2A request: {e}")
            return ChatResponse(
                role="assistant",
                content=f"An error occurred while processing the ticket request: {str(e)}",
                agent="EscalationAgent"
            )


# Global instance
_a2a_handler: Optional[A2AHandler] = None


async def get_a2a_handler() -> A2AHandler:
    """Get or create global A2A handler."""
    global _a2a_handler
    if _a2a_handler is None:
        _a2a_handler = A2AHandler()
    return _a2a_handler
