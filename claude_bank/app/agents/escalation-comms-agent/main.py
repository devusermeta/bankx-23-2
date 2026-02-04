"""
EscalationComms Agent Service - A2A enabled microservice for email notifications.

This agent handles:
- Sending support ticket notification emails
- Customer email notifications
- Bank employee email notifications
- Email delivery via Azure Communication Services
"""
import os
import sys
import asyncio
from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from a2a_sdk.models.message import A2AMessage, A2AResponse
from a2a_sdk.client.registry_client import RegistryClient
from common.observability import (
    setup_app_insights, setup_logging, get_logger,
    instrument_app, get_metrics_collector,
)
from config import AgentConfig
from a2a_handler import EscalationCommsAgentHandler

config = AgentConfig()
logger = get_logger(__name__)

handler: EscalationCommsAgentHandler = None
registry_client: RegistryClient = None
heartbeat_task: asyncio.Task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global handler, registry_client, heartbeat_task

    logger.info(f"Starting {config.AGENT_NAME} v{config.AGENT_VERSION}")

    setup_app_insights(
        service_name=config.AGENT_NAME,
        service_version=config.AGENT_VERSION,
    )

    handler = EscalationCommsAgentHandler(config)

    if config.AGENT_REGISTRY_URL:
        registry_client = RegistryClient(config.AGENT_REGISTRY_URL)
        try:
            agent_id = await registry_client.register(
                agent_name=config.AGENT_NAME,
                agent_type="communication",
                version=config.AGENT_VERSION,
                capabilities=[
                    "escalation.send_email",
                    "email.send",
                    "notification.send",
                    "escalation.send_ticket_email",
                    "ticket.notify"
                ],
                endpoints={
                    "http": f"http://{config.HOST}:{config.PORT}",
                    "health": f"http://{config.HOST}:{config.PORT}/health",
                    "a2a": f"http://{config.HOST}:{config.PORT}/a2a/invoke",
                },
                metadata={
                    "description": "Handles email notifications via Azure Communication Services",
                    "mcp_tools": ["escalationcomms.sendemail"],
                    "output_formats": ["EMAIL_CONFIRMATION", "TICKET_EMAIL_CONFIRMATION"],
                    "shared_by": ["ProdInfoFAQAgent", "AIMoneyCoachAgent"],
                },
                tags=["uc2", "uc3", "communication", "email", "escalation"],
            )
            logger.info(f"Registered with agent registry. Agent ID: {agent_id}")
            heartbeat_task = asyncio.create_task(_heartbeat_loop())
        except Exception as e:
            logger.error(f"Failed to register with agent registry: {e}")

    logger.info(f"{config.AGENT_NAME} started successfully on port {config.PORT}")
    yield

    logger.info(f"Shutting down {config.AGENT_NAME}")
    if heartbeat_task:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
    if handler:
        await handler.close()
    if registry_client:
        try:
            await registry_client.deregister()
        except Exception as e:
            logger.error(f"Failed to deregister: {e}")

app = FastAPI(
    title="EscalationComms Agent Service",
    description="A2A-enabled microservice for email notifications and escalation communications",
    version=config.AGENT_VERSION,
    lifespan=lifespan,
)

instrument_app(app)
setup_logging(
    level=config.LOG_LEVEL,
    json_format=config.ENVIRONMENT == "production",
    service_name=config.AGENT_NAME,
)

async def _heartbeat_loop():
    """Send periodic heartbeats to agent registry."""
    while True:
        try:
            await asyncio.sleep(30)
            if registry_client:
                await registry_client.heartbeat()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")

@app.get("/health")
async def health():
    """Health check endpoint."""
    metrics_collector = get_metrics_collector(config.AGENT_NAME)
    mcp_healthy = await handler.check_mcp_health()

    is_healthy = mcp_healthy
    metrics_collector.record_health_check(is_healthy)

    if not is_healthy:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "mcp_service": "unavailable"
            }
        )

    return {
        "status": "healthy",
        "agent": config.AGENT_NAME,
        "version": config.AGENT_VERSION,
        "mcp_service": "healthy"
    }

@app.post("/a2a/invoke")
async def a2a_invoke(message: A2AMessage, request: Request) -> A2AResponse:
    """
    A2A message handler endpoint.

    Receives A2A messages from ProdInfoFAQ or AIMoneyCoach agents
    to send email notifications.
    """
    start_time = time.perf_counter()
    logger.info(
        f"Received A2A request: intent={message.intent}, "
        f"from={message.source.get('agent_name', 'unknown')}"
    )

    metrics_collector = get_metrics_collector(config.AGENT_NAME)

    try:
        response_payload = await handler.handle_a2a_message(message)
        duration_ms = (time.perf_counter() - start_time) * 1000

        metrics_collector.record_a2a_request(
            success=True,
            duration_ms=duration_ms,
            intent=message.intent
        )

        logger.info(
            f"A2A request completed successfully: "
            f"intent={message.intent}, duration={duration_ms:.2f}ms"
        )

        return A2AResponse(
            message_id=f"resp-{message.message_id}",
            correlation_id=message.correlation_id,
            protocol_version="1.0",
            source={"agent_id": config.AGENT_ID, "agent_name": config.AGENT_NAME},
            target=message.source,
            status="success",
            response=response_payload,
            metadata={"processing_time_ms": duration_ms},
        )

    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        metrics_collector.record_a2a_request(
            success=False,
            duration_ms=duration_ms,
            intent=message.intent
        )
        logger.error(f"A2A request failed: {e}", exc_info=True)

        return A2AResponse(
            message_id=f"resp-{message.message_id}",
            correlation_id=message.correlation_id,
            protocol_version="1.0",
            source={"agent_id": config.AGENT_ID, "agent_name": config.AGENT_NAME},
            target=message.source,
            status="error",
            response={"error": str(e), "type": "EMAIL_ERROR"},
            metadata={"processing_time_ms": duration_ms},
        )

@app.get("/")
async def root():
    """Root endpoint with agent information."""
    return {
        "agent": config.AGENT_NAME,
        "version": config.AGENT_VERSION,
        "type": "communication",
        "capabilities": [
            "escalation.send_email",
            "email.send",
            "notification.send",
            "escalation.send_ticket_email",
            "ticket.notify"
        ],
        "description": "Email notification service for support ticket escalations",
        "shared_by": ["ProdInfoFAQAgent", "AIMoneyCoachAgent"],
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    metrics_collector = get_metrics_collector(config.AGENT_NAME)
    return metrics_collector.get_metrics()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
