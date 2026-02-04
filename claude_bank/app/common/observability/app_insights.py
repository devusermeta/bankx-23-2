"""
Application Insights integration for BankX A2A system.

This module provides centralized Application Insights setup with OpenTelemetry.
"""

import os
import logging
from typing import Optional

from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes

logger = logging.getLogger(__name__)

_tracer: Optional[trace.Tracer] = None
_meter: Optional[metrics.Meter] = None
_initialized = False


def setup_app_insights(
    service_name: str,
    service_namespace: str = "bankx",
    service_version: str = "1.0.0",
    connection_string: Optional[str] = None,
) -> None:
    """
    Set up Application Insights with OpenTelemetry.

    Args:
        service_name: Name of the service (e.g., "account-agent")
        service_namespace: Namespace for grouping services (default: "bankx")
        service_version: Version of the service
        connection_string: Application Insights connection string
                         (defaults to APPLICATIONINSIGHTS_CONNECTION_STRING env var)

    Example:
        >>> setup_app_insights(
        ...     service_name="account-agent",
        ...     service_version="1.0.0"
        ... )
    """
    global _tracer, _meter, _initialized

    if _initialized:
        logger.warning(f"Application Insights already initialized for {service_name}")
        return

    # Get connection string from parameter or environment
    conn_str = connection_string or os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")

    if not conn_str:
        logger.warning(
            "No Application Insights connection string found. "
            "Telemetry will not be exported. "
            "Set APPLICATIONINSIGHTS_CONNECTION_STRING environment variable."
        )
        # Continue with local telemetry only
        _initialize_local_telemetry(service_name, service_namespace, service_version)
        return

    try:
        # Create resource with service information
        resource = Resource.create(
            {
                ResourceAttributes.SERVICE_NAME: service_name,
                ResourceAttributes.SERVICE_NAMESPACE: service_namespace,
                ResourceAttributes.SERVICE_VERSION: service_version,
                ResourceAttributes.DEPLOYMENT_ENVIRONMENT: os.getenv(
                    "ENVIRONMENT", "development"
                ),
            }
        )

        # Configure Azure Monitor with OpenTelemetry
        configure_azure_monitor(
            connection_string=conn_str,
            resource=resource,
            enable_live_metrics=True,  # Enable live metrics streaming
        )

        # Get tracer and meter
        _tracer = trace.get_tracer(service_name, service_version)
        _meter = metrics.get_meter(service_name, service_version)

        _initialized = True

        logger.info(
            f"Application Insights initialized successfully for {service_name} "
            f"(version: {service_version})"
        )

    except Exception as e:
        logger.error(f"Failed to initialize Application Insights: {e}")
        # Fall back to local telemetry
        _initialize_local_telemetry(service_name, service_namespace, service_version)


def _initialize_local_telemetry(
    service_name: str, service_namespace: str, service_version: str
) -> None:
    """Initialize local telemetry without Azure Monitor export."""
    global _tracer, _meter, _initialized

    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: service_name,
            ResourceAttributes.SERVICE_NAMESPACE: service_namespace,
            ResourceAttributes.SERVICE_VERSION: service_version,
        }
    )

    # Set up local tracer provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    _tracer = trace.get_tracer(service_name, service_version)

    # Set up local meter provider
    meter_provider = MeterProvider(resource=resource)
    metrics.set_meter_provider(meter_provider)
    _meter = metrics.get_meter(service_name, service_version)

    _initialized = True

    logger.info(
        f"Local telemetry initialized for {service_name} "
        "(telemetry will not be exported to Azure Monitor)"
    )


def get_tracer() -> trace.Tracer:
    """
    Get the configured OpenTelemetry tracer.

    Returns:
        Tracer instance for creating spans

    Raises:
        RuntimeError: If Application Insights has not been initialized

    Example:
        >>> tracer = get_tracer()
        >>> with tracer.start_as_current_span("my_operation"):
        ...     # do work
        ...     pass
    """
    if _tracer is None:
        raise RuntimeError(
            "Application Insights not initialized. Call setup_app_insights() first."
        )
    return _tracer


def get_meter() -> metrics.Meter:
    """
    Get the configured OpenTelemetry meter.

    Returns:
        Meter instance for creating metrics

    Raises:
        RuntimeError: If Application Insights has not been initialized

    Example:
        >>> meter = get_meter()
        >>> counter = meter.create_counter("requests_total")
        >>> counter.add(1, {"endpoint": "/api/v1/agents"})
    """
    if _meter is None:
        raise RuntimeError(
            "Application Insights not initialized. Call setup_app_insights() first."
        )
    return _meter


def is_initialized() -> bool:
    """Check if Application Insights has been initialized."""
    return _initialized
