"""
User Cache Manager - JSON-based caching for fast UC1 responses

This module provides:
- JSON file per logged-in user (memory/CUST-XXX.json)
- 5-minute TTL with auto-refresh
- Thread-safe file operations with locking
- Background cleanup of old cache files
- Fallback to MCP servers if cache missing/stale
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional
import logging
import platform
import sys

# Import file locking modules based on platform
if platform.system() == "Windows":
    import msvcrt
else:
    import fcntl

# Add common module to path for environment-aware utilities
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "app" / "common"))
from path_utils import get_base_dir

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_DIR = get_base_dir() / "memory"
CACHE_TTL_SECONDS = 300  # 5 minutes
CACHE_CLEANUP_AGE_SECONDS = 3600  # Delete files older than 1 hour


class UserCacheManager:
    """Manages JSON-based user data caching."""
    
    def __init__(self):
        """Initialize cache manager and ensure cache directory exists."""
        self.cache_dir = CACHE_DIR
        self.cache_dir.mkdir(exist_ok=True)
        logger.info(f"✅ UserCacheManager initialized with cache_dir: {self.cache_dir}")
    
    def _get_cache_path(self, customer_id: str) -> Path:
        """Get cache file path for a customer."""
        return self.cache_dir / f"{customer_id}.json"
    
    def _lock_file(self, file_handle):
        """Cross-platform file locking."""
        if platform.system() == "Windows":
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    
    def _unlock_file(self, file_handle):
        """Cross-platform file unlocking."""
        if platform.system() == "Windows":
            msvcrt.locking(file_handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl.flock(file_handle.fileno(), fcntl.LOCK_UN)
    
    def _is_cache_valid(self, cache_data: Dict[str, Any]) -> bool:
        """Check if cache is still valid based on TTL."""
        cached_at = cache_data.get("cached_at")
        if not cached_at:
            return False
        
        cached_time = datetime.fromisoformat(cached_at)
        age_seconds = (datetime.now() - cached_time).total_seconds()
        
        return age_seconds < CACHE_TTL_SECONDS
    
    async def initialize_user_cache(self, customer_id: str, user_email: str, mcp_clients: Dict[str, Any]) -> Dict[str, Any]:
        """
        Initialize cache for a user by fetching all data from MCP servers.
        
        Args:
            customer_id: Customer ID (e.g., "CUST-002")
            user_email: User's email address (used for MCP calls as userName)
            mcp_clients: Dictionary with MCP client instances
                - account_mcp: AccountMCP client
                - transaction_mcp: TransactionMCP client
                - payment_mcp: PaymentMCP client
                - limits_mcp: LimitsMCP client
        
        Returns:
            Dict containing all cached data
        """
        print(f"\n{'='*80}")
        print(f"[CACHE_INIT] 🔄 Starting cache initialization for {customer_id} ({user_email})")
        print(f"[CACHE_INIT] 📦 MCP clients received: {list(mcp_clients.keys())}")
        print(f"{'='*80}\n")
        logger.info(f"🔄 Initializing cache for {customer_id} ({user_email})")
        
        try:
            # Step 1: Fetch account data first to get primary account ID
            print(f"[CACHE_INIT] 📊 Step 1: Fetching account data...")
            account_data = {}
            primary_account_id = None
            
            if "account_mcp" in mcp_clients:
                print(f"[CACHE_INIT] ✅ account_mcp client found, calling _fetch_account_data...")
                account_data = await self._fetch_account_data(customer_id, user_email, mcp_clients["account_mcp"])
                # Get primary account ID from accounts list
                accounts = account_data.get("accounts", [])
                if accounts and len(accounts) > 0:
                    primary_account_id = accounts[0].get("id")
            
            # Step 2: Fetch other data in parallel using primary account ID
            tasks = []
            
            # Transaction data (needs accountId)
            if "transaction_mcp" in mcp_clients and primary_account_id:
                tasks.append(self._fetch_transaction_data(primary_account_id, mcp_clients["transaction_mcp"]))
            
            # Contacts data (beneficiaries - needs accountId)
            if "contacts_mcp" in mcp_clients and primary_account_id:
                tasks.append(self._fetch_contacts_data(primary_account_id, mcp_clients["contacts_mcp"]))
            
            # Limits data (needs accountId)
            if "limits_mcp" in mcp_clients and primary_account_id:
                tasks.append(self._fetch_limits_data(primary_account_id, mcp_clients["limits_mcp"]))
            
            # Execute all fetches in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Merge results
            cache_data = {
                "customer_id": customer_id,
                "cached_at": datetime.now().isoformat(),
                "ttl_seconds": CACHE_TTL_SECONDS,
                "data": account_data  # Start with account data
            }
            
            # Merge parallel fetch results
            for result in results:
                if isinstance(result, dict) and not isinstance(result, Exception):
                    cache_data["data"].update(result)
                elif isinstance(result, Exception):
                    logger.error(f"❌ Error fetching data for {customer_id}: {result}")
            
            # Write to JSON file with locking
            await self._write_cache(customer_id, cache_data)
            
            logger.info(f"✅ Cache initialized for {customer_id} with {len(cache_data['data'])} data sections")
            return cache_data
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize cache for {customer_id}: {e}")
            raise
    
    async def _fetch_account_data(self, customer_id: str, user_email: str, account_mcp) -> Dict[str, Any]:
        """Fetch account-related data."""
        print(f"[CACHE_INIT] 🏦 _fetch_account_data called for {user_email}")
        try:
            # Call MCP tools to get account data (using email as userName)
            print(f"[CACHE_INIT] 📞 Calling account_mcp.get_accounts_by_username({user_email})...")
            accounts_response = await account_mcp.get_accounts_by_username(user_email)
            
            # Handle both dict response and list response
            if isinstance(accounts_response, dict):
                accounts = accounts_response.get("accounts", [])
            else:
                accounts = accounts_response if accounts_response else []
            
            print(f"[CACHE_INIT] ✅ Got accounts: {len(accounts)} accounts")
            # Get details for primary account if available
            account_id = accounts[0].get("id") if accounts and len(accounts) > 0 else None
            account_details = await account_mcp.get_account_details(account_id) if account_id else None
            
            # Calculate total balance (balance might be string)
            total_balance = 0
            if accounts:
                for acc in accounts:
                    if isinstance(acc, dict):
                        balance = acc.get("balance", 0)
                        # Convert string balance to float
                        if isinstance(balance, str):
                            try:
                                balance = float(balance)
                            except (ValueError, TypeError):
                                balance = 0
                        total_balance += balance
            
            result = {
                "accounts": accounts or [],
                "balance": total_balance,
                "account_details": account_details or {},
                "customer_name": account_details.get("accountHolderFullName") if account_details else None
            }
            print(f"[CACHE_INIT] ✅ Account data fetched successfully: balance={total_balance}, customer={result['customer_name']}")
            return result
        except Exception as e:
            print(f"[CACHE_INIT] ❌ Error fetching account data: {e}")
            import traceback
            print(f"[CACHE_INIT] ❌ Traceback: {traceback.format_exc()}")
            logger.error(f"❌ Error fetching account data: {e}")
            return {}
    
    async def _fetch_transaction_data(self, account_id: str, transaction_mcp) -> Dict[str, Any]:
        """Fetch transaction-related data."""
        try:
            # Get last 5 transactions for account
            transactions = await transaction_mcp.get_transactions(account_id, limit=5)
            last_transaction = transactions[0] if transactions and len(transactions) > 0 else None
            
            return {
                "last_5_transactions": transactions,
                "last_transaction": last_transaction
            }
        except Exception as e:
            logger.error(f"❌ Error fetching transaction data: {e}")
            return {}
    
    async def _fetch_contacts_data(self, account_id: str, contacts_mcp) -> Dict[str, Any]:
        """Fetch contacts-related data (beneficiaries)."""
        try:
            beneficiaries = await contacts_mcp.get_registered_beneficiaries(account_id)
            
            return {
                "beneficiaries": beneficiaries
            }
        except Exception as e:
            logger.error(f"❌ Error fetching contacts data: {e}")
            return {}
    
    async def _fetch_limits_data(self, account_id: str, limits_mcp) -> Dict[str, Any]:
        """Fetch limits-related data."""
        try:
            limits = await limits_mcp.get_account_limits(account_id)
            
            return {
                "limits": limits
            }
        except Exception as e:
            logger.error(f"❌ Error fetching limits data: {e}")
            return {}
    
    async def _write_cache(self, customer_id: str, cache_data: Dict[str, Any]):
        """Write cache data to JSON file with file locking."""
        cache_path = self._get_cache_path(customer_id)
        
        try:
            # Write to temp file first, then atomic rename
            temp_path = cache_path.with_suffix('.tmp')
            
            with open(temp_path, 'w') as f:
                self._lock_file(f)
                try:
                    json.dump(cache_data, f, indent=2)
                finally:
                    self._unlock_file(f)
            
            # Atomic rename
            temp_path.replace(cache_path)
            logger.debug(f"✅ Cache written to {cache_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to write cache for {customer_id}: {e}")
            raise
    
    async def get_cached_data(self, customer_id: str, key: Optional[str] = None) -> Optional[Any]:
        """
        Get cached data for a customer.
        
        Args:
            customer_id: Customer ID
            key: Optional specific key to retrieve (e.g., "balance", "last_5_transactions")
                 If None, returns entire data dictionary
        
        Returns:
            Cached data or None if cache invalid/missing
        """
        cache_path = self._get_cache_path(customer_id)
        
        if not cache_path.exists():
            logger.debug(f"⚠️ No cache file for {customer_id}")
            return None
        
        # Retry mechanism for file locking (Windows can be aggressive with locks)
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                # Read without locking - JSON reads are atomic and we only update via separate writes
                with open(cache_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                # Check if cache is still valid
                if not self._is_cache_valid(cache_data):
                    logger.info(f"⏰ Cache expired for {customer_id}")
                    return None
                
                # Return requested data
                data = cache_data.get("data", {})
                if key:
                    return data.get(key)
                return data
                
            except (OSError, IOError) as e:
                if attempt < max_retries - 1:
                    logger.debug(f"⚠️ Cache read attempt {attempt + 1} failed, retrying: {e}")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"❌ Error reading cache for {customer_id} after {max_retries} attempts: {e}")
                    return None
            except Exception as e:
                logger.error(f"❌ Error reading cache for {customer_id}: {e}")
                return None
        
        return None
    
    async def update_cache(self, customer_id: str, updates: Dict[str, Any]):
        """
        Update specific fields in cache (e.g., after a transaction).
        
        Args:
            customer_id: Customer ID
            updates: Dictionary of fields to update in cache.data
        """
        cache_path = self._get_cache_path(customer_id)
        
        try:
            # Read existing cache
            if cache_path.exists():
                with open(cache_path, 'r') as f:
                    self._lock_file(f)
                    try:
                        cache_data = json.load(f)
                    finally:
                        self._unlock_file(f)
            else:
                # No existing cache, create new
                cache_data = {
                    "customer_id": customer_id,
                    "cached_at": datetime.now().isoformat(),
                    "ttl_seconds": CACHE_TTL_SECONDS,
                    "data": {}
                }
            
            # Update fields
            cache_data["data"].update(updates)
            cache_data["cached_at"] = datetime.now().isoformat()  # Refresh timestamp
            
            # Write back
            await self._write_cache(customer_id, cache_data)
            logger.info(f"✅ Cache updated for {customer_id}: {list(updates.keys())}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update cache for {customer_id}: {e}")
    
    async def invalidate_cache(self, customer_id: str):
        """Delete cache file for a customer."""
        cache_path = self._get_cache_path(customer_id)
        
        try:
            if cache_path.exists():
                cache_path.unlink()
                logger.info(f"🗑️ Cache deleted for {customer_id}")
        except Exception as e:
            logger.error(f"❌ Failed to delete cache for {customer_id}: {e}")
    
    async def cleanup_old_caches(self):
        """Background task: Delete cache files older than 1 hour."""
        logger.info("🧹 Starting cache cleanup task")
        
        try:
            cutoff_time = datetime.now() - timedelta(seconds=CACHE_CLEANUP_AGE_SECONDS)
            deleted_count = 0
            
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                    
                    if mtime < cutoff_time:
                        cache_file.unlink()
                        deleted_count += 1
                        logger.debug(f"🗑️ Deleted old cache: {cache_file.name}")
                
                except Exception as e:
                    logger.error(f"❌ Error deleting {cache_file}: {e}")
            
            logger.info(f"✅ Cache cleanup complete: deleted {deleted_count} old files")
            
        except Exception as e:
            logger.error(f"❌ Cache cleanup failed: {e}")


# Singleton instance
_cache_manager: Optional[UserCacheManager] = None


def get_cache_manager() -> UserCacheManager:
    """Get or create the singleton cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = UserCacheManager()
    return _cache_manager
