"""
API endpoints for conversation retrieval from conversations/ folder
"""
from fastapi import APIRouter, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import json
import os

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

# Environment-aware path resolution
def get_base_dir() -> Path:
    """Get base directory - works in both local and Docker environments"""
    # Check if /app/conversations exists (Docker/Azure environment)
    if Path("/app/conversations").exists():
        return Path("/app")
    # Check for .dockerenv file (standard Docker)
    elif os.path.exists("/.dockerenv"):
        return Path("/app")
    # Local development - go up from app/copilot/app/api/ to project root
    else:
        return Path(__file__).parent.parent.parent.parent.parent

CONVERSATIONS_DIR = get_base_dir() / "conversations"

class Message(BaseModel):
    """Single message in a conversation"""
    timestamp: str
    role: str  # 'user' or 'assistant'
    content: str
    metadata: Dict[str, Any] = {}

class BankingOperation(BaseModel):
    """Banking operation metadata"""
    timestamp: str
    type: str
    details: Dict[str, Any]

class ConversationMetadata(BaseModel):
    """Conversation metadata"""
    azure_thread_id: str
    agent_types: List[str] = []
    banking_operations: List[BankingOperation] = []

class ConversationSession(BaseModel):
    """Full conversation session"""
    session_id: str
    created_at: str
    updated_at: str
    messages: List[Message]
    metadata: ConversationMetadata

class SessionSummary(BaseModel):
    """Conversation session summary for list view"""
    session_id: str
    created_at: str
    updated_at: str
    message_count: int
    agent_operations_count: int


@router.get("/", response_model=List[SessionSummary])
async def list_conversations(
    limit: Optional[int] = 50,
    min_messages: Optional[int] = 3  # Filter conversations with 3+ messages
):
    """
    List all conversation sessions from conversations/ folder
    
    Args:
        limit: Maximum number of sessions to return (default 50)
        min_messages: Minimum number of messages to include (default 3)
    
    Returns:
        List of session summaries
    """
    try:
        print(f"📂 [CONVERSATIONS API] Reading from: {CONVERSATIONS_DIR}")
        print(f"🔍 [CONVERSATIONS API] Filter: min_messages={min_messages}, limit={limit}")
        
        if not CONVERSATIONS_DIR.exists():
            print(f"⚠️ [CONVERSATIONS API] Directory not found: {CONVERSATIONS_DIR}")
            return []
        
        # Get all conversation files (both thread_*.json and session_*.json)
        thread_files = list(CONVERSATIONS_DIR.glob("thread_*.json"))
        session_files = list(CONVERSATIONS_DIR.glob("session_*.json"))
        
        # Combine and sort by modification time
        all_files = thread_files + session_files
        conversation_files = sorted(
            all_files,
            key=lambda p: p.stat().st_mtime,
            reverse=True  # Most recent first
        )
        
        print(f"📊 [CONVERSATIONS API] Found {len(thread_files)} thread files, {len(session_files)} session files")
        print(f"📊 [CONVERSATIONS API] Total {len(conversation_files)} conversation files")
        
        summaries = []
        for file_path in conversation_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                message_count = len(data.get("messages", []))
                
                # Filter by minimum messages
                if message_count < min_messages:
                    print(f"⏭️ [CONVERSATIONS API] Skipping {file_path.name}: only {message_count} messages")
                    continue
                
                summary = SessionSummary(
                    session_id=data.get("session_id", ""),
                    created_at=data.get("created_at", ""),
                    updated_at=data.get("updated_at", ""),
                    message_count=message_count,
                    agent_operations_count=len(data.get("metadata", {}).get("banking_operations", []))
                )
                summaries.append(summary)
                print(f"✅ [CONVERSATIONS API] Loaded: {summary.session_id} ({summary.message_count} messages)")
                
                # Stop if we've reached the limit
                if len(summaries) >= limit:
                    break
                
            except Exception as e:
                print(f"❌ [CONVERSATIONS API] Error reading {file_path.name}: {e}")
                continue
        
        print(f"🏁 [CONVERSATIONS API] Returning {len(summaries)} summaries (filtered from {len(conversation_files)} total)")
        return summaries
        
    except Exception as e:
        print(f"❌ [CONVERSATIONS API] Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Error listing conversations: {str(e)}")


@router.get("/{session_id}", response_model=ConversationSession)
async def get_conversation(
    session_id: str
):
    """
    Get full conversation for a specific session from conversations/ folder
    
    Args:
        session_id: Thread ID (e.g., thread_HRJibyNMeUPqW6zcsmYmVD4S)
    
    Returns:
        Full conversation data with messages and metadata
    """
    try:
        print(f"🔍 [CONVERSATIONS API] Fetching session: {session_id}")
        
        # Construct file path
        file_path = CONVERSATIONS_DIR / f"{session_id}.json"
        
        if not file_path.exists():
            print(f"❌ [CONVERSATIONS API] File not found: {file_path}")
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
        
        # Read and parse JSON
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ [CONVERSATIONS API] Loaded session: {session_id}")
        print(f"📊 [CONVERSATIONS API] Messages: {len(data.get('messages', []))}, Operations: {len(data.get('metadata', {}).get('banking_operations', []))}")
        
        # Return data (Pydantic will validate)
        return data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ [CONVERSATIONS API] Error retrieving conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")
