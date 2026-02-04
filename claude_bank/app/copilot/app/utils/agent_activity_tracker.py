"""
Agent Activity Tracker
Tracks and streams important agent decisions and activities to frontend for real-time display.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel
from collections import defaultdict
from threading import Lock

logger = logging.getLogger(__name__)


class AgentActivityType(str, Enum):
    """Types of agent activities to track"""
    AGENT_STARTED = "agent_started"
    AGENT_COMPLETED = "agent_completed"
    TOOL_CALL = "tool_call"
    DECISION = "decision"
    CONFIRMATION_REQUEST = "confirmation_request"
    ERROR = "error"
    ROUTING = "routing"


class AgentActivity(BaseModel):
    """Represents a single agent activity"""
    timestamp: str
    session_id: str
    agent_name: str
    activity_type: AgentActivityType
    message: str
    details: Optional[Dict] = None


class AgentActivityTracker:
    """
    Tracks agent activities for real-time display on frontend.
    
    Features:
    - Session-specific activity tracking
    - Real-time activity streaming
    - Important decision logging
    - Thread-safe operations
    """
    
    def __init__(self, max_activities_per_session: int = 50):
        """
        Initialize the activity tracker.
        
        Args:
            max_activities_per_session: Maximum activities to keep per session
        """
        # Session-specific activities: {session_id: [activities]}
        self.activities: Dict[str, List[AgentActivity]] = defaultdict(list)
        self.max_activities = max_activities_per_session
        self.lock = Lock()
        
        logger.info("✅ AgentActivityTracker initialized")
    
    def log_activity(
        self,
        session_id: str,
        agent_name: str,
        activity_type: AgentActivityType,
        message: str,
        details: Optional[Dict] = None
    ) -> AgentActivity:
        """
        Log an agent activity.
        
        Args:
            session_id: Session identifier
            agent_name: Name of the agent
            activity_type: Type of activity
            message: Human-readable message
            details: Optional additional details
            
        Returns:
            The created AgentActivity object
        """
        activity = AgentActivity(
            timestamp=datetime.now().isoformat(),
            session_id=session_id,
            agent_name=agent_name,
            activity_type=activity_type,
            message=message,
            details=details
        )
        
        with self.lock:
            self.activities[session_id].append(activity)
            
            # Keep only recent activities
            if len(self.activities[session_id]) > self.max_activities:
                self.activities[session_id] = self.activities[session_id][-self.max_activities:]
        
        # Also log to standard logger for persistence
        log_message = f"[{agent_name}] {activity_type.value}: {message}"
        if details:
            log_message += f" | Details: {details}"
        logger.info(log_message)
        
        return activity
    
    def get_session_activities(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[AgentActivity]:
        """
        Get activities for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of activities to return (most recent)
            
        Returns:
            List of activities
        """
        with self.lock:
            activities = self.activities.get(session_id, [])
            if limit:
                return activities[-limit:]
            return activities.copy()
    
    def get_latest_activity(self, session_id: str) -> Optional[AgentActivity]:
        """
        Get the most recent activity for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Latest activity or None
        """
        with self.lock:
            activities = self.activities.get(session_id, [])
            return activities[-1] if activities else None
    
    def clear_session_activities(self, session_id: str):
        """
        Clear all activities for a session.
        
        Args:
            session_id: Session identifier
        """
        with self.lock:
            if session_id in self.activities:
                del self.activities[session_id]
                logger.info(f"🧹 Cleared activities for session {session_id}")
    
    def log_agent_started(self, session_id: str, agent_name: str, reason: str = ""):
        """Convenience method to log agent start"""
        message = f"Started processing request"
        if reason:
            message += f": {reason}"
        return self.log_activity(
            session_id=session_id,
            agent_name=agent_name,
            activity_type=AgentActivityType.AGENT_STARTED,
            message=message
        )
    
    def log_agent_completed(self, session_id: str, agent_name: str):
        """Convenience method to log agent completion"""
        return self.log_activity(
            session_id=session_id,
            agent_name=agent_name,
            activity_type=AgentActivityType.AGENT_COMPLETED,
            message="Completed processing"
        )
    
    def log_tool_call(self, session_id: str, agent_name: str, tool_name: str, args: Optional[Dict] = None):
        """Convenience method to log tool calls"""
        return self.log_activity(
            session_id=session_id,
            agent_name=agent_name,
            activity_type=AgentActivityType.TOOL_CALL,
            message=f"Calling tool: {tool_name}",
            details={"tool_name": tool_name, "args": args}
        )
    
    def log_decision(self, session_id: str, agent_name: str, decision: str, reasoning: str = ""):
        """Convenience method to log decisions"""
        message = f"Decision: {decision}"
        details = {"decision": decision}
        if reasoning:
            details["reasoning"] = reasoning
        return self.log_activity(
            session_id=session_id,
            agent_name=agent_name,
            activity_type=AgentActivityType.DECISION,
            message=message,
            details=details
        )
    
    def log_confirmation_request(self, session_id: str, agent_name: str, confirmation_type: str, details: Dict):
        """Convenience method to log confirmation requests"""
        return self.log_activity(
            session_id=session_id,
            agent_name=agent_name,
            activity_type=AgentActivityType.CONFIRMATION_REQUEST,
            message=f"Requesting {confirmation_type} confirmation",
            details=details
        )
    
    def log_routing(self, session_id: str, from_agent: str, to_agent: str, reason: str):
        """Convenience method to log agent routing"""
        return self.log_activity(
            session_id=session_id,
            agent_name=from_agent,
            activity_type=AgentActivityType.ROUTING,
            message=f"Routing to {to_agent}: {reason}",
            details={"to_agent": to_agent, "reason": reason}
        )
    
    def log_error(self, session_id: str, agent_name: str, error_message: str):
        """Convenience method to log errors"""
        return self.log_activity(
            session_id=session_id,
            agent_name=agent_name,
            activity_type=AgentActivityType.ERROR,
            message=f"Error: {error_message}",
            details={"error": error_message}
        )


# Global instance
_activity_tracker: Optional[AgentActivityTracker] = None


def get_activity_tracker() -> AgentActivityTracker:
    """
    Get the global activity tracker instance.
    
    Returns:
        AgentActivityTracker instance
    """
    global _activity_tracker
    if _activity_tracker is None:
        _activity_tracker = AgentActivityTracker()
    return _activity_tracker


def init_activity_tracker(max_activities_per_session: int = 50) -> AgentActivityTracker:
    """
    Initialize the global activity tracker.
    
    Args:
        max_activities_per_session: Maximum activities to keep per session
        
    Returns:
        AgentActivityTracker instance
    """
    global _activity_tracker
    _activity_tracker = AgentActivityTracker(max_activities_per_session)
    return _activity_tracker
