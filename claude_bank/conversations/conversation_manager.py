"""
Conversation Manager for BankX Multi-Agent System
Handles conversation storage and retrieval using JSON files with thread lifecycle management.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import filelock
import logging
import threading
import time

logger = logging.getLogger(__name__)

class ConversationManager:
    """Manages conversation storage with thread-safe operations and lifecycle tracking."""
    
    def __init__(self, storage_path: str = None, cosmos_sync=None):
        if storage_path is None:
            # Environment detection: Docker vs Local
            import os
            if os.path.exists("/.dockerenv") or os.path.exists("/app/conversations"):
                # Docker: Use Azure Files mount point
                storage_path = "/app/conversations"
            else:
                # Local: Use current directory (conversations/)
                storage_path = str(Path(__file__).parent)
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(exist_ok=True)
        
        # Thread lifecycle tracking
        self.active_threads: Dict[str, datetime] = {}  # thread_id -> last_activity
        self.thread_inactivity_timeout = timedelta(minutes=5)  # 5-minute timeout
        self.cosmos_sync = cosmos_sync
        
        # Background monitoring
        self._monitoring_active = True
        self._monitor_thread = threading.Thread(target=self._monitor_thread_lifecycle, daemon=True)
        self._monitor_thread.start()
        
        logger.info(f"ConversationManager initialized with storage: {self.storage_path}")
        if cosmos_sync:
            logger.info("✅ Cosmos DB sync enabled")
        else:
            logger.info("⚠️ Cosmos DB sync disabled")
    
    def create_session(self, session_id: str = None) -> str:
        """Create a new conversation session."""
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        session_file = self.storage_path / f"{session_id}.json"
        
        conversation_data = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "metadata": {
                "azure_thread_id": None,
                "agent_types": [],
                "banking_operations": []
            }
        }
        
        # Use file locking for thread safety
        lock_file = session_file.with_suffix('.lock')
        with filelock.FileLock(str(lock_file)):
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(conversation_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Created new conversation session: {session_id}")
        return session_id
    
    def get_conversation(self, session_id: str) -> Optional[Dict]:
        """Retrieve a conversation by session ID."""
        session_file = self.storage_path / f"{session_id}.json"
        
        if not session_file.exists():
            return None
        
        lock_file = session_file.with_suffix('.lock')
        try:
            with filelock.FileLock(str(lock_file)):
                with open(session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error reading conversation {session_id}: {e}")
            return None
    
    def add_message(self, session_id: str, role: str, content: str, azure_thread_id: str = None, metadata: Dict = None):
        """Add a message to the conversation and update thread activity."""
        session_file = self.storage_path / f"{session_id}.json"
        
        if not session_file.exists():
            logger.warning(f"Session {session_id} not found, creating new one")
            self.create_session(session_id)
        
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {}
        }
        
        lock_file = session_file.with_suffix('.lock')
        with filelock.FileLock(str(lock_file)):
            # Read current conversation
            with open(session_file, 'r', encoding='utf-8') as f:
                conversation = json.load(f)
            
            # Update azure_thread_id if provided
            if azure_thread_id and not conversation["metadata"]["azure_thread_id"]:
                conversation["metadata"]["azure_thread_id"] = azure_thread_id
            
            # Add message
            conversation["messages"].append(message)
            conversation["updated_at"] = datetime.now().isoformat()
            
            # Write back
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(conversation, f, indent=2, ensure_ascii=False)
        
        # Update thread activity tracking
        self.update_thread_activity(session_id)
        
        logger.debug(f"Added {role} message to session {session_id}")
    
    def log_banking_operation(self, session_id: str, operation_type: str, details: Dict):
        """Log a banking operation to the conversation metadata."""
        session_file = self.storage_path / f"{session_id}.json"
        
        if not session_file.exists():
            logger.warning(f"Session {session_id} not found for banking operation log")
            return
        
        operation = {
            "timestamp": datetime.now().isoformat(),
            "type": operation_type,
            "details": details
        }
        
        lock_file = session_file.with_suffix('.lock')
        with filelock.FileLock(str(lock_file)):
            # Read current conversation
            with open(session_file, 'r', encoding='utf-8') as f:
                conversation = json.load(f)
            
            # Add banking operation
            conversation["metadata"]["banking_operations"].append(operation)
            conversation["updated_at"] = datetime.now().isoformat()
            
            # Write back
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(conversation, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Logged banking operation {operation_type} for session {session_id}")
    
    def log_error(self, session_id: str, error_type: str, error_details: str):
        """Log an error to the conversation metadata."""
        self.log_banking_operation(session_id, f"error_{error_type}", {"error": error_details})
    
    def list_sessions(self) -> List[str]:
        """List all conversation session IDs."""
        return [f.stem for f in self.storage_path.glob("*.json") if not f.name.endswith('.lock')]
    
    def delete_session(self, session_id: str, force_cosmos_sync: bool = False) -> bool:
        """Delete a conversation session, optionally syncing to Cosmos DB first."""
        if force_cosmos_sync and self.cosmos_sync and session_id in self.active_threads:
            # Force sync before deletion
            self.mark_thread_complete(session_id)
        
        session_file = self.storage_path / f"{session_id}.json"
        lock_file = session_file.with_suffix('.lock')
        
        try:
            if session_file.exists():
                session_file.unlink()
            if lock_file.exists():
                lock_file.unlink()
            
            # Remove from thread tracking
            if session_id in self.active_threads:
                del self.active_threads[session_id]
            
            logger.info(f"Deleted conversation session: {session_id}")
            return True
        except OSError as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False
    
    def update_thread_activity(self, session_id: str):
        """Update the last activity timestamp for a thread."""
        self.active_threads[session_id] = datetime.now()
        logger.debug(f"Updated thread activity: {session_id}")
    
    def mark_thread_complete(self, session_id: str):
        """Mark a thread as complete and sync to Cosmos DB."""
        if not self.cosmos_sync:
            logger.debug(f"No Cosmos sync configured for thread: {session_id}")
            return
        
        # Get conversation data
        conversation_data = self.get_conversation(session_id)
        if not conversation_data:
            logger.warning(f"Cannot sync thread {session_id} - conversation not found")
            return
        
        # Add completion timestamp
        conversation_data["completed_at"] = datetime.now().isoformat()
        
        # Queue for Cosmos DB sync
        self.cosmos_sync.queue_thread_sync(session_id, conversation_data)
        
        # Remove from active threads
        if session_id in self.active_threads:
            del self.active_threads[session_id]
        
        logger.info(f"🏁 Marked thread complete and queued for sync: {session_id}")
    
    def check_inactive_threads(self) -> List[str]:
        """Check for inactive threads and mark them complete."""
        now = datetime.now()
        inactive_threads = []
        
        for thread_id, last_activity in list(self.active_threads.items()):
            if now - last_activity > self.thread_inactivity_timeout:
                logger.info(f"⏰ Thread inactive for {self.thread_inactivity_timeout}: {thread_id}")
                self.mark_thread_complete(thread_id)
                inactive_threads.append(thread_id)
        
        return inactive_threads
    
    def _monitor_thread_lifecycle(self):
        """Background thread to monitor thread lifecycle and trigger sync."""
        while self._monitoring_active:
            try:
                inactive_threads = self.check_inactive_threads()
                if inactive_threads:
                    logger.info(f"📦 Processed {len(inactive_threads)} inactive threads")
                
                # Sleep for 30 seconds before next check
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"❌ Error in thread lifecycle monitoring: {e}")
                time.sleep(60)  # Longer sleep on error
    
    def shutdown(self):
        """Shutdown the conversation manager and sync all active threads."""
        logger.info("🔄 Shutting down ConversationManager...")
        
        # Stop monitoring thread
        self._monitoring_active = False
        
        # Force sync all active threads
        if self.cosmos_sync and self.active_threads:
            logger.info(f"🔄 Force syncing {len(self.active_threads)} active threads")
            for thread_id in list(self.active_threads.keys()):
                self.mark_thread_complete(thread_id)
            
            # Wait for sync to complete
            self.cosmos_sync.force_sync_all()
        
        logger.info("✅ ConversationManager shutdown complete")
    
    def get_active_threads_status(self) -> Dict[str, Any]:
        """Get status of active threads for monitoring."""
        now = datetime.now()
        thread_status = {}
        
        for thread_id, last_activity in self.active_threads.items():
            age_minutes = (now - last_activity).total_seconds() / 60
            thread_status[thread_id] = {
                "last_activity": last_activity.isoformat(),
                "age_minutes": round(age_minutes, 2),
                "will_timeout_in": max(0, (self.thread_inactivity_timeout.total_seconds() / 60) - age_minutes)
            }
        
        return {
            "active_thread_count": len(self.active_threads),
            "threads": thread_status,
            "cosmos_sync_status": self.cosmos_sync.get_sync_status() if self.cosmos_sync else None
        }


# Global conversation manager instance
_conversation_manager = None

def get_conversation_manager() -> ConversationManager:
    """Get the global conversation manager instance with Cosmos DB sync if configured."""
    global _conversation_manager
    if _conversation_manager is None:
        # Try to initialize Cosmos DB sync
        cosmos_sync = None
        try:
            from cosmos_sync import create_cosmos_sync_from_env
            cosmos_sync = create_cosmos_sync_from_env()
        except ImportError:
            logger.warning("⚠️ cosmos_sync module not available")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize Cosmos DB sync: {e}")
        
        _conversation_manager = ConversationManager(cosmos_sync=cosmos_sync)
    return _conversation_manager