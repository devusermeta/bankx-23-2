"""
Banking Telemetry for A2A Agents
Provides JSON logging capabilities for standalone A2A agents to maintain observability consistency.

This module is shared across all A2A agents to ensure consistent logging format.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class A2ABankingTelemetry:
    """
    Telemetry logger for A2A agents - writes to the same JSON files as copilot backend.
    This ensures frontend dashboard can display metrics from both A2A and in-process agents.
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize telemetry for an A2A agent.
        
        Args:
            agent_name: Name of the agent (e.g., "AccountAgent", "PaymentAgent")
        """
        self.agent_name = agent_name
        
        # Find observability directory (shared with copilot backend)
        # Look for it in the project root (go up from app/agents/common)
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent  # Up to claude_bank/
        self.observability_dir = project_root / "observability"
        
        # Create if it doesn't exist
        self.observability_dir.mkdir(exist_ok=True)
        
        print(f"\n{'='*80}")
        print(f"[A2A TELEMETRY INIT] Agent: {agent_name}")
        print(f"[A2A TELEMETRY INIT] Observability Dir: {self.observability_dir}")
        print(f"[A2A TELEMETRY INIT] Directory exists: {self.observability_dir.exists()}")
        print(f"{'='*80}\n")
        
        logger.info(f"A2A Telemetry initialized for {agent_name}")
        logger.info(f"Observability directory: {self.observability_dir}")
    
    def log_agent_decision(
        self,
        thread_id: Optional[str],
        user_query: str,
        triage_rule: str,
        reasoning: str,
        tools_considered: list[str],
        tools_invoked: list[Dict[str, Any]],
        result_status: str,
        result_summary: str,
        duration_seconds: float,
        context: Dict[str, Any] = None
    ):
        """
        Log an agent decision to JSON file.
        
        This matches the format used by copilot backend's banking_telemetry.py
        """
        print(f"\n{'─'*80}")
        print(f"[A2A TELEMETRY] 📝 LOGGING AGENT DECISION")
        print(f"[A2A TELEMETRY]   Agent: {self.agent_name}")
        print(f"[A2A TELEMETRY]   Thread: {thread_id}")
        print(f"[A2A TELEMETRY]   Query: {user_query[:60]}...")
        print(f"[A2A TELEMETRY]   Triage Rule: {triage_rule}")
        print(f"[A2A TELEMETRY]   Status: {result_status}")
        print(f"[A2A TELEMETRY]   Duration: {duration_seconds:.3f}s")
        print(f"[A2A TELEMETRY]   Tools Invoked: {len(tools_invoked)}")
        print(f"{'─'*80}")
        
        try:
            decision_data = {
                "timestamp": datetime.now().isoformat(),
                "agent_name": self.agent_name,
                "thread_id": thread_id,
                "user_query": user_query[:200],  # Truncate for storage
                "triage_rule": triage_rule,
                "reasoning": reasoning,
                "tools_considered": tools_considered,
                "tools_invoked": tools_invoked,
                "result_status": result_status,
                "result_summary": result_summary,
                "context": context or {},
                "duration_seconds": round(duration_seconds, 3),
                "message_type": self._classify_message_type(user_query)
            }
            
            self._write_to_json("agent_decisions", decision_data)
            print(f"[A2A TELEMETRY] ✅ Agent decision logged successfully\n")
            logger.info(f"✅ Logged agent decision for {self.agent_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to log agent decision: {e}")
    
    def log_tool_invocation(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result_status: str,
        result_summary: str = None,
        duration_ms: float = 0
    ):
        """Log a tool invocation (MCP tool call)."""
        try:
            # This can be used for detailed tool tracking if needed
            # For now, tools are logged as part of agent_decisions
            logger.debug(f"Tool invoked: {tool_name} - {result_status}")
        except Exception as e:
            logger.error(f"❌ Failed to log tool invocation: {e}")
    
    def log_user_message(
        self,
        thread_id: Optional[str],
        user_query: str,
        response_text: str,
        duration_seconds: float
    ):
        """Log a user message and response."""
        print(f"[A2A TELEMETRY] 💬 Logging user message (query: {len(user_query)} chars, response: {len(response_text) if response_text else 0} chars)")
        
        try:
            message_data = {
                "timestamp": datetime.now().isoformat(),
                "thread_id": thread_id,
                "user_query": user_query[:500],
                "response_preview": response_text[:200] if response_text else None,
                "response_length": len(response_text) if response_text else 0,
                "duration_seconds": round(duration_seconds, 3),
                "message_type": self._classify_message_type(user_query)
            }
            
            self._write_to_json("user_messages", message_data)
            print(f"[A2A TELEMETRY] ✅ User message logged successfully\n")
            logger.info(f"✅ Logged user message")
            
        except Exception as e:
            logger.error(f"❌ Failed to log user message: {e}")
    
    def _write_to_json(self, log_type: str, data: Dict[str, Any]):
        """
        Write data to NDJSON file (newline-delimited JSON).
        Same format as copilot backend's banking_telemetry.py
        """
        try:
            # Daily log files with date suffix
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = self.observability_dir / f"{log_type}_{today}.json"
            
            print(f"[A2A TELEMETRY] 💾 Writing to file: {log_file.name}")
            print(f"[A2A TELEMETRY] 📂 Full path: {log_file}")
            
            # Append as newline-delimited JSON (NDJSON)
            with open(log_file, "a", encoding="utf-8") as f:
                json_line = json.dumps(data, ensure_ascii=False, default=str) + "\n"
                f.write(json_line)
            
            # Verify write
            file_size = log_file.stat().st_size if log_file.exists() else 0
            print(f"[A2A TELEMETRY] ✍️  Written {len(json_line)} bytes (total file size: {file_size} bytes)")
                
        except Exception as e:
            print(f"[A2A TELEMETRY] ❌ ERROR writing to {log_type}: {e}")
            logger.error(f"❌ Failed to write to {log_type}.json: {e}")
            import traceback
            traceback.print_exc()
    
    def _classify_message_type(self, message: str) -> str:
        """Classify message type (same logic as backend)."""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["pay", "transfer", "send"]):
            return "payment"
        elif any(word in message_lower for word in ["transaction", "history", "spent"]):
            return "transaction"
        elif any(word in message_lower for word in ["balance", "account", "limit"]):
            return "account"
        elif any(word in message_lower for word in ["interest", "rate", "product", "loan"]):
            return "product_info"
        elif any(word in message_lower for word in ["advice", "debt", "budget", "invest"]):
            return "financial_advice"
        else:
            return "general"


# Singleton instances per agent
_telemetry_instances: Dict[str, A2ABankingTelemetry] = {}


def get_a2a_telemetry(agent_name: str) -> A2ABankingTelemetry:
    """
    Get or create telemetry instance for an A2A agent.
    
    Args:
        agent_name: Name of the agent (e.g., "AccountAgent")
        
    Returns:
        A2ABankingTelemetry instance
        
    Example:
        >>> telemetry = get_a2a_telemetry("AccountAgent")
        >>> telemetry.log_agent_decision(...)
    """
    if agent_name not in _telemetry_instances:
        _telemetry_instances[agent_name] = A2ABankingTelemetry(agent_name)
    
    return _telemetry_instances[agent_name]
