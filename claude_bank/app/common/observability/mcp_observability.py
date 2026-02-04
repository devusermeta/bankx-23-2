"""
MCP Server Observability Module
Shared observability utilities for all BankX MCP servers

This module provides:
- Application Insights integration
- OpenTelemetry tracing for MCP tool invocations
- Custom metrics for performance tracking
- Cost tracking for Azure services
- Custom events for business intelligence
"""

import os
import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import contextmanager

from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode
from azure.monitor.opentelemetry import configure_azure_monitor

logger = logging.getLogger(__name__)

# Global telemetry instances
_tracer: Optional[trace.Tracer] = None
_meter: Optional[metrics.Meter] = None
_initialized = False


def setup_mcp_observability(
    service_name: str,
    service_version: str = "1.0.0",
    port: int = None,
    connection_string: str = None
) -> bool:
    """
    Set up Application Insights observability for an MCP server.
    
    Args:
        service_name: Name of the MCP service (e.g., "ai-money-coach")
        service_version: Version of the service
        port: MCP server port number
        connection_string: Application Insights connection string
        
    Returns:
        True if successful, False otherwise
        
    Example:
        >>> setup_mcp_observability(
        ...     service_name="ai-money-coach",
        ...     port=8077
        ... )
    """
    global _tracer, _meter, _initialized
    
    if _initialized:
        logger.info(f"Observability already initialized for {service_name}")
        return True
    
    # Get connection string from parameter or environment
    conn_str = connection_string or os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    
    if not conn_str:
        logger.warning(
            "No Application Insights connection string found. "
            "Telemetry will not be exported. "
            "Set APPLICATIONINSIGHTS_CONNECTION_STRING environment variable."
        )
        return False
    
    # Check if OTEL is enabled
    enable_otel = os.getenv("ENABLE_OTEL", "true").lower() == "true"
    if not enable_otel:
        logger.info("OpenTelemetry disabled (ENABLE_OTEL=false)")
        return False
    
    try:
        # Configure Azure Monitor
        configure_azure_monitor(
            connection_string=conn_str,
            enable_live_metrics=True,
        )
        
        # Get tracer and meter
        service_namespace = f"bankx.mcp.port{port}" if port else "bankx.mcp"
        _tracer = trace.get_tracer(service_name, service_version)
        _meter = metrics.get_meter(service_name, service_version)
        
        _initialized = True
        
        logger.info(
            f"✅ Application Insights initialized for {service_name} "
            f"(version: {service_version}, port: {port})"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Application Insights: {e}")
        return False


def get_tracer() -> Optional[trace.Tracer]:
    """Get the configured OpenTelemetry tracer."""
    return _tracer


def get_meter() -> Optional[metrics.Meter]:
    """Get the configured OpenTelemetry meter."""
    return _meter


@contextmanager
def trace_mcp_tool(
    tool_name: str,
    query: str = None,
    attributes: Dict[str, Any] = None
):
    """
    Context manager for tracing MCP tool invocations.
    
    Args:
        tool_name: Name of the MCP tool being invoked
        query: User query (optional, will be redacted in prod)
        attributes: Additional span attributes
        
    Example:
        >>> with trace_mcp_tool("ai_search_rag_results", query="How much to save?"):
        ...     results = search_service.search(query)
        ...     return results
    """
    if not _tracer:
        yield None
        return
    
    # Determine if we should log full query or redacted version
    environment = os.getenv("PROFILE", "dev")
    if environment == "prod" and query:
        query = f"<redacted:{len(query)} chars>"
    
    span_attributes = {
        "mcp.tool_name": tool_name,
        "mcp.environment": environment,
    }
    
    if query:
        span_attributes["mcp.query"] = query
    
    if attributes:
        span_attributes.update(attributes)
    
    with _tracer.start_as_current_span(f"mcp.tool.{tool_name}") as span:
        span.set_attributes(span_attributes)
        
        start_time = time.time()
        try:
            yield span
            
            # Mark as successful
            span.set_status(Status(StatusCode.OK))
            
        except Exception as e:
            # Mark as error
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
            
        finally:
            # Record duration
            duration_ms = (time.time() - start_time) * 1000
            span.set_attribute("mcp.duration_ms", duration_ms)


def instrument_mcp_tool(func: Callable) -> Callable:
    """
    Decorator to automatically instrument MCP tool functions.
    
    Example:
        >>> @instrument_mcp_tool
        ... async def search_documents(query: str, top_k: int):
        ...     return await ai_search.search(query, top_k)
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        tool_name = func.__name__
        
        # Extract query if present
        query = kwargs.get("query") or (args[0] if args and isinstance(args[0], str) else None)
        
        with trace_mcp_tool(tool_name, query=query):
            return await func(*args, **kwargs)
    
    return wrapper


class MCPMetrics:
    """
    Metrics collector for MCP servers.
    
    Tracks:
    - Tool invocation counts
    - Tool execution duration
    - Success/error rates
    - Azure service costs
    """
    
    def __init__(self, service_name: str):
        """Initialize metrics for an MCP service."""
        if not _meter:
            logger.warning("Meter not initialized - metrics will not be collected")
            self.enabled = False
            return
        
        self.enabled = True
        self.service_name = service_name
        
        # Counters
        self.tool_invocations = _meter.create_counter(
            name=f"{service_name}.mcp.tool.invocations",
            description="Total MCP tool invocations",
            unit="1"
        )
        
        self.tool_errors = _meter.create_counter(
            name=f"{service_name}.mcp.tool.errors",
            description="Total MCP tool errors",
            unit="1"
        )
        
        self.azure_api_calls = _meter.create_counter(
            name=f"{service_name}.azure.api.calls",
            description="Total Azure API calls",
            unit="1"
        )
        
        # Histograms
        self.tool_duration = _meter.create_histogram(
            name=f"{service_name}.mcp.tool.duration",
            description="MCP tool execution duration",
            unit="ms"
        )
        
        self.search_latency = _meter.create_histogram(
            name=f"{service_name}.search.latency",
            description="Azure AI Search query latency",
            unit="ms"
        )
        
        self.embedding_latency = _meter.create_histogram(
            name=f"{service_name}.embedding.latency",
            description="Embedding generation latency",
            unit="ms"
        )
        
        # Cost tracking
        self.cost_tracker = _meter.create_histogram(
            name=f"{service_name}.cost.dollars",
            description="Azure service costs",
            unit="USD"
        )
    
    def record_tool_invocation(self, tool_name: str, success: bool, duration_ms: float):
        """Record a tool invocation."""
        if not self.enabled:
            return
        
        attributes = {"tool_name": tool_name, "success": str(success)}
        
        self.tool_invocations.add(1, attributes)
        self.tool_duration.record(duration_ms, attributes)
        
        if not success:
            self.tool_errors.add(1, attributes)
    
    def record_search_query(self, index_name: str, duration_ms: float, result_count: int):
        """Record an Azure AI Search query."""
        if not self.enabled:
            return
        
        attributes = {
            "index_name": index_name,
            "has_results": str(result_count > 0)
        }
        
        self.search_latency.record(duration_ms, attributes)
        self.azure_api_calls.add(1, {"service": "ai_search", "operation": "search"})
    
    def record_embedding_generation(self, model: str, duration_ms: float, token_count: int = None):
        """Record an embedding generation request."""
        if not self.enabled:
            return
        
        attributes = {"model": model}
        if token_count:
            attributes["token_count"] = str(token_count)
        
        self.embedding_latency.record(duration_ms, attributes)
        self.azure_api_calls.add(1, {"service": "openai", "operation": "embedding"})
        
        # Estimate cost (text-embedding-3-large: $0.13 per 1M tokens)
        if token_count:
            cost = (token_count / 1_000_000) * 0.13
            self.cost_tracker.record(cost, {"service": "openai", "operation": "embedding"})
    
    def record_cost(self, service: str, operation: str, cost_usd: float):
        """Record a cost for an Azure service."""
        if not self.enabled:
            return
        
        self.cost_tracker.record(cost_usd, {"service": service, "operation": operation})


def log_custom_event(
    event_name: str,
    properties: Dict[str, Any] = None,
    measurements: Dict[str, float] = None
):
    """
    Log a custom event to Application Insights.
    
    Args:
        event_name: Name of the event (e.g., "ticket_created", "debt_plan_generated")
        properties: String properties
        measurements: Numeric measurements
        
    Example:
        >>> log_custom_event(
        ...     "ticket_created",
        ...     properties={"category": "product_info", "priority": "normal"},
        ...     measurements={"ticket_id": 12345}
        ... )
    """
    if not _tracer:
        return
    
    span = trace.get_current_span()
    if span:
        span.add_event(
            name=event_name,
            attributes={**(properties or {}), **(measurements or {})}
        )
        logger.info(f"📊 Custom Event: {event_name}", extra=properties)


# Environment-aware logging utilities
def should_redact() -> bool:
    """Check if we should redact sensitive data."""
    return os.getenv("PROFILE", "dev") == "prod"


def redact_if_needed(text: str, max_length: int = 50) -> str:
    """Redact text in production, show in dev."""
    if should_redact():
        return f"<redacted:{len(text)} chars>"
    return text[:max_length] + ("..." if len(text) > max_length else "")
