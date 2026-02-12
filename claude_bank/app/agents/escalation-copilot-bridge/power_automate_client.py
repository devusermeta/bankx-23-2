"""
Power Automate client for communicating with the Escalation Agent
via HTTP workflow trigger.
"""

import logging
import httpx
from typing import Optional, Dict, Any
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)


class PowerAutomateClient:
    """
    Client for communicating with Copilot Studio agent via Power Automate flow.
    """
    
    def __init__(self):
        self.flow_url = settings.POWER_AUTOMATE_FLOW_URL
        self.timeout = settings.POWER_AUTOMATE_TIMEOUT_SECONDS
    
    async def create_escalation_ticket(
        self,
        customer_id: str,
        customer_email: str,
        customer_name: str,
        description: str,
        priority: str = "Medium"
    ) -> Dict[str, Any]:
        """
        Create an escalation ticket by calling Power Automate flow.
        
        Args:
            customer_id: Customer identifier
            customer_email: Customer email address
            customer_name: Customer name
            description: Issue description
            priority: Priority level (default: "Medium")
            
        Returns:
            dict: Result with success status and details
        """
        # Prepare payload for Power Automate flow
        payload = {
            "customer_id": customer_id,
            "customer_email": customer_email,
            "customer_name": customer_name,
            "description": description,
            "priority": priority
        }
        
        logger.info(f"Creating escalation ticket via Power Automate for customer {customer_id}")
        logger.debug(f"Payload: {payload}")
        
        try:
            # Call Power Automate flow
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.flow_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json"
                    }
                )
                
                response.raise_for_status()
                
                # Parse response
                response_text = response.text
                logger.info(f"Received response from Power Automate: {response_text[:200]}...")
                
                # Extract ticket ID from response
                ticket_id = self._extract_ticket_id(response_text)
                
                result = {
                    "success": True,
                    "ticket_id": ticket_id,
                    "response": response_text,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Successfully created ticket: {ticket_id or 'N/A'}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from Power Automate: {e}")
            logger.error(f"Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text if hasattr(e, 'response') else str(e)}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except httpx.TimeoutException:
            logger.error(f"Timeout calling Power Automate flow after {self.timeout}s")
            return {
                "success": False,
                "error": f"Power Automate flow timeout after {self.timeout}s",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to call Power Automate: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _extract_ticket_id(self, response_text: str) -> Optional[str]:
        """
        Extract ticket ID from Power Automate/Copilot Studio response.
        
        Args:
            response_text: Response from Power Automate
            
        Returns:
            str: Ticket ID or None
        """
        import re
        
        # Look for patterns like "TKT-2026-0212..." or "Ticket ID: TKT-..."
        patterns = [
            r'TKT-\d{4}-\d{10,}',
            r'Ticket ID:\s*(TKT-[\w-]+)',
            r'ticket\s*#?\s*(TKT-[\w-]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response_text, re.IGNORECASE)
            if match:
                return match.group(1) if '(' in pattern else match.group(0)
        
        return None
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Power Automate flow.
        
        Returns:
            dict: Connection test result
        """
        logger.info("Testing Power Automate connection...")
        
        try:
            # Send a test request
            test_payload = {
                "customer_id": "TEST-CONNECTION",
                "customer_email": "test@example.com",
                "customer_name": "Test User",
                "description": "Connection test from A2A bridge",
                "priority": "Low"
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.flow_url,
                    json=test_payload,
                    headers={
                        "Content-Type": "application/json"
                    }
                )
                
                response.raise_for_status()
                
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "message": "Successfully connected to Power Automate flow"
                }
                
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to connect to Power Automate flow"
            }


# Singleton instance
_power_automate_client: Optional[PowerAutomateClient] = None


async def get_power_automate_client() -> PowerAutomateClient:
    """
    Get or create the Power Automate client singleton.
    
    Returns:
        PowerAutomateClient instance
    """
    global _power_automate_client
    
    if _power_automate_client is None:
        _power_automate_client = PowerAutomateClient()
    
    return _power_automate_client
