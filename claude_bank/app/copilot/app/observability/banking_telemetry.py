"""
Banking Telemetry Module
Provides comprehensive observability and auditing for banking operations.

Enhanced with custom telemetry for agent reasoning on top of agent_framework's built-in observability.
Reference: https://learn.microsoft.com/en-us/agent-framework/user-guide/agents/agent-observability
"""

import logging
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode, Span
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
import os

logger = logging.getLogger(__name__)

class BankingTelemetry:
    """Handles telemetry and auditing for banking operations"""
    
    def __init__(self):
        self.tracer = trace.get_tracer(__name__)
        self.meter = metrics.get_meter(__name__)
        
        # Create custom metrics
        self.conversation_counter = self.meter.create_counter(
            name="bankx_conversations_total",
            description="Total number of conversations started"
        )
        
        self.banking_operation_counter = self.meter.create_counter(
            name="bankx_banking_operations_total",
            description="Total number of banking operations performed"
        )
        
        self.agent_routing_counter = self.meter.create_counter(
            name="bankx_agent_routing_total", 
            description="Total number of agent routing decisions"
        )
        
        self.conversation_duration = self.meter.create_histogram(
            name="bankx_conversation_duration_seconds",
            description="Duration of conversations in seconds"
        )
        
        self.banking_operation_duration = self.meter.create_histogram(
            name="bankx_banking_operation_duration_seconds",
            description="Duration of banking operations in seconds"
        )
        
        # Agent reasoning metrics
        self.agent_decision_counter = self.meter.create_counter(
            name="bankx_agent_decisions_total",
            description="Total number of agent routing decisions with reasoning"
        )
        
        self.triage_rule_counter = self.meter.create_counter(
            name="bankx_triage_rules_matched_total",
            description="Total number of triage rule matches"
        )
        
        self.tool_invocation_counter = self.meter.create_counter(
            name="bankx_tool_invocations_total",
            description="Total number of tool invocations by agents"
        )
        
        self.agent_execution_duration = self.meter.create_histogram(
            name="bankx_agent_execution_duration_seconds",
            description="Duration of agent execution in seconds"
        )
        
        # Create observability directory for local JSON logs
        # Use container-aware path so dashboard can read files consistently
        if os.path.exists("/.dockerenv"):
            # Running in container
            self.log_dir = Path("/app/observability")
        else:
            # Running locally relative to repo
            self.log_dir = Path("observability")
        self.log_dir.mkdir(exist_ok=True)
        
        # Add .gitignore to prevent committing logs
        gitignore_path = self.log_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("*.json\n*.log\n")

    def _write_to_local_json(self, log_type: str, data: Dict[str, Any]):
        """
        Write telemetry event to local JSON file (NDJSON format).
        
        Args:
            log_type: Type of log (agent_decisions, triage_rules, errors)
            data: Event data to log
        """
        try:
            # Daily log files with date suffix
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = self.log_dir / f"{log_type}_{today}.json"
            
            # Append as newline-delimited JSON (NDJSON)
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False, default=str) + "\n")
        except Exception as e:
            # Don't let JSON logging break the app
            logger.warning(f"Failed to write local JSON log ({log_type}): {e}")

    def start_conversation_span(self, thread_id: str, user_message: str) -> trace.Span:
        """Start a new conversation span for telemetry tracking"""
        span = self.tracer.start_span(
            name="bankx.conversation",
            attributes={
                "bankx.thread_id": thread_id,
                "bankx.conversation.type": "user_message",
                "bankx.message.length": len(user_message),
                "bankx.timestamp": datetime.now().isoformat()
            }
        )
        
        # Increment conversation counter
        self.conversation_counter.add(1, {"thread_id": thread_id})
        
        return span

    def track_agent_routing(self, span: trace.Span, agent_name: str, user_message: str, reasoning: str = None):
        """Track agent routing decisions"""
        span.set_attributes({
            "bankx.agent.routed_to": agent_name,
            "bankx.agent.routing_reason": reasoning or "automatic_routing",
            "bankx.agent.message_content_type": self._classify_message_type(user_message)
        })
        
        # Increment agent routing counter
        self.agent_routing_counter.add(1, {"agent": agent_name})
        
        logger.info(f"🎯 Agent routing telemetry: {agent_name} for message type: {self._classify_message_type(user_message)}")

    @contextmanager
    def track_agent_decision(self, agent_name: str, user_query: str, thread_id: Optional[str]):
        """
        Context manager to track agent decision-making process.
        Captures: Why agent was invoked, what triage rule matched, execution time
        
        Usage:
            with telemetry.track_agent_decision("AccountAgent", query, thread_id) as decision:
                decision.set_triage_rule("UC1_ACCOUNT_BALANCE")
                decision.set_reasoning("User asked about balance")
                # ... agent execution ...
                decision.set_result("success", response_text)
        """
        # Build attributes dictionary, only include thread_id if it's not None
        attributes = {
            "bankx.agent.name": agent_name,
            "bankx.agent.user_query": user_query[:200],  # Truncate for telemetry
            "bankx.message_type": self._classify_message_type(user_query),
            "bankx.timestamp": datetime.now().isoformat()
        }
        
        # Only add thread_id if it's not None (to avoid OpenTelemetry type error)
        if thread_id:
            attributes["bankx.thread_id"] = thread_id
        
        decision_span = self.tracer.start_span(
            name=f"bankx.agent.decision.{agent_name}",
            attributes=attributes
        )
        
        start_time = time.time()
        decision_tracker = AgentDecisionTracker(decision_span, self)
        
        try:
            yield decision_tracker
            decision_span.set_status(Status(StatusCode.OK))
        except Exception as e:
            decision_span.set_status(Status(StatusCode.ERROR, str(e)))
            decision_span.set_attribute("bankx.agent.error", str(e))
            logger.error(f"❌ Agent decision error: {agent_name} - {e}")
            
            # Write error to local JSON log
            self._write_to_local_json("errors", {
                "timestamp": datetime.now().isoformat(),
                "error_type": "AgentDecisionError",
                "agent_name": agent_name,
                "error_message": str(e),
                "user_query": user_query[:200],
                "thread_id": thread_id
            })
            raise
        finally:
            duration = time.time() - start_time
            decision_span.set_attribute("bankx.agent.execution_duration_seconds", duration)
            self.agent_execution_duration.record(duration, {"agent": agent_name})
            decision_span.end()
            
            # Log to Application Insights custom events
            logger.info(
                f"🧠 Agent Decision: {agent_name} | "
                f"Query: {user_query[:50]}... | "
                f"Duration: {duration:.2f}s | "
                f"Triage Rule: {decision_tracker.triage_rule}"
            )
            
            # Write to local JSON log
            self._write_to_local_json("agent_decisions", {
                "timestamp": datetime.now().isoformat(),
                "agent_name": agent_name,
                "thread_id": thread_id,
                "user_query": user_query[:200],
                "triage_rule": decision_tracker.triage_rule,
                "reasoning": decision_tracker.reasoning,
                "tools_considered": decision_tracker.tools_considered,
                "tools_invoked": decision_tracker.tools_invoked,
                "result_status": decision_tracker.result_status,
                "result_summary": decision_tracker.result_summary,
                "context": decision_tracker.context,
                "duration_seconds": round(duration, 3),
                "message_type": self._classify_message_type(user_query)
            })

    def track_user_message(self, user_query: str, thread_id: Optional[str], response_text: str = None, duration_seconds: float = 0):
        """
        Track EVERY user message at the SupervisorAgent level.
        This captures all queries, including follow-ups that don't trigger routing.
        
        Args:
            user_query: The user's question/message
            thread_id: The conversation thread ID
            response_text: The response from the agent (optional)
            duration_seconds: Total execution time
        """
        # Create span for user message
        message_span = self.tracer.start_span(
            name="bankx.user.message",
            attributes={
                "bankx.user.query": user_query[:200],
                "bankx.thread_id": thread_id if thread_id else "new_conversation",
                "bankx.message_type": self._classify_message_type(user_query),
                "bankx.timestamp": datetime.now().isoformat(),
                "bankx.response_length": len(response_text) if response_text else 0
            }
        )
        message_span.end()
        
        # Increment conversation counter
        self.conversation_counter.add(1, {"thread_id": thread_id or "new"})
        
        logger.info(f"💬 User Message: {user_query[:50]}... | Thread: {thread_id or 'NEW'}")
        
        # Write to local JSON log (separate file for all messages)
        self._write_to_local_json("user_messages", {
            "timestamp": datetime.now().isoformat(),
            "thread_id": thread_id,
            "user_query": user_query[:500],  # More context for user messages
            "response_preview": response_text[:200] if response_text else None,
            "response_length": len(response_text) if response_text else 0,
            "duration_seconds": round(duration_seconds, 3),
            "message_type": self._classify_message_type(user_query)
        })

    def track_triage_rule_match(self, rule_name: str, agent_name: str, user_query: str, confidence: float = 1.0):
        """
        Track which triage rule matched and why.
        
        Args:
            rule_name: Name of the triage rule (e.g., "UC1_ACCOUNT_BALANCE", "UC2_PRODUCT_INFO")
            agent_name: Agent that will handle the request
            user_query: The user's query
            confidence: Confidence score (0.0-1.0) if using classification
        """
        # Create custom event for triage rule matching
        triage_span = self.tracer.start_span(
            name="bankx.triage.rule_match",
            attributes={
                "bankx.triage.rule_name": rule_name,
                "bankx.triage.target_agent": agent_name,
                "bankx.triage.user_query": user_query[:200],
                "bankx.triage.confidence": confidence,
                "bankx.timestamp": datetime.now().isoformat()
            }
        )
        triage_span.end()
        
        # Increment counter
        self.triage_rule_counter.add(1, {
            "rule": rule_name,
            "agent": agent_name
        })
        
        logger.info(f"📋 Triage Rule Matched: {rule_name} → {agent_name} (confidence: {confidence:.2f})")
        
        # Write to local JSON log
        self._write_to_local_json("triage_rules", {
            "timestamp": datetime.now().isoformat(),
            "rule_name": rule_name,
            "target_agent": agent_name,
            "user_query": user_query[:200],
            "confidence": confidence
        })

    def track_tool_invocation(self, tool_name: str, agent_name: str, parameters: Dict[str, Any], result_summary: str = None):
        """
        Track tool invocations by agents (MCP tools).
        
        Args:
            tool_name: Name of the MCP tool (e.g., "getAccountsByUserName")
            agent_name: Agent that invoked the tool
            parameters: Tool parameters
            result_summary: Brief summary of the result
        """
        tool_span = self.tracer.start_span(
            name=f"bankx.tool.invocation.{tool_name}",
            attributes={
                "bankx.tool.name": tool_name,
                "bankx.tool.agent": agent_name,
                "bankx.tool.result_summary": result_summary or "completed",
                "bankx.timestamp": datetime.now().isoformat()
            }
        )
        
        # Add parameters as attributes (sanitize sensitive data)
        for key, value in parameters.items():
            if key not in ["password", "token", "secret"]:  # Skip sensitive fields
                tool_span.set_attribute(f"bankx.tool.param.{key}", str(value)[:100])
        
        tool_span.end()
        
        # Increment counter
        self.tool_invocation_counter.add(1, {
            "tool": tool_name,
            "agent": agent_name
        })
        
        logger.info(f"🔧 Tool Invocation: {tool_name} by {agent_name} | Params: {list(parameters.keys())}")

    def track_banking_operation(self, span: trace.Span, operation_type: str, details: Dict[str, Any], success: bool = True):
        """Track banking operations with detailed telemetry"""
        operation_span = self.tracer.start_span(
            name=f"bankx.banking_operation.{operation_type}",
            attributes={
                "bankx.operation.type": operation_type,
                "bankx.operation.success": success,
                "bankx.operation.amount": details.get("amount", 0),
                "bankx.operation.from_account": details.get("from_account", "unknown"),
                "bankx.operation.to_account": details.get("to_account", "unknown"),
                "bankx.operation.currency": details.get("currency", "USD"),
                "bankx.timestamp": datetime.now().isoformat()
            }
        )
        
        if success:
            operation_span.set_status(Status(StatusCode.OK))
        else:
            operation_span.set_status(Status(StatusCode.ERROR, details.get("error", "Unknown error")))
        
        # Add operation details as span attributes
        for key, value in details.items():
            if isinstance(value, (str, int, float, bool)):
                operation_span.set_attribute(f"bankx.operation.{key}", value)
        
        # Increment banking operation counter
        self.banking_operation_counter.add(1, {
            "operation_type": operation_type,
            "success": str(success)
        })
        
        operation_span.end()
        
        logger.info(f"💰 Banking operation telemetry: {operation_type} - Success: {success}")

    def track_mcp_service_call(self, span: trace.Span, service_name: str, method: str, duration_ms: float, success: bool):
        """Track MCP service calls"""
        span.set_attributes({
            "bankx.mcp.service": service_name,
            "bankx.mcp.method": method,
            "bankx.mcp.duration_ms": duration_ms,
            "bankx.mcp.success": success
        })
        
        if not success:
            span.set_status(Status(StatusCode.ERROR, f"MCP service call failed: {service_name}.{method}"))

    def track_cosmos_sync(self, span: trace.Span, thread_id: str, success: bool, retry_count: int = 0):
        """Track Cosmos DB sync operations"""
        sync_span = self.tracer.start_span(
            name="bankx.cosmos_sync",
            attributes={
                "bankx.cosmos.thread_id": thread_id,
                "bankx.cosmos.success": success,
                "bankx.cosmos.retry_count": retry_count,
                "bankx.timestamp": datetime.now().isoformat()
            }
        )
        
        if success:
            sync_span.set_status(Status(StatusCode.OK))
        else:
            sync_span.set_status(Status(StatusCode.ERROR, "Cosmos DB sync failed"))
        
        sync_span.end()
        
        logger.info(f"📦 Cosmos sync telemetry: {thread_id} - Success: {success}, Retries: {retry_count}")

    def track_conversation_completion(self, span: trace.Span, thread_id: str, duration_seconds: float, message_count: int, operations_count: int):
        """Track conversation completion metrics"""
        span.set_attributes({
            "bankx.conversation.completed": True,
            "bankx.conversation.duration_seconds": duration_seconds,
            "bankx.conversation.message_count": message_count,
            "bankx.conversation.operations_count": operations_count
        })
        
        # Record duration histogram
        self.conversation_duration.record(duration_seconds, {"thread_id": thread_id})
        
        logger.info(f"🏁 Conversation completion telemetry: {thread_id} - Duration: {duration_seconds}s, Messages: {message_count}, Operations: {operations_count}")

    def track_error(self, span: trace.Span, error_type: str, error_message: str, error_details: Dict[str, Any] = None):
        """Track errors with detailed context"""
        span.set_status(Status(StatusCode.ERROR, error_message))
        span.set_attributes({
            "bankx.error.type": error_type,
            "bankx.error.message": error_message,
            "bankx.timestamp": datetime.now().isoformat()
        })
        
        if error_details:
            for key, value in error_details.items():
                if isinstance(value, (str, int, float, bool)):
                    span.set_attribute(f"bankx.error.{key}", value)
        
        logger.error(f"❌ Error telemetry: {error_type} - {error_message}")
        
        # Write to local JSON error log
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "error_details": error_details or {}
        }
        self._write_to_local_json("errors", error_data)

    def _classify_message_type(self, message: str) -> str:
        """Classify message type for telemetry"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["balance", "account", "card", "limit"]):
            return "account_inquiry"
        elif any(word in message_lower for word in ["transfer", "payment", "pay", "send"]):
            return "payment_request"
        elif any(word in message_lower for word in ["transaction", "history", "statement"]):
            return "transaction_inquiry"
        elif any(word in message_lower for word in ["yes", "confirm", "proceed", "ok", "sure"]):
            return "confirmation"
        else:
            return "general_inquiry"

    def create_banking_operation_timer(self):
        """Create a timer for banking operations"""
        return BankingOperationTimer(self)


class AgentDecisionTracker:
    """Helper class to track agent decision-making process within a span"""
    
    def __init__(self, span: Span, telemetry: 'BankingTelemetry'):
        self.span = span
        self.telemetry = telemetry
        self.triage_rule = None
        self.reasoning = None
        self.tools_considered = []
        self.tools_invoked = []
        self.result_status = None
        self.result_summary = None
        self.context = {}
    
    def set_triage_rule(self, rule_name: str):
        """Set which triage rule was matched"""
        self.triage_rule = rule_name
        self.span.set_attribute("bankx.agent.triage_rule", rule_name)
        self.telemetry.triage_rule_counter.add(1, {"rule": rule_name})
    
    def set_reasoning(self, reasoning: str):
        """Set the agent's reasoning for the decision"""
        self.reasoning = reasoning
        self.span.set_attribute("bankx.agent.reasoning", reasoning[:500])  # Truncate
    
    def add_tool_considered(self, tool_name: str):
        """Add a tool that was considered but not invoked"""
        self.tools_considered.append(tool_name)
        self.span.set_attribute(f"bankx.agent.tool_considered.{len(self.tools_considered)}", tool_name)
    
    def add_tool_invoked(self, tool_name: str, parameters: Dict[str, Any] = None):
        """Add a tool that was actually invoked"""
        self.tools_invoked.append(tool_name)
        self.span.set_attribute(f"bankx.agent.tool_invoked.{len(self.tools_invoked)}", tool_name)
        
        if parameters:
            # Sanitize and add parameters
            safe_params = {k: str(v)[:50] for k, v in parameters.items() if k not in ["password", "token"]}
            self.span.set_attribute(f"bankx.agent.tool_params.{tool_name}", str(safe_params))
    
    def set_result(self, status: str, summary: str = None):
        """Set the result of the agent decision"""
        self.result_status = status
        self.result_summary = summary
        self.span.set_attribute("bankx.agent.result_status", status)
        if summary:
            self.span.set_attribute("bankx.agent.result_summary", summary[:200])
    
    def add_context(self, key: str, value: Any):
        """Add custom context to the decision"""
        self.context[key] = value
        if isinstance(value, (str, int, float, bool)):
            self.span.set_attribute(f"bankx.agent.context.{key}", value)


class BankingOperationTimer:
    """Timer for tracking banking operation duration"""
    
    def __init__(self, telemetry: BankingTelemetry):
        self.telemetry = telemetry
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration = time.time() - self.start_time
            self.telemetry.banking_operation_duration.record(duration)


# Global telemetry instance
_banking_telemetry = None

def get_banking_telemetry() -> BankingTelemetry:
    """Get the global banking telemetry instance"""
    global _banking_telemetry
    if _banking_telemetry is None:
        _banking_telemetry = BankingTelemetry()
    return _banking_telemetry

def setup_banking_observability():
    """Setup banking-specific observability"""
    try:
        # Configure Azure Monitor if connection string is available
        connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
        if connection_string:
            configure_azure_monitor(connection_string=connection_string)
            logger.info("✅ Azure Monitor configured for banking telemetry")
        else:
            logger.warning("⚠️ APPLICATIONINSIGHTS_CONNECTION_STRING not configured")
        
        # Initialize banking telemetry
        telemetry = get_banking_telemetry()
        logger.info("✅ Banking telemetry initialized")
        
        return telemetry
    except Exception as e:
        logger.error(f"❌ Failed to setup banking observability: {e}")
        return None