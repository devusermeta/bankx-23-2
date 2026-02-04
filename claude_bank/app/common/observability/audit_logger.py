"""
MCP Audit Logger
Compliance audit trail for MCP tool invocations in banking operations.

Captures: User identity, operation type, data scope, timestamps, results
Purpose: GDPR, PCI-DSS compliance, fraud detection, security audit
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
from opentelemetry import trace

logger = logging.getLogger(__name__)


class MCPAuditLogger:
    """
    Audit logger for MCP tool invocations.
    
    Tracks all data access operations for compliance and security monitoring.
    """
    
    def __init__(self):
        self.tracer = trace.get_tracer(__name__)
        
        # Create observability directory for audit logs
        self.log_dir = Path("observability")
        self.log_dir.mkdir(exist_ok=True)
    
    @contextmanager
    def audit_operation(
        self,
        operation_type: str,
        mcp_server: str,
        tool_name: str,
        user_id: Optional[str] = None,
        thread_id: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None
    ):
        """
        Context manager for auditing MCP operations.
        
        Args:
            operation_type: Type of operation (READ, WRITE, UPDATE, DELETE)
            mcp_server: MCP server name (account, transaction, payment, etc.)
            tool_name: Name of the MCP tool being invoked
            user_id: Customer/user identifier
            thread_id: Conversation thread ID
            parameters: Tool parameters (sanitized)
        
        Usage:
            with audit_logger.audit_operation("READ", "account", "getCustomerAccounts", user_id="alice") as audit:
                # ... perform operation ...
                audit.set_data_accessed(["CHK-001", "SAV-002"])
                audit.set_result("success", {"account_count": 2})
        """
        start_time = time.time()
        
        # Sanitize parameters (remove sensitive data)
        safe_parameters = self._sanitize_parameters(parameters or {})
        
        # Create audit span
        audit_span = self.tracer.start_span(
            name=f"bankx.mcp.audit.{mcp_server}.{tool_name}",
            attributes={
                "bankx.audit.operation_type": operation_type,
                "bankx.audit.mcp_server": mcp_server,
                "bankx.audit.tool_name": tool_name,
                "bankx.audit.user_id": user_id or "unknown",
                "bankx.audit.thread_id": thread_id or "unknown",
                "bankx.audit.timestamp": datetime.now().isoformat(),
                "bankx.audit.parameters": str(safe_parameters)[:200]
            }
        )
        
        # Create audit tracker
        audit_tracker = AuditTracker(audit_span, self)
        audit_tracker.operation_type = operation_type
        audit_tracker.mcp_server = mcp_server
        audit_tracker.tool_name = tool_name
        audit_tracker.user_id = user_id
        audit_tracker.thread_id = thread_id
        audit_tracker.parameters = safe_parameters
        
        try:
            yield audit_tracker
            audit_span.set_status(trace.Status(trace.StatusCode.OK))
        except Exception as e:
            audit_span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            audit_span.set_attribute("bankx.audit.error", str(e))
            audit_tracker.result_status = "error"
            audit_tracker.error_message = str(e)
            logger.error(f"❌ MCP Audit: {mcp_server}.{tool_name} failed - {e}")
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            audit_span.set_attribute("bankx.audit.duration_ms", duration_ms)
            audit_span.end()
            
            # Write audit log
            self._write_audit_log(audit_tracker, duration_ms)
            
            logger.info(
                f"📋 MCP Audit: {operation_type} {mcp_server}.{tool_name} | "
                f"User: {user_id or 'unknown'} | "
                f"Duration: {duration_ms:.0f}ms | "
                f"Status: {audit_tracker.result_status}"
            )
    
    def _sanitize_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive data from parameters."""
        sensitive_keys = {"password", "token", "secret", "api_key", "auth", "credential"}
        
        sanitized = {}
        for key, value in parameters.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            else:
                # Truncate long values
                if isinstance(value, str) and len(value) > 100:
                    sanitized[key] = value[:100] + "..."
                else:
                    sanitized[key] = value
        
        return sanitized
    
    def _write_audit_log(self, audit_tracker: 'AuditTracker', duration_ms: float):
        """Write audit entry to local JSON file."""
        try:
            # Daily audit log files
            today = datetime.now().strftime("%Y-%m-%d")
            log_file = self.log_dir / f"mcp_audit_{today}.json"
            
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "operation_type": audit_tracker.operation_type,
                "mcp_server": audit_tracker.mcp_server,
                "tool_name": audit_tracker.tool_name,
                "user_id": audit_tracker.user_id,
                "thread_id": audit_tracker.thread_id,
                "parameters": audit_tracker.parameters,
                "data_accessed": audit_tracker.data_accessed,
                "data_scope": audit_tracker.data_scope,
                "result_status": audit_tracker.result_status,
                "result_summary": audit_tracker.result_summary,
                "error_message": audit_tracker.error_message,
                "duration_ms": round(duration_ms, 2),
                "compliance_flags": audit_tracker.compliance_flags
            }
            
            # Append as newline-delimited JSON
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False, default=str) + "\n")
        
        except Exception as e:
            logger.warning(f"Failed to write MCP audit log: {e}")


class AuditTracker:
    """Helper class to track audit information within a span."""
    
    def __init__(self, span: trace.Span, logger: MCPAuditLogger):
        self.span = span
        self.logger = logger
        self.operation_type = None
        self.mcp_server = None
        self.tool_name = None
        self.user_id = None
        self.thread_id = None
        self.parameters = {}
        self.data_accessed = []
        self.data_scope = None
        self.result_status = "unknown"
        self.result_summary = None
        self.error_message = None
        self.compliance_flags = []
    
    def set_data_accessed(self, data_ids: List[str]):
        """Set which data entities were accessed (account IDs, transaction IDs, etc.)."""
        self.data_accessed = data_ids
        self.span.set_attribute("bankx.audit.data_accessed", str(data_ids)[:200])
    
    def set_data_scope(self, scope: str):
        """
        Set the scope of data accessed.
        Examples: "account_details", "transaction_history", "payment_info", "personal_info"
        """
        self.data_scope = scope
        self.span.set_attribute("bankx.audit.data_scope", scope)
    
    def set_result(self, status: str, summary: Optional[str] = None):
        """Set the result of the operation."""
        self.result_status = status
        self.result_summary = summary
        self.span.set_attribute("bankx.audit.result_status", status)
        if summary:
            self.span.set_attribute("bankx.audit.result_summary", str(summary)[:200])
    
    def add_compliance_flag(self, flag: str):
        """
        Add compliance-related flag.
        Examples: "PCI_DSS", "GDPR_PERSONAL_DATA", "HIGH_VALUE_TRANSACTION", "CROSS_BORDER"
        """
        self.compliance_flags.append(flag)
        self.span.set_attribute(f"bankx.audit.compliance.{flag}", True)


# Singleton instance
_audit_logger_instance = None


def get_audit_logger() -> MCPAuditLogger:
    """Get singleton instance of MCP audit logger."""
    global _audit_logger_instance
    if _audit_logger_instance is None:
        _audit_logger_instance = MCPAuditLogger()
    return _audit_logger_instance
