"""
Copilot Studio client for communicating with the Escalation Agent
via Direct Line API (Bot Framework).
"""

import logging
import httpx
import asyncio
import uuid
from typing import Optional, Dict, Any, List
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)


class CopilotStudioClient:
    """
    Client for communicating with Copilot Studio agent via Direct Line API.
    """
    
    def __init__(self):
        self.direct_line_secret = settings.COPILOT_DIRECT_LINE_SECRET
        self.direct_line_endpoint = settings.COPILOT_DIRECT_LINE_ENDPOINT
        self.bot_name = settings.COPILOT_BOT_NAME
        self.timeout = settings.COPILOT_TIMEOUT_SECONDS
        self.max_response_wait = settings.COPILOT_MAX_RESPONSE_WAIT
        
        # Will be set after starting conversation
        self.conversation_id: Optional[str] = None
        self.stream_url: Optional[str] = None
        self.watermark: Optional[str] = None
    
    async def start_conversation(self) -> Dict[str, Any]:
        """
        Start a new conversation with the Copilot Studio agent.
        
        Returns:
            dict: Conversation details including conversation_id and stream_url
            
        Raises:
            Exception: If conversation start fails
        """
        url = f"{self.direct_line_endpoint}/conversations"
        headers = {
            "Authorization": f"Bearer {self.direct_line_secret}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                self.conversation_id = data.get("conversationId")
                self.stream_url = data.get("streamUrl")
                
                logger.info(f"Started conversation with Copilot Studio: {self.conversation_id}")
                return data
                
        except Exception as e:
            logger.error(f"Failed to start conversation with Copilot Studio: {e}")
            raise Exception(f"Could not start Copilot Studio conversation: {e}")
    
    async def send_message(
        self,
        message: str,
        user_id: str = "local-a2a-bridge",
        user_name: str = "A2A Bridge"
    ) -> Dict[str, Any]:
        """
        Send a message to the Copilot Studio agent.
        
        Args:
            message: The message text to send
            user_id: User identifier (default: "local-a2a-bridge")
            user_name: User display name (default: "A2A Bridge")
            
        Returns:
            dict: Response from Direct Line API
            
        Raises:
            Exception: If message send fails
        """
        if not self.conversation_id:
            await self.start_conversation()
        
        url = f"{self.direct_line_endpoint}/conversations/{self.conversation_id}/activities"
        headers = {
            "Authorization": f"Bearer {self.direct_line_secret}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "type": "message",
            "from": {
                "id": user_id,
                "name": user_name
            },
            "text": message,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Sent message to Copilot Studio, activity ID: {data.get('id')}")
                return data
                
        except Exception as e:
            logger.error(f"Failed to send message to Copilot Studio: {e}")
            raise Exception(f"Could not send message to Copilot Studio: {e}")
    
    async def get_activities(self, watermark: Optional[str] = None) -> Dict[str, Any]:
        """
        Get activities (messages) from the conversation.
        
        Args:
            watermark: Optional watermark to get only new activities
            
        Returns:
            dict: Activities from the conversation
            
        Raises:
            Exception: If getting activities fails
        """
        if not self.conversation_id:
            raise Exception("No active conversation. Call start_conversation() first.")
        
        url = f"{self.direct_line_endpoint}/conversations/{self.conversation_id}/activities"
        if watermark:
            url += f"?watermark={watermark}"
        
        headers = {
            "Authorization": f"Bearer {self.direct_line_secret}"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                self.watermark = data.get("watermark")
                return data
                
        except Exception as e:
            logger.error(f"Failed to get activities from Copilot Studio: {e}")
            raise Exception(f"Could not get activities from Copilot Studio: {e}")
    
    async def wait_for_response(
        self,
        max_wait_seconds: Optional[int] = None,
        poll_interval: float = 1.0
    ) -> Optional[str]:
        """
        Wait for a response from the Copilot Studio agent.
        Polls the conversation for new bot messages.
        
        Args:
            max_wait_seconds: Maximum time to wait (default: from config)
            poll_interval: How often to poll in seconds (default: 1.0)
            
        Returns:
            str: The bot's response text, or None if timeout
        """
        max_wait = max_wait_seconds or self.max_response_wait
        start_time = asyncio.get_event_loop().time()
        
        logger.info(f"Waiting for Copilot Studio response (max {max_wait}s)...")
        
        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > max_wait:
                logger.warning(f"Timeout waiting for Copilot Studio response after {max_wait}s")
                return None
            
            try:
                # Get new activities
                data = await self.get_activities(watermark=self.watermark)
                activities = data.get("activities", [])
                
                # Look for bot messages
                for activity in activities:
                    if activity.get("type") == "message" and activity.get("from", {}).get("id") != "local-a2a-bridge":
                        # This is a bot message
                        text = activity.get("text", "")
                        if text:
                            logger.info(f"Received response from Copilot Studio: {text[:100]}...")
                            return text
                
                # No response yet, wait and try again
                await asyncio.sleep(poll_interval)
                
            except Exception as e:
                logger.error(f"Error while waiting for response: {e}")
                await asyncio.sleep(poll_interval)
    
    async def send_and_wait(
        self,
        message: str,
        user_id: str = "local-a2a-bridge",
        user_name: str = "A2A Bridge",
        max_wait_seconds: Optional[int] = None
    ) -> Optional[str]:
        """
        Send a message and wait for the bot's response.
        Convenience method that combines send_message and wait_for_response.
        
        Args:
            message: The message text to send
            user_id: User identifier
            user_name: User display name
            max_wait_seconds: Maximum time to wait for response
            
        Returns:
            str: The bot's response text, or None if timeout
        """
        # Start a fresh conversation for each request
        await self.start_conversation()
        
        # Send the message
        await self.send_message(message, user_id, user_name)
        
        # Wait for response
        response = await self.wait_for_response(max_wait_seconds)
        
        return response
    
    async def create_escalation_ticket(
        self,
        customer_id: str,
        customer_email: str,
        customer_name: str,
        description: str,
        priority: str = "Medium"
    ) -> Dict[str, Any]:
        """
        Create an escalation ticket by sending a structured request to Copilot Studio.
        
        Args:
            customer_id: Customer identifier
            customer_email: Customer email address
            customer_name: Customer name
            description: Issue description
            priority: Priority level (default: "Medium")
            
        Returns:
            dict: Result with success status and details
        """
        # Format the message for the Copilot Studio agent
        # Adjust this format based on how your Copilot Studio agent expects data
        message = f"""
Create escalation ticket:
Customer ID: {customer_id}
Customer Email: {customer_email}
Customer Name: {customer_name}
Priority: {priority}
Description: {description}
""".strip()
        
        logger.info(f"Creating escalation ticket via Copilot Studio for customer {customer_id}")
        
        try:
            # Send message and wait for response
            response_text = await self.send_and_wait(
                message,
                user_id=customer_id or "unknown",
                user_name=customer_name or "Unknown Customer"
            )
            
            if response_text:
                # Parse the response
                # Adjust parsing based on your Copilot Studio agent's response format
                result = {
                    "success": True,
                    "ticket_id": self._extract_ticket_id(response_text),
                    "response": response_text,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                logger.info(f"Successfully created ticket: {result.get('ticket_id', 'N/A')}")
                return result
            else:
                # Timeout or no response
                return {
                    "success": False,
                    "error": "No response from Copilot Studio (timeout)",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to create escalation ticket: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _extract_ticket_id(self, response_text: str) -> Optional[str]:
        """
        Extract ticket ID from Copilot Studio response.
        Adjust the parsing logic based on your agent's response format.
        
        Args:
            response_text: Response from Copilot Studio
            
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
    
    def close_conversation(self):
        """
        Close the current conversation (cleanup).
        """
        self.conversation_id = None
        self.stream_url = None
        self.watermark = None
        logger.info("Closed Copilot Studio conversation")


# Singleton instance
_copilot_client: Optional[CopilotStudioClient] = None


async def get_copilot_client() -> CopilotStudioClient:
    """
    Get or create the Copilot Studio client singleton.
    
    Returns:
        CopilotStudioClient instance
    """
    global _copilot_client
    
    if _copilot_client is None:
        _copilot_client = CopilotStudioClient()
    
    return _copilot_client
