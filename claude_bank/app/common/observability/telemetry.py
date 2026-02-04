"""
OpenTelemetry instrumentation utilities for BankX A2A system.
"""

import functools
import time
from typing import Any, Callable, Dict, Optional
from contextlib import contextmanager

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from .app_insights import get_tracer


def instrument_app(app: FastAPI) -> None:
    """
    Instrument a FastAPI application with OpenTelemetry.

    This adds automatic instrumentation for:
    - FastAPI routes
    - HTTPX client requests
    - Redis operations (if used)

    Args:
        app: FastAPI application instance

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> instrument_app(app)
    """
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Instrument HTTPX (for A2A client calls)
    HTTPXClientInstrumentor().instrument()

    # Instrument Redis (for registry cache)
    try:
        RedisInstrumentor().instrument()
    except Exception:
        # Redis instrumentation is optional
        pass


@contextmanager
def create_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    kind: trace.SpanKind = trace.SpanKind.INTERNAL,
):
    """
    Create a traced span as a context manager.

    Args:
        name: Name of the span
        attributes: Optional attributes to add to the span
        kind: Type of span (INTERNAL, CLIENT, SERVER, etc.)

    Example:
        >>> with create_span("process_message", {"message_id": "123"}):
        ...     # do work
        ...     pass
    """
    tracer = get_tracer()
    with tracer.start_as_current_span(name, kind=kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


def add_span_attributes(**attributes: Any) -> None:
    """
    Add attributes to the current span.

    Args:
        **attributes: Key-value pairs to add as attributes

    Example:
        >>> add_span_attributes(customer_id="CUST-001", agent="account")
    """
    span = trace.get_current_span()
    if span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def trace_async(span_name: Optional[str] = None, **span_attributes):
    """
    Decorator to trace async functions.

    Args:
        span_name: Optional custom span name (defaults to function name)
        **span_attributes: Additional attributes to add to the span

    Example:
        >>> @trace_async(span_name="fetch_balance", agent_type="account")
        ... async def get_balance(customer_id: str):
        ...     return {"balance": 1000}
    """

    def decorator(func: Callable):
        name = span_name or func.__name__

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            with create_span(name, span_attributes):
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def trace_sync(span_name: Optional[str] = None, **span_attributes):
    """
    Decorator to trace synchronous functions.

    Args:
        span_name: Optional custom span name (defaults to function name)
        **span_attributes: Additional attributes to add to the span

    Example:
        >>> @trace_sync(span_name="validate_data")
        ... def validate(data: dict):
        ...     return True
    """

    def decorator(func: Callable):
        name = span_name or func.__name__

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            with create_span(name, span_attributes):
                return func(*args, **kwargs)

        return wrapper

    return decorator


def record_exception(exception: Exception) -> None:
    """
    Record an exception in the current span.

    Args:
        exception: Exception to record

    Example:
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     record_exception(e)
        ...     raise
    """
    span = trace.get_current_span()
    if span.is_recording():
        span.record_exception(exception)
        span.set_status(trace.Status(trace.StatusCode.ERROR, str(exception)))


def measure_latency(func: Callable) -> Callable:
    """
    Decorator to measure and record function latency.

    Adds a "latency_ms" attribute to the current span.

    Example:
        >>> @measure_latency
        ... async def slow_operation():
        ...     await asyncio.sleep(1)
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            latency_ms = (time.perf_counter() - start_time) * 1000
            add_span_attributes(latency_ms=latency_ms)

    return wrapper
