"""
MCP Data Fetcher
Automatically triggers MCP servers and populates session cache on user login.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MCPDataFetcher:
    """
    Fetches data from MCP servers and populates session cache.
    
    Triggered on:
    - User login/session start
    - Periodic refresh (every 5 minutes)
    - Manual refresh request
    """
    
    def __init__(self):
        """Initialize the MCP data fetcher."""
        self.is_fetching = False
        logger.info("✅ MCPDataFetcher initialized")
    
    async def fetch_account_data(self, user_email: str) -> Optional[Dict[str, Any]]:
        """
        Fetch account data from Account MCP server.
        
        Args:
            user_email: User's email address
            
        Returns:
            Account data or None if error
        """
        try:
            from app.config.settings import settings
            import httpx
            
            logger.info(f"📊 Fetching account data for {user_email}")
            
            if not settings.ACCOUNT_MCP_URL:
                logger.warning("ACCOUNT_MCP_URL not configured, using placeholder data")
                return {
                    "account_id": "CHK-001",
                    "account_holder": user_email,
                    "balance": 99650.00,
                    "currency": "THB",
                    "account_type": "checking",
                    "fetched_at": datetime.now().isoformat()
                }
            
            url = f"{settings.ACCOUNT_MCP_URL}/mcp"
            
            # MCP protocol request format
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_customer_accounts",
                    "arguments": {
                        "customer_id": user_email
                    }
                },
                "id": 1
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                if "result" in result:
                    account_data = result["result"]
                    account_data["fetched_at"] = datetime.now().isoformat()
                    logger.info(f"✅ Account data fetched for {user_email}")
                    return account_data
                elif "error" in result:
                    logger.error(f"MCP error: {result['error']}")
                    return None
                    
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching account data: {e}", exc_info=True)
            return None
    
    async def fetch_transaction_history(self, user_email: str, limit: int = 20) -> Optional[list]:
        """
        Fetch transaction history from Transaction MCP server.
        
        Args:
            user_email: User's email address
            limit: Number of transactions to fetch
            
        Returns:
            List of transactions or None if error
        """
        try:
            from app.config.settings import settings
            import httpx
            
            logger.info(f"📊 Fetching transaction history for {user_email}")
            
            if not settings.TRANSACTION_MCP_URL:
                logger.warning("TRANSACTION_MCP_URL not configured, using placeholder data")
                return [{
                    "transaction_id": "TXN-001",
                    "date": "2025-11-15",
                    "description": "Transfer to Somchai",
                    "amount": 500.00,
                    "type": "debit",
                    "recipient": "Somchai Rattanakorn"
                }]
            
            url = f"{settings.TRANSACTION_MCP_URL}/mcp"
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_transaction_history",
                    "arguments": {
                        "customer_id": user_email,
                        "limit": limit
                    }
                },
                "id": 2
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                if "result" in result:
                    logger.info(f"✅ Transaction history fetched for {user_email}")
                    return result["result"] if isinstance(result["result"], list) else []
                elif "error" in result:
                    logger.error(f"MCP error: {result['error']}")
                    return None
                    
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching transaction history: {e}", exc_info=True)
            return None
    
    async def fetch_beneficiaries(self, user_email: str) -> Optional[list]:
        """
        Fetch registered beneficiaries from Beneficiary MCP server.
        
        Args:
            user_email: User's email address
            
        Returns:
            List of beneficiaries or None if error
        """
        try:
            from app.config.settings import settings
            import httpx
            
            logger.info(f"📊 Fetching beneficiaries for {user_email}")
            
            # Beneficiaries might be in contacts or payment MCP server
            if not settings.PAYMENT_MCP_URL:
                logger.warning("PAYMENT_MCP_URL not configured, using placeholder data")
                return [{
                    "beneficiary_id": "BEN-001",
                    "name": "Nattaporn Suksawat",
                    "account_number": "123-456-002",
                    "nickname": "Nat"
                }]
            
            url = f"{settings.PAYMENT_MCP_URL}/mcp"
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_beneficiaries",
                    "arguments": {
                        "customer_id": user_email
                    }
                },
                "id": 3
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                if "result" in result:
                    logger.info(f"✅ Beneficiaries fetched for {user_email}")
                    return result["result"] if isinstance(result["result"], list) else []
                elif "error" in result:
                    logger.error(f"MCP error: {result['error']}")
                    return None
                    
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching beneficiaries: {e}", exc_info=True)
            return None
    
    async def fetch_payment_methods(self, user_email: str) -> Optional[list]:
        """
        Fetch payment methods from Account MCP server.
        
        Args:
            user_email: User's email address
            
        Returns:
            List of payment methods or None if error
        """
        try:
            from app.config.settings import settings
            import httpx
            
            logger.info(f"📊 Fetching payment methods for {user_email}")
            
            if not settings.PAYMENT_MCP_URL:
                logger.warning("PAYMENT_MCP_URL not configured, using placeholder data")
                return [{
                    "method_id": "PM-CHK-001",
                    "name": "Bank Transfer",
                    "account_id": "CHK-001"
                }]
            
            url = f"{settings.PAYMENT_MCP_URL}/mcp"
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_payment_methods",
                    "arguments": {
                        "customer_id": user_email
                    }
                },
                "id": 4
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                if "result" in result:
                    logger.info(f"✅ Payment methods fetched for {user_email}")
                    return result["result"] if isinstance(result["result"], list) else []
                elif "error" in result:
                    logger.error(f"MCP error: {result['error']}")
                    return None
                    
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching payment methods: {e}", exc_info=True)
            return None
    
    async def fetch_limits(self, user_email: str) -> Optional[Dict[str, Any]]:
        """
        Fetch account limits from Limits MCP server.
        
        Args:
            user_email: User's email address
            
        Returns:
            Limits data or None if error
        """
        try:
            logger.info(f"📊 Fetching limits for {user_email}")
            
            from app.config.settings import settings
            import httpx
            
            if not settings.LIMITS_MCP_URL:
                logger.warning("LIMITS_MCP_URL not configured, using placeholder data")
                return {
                    "daily_limit": 200000.00,
                    "per_transaction_limit": 50000.00,
                    "daily_remaining": 200000.00,
                    "currency": "THB"
                }
            
            url = f"{settings.LIMITS_MCP_URL}/mcp"
            payload = {
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "get_limits",
                    "arguments": {
                        "customer_id": user_email
                    }
                },
                "id": 5
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                if "result" in result:
                    logger.info(f"✅ Limits fetched for {user_email}")
                    return result["result"]
                elif "error" in result:
                    logger.error(f"MCP error: {result['error']}")
                    return None
                    
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching limits: {e}", exc_info=True)
            return None
    
    async def fetch_all_data(self, user_email: str) -> Dict[str, Any]:
        """
        Fetch all data from all MCP servers sequentially.
        Account data first, then others in parallel.
        
        Args:
            user_email: User's email address
            
        Returns:
            Dictionary with all fetched data
        """
        if self.is_fetching:
            logger.warning("⚠️  Fetch already in progress, skipping")
            return {}
        
        self.is_fetching = True
        logger.info(f"🚀 Starting data fetch for {user_email}")
        
        try:
            # Step 1: Fetch account data first (priority)
            account_data = await self.fetch_account_data(user_email)
            
            # Step 2: Fetch other data in parallel
            results = await asyncio.gather(
                self.fetch_transaction_history(user_email),
                self.fetch_beneficiaries(user_email),
                self.fetch_payment_methods(user_email),
                self.fetch_limits(user_email),
                return_exceptions=True
            )
            
            transaction_history, beneficiaries, payment_methods, limits = results
            
            # Build cache data
            cache_data = {
                "account_data": account_data,
                "transaction_history": transaction_history if not isinstance(transaction_history, Exception) else None,
                "beneficiaries": beneficiaries if not isinstance(beneficiaries, Exception) else None,
                "payment_methods": payment_methods if not isinstance(payment_methods, Exception) else None,
                "limits": limits if not isinstance(limits, Exception) else None,
            }
            
            logger.info(f"✅ All data fetched for {user_email}")
            return cache_data
        except Exception as e:
            logger.error(f"❌ Error in fetch_all_data: {e}")
            return {}
        finally:
            self.is_fetching = False
    
    async def populate_session_cache(self, session_id: str, user_email: str) -> bool:
        """
        Fetch all MCP data and populate session cache.
        
        Args:
            session_id: Session identifier
            user_email: User's email address
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from app.utils.session_memory import get_session_manager
            
            logger.info(f"🔄 Populating cache for session {session_id}")
            
            # Fetch all data
            cache_data = await self.fetch_all_data(user_email)
            
            # Update session cache
            session_manager = get_session_manager()
            
            for key, value in cache_data.items():
                if value is not None:
                    session_manager.update_session_cache(session_id, key, value)
            
            logger.info(f"✅ Session cache populated for {session_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error populating session cache: {e}")
            return False


# Global instance
_mcp_fetcher: Optional[MCPDataFetcher] = None


def get_mcp_fetcher() -> MCPDataFetcher:
    """
    Get the global MCP data fetcher instance.
    
    Returns:
        MCPDataFetcher instance
    """
    global _mcp_fetcher
    if _mcp_fetcher is None:
        _mcp_fetcher = MCPDataFetcher()
    return _mcp_fetcher


def init_mcp_fetcher() -> MCPDataFetcher:
    """
    Initialize the global MCP data fetcher.
    
    Returns:
        MCPDataFetcher instance
    """
    global _mcp_fetcher
    _mcp_fetcher = MCPDataFetcher()
    return _mcp_fetcher
