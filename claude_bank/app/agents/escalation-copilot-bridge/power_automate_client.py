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
        # Prepare payload for Power Automate flow (matching expected schema)
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
    
    async def test_connection(self, raise_on_error: bool = False) -> Dict[str, Any]:
        """
        Test connection to Power Automate flow.
        
        Args:
            raise_on_error: If True, raises exceptions on errors (default: False for startup)
        
        Returns:
            dict: Connection test result with detailed diagnostics
        """
        logger.info("Testing Power Automate connection...")
        
        try:
            # Send a minimal test request
            test_payload = {
                "customer_id": "TEST-CONN-001",
                "customer_email": "startup-test@example.com",
                "customer_name": "Startup Test", 
                "description": "Connection test from A2A bridge startup",
                "priority": "Medium"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:  # Shorter timeout for startup
                response = await client.post(
                    self.flow_url,
                    json=test_payload,
                    headers={
                        "Content-Type": "application/json"
                    }
                )
                
                # Don't raise for HTTP errors during startup - we want to diagnose them
                if response.status_code == 200:
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "message": "✅ Successfully connected to Power Automate flow",
                        "diagnostics": {
                            "flow_reachable": True,
                            "flow_responding": True,
                            "response_time_ms": response.elapsed.total_seconds() * 1000
                        }
                    }
                elif response.status_code == 502:
                    # 502 Bad Gateway - Flow is reachable but downstream service failing
                    error_details = "Unknown"
                    try:
                        error_data = response.json()
                        error_details = error_data.get('error', {}).get('message', 'Unknown 502 error')
                    except:
                        error_details = response.text[:200]
                        
                    result = {
                        "success": False,
                        "status_code": response.status_code,
                        "error": f"502 Bad Gateway: {error_details}",
                        "message": "❌ Power Automate flow reachable but internal error",
                        "diagnostics": {
                            "flow_reachable": True,
                            "flow_responding": False,
                            "error_type": "downstream_service_failure",
                            "likely_causes": [
                                "Copilot Studio bot not published or accessible",
                                "Outlook connector authentication expired", 
                                "Excel connector permissions revoked",
                                "Flow disabled or has logic errors"
                            ],
                            "recommended_actions": [
                                "Check Power Automate flow run history",
                                "Re-publish Copilot Studio bot",
                                "Re-authenticate connectors",
                                "Test flow manually in Power Automate"
                            ]
                        }
                    }
                    
                    if raise_on_error:
                        raise httpx.HTTPStatusError(f"502 Bad Gateway: {error_details}", request=response.request, response=response)
                    
                    return result
                    
                elif response.status_code == 500:
                    # 500 Internal Server Error - Flow has internal issues
                    error_details = "Unknown"
                    try:
                        error_data = response.json()
                        error_details = error_data.get('error', {}).get('message', 'Unknown server error')
                    except:
                        error_details = response.text[:200]
                    
                    result = {
                        "success": False,
                        "status_code": response.status_code,
                        "error": f"500 Internal Server Error: {error_details}", 
                        "message": "❌ Power Automate flow has internal server error",
                        "diagnostics": {
                            "flow_reachable": True,
                            "flow_responding": False,
                            "error_type": "internal_server_error",
                            "likely_causes": [
                                "Flow configuration error",
                                "Connector authentication issues",
                                "Resource permission problems",
                                "Power Platform service issues"
                            ]
                        }
                    }
                    
                    if raise_on_error:
                        raise httpx.HTTPStatusError(f"500 Internal Server Error: {error_details}", request=response.request, response=response)
                    
                    return result
                    
                else:
                    # Other HTTP errors
                    result = {
                        "success": False,
                        "status_code": response.status_code,
                        "error": f"HTTP {response.status_code}: {response.text[:200]}",
                        "message": f"❌ Power Automate returned HTTP {response.status_code}",
                        "diagnostics": {
                            "flow_reachable": True,
                            "flow_responding": False,
                            "error_type": "http_error"
                        }
                    }
                    
                    if raise_on_error:
                        response.raise_for_status()
                    
                    return result
                
        except httpx.TimeoutException as e:
            result = {
                "success": False,
                "error": f"Connection timeout: {e}",
                "message": "❌ Power Automate flow connection timeout",
                "diagnostics": {
                    "flow_reachable": False,
                    "error_type": "timeout",
                    "likely_causes": ["Network issues", "Flow taking too long to respond", "Service overloaded"]
                }
            }
            
            if raise_on_error:
                raise e
                
            return result
            
        except httpx.ConnectError as e:
            result = {
                "success": False,
                "error": f"Connection error: {e}",
                "message": "❌ Cannot connect to Power Automate flow",
                "diagnostics": {
                    "flow_reachable": False,
                    "error_type": "connection_error",
                    "likely_causes": ["Wrong URL", "Network issues", "Service down"]
                }
            }
            
            if raise_on_error:
                raise e
                
            return result
            
        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "message": "❌ Unexpected error testing Power Automate connection",
                "diagnostics": {
                    "error_type": "unknown"
                }
            }
            
            logger.error(f"Connection test failed: {e}")
            
            if raise_on_error:
                raise e
                
            return result


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
