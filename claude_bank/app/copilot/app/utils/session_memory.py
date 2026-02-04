"""
Session Memory Manager for BankX
Handles session-specific caching of MCP server data for improved performance.
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
from threading import Lock
import atexit

logger = logging.getLogger(__name__)

class SessionMemoryManager:
    """
    Manages session-specific memory cache for MCP data.
    
    Features:
    - Session-specific JSON file storage
    - Automatic cache refresh every 5 minutes
    - Cleanup on logout or server shutdown
    - Thread-safe operations
    """
    
    def __init__(self, memory_dir: str = "memory"):
        """
        Initialize the session memory manager.
        
        Args:
            memory_dir: Directory to store session cache files
        """
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(exist_ok=True)
        
        # Active sessions: {session_id: file_path}
        self.active_sessions: Dict[str, Path] = {}
        
        # Locks for thread safety
        self.session_lock = Lock()
        
        # Background refresh task
        self.refresh_task: Optional[asyncio.Task] = None
        
        # Register cleanup on exit
        atexit.register(self.cleanup_all_sessions)
        
        logger.info(f"✅ SessionMemoryManager initialized. Memory dir: {self.memory_dir}")
    
    def create_session(self, user_id: str, session_id: str) -> Path:
        """
        Create a new session cache file.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            
        Returns:
            Path to the created session file
        """
        with self.session_lock:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"session_{user_id}_{timestamp}.json"
            file_path = self.memory_dir / filename
            
            session_data = {
                "user_id": user_id,
                "session_id": session_id,
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "cache": {
                    "account_data": None,
                    "transaction_history": None,
                    "beneficiaries": None,
                    "payment_methods": None,
                    "limits": None,
                }
            }
            
            with open(file_path, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            self.active_sessions[session_id] = file_path
            logger.info(f"✅ Created session cache: {filename} for user {user_id}")
            
            return file_path
    
    def get_session_file(self, session_id: str) -> Optional[Path]:
        """
        Get the file path for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Path to session file or None if not found
        """
        with self.session_lock:
            return self.active_sessions.get(session_id)
    
    def read_session_cache(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Read cache data for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Cached data or None if not found
        """
        file_path = self.get_session_file(session_id)
        if not file_path or not file_path.exists():
            logger.warning(f"⚠️  Session cache not found: {session_id}")
            return None
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return data.get("cache")
        except Exception as e:
            logger.error(f"❌ Error reading session cache {session_id}: {e}")
            return None
    
    def update_session_cache(self, session_id: str, cache_key: str, data: Any) -> bool:
        """
        Update a specific cache entry for a session.
        
        Args:
            session_id: Session identifier
            cache_key: Key to update (e.g., 'account_data', 'beneficiaries')
            data: Data to store
            
        Returns:
            True if successful, False otherwise
        """
        file_path = self.get_session_file(session_id)
        if not file_path or not file_path.exists():
            logger.warning(f"⚠️  Session cache not found: {session_id}")
            return False
        
        try:
            with self.session_lock:
                with open(file_path, 'r') as f:
                    session_data = json.load(f)
                
                session_data["cache"][cache_key] = data
                session_data["last_updated"] = datetime.now().isoformat()
                
                with open(file_path, 'w') as f:
                    json.dump(session_data, f, indent=2)
            
            logger.debug(f"✅ Updated cache key '{cache_key}' for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error updating session cache {session_id}: {e}")
            return False
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session cache file.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False otherwise
        """
        with self.session_lock:
            file_path = self.active_sessions.pop(session_id, None)
            if not file_path:
                logger.warning(f"⚠️  Session not found: {session_id}")
                return False
            
            try:
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"✅ Deleted session cache: {file_path.name}")
                return True
            except Exception as e:
                logger.error(f"❌ Error deleting session cache {session_id}: {e}")
                return False
    
    def cleanup_all_sessions(self):
        """
        Clean up all active session files.
        Called on server shutdown.
        """
        logger.info("🧹 Cleaning up all session caches...")
        with self.session_lock:
            for session_id, file_path in list(self.active_sessions.items()):
                try:
                    if file_path.exists():
                        file_path.unlink()
                        logger.info(f"   Deleted: {file_path.name}")
                except Exception as e:
                    logger.error(f"   Error deleting {file_path.name}: {e}")
            
            self.active_sessions.clear()
        logger.info("✅ Session cleanup complete")
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """
        Clean up session files older than max_age_hours.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
        """
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for file_path in self.memory_dir.glob("session_*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                
                created_at = datetime.fromisoformat(data["created_at"])
                if created_at < cutoff_time:
                    file_path.unlink()
                    logger.info(f"🧹 Cleaned up old session: {file_path.name}")
            except Exception as e:
                logger.error(f"❌ Error cleaning up {file_path.name}: {e}")
    
    async def start_periodic_refresh(self, interval_minutes: int = 5):
        """
        Start background task for periodic cache refresh.
        
        Args:
            interval_minutes: Refresh interval in minutes
        """
        async def refresh_loop():
            while True:
                try:
                    await asyncio.sleep(interval_minutes * 60)
                    logger.info("🔄 Periodic cache refresh triggered")
                    # TODO: Implement actual MCP data refresh
                    # This will be implemented when MCP auto-trigger is added
                except asyncio.CancelledError:
                    logger.info("Cache refresh task cancelled")
                    break
                except Exception as e:
                    logger.error(f"❌ Error in cache refresh: {e}")
        
        self.refresh_task = asyncio.create_task(refresh_loop())
        logger.info(f"✅ Started periodic cache refresh (every {interval_minutes} minutes)")
    
    def stop_periodic_refresh(self):
        """Stop the background refresh task."""
        if self.refresh_task and not self.refresh_task.done():
            self.refresh_task.cancel()
            logger.info("✅ Stopped periodic cache refresh")


# Global instance
_session_manager: Optional[SessionMemoryManager] = None


def get_session_manager() -> SessionMemoryManager:
    """
    Get the global session memory manager instance.
    
    Returns:
        SessionMemoryManager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionMemoryManager()
    return _session_manager


def init_session_manager(memory_dir: str = "memory") -> SessionMemoryManager:
    """
    Initialize the global session memory manager.
    
    Args:
        memory_dir: Directory for session cache files
        
    Returns:
        SessionMemoryManager instance
    """
    global _session_manager
    _session_manager = SessionMemoryManager(memory_dir)
    return _session_manager
