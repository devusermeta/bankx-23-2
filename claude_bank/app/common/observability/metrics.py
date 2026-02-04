"""
Custom metrics collection for BankX A2A system.
"""

import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, UpDownCounter

from .app_insights import get_meter


@dataclass
class A2AMetrics:
    """Metrics for A2A communication."""

    # Counters
    requests_total: Counter
    requests_success: Counter
    requests_error: Counter
    circuit_breaker_open: Counter

    # Histograms
    request_duration: Histogram
    payload_size: Histogram

    # UpDown counters
    active_requests: UpDownCounter

    @classmethod
    def create(cls, service_name: str) -> "A2AMetrics":
        """Create A2A metrics for a service."""
        meter = get_meter()

        return cls(
            requests_total=meter.create_counter(
                name=f"{service_name}.a2a.requests.total",
                description="Total number of A2A requests",
                unit="1",
            ),
            requests_success=meter.create_counter(
                name=f"{service_name}.a2a.requests.success",
                description="Number of successful A2A requests",
                unit="1",
            ),
            requests_error=meter.create_counter(
                name=f"{service_name}.a2a.requests.error",
                description="Number of failed A2A requests",
                unit="1",
            ),
            circuit_breaker_open=meter.create_counter(
                name=f"{service_name}.a2a.circuit_breaker.open",
                description="Number of times circuit breaker opened",
                unit="1",
            ),
            request_duration=meter.create_histogram(
                name=f"{service_name}.a2a.request.duration",
                description="A2A request duration",
                unit="ms",
            ),
            payload_size=meter.create_histogram(
                name=f"{service_name}.a2a.payload.size",
                description="A2A payload size",
                unit="bytes",
            ),
            active_requests=meter.create_up_down_counter(
                name=f"{service_name}.a2a.requests.active",
                description="Number of active A2A requests",
                unit="1",
            ),
        )

    def record_request(
        self,
        success: bool,
        duration_ms: float,
        attributes: Optional[Dict[str, str]] = None,
    ) -> None:
        """Record an A2A request."""
        attrs = attributes or {}

        self.requests_total.add(1, attrs)

        if success:
            self.requests_success.add(1, attrs)
        else:
            self.requests_error.add(1, attrs)

        self.request_duration.record(duration_ms, attrs)


class MetricsCollector:
    """
    Centralized metrics collector for agent services.

    Example:
        >>> collector = MetricsCollector("account-agent")
        >>> collector.record_a2a_request(
        ...     success=True,
        ...     duration_ms=245.3,
        ...     target_agent="transaction-agent"
        ... )
    """

    def __init__(self, service_name: str):
        """Initialize metrics collector."""
        self.service_name = service_name
        meter = get_meter()

        # Health metrics
        self.health_status = meter.create_up_down_counter(
            name=f"{service_name}.health.status",
            description="Service health status (1=healthy, 0=unhealthy)",
            unit="1",
        )

        # MCP call metrics
        self.mcp_calls_total = meter.create_counter(
            name=f"{service_name}.mcp.calls.total",
            description="Total MCP calls",
            unit="1",
        )
        self.mcp_calls_success = meter.create_counter(
            name=f"{service_name}.mcp.calls.success",
            description="Successful MCP calls",
            unit="1",
        )
        self.mcp_calls_error = meter.create_counter(
            name=f"{service_name}.mcp.calls.error",
            description="Failed MCP calls",
            unit="1",
        )
        self.mcp_call_duration = meter.create_histogram(
            name=f"{service_name}.mcp.call.duration",
            description="MCP call duration",
            unit="ms",
        )

        # A2A metrics
        self.a2a_metrics = A2AMetrics.create(service_name)

    def record_health_check(self, is_healthy: bool) -> None:
        """Record health check result."""
        self.health_status.add(1 if is_healthy else 0)

    def record_mcp_call(
        self,
        success: bool,
        duration_ms: float,
        tool_name: str,
    ) -> None:
        """Record an MCP tool call."""
        attrs = {"tool_name": tool_name}

        self.mcp_calls_total.add(1, attrs)

        if success:
            self.mcp_calls_success.add(1, attrs)
        else:
            self.mcp_calls_error.add(1, attrs)

        self.mcp_call_duration.record(duration_ms, attrs)

    def record_a2a_request(
        self,
        success: bool,
        duration_ms: float,
        target_agent: Optional[str] = None,
        intent: Optional[str] = None,
    ) -> None:
        """Record an A2A request."""
        attrs = {}
        if target_agent:
            attrs["target_agent"] = target_agent
        if intent:
            attrs["intent"] = intent

        self.a2a_metrics.record_request(success, duration_ms, attrs)


# Global metrics collector instance
_collectors: Dict[str, MetricsCollector] = {}


def get_metrics_collector(service_name: str) -> MetricsCollector:
    """
    Get or create a metrics collector for a service.

    Args:
        service_name: Name of the service

    Returns:
        MetricsCollector instance

    Example:
        >>> collector = get_metrics_collector("account-agent")
    """
    if service_name not in _collectors:
        _collectors[service_name] = MetricsCollector(service_name)
    return _collectors[service_name]
