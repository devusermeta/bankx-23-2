"""
Escalation Agent A2A Service

FastAPI server implementing Agent-to-Agent (A2A) protocol for ticket management.
Handles customer support tickets using Escalation MCP tools.

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
    ESCALATION_AGENT_NAME,
    ESCALATION_AGENT_VERSION,
)
from agent_handler import EscalationAgentHandler

# Configure logging
logging.basicConfig(
    level=LOG_LEVEL,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Silence noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("mcp.client.streamable_http").setLevel(logging.WARNING)

# Global agent handler instance
handler: Optional[EscalationAgentHandler] = None

# ==============================================================================
# Agent Card (A2A Discovery)
# ==============================================================================

AGENT_CARD = {
    "name": "Escalation Agent",
    "description": (
        "BankX Ticket Management & Escalation Agent. "
        "Handles customer support tickets, escalations, and email notifications. "
        "Uses MCP tools for ticket management and Azure Communication Services for emails."
    ),
    "url": f"http://localhost:{A2A_SERVER_PORT}",
    "version": "1.0.0",
    "capabilities": [
        "create_ticket",
        "view_tickets",
        "update_ticket",
        "close_ticket",
        "ticket_status",
    ],
    "agent_id": f"{ESCALATION_AGENT_NAME}:{ESCALATION_AGENT_VERSION}",  # Format: name:version
    "endpoints": {
        "chat": f"http://localhost:{A2A_SERVER_PORT}/a2a/invoke",
        "health": f"http://localhost:{A2A_SERVER_PORT}/health",
    },
    "protocol": "a2a",
    "platform": "Azure AI Foundry",
    "mcp_backed": True,
    "foundry_v2_hosted": True,
    "metadata": {
        "project": "BankX",
        "role": "escalation_specialist",
        "mcp_servers": ["escalation-comms"],
        "agent_name": ESCALATION_AGENT_NAME,
        "agent_version": str(ESCALATION_AGENT_VERSION),
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for FastAPI app"""
    global handler

    # Startup
    logger.info("Starting Escalation Agent A2A Service...")
    handler = EscalationAgentHandler()
    logger.info(f"Service started on port {A2A_SERVER_PORT}")

    yield

    # Shutdown
    logger.info("Shutting down Escalation Agent A2A Service...")


# Create FastAPI app
app = FastAPI(
    title="Escalation Agent A2A Service",
    description="Agent-to-Agent communication service for ticket management",
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
    """Single message in conversation"""

    role: str = Field(description="Message role (user/assistant)")
    content: str = Field(description="Message content")


class ChatRequest(BaseModel):
    """Chat request payload (A2A Protocol)"""

    messages: list[ChatMessage] = Field(description="Conversation messages")
    stream: bool = Field(default=False, description="Enable streaming response")
    customer_id: str = Field(description="Customer unique identifier")
    thread_id: Optional[str] = Field(
        default=None, description="Thread ID for conversation continuity"
    )


class ChatResponse(BaseModel):
    """Chat response payload (A2A Protocol)"""

    role: str = Field(default="assistant", description="Response role")
    content: str = Field(description="Agent's response")
    agent: str = Field(default="EscalationAgent", description="Agent name")


# ==============================================================================
# A2A Endpoints
# ==============================================================================


@app.get("/.well-known/agent.json")
async def get_agent_card():
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

    Processes user messages and returns agent responses.
    Supports both streaming and non-streaming modes.
    """
    if not handler:
        raise HTTPException(status_code=503, detail="Agent handler not initialized")

    try:
        # Extract messages array (full conversation history)
        messages = request.messages if request.messages else []
        
        # Generate thread_id if not provided
        thread_id = request.thread_id or f"thread_{asyncio.get_event_loop().time()}"

        logger.info(
            f"Processing message for customer {request.customer_id}, "
            f"thread {thread_id}, stream={request.stream}, messages_count={len(messages)}"
        )

        # Process message with full conversation history
        result = await handler.process_message(
            messages=messages,
            thread_id=thread_id,
            customer_id=request.customer_id,
            stream=request.stream,
        )

        if request.stream:
            # Streaming response (text/event-stream)
            async def event_generator():
                async for chunk in result:
                    # Return plain text chunks
                    yield chunk

            return StreamingResponse(
                event_generator(),
                media_type="text/plain",
            )
        else:
            # Non-streaming response
            full_response = ""
            async for chunk in result:
                full_response += chunk
            
            return JSONResponse(
                content=ChatResponse(
                    role="assistant",
                    content=full_response,
                    agent="EscalationAgent",
                ).model_dump()
            )

    except Exception as e:
        logger.error(f"Error in invoke_agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ==============================================================================
# Health & Utility Endpoints
# ==============================================================================


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "escalation-agent-a2a",
        "version": "1.0.0",
        "handler_initialized": handler is not None,
    }


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Escalation Agent A2A Service",
        "version": "1.0.0",
        "agent_card": "/.well-known/agent.json",
        "invoke_endpoint": "/a2a/invoke",
        "health": "/health",
        "docs": "/docs",
    }


# ==============================================================================
# Main Entry Point
# ==============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting Escalation Agent A2A Service on {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")

    uvicorn.run(
        "main:app",
        host=A2A_SERVER_HOST,
        port=A2A_SERVER_PORT,
        reload=True,
        log_level=LOG_LEVEL.lower(),
    )
