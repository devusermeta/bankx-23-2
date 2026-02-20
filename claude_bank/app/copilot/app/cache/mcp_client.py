"""
MCP Client Wrapper - Direct HTTP calls to MCP servers for cache population.

This module provides a lightweight client to fetch data from MCP servers
without going through the agent framework.
"""

import os
import httpx
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class MCPClient:
    """Base MCP client for making HTTP requests to MCP servers."""
    
    def __init__(self, base_url: str, timeout: float = 60.0):
        """
        Initialize MCP client.
        
        Args:
            base_url: Base URL of the MCP server (e.g., "https://account-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io")
            timeout: Request timeout in seconds (default 60s for container cold starts)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
        )
        self._session_initialized = False
        self._session_id = None  # Store session ID from initialize
    
    async def close(self):
        """Close the HTTP client connection."""
        await self.client.aclose()
    
    async def _ensure_session(self):
        """
        Ensure MCP session is initialized.
        FastMCP requires an initialize handshake before any tool calls.
        """
        if self._session_initialized:
            # print(f"[MCP_CLIENT] ✅ Session already initialized for {self.base_url}")
            return
        
        try:
            url = f"{self.base_url}/mcp"
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "cache-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            
            # print(f"[MCP_CLIENT] 🔌 Initializing MCP session with {self.base_url}")
            # print(f"[MCP_CLIENT] 📤 Sending POST to {url}")
            # print(f"[MCP_CLIENT] 📋 Headers: {headers}")
            logger.debug(f"🔌 Initializing MCP session with {self.base_url}")
            response = await self.client.post(url, json=payload, headers=headers)
            # print(f"[MCP_CLIENT] 📥 Response status: {response.status_code}")
            response.raise_for_status()
            
            # Extract session ID from response headers
            self._session_id = response.headers.get('mcp-session-id')
            # print(f"[MCP_CLIENT] 🆔 Session ID: {self._session_id}")
            if not self._session_id:
                raise Exception("MCP server did not return session ID")
            
            # Parse SSE response
            # print(f"[MCP_CLIENT] 📖 Parsing SSE response...")
            self._parse_sse_response(response.text)
            self._session_initialized = True
            # print(f"[MCP_CLIENT] ✅ MCP session initialized with {self.base_url} (session: {self._session_id})")
            logger.debug(f"✅ MCP session initialized with {self.base_url} (session: {self._session_id})")
            
        except Exception as e:
            print(f"[MCP_CLIENT] ❌ Failed to initialize MCP session with {self.base_url}")
            print(f"[MCP_CLIENT] ❌ Error type: {type(e).__name__}")
            print(f"[MCP_CLIENT] ❌ Error message: {e}")
            import traceback
            print(f"[MCP_CLIENT] ❌ Traceback: {traceback.format_exc()}")
            logger.error(f"❌ Failed to initialize MCP session with {self.base_url}: {e}")
            raise
    
    def _parse_sse_response(self, response_text: str) -> Any:
        """
        Parse Server-Sent Events (SSE) response format.
        
        SSE format:
        event: message
        data: {"jsonrpc":"2.0","id":1,"result":{...}}
        """
        lines = response_text.strip().split('\n')
        data_line = None
        
        for line in lines:
            if line.startswith('data: '):
                data_line = line[6:]  # Remove 'data: ' prefix
                break
        
        if data_line:
            import json
            result = json.loads(data_line)
            
            # Check for JSON-RPC error
            if "error" in result:
                error_msg = result["error"].get("message", "Unknown error")
                raise Exception(f"MCP error: {error_msg}")
            
            # Return the result field if present
            if "result" in result:
                return result["result"]
            
            return result
        
        return None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool using JSON-RPC 2.0 over HTTP with SSE transport.
        
        FastMCP implements the Model Context Protocol which uses:
        1. JSON-RPC 2.0 format for requests
        2. Server-Sent Events (SSE) for responses
        3. Session initialization before first tool call
        
        Args:
            tool_name: Name of the tool to call
            arguments: Tool arguments as dictionary
        
        Returns:
            Tool response data
        """
        # Ensure session is initialized
        await self._ensure_session()
        
        url = f"{self.base_url}/mcp"
        
        # JSON-RPC 2.0 format for tools/call
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "mcp-session-id": self._session_id  # Include session ID in request
        }
        
        try:
            logger.info(f"📞 Calling MCP tool: {tool_name} (session: {self._session_id})")
            logger.debug(f"📝 Arguments: {arguments}")
            logger.debug(f"📤 Payload: {payload}")
            logger.debug(f"📋 Headers: {headers}")
            
            response = await self.client.post(url, json=payload, headers=headers)
            
            # Log response even if error
            if response.status_code != 200:
                logger.error(f"❌ HTTP {response.status_code}: {response.text[:500]}")
            
            # If session expired (400/401), re-initialize and retry once
            if response.status_code in [400, 401]:
                error_text = response.text.lower()
                if 'session' in error_text or 'unauthorized' in error_text:
                    logger.warning(f"⚠️ Session expired or invalid, re-initializing...")
                    self._session_initialized = False
                    await self._ensure_session()
                    # Retry with new session
                    headers["mcp-session-id"] = self._session_id
                    response = await self.client.post(url, json=payload, headers=headers)
            
            response.raise_for_status()
            
            # Parse SSE response
            result = self._parse_sse_response(response.text)
            # print(f"[MCP_CLIENT] ✅ MCP tool {tool_name} succeeded")
            # print(f"[MCP_CLIENT] 📄 Raw result: {result}")
            logger.info(f"✅ MCP tool {tool_name} succeeded")
            logger.debug(f"📄 Response: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error calling MCP tool {tool_name}: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    def _extract_tool_result(self, mcp_response: Any) -> Any:
        """
        Extract actual data from MCP tool response.
        
        MCP tools return: {"content": [{"type": "text", "text": "..."}], "isError": false}
        We need to extract and parse the text content.
        """
        if isinstance(mcp_response, dict):
            # Check for error
            if mcp_response.get("isError"):
                logger.error(f"MCP tool error: {mcp_response}")
                return None
            
            # Extract content
            content = mcp_response.get("content", [])
            # print(f"[MCP_CLIENT] 📦 Extracting content from response: {len(content)} items")
            if content and len(content) > 0:
                text = content[0].get("text", "")
                # print(f"[MCP_CLIENT] 📝 Text content: {text[:200]}...")
                
                # Try to parse as JSON
                if text.strip().startswith(("{", "[")):
                    import json
                    try:
                        parsed = json.loads(text)
                        # print(f"[MCP_CLIENT] ✅ Parsed JSON successfully")
                        return parsed
                    except json.JSONDecodeError as e:
                        # print(f"[MCP_CLIENT] ❌ Failed to parse JSON: {e}")
                        logger.warning(f"Failed to parse MCP response as JSON: {text[:100]}")
                        return None
                
                return text
        
        return mcp_response


class AccountMCPClient(MCPClient):
    """Client for Account MCP server."""
    
    async def get_accounts_by_username(self, user_email: str) -> Optional[List[Dict]]:
        """Get all accounts for a customer by their email (UPN from access token).
        
        Args:
            user_email: User's email/UPN from Entra ID token (e.g., nattaporn.suksawat@example.com)
        """
        result = await self.call_tool("getAccountsByUserName", {"userName": user_email})
        if result:
            return self._extract_tool_result(result)
        return None
    
    async def get_account_details(self, account_id: str) -> Optional[Dict]:
        """Get account details for a specific account ID."""
        result = await self.call_tool("getAccountDetails", {"accountId": account_id})
        if result:
            # MCP returns content in SSE format
            return self._extract_tool_result(result)
        return None


class TransactionMCPClient(MCPClient):
    """Client for Transaction MCP server."""
    
    async def get_transactions(self, account_id: str, limit: int = 5) -> Optional[List[Dict]]:
        """Get recent transactions for an account."""
        result = await self.call_tool("getLastTransactions", {
            "accountId": account_id,
            "limit": limit
        })
        if result:
            return self._extract_tool_result(result)
        return None


class ContactsMCPClient(MCPClient):
    """Client for Contacts MCP server (beneficiaries)."""
    
    async def get_registered_beneficiaries(self, account_id: str) -> Optional[List[Dict]]:
        """Get registered beneficiaries for an account."""
        result = await self.call_tool("getRegisteredBeneficiaries", {"accountId": account_id})
        if result:
            return self._extract_tool_result(result)
        return None


class LimitsMCPClient(MCPClient):
    """Client for Limits MCP server."""
    
    async def get_account_limits(self, account_id: str) -> Optional[Dict]:
        """Get transaction limits for an account."""
        result = await self.call_tool("getAccountLimits", {"accountId": account_id})
        if result:
            return self._extract_tool_result(result)
        return None


# Singleton instances
_account_client: Optional[AccountMCPClient] = None
_transaction_client: Optional[TransactionMCPClient] = None
_contacts_client: Optional[ContactsMCPClient] = None
_limits_client: Optional[LimitsMCPClient] = None


def get_account_mcp_client(url: str = None) -> AccountMCPClient:
    """Get or create Account MCP client singleton."""
    global _account_client
    if _account_client is None:
        if url is None:
            url = os.getenv("ACCOUNT_MCP_URL", "https://account-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io")
        _account_client = AccountMCPClient(url)
    return _account_client


def get_transaction_mcp_client(url: str = None) -> TransactionMCPClient:
    """Get or create Transaction MCP client singleton."""
    global _transaction_client
    if url is None:
        url = os.getenv("TRANSACTION_MCP_URL", "https://transaction.mangopond-a6402d9f.swedencentral.azurecontainerapps.io")
    if _transaction_client is None:
        _transaction_client = TransactionMCPClient(url)
    return _transaction_client


def get_contacts_mcp_client(url: str = None) -> ContactsMCPClient:
    """Get or create Contacts MCP client singleton."""
    global _contacts_client
    if url is None:
        url = os.getenv("CONTACTS_MCP_URL", "https://contacts-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io")
    if _contacts_client is None:
        _contacts_client = ContactsMCPClient(url)
    return _contacts_client


def get_limits_mcp_client(url: str = None) -> LimitsMCPClient:
    """Get or create Limits MCP client singleton."""
    global _limits_client
    if url is None:
        url = os.getenv("LIMITS_MCP_URL", "https://limits-mcp.mangopond-a6402d9f.swedencentral.azurecontainerapps.io")
    if _limits_client is None:
        _limits_client = LimitsMCPClient(url)
    return _limits_client
