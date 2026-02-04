"""
Conversation State Manager
Tracks active agents per customer to enable conversation continuity
"""
import time
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class ConversationState:
    """State of an active conversation"""
    thread_id: str
    agent_name: str
    agent_instance: Any  # The actual agent instance
    last_activity: float  # timestamp
    customer_id: str
    message_count: int = 0
    

class ConversationStateManager:
    """
    Manages active conversation states to enable multi-turn conversations
    without re-routing through Supervisor.
    
    Uses customer_id as the primary key to handle cases where frontend
    sends different thread_ids between requests.
    """
    
    def __init__(self, ttl_minutes: int = 5):
        """
        Initialize conversation state manager.
        
        Args:
            ttl_minutes: Time-to-live for inactive conversations (default: 5 minutes)
        """
        self._active_conversations_by_customer: Dict[str, ConversationState] = {}
        self._ttl_seconds = ttl_minutes * 60
        print(f"✅ [CONVERSATION STATE] Initialized with {ttl_minutes}min TTL (customer-based)")
        
    def set_active_agent(
        self, 
        thread_id: str, 
        agent_name: str, 
        agent_instance: Any,
        customer_id: str
    ) -> None:
        """
        Store the active agent for a customer.
        
        Args:
            thread_id: Azure thread ID (may be None or change between requests)
            agent_name: Name of the agent (e.g., 'PaymentAgent')
            agent_instance: The actual agent instance
            customer_id: Customer identifier (used as primary key)
        """
        if not customer_id:
            print(f"⚠️ [CONVERSATION STATE] Cannot store agent without customer_id")
            return
        
        # Check if customer already has an active conversation
        if customer_id in self._active_conversations_by_customer:
            state = self._active_conversations_by_customer[customer_id]
            old_thread = state.thread_id
            old_agent = state.agent_name
            state.thread_id = thread_id or old_thread  # Keep old thread if new one is None
            state.agent_name = agent_name
            state.agent_instance = agent_instance
            state.last_activity = time.time()
            state.message_count += 1
            print(f"🔄 [CONVERSATION STATE] Updated for customer {customer_id}: {old_agent} → {agent_name} (msg #{state.message_count}, thread: {thread_id or 'none'})")
        else:
            state = ConversationState(
                thread_id=thread_id or "",
                agent_name=agent_name,
                agent_instance=agent_instance,
                last_activity=time.time(),
                customer_id=customer_id,
                message_count=1
            )
            self._active_conversations_by_customer[customer_id] = state
            print(f"✅ [CONVERSATION STATE] Created for customer {customer_id}: {agent_name} (thread: {thread_id or 'pending'})")
    
    def get_active_agent(self, customer_id: str) -> Optional[Tuple[str, Any, str]]:
        """
        Get the active agent for a customer if it exists and hasn't expired.
        
        Args:
            customer_id: Customer identifier
            
        Returns:
            Tuple of (agent_name, agent_instance, thread_id) or None if no active agent
        """
        if not customer_id or customer_id not in self._active_conversations_by_customer:
            return None
            
        state = self._active_conversations_by_customer[customer_id]
        
        # Check if conversation has expired
        age_seconds = time.time() - state.last_activity
        if age_seconds > self._ttl_seconds:
            print(f"⏰ [CONVERSATION STATE] Customer {customer_id} conversation expired ({age_seconds:.0f}s > {self._ttl_seconds}s)")
            del self._active_conversations_by_customer[customer_id]
            return None
        
        # Update last activity
        state.last_activity = time.time()
        print(f"⚡ [CONVERSATION STATE] Found active {state.agent_name} for customer {customer_id} (age: {age_seconds:.1f}s, msg #{state.message_count})")
        
        return (state.agent_name, state.agent_instance, state.thread_id)
    
    def clear_conversation(self, customer_id: str) -> None:
        """
        Clear conversation state for a customer.
        
        Args:
            customer_id: Customer identifier
        """
        if customer_id and customer_id in self._active_conversations_by_customer:
            agent_name = self._active_conversations_by_customer[customer_id].agent_name
            del self._active_conversations_by_customer[customer_id]
            print(f"🗑️ [CONVERSATION STATE] Cleared {agent_name} for customer {customer_id}")
    
    def cleanup_expired(self) -> int:
        """
        Remove expired conversations.
        
        Returns:
            Number of conversations cleaned up
        """
        now = time.time()
        expired_customers = [
            customer_id for customer_id, state in self._active_conversations_by_customer.items()
            if (now - state.last_activity) > self._ttl_seconds
        ]
        
        for customer_id in expired_customers:
            agent_name = self._active_conversations_by_customer[customer_id].agent_name
            del self._active_conversations_by_customer[customer_id]
            print(f"🧹 [CONVERSATION STATE] Expired {agent_name} for customer {customer_id}")
        
        return len(expired_customers)
    
    def get_active_conversations(self) -> Dict[str, ConversationState]:
        """Get all active conversations (for debugging/monitoring)"""
        return self._active_conversations_by_customer.copy()


def is_continuation_message(user_message: str) -> bool:
    """
    Detect if a message is a continuation/confirmation of a previous conversation.
    
    Args:
        user_message: The user's message
        
    Returns:
        True if the message appears to be a continuation/confirmation
    """
    message_lower = user_message.lower().strip()
    
    # Confirmation keywords
    confirmation_keywords = [
        "yes", "yeah", "yep", "yup", "ok", "okay", "confirm", "confirmed",
        "proceed", "continue", "go ahead", "do it", "sure", "correct",
        "right", "exactly", "that's right", "affirmative"
    ]
    
    # Negation keywords
    negation_keywords = [
        "no", "nope", "cancel", "stop", "abort", "nevermind", "never mind",
        "don't", "do not", "incorrect", "wrong"
    ]
    
    # Option selection patterns (e.g., "option 1", "choice A", "pick 2")
    option_patterns = [
        "option", "choice", "pick", "select", "number", "#"
    ]
    
    # Check for confirmation keywords
    for keyword in confirmation_keywords:
        if keyword == message_lower or message_lower.startswith(keyword + " ") or message_lower.startswith(keyword + ","):
            print(f"🔍 [CONTINUATION CHECK] '{user_message}' → CONTINUATION (matched: {keyword})")
            return True
    
    # Check for negation keywords (also continuations)
    for keyword in negation_keywords:
        if keyword == message_lower or message_lower.startswith(keyword + " ") or message_lower.startswith(keyword + ","):
            print(f"🔍 [CONTINUATION CHECK] '{user_message}' → CONTINUATION (matched negation: {keyword})")
            return True
    
    # Check for option selection patterns
    for pattern in option_patterns:
        if pattern in message_lower and len(message_lower) < 20:  # Short messages like "option 1"
            print(f"🔍 [CONTINUATION CHECK] '{user_message}' → CONTINUATION (option selection)")
            return True
    
    print(f"🔍 [CONTINUATION CHECK] '{user_message}' → NEW QUERY")
    return False


# Global singleton instance
_state_manager: Optional[ConversationStateManager] = None

def get_conversation_state_manager() -> ConversationStateManager:
    """Get the global conversation state manager instance."""
    global _state_manager
    if _state_manager is None:
        _state_manager = ConversationStateManager(ttl_minutes=5)
    return _state_manager
