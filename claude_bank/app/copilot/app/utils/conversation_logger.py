"""
Conversation Logger Utility
Stores question-answer pairs for observability dashboard
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Base directory for conversation logs
CONVERSATION_DIR = Path(__file__).parent.parent.parent.parent / "question-answer"

class ConversationLogger:
    """Logger for storing Q&A conversations by session"""
    
    def __init__(self):
        """Initialize conversation logger"""
        # Ensure directory exists
        CONVERSATION_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"📁 ConversationLogger initialized - Storage: {CONVERSATION_DIR}")
    
    def _get_session_file(self, session_id: str) -> Path:
        """Get file path for a session"""
        # Sanitize session_id for filename
        safe_session_id = session_id.replace("/", "_").replace("\\", "_")
        return CONVERSATION_DIR / f"session_{safe_session_id}.json"
    
    def _load_session(self, session_id: str) -> Dict:
        """Load existing session data or create new"""
        file_path = self._get_session_file(session_id)
        
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"❌ Error loading session {session_id}: {e}")
                return self._create_new_session(session_id)
        else:
            return self._create_new_session(session_id)
    
    def _create_new_session(self, session_id: str) -> Dict:
        """Create new session structure"""
        return {
            "session_id": session_id,
            "customer_id": None,
            "user_email": None,
            "started_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "conversation": []
        }
    
    def _save_session(self, session_id: str, data: Dict):
        """Save session data to file"""
        file_path = self._get_session_file(session_id)
        
        try:
            # Update last_updated timestamp
            data["last_updated"] = datetime.now().isoformat()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Saved conversation for session {session_id}")
        except Exception as e:
            logger.error(f"❌ Error saving session {session_id}: {e}", exc_info=True)
    
    def log_qa_pair(
        self,
        session_id: str,
        question: str,
        answer: str,
        agent_used: Optional[str] = None,
        thinking_steps: Optional[List[Dict]] = None,
        duration_seconds: Optional[float] = None,
        customer_id: Optional[str] = None,
        user_email: Optional[str] = None
    ):
        """
        Log a question-answer pair to the session
        
        Args:
            session_id: Thread ID or session identifier
            question: User's question
            answer: AI's answer
            agent_used: Name of specialist agent used
            thinking_steps: List of thinking process steps
            duration_seconds: Time taken to generate response
            customer_id: Customer identifier
            user_email: User's email
        """
        try:
            logger.info(f"📝 Logging Q&A pair for session {session_id}")
            
            # Load existing session
            session_data = self._load_session(session_id)
            
            # Update customer info if provided
            if customer_id and not session_data.get("customer_id"):
                session_data["customer_id"] = customer_id
            if user_email and not session_data.get("user_email"):
                session_data["user_email"] = user_email
            
            # Create Q&A entry
            qa_entry = {
                "question": question,
                "answer": answer,
                "timestamp": datetime.now().isoformat(),
                "agent_used": agent_used,
                "duration_seconds": duration_seconds
            }
            
            # Add thinking steps if provided
            if thinking_steps:
                qa_entry["thinking_steps"] = thinking_steps
            
            # Append to conversation
            session_data["conversation"].append(qa_entry)
            
            # Save to file
            self._save_session(session_id, session_data)
            
            logger.info(f"✅ Successfully logged Q&A pair (total pairs: {len(session_data['conversation'])})")
            
        except Exception as e:
            logger.error(f"❌ Error logging Q&A pair: {e}", exc_info=True)
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get conversation data for a session"""
        file_path = self._get_session_file(session_id)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"❌ Error reading session {session_id}: {e}")
            return None
    
    def list_sessions(self, limit: Optional[int] = None) -> List[Dict]:
        """
        List all conversation sessions
        
        Args:
            limit: Maximum number of sessions to return (most recent first)
        
        Returns:
            List of session metadata
        """
        try:
            sessions = []
            
            # Get all session files
            for file_path in CONVERSATION_DIR.glob("session_*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Create metadata summary
                    sessions.append({
                        "session_id": data.get("session_id"),
                        "customer_id": data.get("customer_id"),
                        "user_email": data.get("user_email"),
                        "started_at": data.get("started_at"),
                        "last_updated": data.get("last_updated"),
                        "message_count": len(data.get("conversation", []))
                    })
                except Exception as e:
                    logger.error(f"❌ Error reading session file {file_path}: {e}")
            
            # Sort by last_updated (most recent first)
            sessions.sort(key=lambda x: x.get("last_updated", ""), reverse=True)
            
            # Apply limit if specified
            if limit:
                sessions = sessions[:limit]
            
            return sessions
            
        except Exception as e:
            logger.error(f"❌ Error listing sessions: {e}", exc_info=True)
            return []


# Global instance
_conversation_logger: Optional[ConversationLogger] = None

def get_conversation_logger() -> ConversationLogger:
    """Get global conversation logger instance"""
    global _conversation_logger
    if _conversation_logger is None:
        _conversation_logger = ConversationLogger()
    return _conversation_logger
