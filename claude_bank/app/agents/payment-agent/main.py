"""
Payment Agent Service - A2A enabled microservice for payment operations.

This agent handles:
- Account balance inquiries
- Account limits checking
- Account disambiguation (when customer has multiple accounts)
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import httpx

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from a2a_sdk.models.message import A2AMessage, A2AResponse
from a2a_sdk.client.registry_client import RegistryClient
from common.observability import (
    setup_app_insights,
    setup_logging,
    get_logger,
    instrument_app,
    get_metrics_collector,
)
from config import AgentConfig
from a2a_handler import PaymentAgentHandler

# Configuration
config = AgentConfig()
logger = get_logger(__name__)

# Global state
handler: PaymentAgentHandler = None
registry_client: RegistryClient = None
heartbeat_task: asyncio.Task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown."""
    global handler, registry_client, heartbeat_task

    # Startup
    logger.info(f"Starting {config.AGENT_NAME} v{config.AGENT_VERSION}")

    # Initialize observability
    setup_app_insights(
        service_name=config.AGENT_NAME,
        service_version=config.AGENT_VERSION,
    )

    # Initialize handler
    handler = PaymentAgentHandler(config)

    # Initialize registry client
    if config.AGENT_REGISTRY_URL:
        registry_client = RegistryClient(config.AGENT_REGISTRY_URL)

        # Register with agent registry
        try:
            agent_id = await registry_client.register(
                agent_name=config.AGENT_NAME,
                agent_type="domain",
                version=config.AGENT_VERSION,
                capabilities=[
                    "account.balance",
                    "account.limits",
                    "account.disambiguation",
                ],
                endpoints={
                    "http": f"http://{config.HOST}:{config.PORT}",
                    "health": f"http://{config.HOST}:{config.PORT}/health",
                    "metrics": f"http://{config.HOST}:{config.PORT}/metrics",
                    "a2a": f"http://{config.HOST}:{config.PORT}/a2a/invoke",
                },
                metadata={
                    "description": "Handles account resolution, balance inquiries, and limits checking",
                    "mcp_tools": [
                        "Account.getCustomerAccounts",
                        "Account.getAccountDetails",
                    ],
                    "output_formats": ["TRANSFER_RESULT", "TRANSFER_APPROVAL"],
                },
            )
            logger.info(f"Registered with agent registry. Agent ID: {agent_id}")

            # Start heartbeat task
            heartbeat_task = asyncio.create_task(_heartbeat_loop())

        except Exception as e:
            logger.error(f"Failed to register with agent registry: {e}")
    else:
        logger.warning("Agent registry URL not configured. Running without registration.")

    logger.info(f"{config.AGENT_NAME} started successfully on port {config.PORT}")

    yield

    # Shutdown
    logger.info(f"Shutting down {config.AGENT_NAME}")

    # Cancel heartbeat task
    if heartbeat_task:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass

    # Deregister from agent registry
    if registry_client:
        try:
            await registry_client.deregister()
            logger.info("Deregistered from agent registry")
        except Exception as e:
            logger.error(f"Failed to deregister from agent registry: {e}")


# Create FastAPI app
app = FastAPI(
    title="Payment Agent Service",
    description="A2A-enabled microservice for payment operations",
    version=config.AGENT_VERSION,
    lifespan=lifespan,
)

# Instrument with OpenTelemetry
instrument_app(app)

# Setup logging
setup_logging(
    level=config.LOG_LEVEL,
    json_format=config.ENVIRONMENT == "production",
    service_name=config.AGENT_NAME,
)


async def _heartbeat_loop():
    """Send periodic heartbeats to agent registry."""
    while True:
        try:
            await asyncio.sleep(30)  # Send heartbeat every 30 seconds
            if registry_client:
                await registry_client.heartbeat()
                logger.debug("Heartbeat sent to agent registry")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Failed to send heartbeat: {e}")


@app.get("/health")
async def health():
    """Health check endpoint."""
    metrics_collector = get_metrics_collector(config.AGENT_NAME)

    # Check MCP service connectivity
    mcp_healthy = await handler.check_mcp_health()

    # Check registry connectivity
    registry_healthy = True
    if registry_client:
        try:
            await registry_client.heartbeat()
        except Exception:
            registry_healthy = False

    is_healthy = mcp_healthy and registry_healthy

    # Record health status
    metrics_collector.record_health_check(is_healthy)

    if not is_healthy:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "checks": {
                    "mcp_service": "healthy" if mcp_healthy else "unhealthy",
                    "agent_registry": "healthy" if registry_healthy else "unhealthy",
                },
            },
        )

    return {
        "status": "healthy",
        "agent": config.AGENT_NAME,
        "version": config.AGENT_VERSION,
        "checks": {
            "mcp_service": "healthy",
            "agent_registry": "healthy",
        },
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    # Return basic metrics for now
    # In production, use prometheus_client library
    return {
        "agent": config.AGENT_NAME,
        "version": config.AGENT_VERSION,
        "status": "active",
    }


@app.post("/a2a/invoke")
async def a2a_invoke(message: A2AMessage, request: Request) -> A2AResponse:
    """
    A2A invocation endpoint.

    Receives A2A messages from other agents (typically Supervisor)
    and routes them to the appropriate handler.
    """
    import time

    start_time = time.perf_counter()
    logger.info(
        f"Received A2A request: intent={message.intent}, "
        f"correlation_id={message.correlation_id}"
    )

    metrics_collector = get_metrics_collector(config.AGENT_NAME)

    try:
        # Route to handler based on intent
        response_payload = await handler.handle_a2a_message(message)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Record metrics
        metrics_collector.record_a2a_request(
            success=True,
            duration_ms=duration_ms,
            intent=message.intent,
        )

        # Build response
        response = A2AResponse(
            message_id=f"resp-{message.message_id}",
            correlation_id=message.correlation_id,
            protocol_version="1.0",
            source={
                "agent_id": config.AGENT_ID or "payment-agent-001",
                "agent_name": config.AGENT_NAME,
            },
            target=message.source,
            status="success",
            response=response_payload,
            metadata={"processing_time_ms": duration_ms},
        )

        logger.info(
            f"A2A request completed successfully: "
            f"intent={message.intent}, duration={duration_ms:.2f}ms"
        )

        return response

    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Record error metrics
        metrics_collector.record_a2a_request(
            success=False,
            duration_ms=duration_ms,
            intent=message.intent,
        )

        logger.error(
            f"A2A request failed: intent={message.intent}, error={str(e)}",
            exc_info=True,
        )

        # Build error response
        response = A2AResponse(
            message_id=f"resp-{message.message_id}",
            correlation_id=message.correlation_id,
            protocol_version="1.0",
            source={
                "agent_id": config.AGENT_ID or "payment-agent-001",
                "agent_name": config.AGENT_NAME,
            },
            target=message.source,
            status="error",
            response={"error": str(e), "error_type": type(e).__name__},
            metadata={"processing_time_ms": duration_ms},
        )

        return response


@app.get("/")
async def root():
    """Root endpoint with agent information."""
    return {
        "agent": config.AGENT_NAME,
        "version": config.AGENT_VERSION,
        "type": "domain",
        "capabilities": [
            "account.balance",
            "account.limits",
            "account.disambiguation",
        ],
        "status": "active",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level=config.LOG_LEVEL.lower(),
    )
