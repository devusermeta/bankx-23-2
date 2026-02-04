#!/usr/bin/env python3
"""
Real-Time Routing Diagnostics
Monitor agent routing decisions in real-time
Place this in the copilot app to enable detailed routing diagnostics
"""

import json
import asyncio
from datetime import datetime
from typing import Optional
from dataclasses import dataclass, asdict
from pathlib import Path
import os

# ============================================================================
# Routing Event Tracker
# ============================================================================

@dataclass
class RoutingEvent:
    """Represents a routing event in the supervisor agent"""
    timestamp: str
    user_id: str
    thread_id: str
    user_query: str
    detected_intent: str
    target_agent: str
    agent_id: Optional[str]
    is_cache_hit: Optional[bool] = None
    mcp_endpoint: Optional[str] = None
    error: Optional[str] = None
    
    def to_dict(self):
        return asdict(self)
    
    def to_json(self):
        return json.dumps(self.to_dict(), indent=2, default=str)


class RoutingDiagnostics:
    """Tracks routing decisions for debugging"""
    
    def __init__(self, log_dir: str = "/tmp/bankx_routing_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.events = []
        self.current_session = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def log_routing_decision(
        self,
        user_id: str,
        thread_id: str,
        user_query: str,
        detected_intent: str,
        target_agent: str,
        agent_id: Optional[str] = None,
        is_cache_hit: Optional[bool] = None,
        mcp_endpoint: Optional[str] = None,
        error: Optional[str] = None,
    ):
        """Log a routing decision"""
        event = RoutingEvent(
            timestamp=datetime.now().isoformat(),
            user_id=user_id,
            thread_id=thread_id,
            user_query=user_query,
            detected_intent=detected_intent,
            target_agent=target_agent,
            agent_id=agent_id,
            is_cache_hit=is_cache_hit,
            mcp_endpoint=mcp_endpoint,
            error=error,
        )
        
        self.events.append(event)
        
        # Log to file
        self._write_log(event)
        
        # Print to console
        self._print_diagnostic(event)
        
        return event
    
    def _write_log(self, event: RoutingEvent):
        """Write event to log file"""
        log_file = self.log_dir / f"{self.current_session}.jsonl"
        
        with open(log_file, "a") as f:
            f.write(event.to_json() + "\n")
    
    def _print_diagnostic(self, event: RoutingEvent):
        """Print formatted diagnostic output"""
        status = "🔴 ERROR" if event.error else "🟢 ROUTED"
        
        print(f"""
╔════════════════════════════════════════════════════════════════╗
║ {status} - {event.timestamp}
╠════════════════════════════════════════════════════════════════╣
║ User ID:        {event.user_id}
║ Thread ID:      {event.thread_id}
║ Query:          {event.user_query[:50]}{'...' if len(event.user_query) > 50 else ''}
║ Intent:         {event.detected_intent}
║ Target Agent:   {event.target_agent}
║ Agent ID:       {event.agent_id or 'NOT CONFIGURED'}
║ Cache Hit:      {event.is_cache_hit if event.is_cache_hit is not None else 'N/A'}
║ MCP Endpoint:   {event.mcp_endpoint or 'N/A'}
{f'║ Error:          {event.error}' if event.error else ''}
╚════════════════════════════════════════════════════════════════╝
""")
    
    def get_session_summary(self):
        """Get summary of all routing events in session"""
        if not self.events:
            return "No routing events recorded"
        
        total = len(self.events)
        errors = len([e for e in self.events if e.error])
        cache_hits = len([e for e in self.events if e.is_cache_hit])
        cache_misses = len([e for e in self.events if e.is_cache_hit is False])
        
        agent_counts = {}
        for event in self.events:
            agent_counts[event.target_agent] = agent_counts.get(event.target_agent, 0) + 1
        
        summary = f"""
╔════════════════════════════════════════════════════════════════╗
║ ROUTING SESSION SUMMARY
╠════════════════════════════════════════════════════════════════╣
║ Session ID:     {self.current_session}
║ Total Events:   {total}
║ Successful:     {total - errors}
║ Errors:         {errors}
║ Cache Hits:     {cache_hits}
║ Cache Misses:   {cache_misses}
║
║ Agent Routing Counts:
"""
        
        for agent, count in sorted(agent_counts.items()):
            summary += f"║   - {agent}: {count} calls\n"
        
        summary += "╚════════════════════════════════════════════════════════════════╝\n"
        
        return summary


# ============================================================================
# Integration Points for SupervisorAgent
# ============================================================================

"""
To integrate this into supervisor_agent_foundry.py, add these calls:

1. At the top of the supervisor_agent_foundry.py file:
   ```python
   from app.copilot.routing_diagnostics import RoutingDiagnostics
   
   # Initialize diagnostics
   routing_diags = RoutingDiagnostics()
   ```

2. In each route_to_*_agent() method, after setting routed_agent_name:
   ```python
   # Example: in route_to_account_agent()
   routing_diags.log_routing_decision(
       user_id=self.user_id,
       thread_id=self.thread_id,
       user_query=self.current_user_query,
       detected_intent="account_inquiry",
       target_agent="AccountAgent",
       agent_id=self.account_agent.agent_id,
       mcp_endpoint=os.getenv("ACCOUNT_MCP_URL"),
   )
   ```

3. For error cases:
   ```python
   routing_diags.log_routing_decision(
       user_id=self.user_id,
       thread_id=self.thread_id,
       user_query=self.current_user_query,
       detected_intent="unknown",
       target_agent="Unknown",
       error=f"No routing tools matched. Intent: {intent_label}",
   )
   ```

4. To get session summary at end of conversation:
   ```python
   print(routing_diags.get_session_summary())
   ```
"""


# ============================================================================
# Standalone Verification Tool
# ============================================================================

if __name__ == "__main__":
    # Create diagnostics instance
    diags = RoutingDiagnostics()
    
    # Simulate routing events for testing
    print("\n📊 ROUTING DIAGNOSTICS - SIMULATION TEST\n")
    
    # Test UC1 - Account Agent with cache hit
    diags.log_routing_decision(
        user_id="user_123",
        thread_id="thread_456",
        user_query="What is my account balance?",
        detected_intent="account_balance",
        target_agent="AccountAgent",
        agent_id=os.getenv("ACCOUNT_AGENT_ID", "account-agent-id-not-set"),
        is_cache_hit=True,
        mcp_endpoint=os.getenv("ACCOUNT_MCP_URL", "http://account-mcp:8000"),
    )
    
    # Test UC1 - Account Agent with cache miss (MCP fallback)
    diags.log_routing_decision(
        user_id="user_123",
        thread_id="thread_456",
        user_query="Get my latest transaction",
        detected_intent="transaction_history",
        target_agent="TransactionAgent",
        agent_id=os.getenv("TRANSACTION_AGENT_ID", "transaction-agent-id-not-set"),
        is_cache_hit=False,
        mcp_endpoint=os.getenv("TRANSACTION_MCP_URL", "http://transaction-mcp:8000"),
    )
    
    # Test UC2 - ProdInfo FAQ Agent (no cache, direct Foundry)
    diags.log_routing_decision(
        user_id="user_123",
        thread_id="thread_456",
        user_query="What is avalanche method?",
        detected_intent="product_information",
        target_agent="ProdInfoFAQAgent",
        agent_id=os.getenv("PRODINFO_FAQ_AGENT_ID", "prodinfo-agent-id-not-set"),
    )
    
    # Test UC3 - AI Money Coach (no cache, direct Foundry)
    diags.log_routing_decision(
        user_id="user_123",
        thread_id="thread_456",
        user_query="Should I save more?",
        detected_intent="financial_advice",
        target_agent="AIMoneyCoachAgent",
        agent_id=os.getenv("AI_MONEY_COACH_AGENT_ID", "money-coach-agent-id-not-set"),
    )
    
    # Test error case - no routing matched
    diags.log_routing_decision(
        user_id="user_123",
        thread_id="thread_456",
        user_query="Tell me a joke",
        detected_intent="unknown",
        target_agent="Unknown",
        error="No routing tools matched. Intent did not match any agent.",
    )
    
    # Print summary
    print(diags.get_session_summary())
    
    # Show log file location
    print(f"\n📁 Logs saved to: {diags.log_dir / f'{diags.current_session}.jsonl'}\n")
