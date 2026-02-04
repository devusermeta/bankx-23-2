"""
Transaction Agent Service - A2A enabled microservice for transaction operations.

This agent handles:
- Transaction history retrieval
- Transaction aggregation and analysis
- Transaction detail queries
"""

import os
import sys
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

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
from a2a_handler import TransactionAgentHandler

config = AgentConfig()
logger = get_logger(__name__)

handler: TransactionAgentHandler = None
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

    handler = TransactionAgentHandler(config)

    if config.AGENT_REGISTRY_URL:
        registry_client = RegistryClient(config.AGENT_REGISTRY_URL)

        try:
            agent_id = await registry_client.register(
                agent_name=config.AGENT_NAME,
                agent_type="domain",
                version=config.AGENT_VERSION,
                capabilities=[
                    "transaction.history",
                    "transaction.aggregation",
                    "transaction.details",
                ],
                endpoints={
                    "http": f"http://{config.HOST}:{config.PORT}",
                    "health": f"http://{config.HOST}:{config.PORT}/health",
                    "metrics": f"http://{config.HOST}:{config.PORT}/metrics",
                    "a2a": f"http://{config.HOST}:{config.PORT}/a2a/invoke",
                },
                metadata={
                    "description": "Handles transaction history, aggregation, and details",
                    "mcp_tools": [
                        "Reporting.searchTransactions",
                        "Reporting.aggregateTransactions",
                    ],
                    "output_formats": ["TXN_TABLE", "INSIGHTS_CARD"],
                },
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

    if registry_client:
        try:
            await registry_client.deregister()
        except Exception as e:
            logger.error(f"Failed to deregister: {e}")


app = FastAPI(
    title="Transaction Agent Service",
    description="A2A-enabled microservice for transaction operations",
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
    metrics_collector = get_metrics_collector(config.AGENT_NAME)
    mcp_healthy = await handler.check_mcp_health()
    registry_healthy = True
    if registry_client:
        try:
            await registry_client.heartbeat()
        except Exception:
            registry_healthy = False

    is_healthy = mcp_healthy and registry_healthy
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
    }


@app.get("/metrics")
async def metrics():
    return {
        "agent": config.AGENT_NAME,
        "version": config.AGENT_VERSION,
        "status": "active",
    }


@app.post("/a2a/invoke")
async def a2a_invoke(message: A2AMessage, request: Request) -> A2AResponse:
    start_time = time.perf_counter()
    logger.info(f"Received A2A request: intent={message.intent}")

    metrics_collector = get_metrics_collector(config.AGENT_NAME)

    try:
        response_payload = await handler.handle_a2a_message(message)
        duration_ms = (time.perf_counter() - start_time) * 1000

        metrics_collector.record_a2a_request(
            success=True,
            duration_ms=duration_ms,
            intent=message.intent,
        )

        response = A2AResponse(
            message_id=f"resp-{message.message_id}",
            correlation_id=message.correlation_id,
            protocol_version="1.0",
            source={
                "agent_id": config.AGENT_ID,
                "agent_name": config.AGENT_NAME,
            },
            target=message.source,
            status="success",
            response=response_payload,
            metadata={"processing_time_ms": duration_ms},
        )

        return response

    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000

        metrics_collector.record_a2a_request(
            success=False,
            duration_ms=duration_ms,
            intent=message.intent,
        )

        logger.error(f"A2A request failed: {e}", exc_info=True)

        return A2AResponse(
            message_id=f"resp-{message.message_id}",
            correlation_id=message.correlation_id,
            protocol_version="1.0",
            source={"agent_id": config.AGENT_ID, "agent_name": config.AGENT_NAME},
            target=message.source,
            status="error",
            response={"error": str(e)},
            metadata={"processing_time_ms": duration_ms},
        )


@app.get("/")
async def root():
    return {
        "agent": config.AGENT_NAME,
        "version": config.AGENT_VERSION,
        "type": "domain",
        "capabilities": [
            "transaction.history",
            "transaction.aggregation",
            "transaction.details",
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=config.HOST, port=config.PORT)
