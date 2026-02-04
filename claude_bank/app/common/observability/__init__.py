"""
Common observability module for BankX A2A system.

This module provides unified observability capabilities including:
- Application Insights integration
- OpenTelemetry instrumentation
- Structured logging
- Custom metrics collection
- MCP server observability
"""

from .app_insights import setup_app_insights, get_tracer, get_meter
from .logging_config import setup_logging, get_logger
from .mcp_observability import (
    setup_mcp_observability,
    trace_mcp_tool,
    instrument_mcp_tool,
    MCPMetrics,
    log_custom_event,
    should_redact,
    redact_if_needed,
)
from .audit_logger import get_audit_logger, MCPAuditLogger

# Lazy imports to avoid FastAPI dependency for MCP servers
def _get_telemetry():
    from .telemetry import instrument_app, create_span, add_span_attributes
    return instrument_app, create_span, add_span_attributes

def _get_metrics():
    from .metrics import MetricsCollector, A2AMetrics
    return MetricsCollector, A2AMetrics

__all__ = [
    "setup_app_insights",
    "get_tracer",
    "get_meter",
    "setup_logging",
    "get_logger",
    "setup_mcp_observability",
    "trace_mcp_tool",
    "instrument_mcp_tool",
    "MCPMetrics",
    "log_custom_event",
    "should_redact",
    "redact_if_needed",
    "get_audit_logger",
    "MCPAuditLogger",
]

__version__ = "1.0.0"
