"""
Supervisor Agent A2A Service

FastAPI server implementing Agent-to-Agent (A2A) protocol for routing.
Main entry point for BankX - routes queries to specialized agents.

Start: uv run --prerelease=allow python main.py
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import (
    A2A_SERVER_HOST,
    A2A_SERVER_PORT,
    LOG_LEVEL,
    SUPERVISOR_AGENT_NAME,
    SUPERVISOR_AGENT_VERSION,
    ACCOUNT_AGENT_A2A_URL,
    TRANSACTION_AGENT_A2A_URL,
    PAYMENT_AGENT_A2A_URL,
    PRODINFO_FAQ_AGENT_A2A_URL,
    AI_MONEY_COACH_AGENT_A2A_URL,
    ESCALATION_AGENT_A2A_URL,
    validate_config,
)
from agent_handler import SupervisorAgentHandler

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Silence noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)

# Global handler instance
handler: Optional[SupervisorAgentHandler] = None


# ==============================================================================
# Agent Card (A2A Discovery)
# ==============================================================================

AGENT_CARD = {
    "name": "Supervisor Agent",
    "description": (
        "BankX Main Routing Agent. "
        "Orchestrates user intent classification and routes requests to appropriate specialized agents. "
        "Handles account, transaction, payment, product info, AI coaching, and escalation queries."
    ),
    "url": f"http://localhost:{A2A_SERVER_PORT}",
    "version": "1.0.0",
    "capabilities": [
        "route_to_account",
        "route_to_transaction",
        "route_to_payment",
        "route_to_prodinfo",
        "route_to_aicoach",
        "route_to_escalation",
    ],
    "agent_id": f"{SUPERVISOR_AGENT_NAME}:{SUPERVISOR_AGENT_VERSION}",  # Format: name:version
    "endpoints": {
        "chat": f"http://localhost:{A2A_SERVER_PORT}/a2a/invoke",
        "health": f"http://localhost:{A2A_SERVER_PORT}/health",
    },
    "protocol": "a2a",
    "platform": "Azure AI Foundry",
    "mcp_backed": False,
    "foundry_v2_hosted": True,
    "metadata": {
        "project": "BankX",
        "role": "supervisor_router",
        "agent_name": SUPERVISOR_AGENT_NAME,
        "agent_version": str(SUPERVISOR_AGENT_VERSION),
        "specialist_agents": {
            "account": ACCOUNT_AGENT_A2A_URL,
            "transaction": TRANSACTION_AGENT_A2A_URL,
            "payment": PAYMENT_AGENT_A2A_URL,
            "prodinfo": PRODINFO_FAQ_AGENT_A2A_URL,
            "coach": AI_MONEY_COACH_AGENT_A2A_URL,
            "escalation": ESCALATION_AGENT_A2A_URL,
        },
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app"""
    global handler

    # Startup
    logger.info(f"Starting Supervisor Agent A2A Service on {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
    validate_config()
    handler = SupervisorAgentHandler()
    logger.info("Supervisor Agent A2A Service started")

    yield

    # Shutdown
    logger.info("Shutting down Supervisor Agent A2A Service...")


# Create FastAPI app
app = FastAPI(
    title="Supervisor Agent A2A Service",
    description="Main routing agent for BankX - routes to specialized agents",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (for development)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Request/Response Models
# ==============================================================================


class ChatMessage(BaseModel):
    """Single chat message"""
    role: str = Field(description="Message role (user or assistant)")
    content: str = Field(description="Message content")


class ChatRequest(BaseModel):
    """A2A chat request"""
    messages: list[ChatMessage] = Field(description="Conversation messages")
    customer_id: str = Field(description="Customer identifier")
    thread_id: str | None = Field(default=None, description="Thread identifier")
    user_mail: str | None = Field(default=None, description="Customer email")
    stream: bool = Field(default=False, description="Stream response")


class ChatResponse(BaseModel):
    """A2A chat response"""
    role: str = "assistant"
    content: str = Field(description="Response content")
    agent: str = "SupervisorAgent"


class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    agent: str = "SupervisorAgent"
    version: str = "1.0.0"


# ==============================================================================
# Endpoints
# ==============================================================================


@app.get("/health")
async def health() -> HealthResponse:
    """Health check endpoint"""
    return HealthResponse()


@app.get("/.well-known/agent.json")
async def agent_card():
    """
    Agent Card endpoint (A2A Discovery)
    
    Returns metadata about the agent's capabilities and protocol support.
    """
    logger.info("📋 Agent card requested")
    return JSONResponse(content=AGENT_CARD)


@app.post("/a2a/invoke")
async def invoke_agent(request: ChatRequest):
    """
    Main A2A invocation endpoint
    
    Routes user queries to appropriate specialist agents.
    Supports both streaming and non-streaming modes.
    """
    if not handler:
        raise HTTPException(status_code=503, detail="Agent handler not initialized")

    try:
        # Convert messages to list of dicts
        messages = [msg.dict() for msg in request.messages]
        
        # Generate thread_id if not provided
        thread_id = request.thread_id or f"thread_{asyncio.get_event_loop().time()}"

        logger.info(
            f"Processing query for customer {request.customer_id}, "
            f"thread {thread_id}, messages={len(messages)}"
        )

        # Process message and route to specialist
        result = await handler.process_message(
            messages=messages,
            thread_id=thread_id,
            customer_id=request.customer_id,
            user_mail=request.user_mail,
            stream=request.stream,
        )

        if request.stream:
            # Streaming response (text/plain)
            async def event_generator():
                async for chunk in result:
                    yield chunk

            return StreamingResponse(
                event_generator(),
                media_type="text/plain",
            )
        else:
            # Non-streaming response (JSON)
            full_response = ""
            async for chunk in result:
                full_response += chunk
            
            return JSONResponse(
                content=ChatResponse(
                    content=full_response,
                ).dict()
            )

    except Exception as e:
        logger.error(f"Error in invoke_agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# Main
# ==============================================================================


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=A2A_SERVER_HOST,
        port=A2A_SERVER_PORT,
        log_level=LOG_LEVEL.lower(),
    )
