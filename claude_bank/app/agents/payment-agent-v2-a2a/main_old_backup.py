"""
Payment Agent v2 A2A Microservice - FastAPI Server

Simplified A2A protocol server for transferstransfers/payments.
REPLACES the old payment-agent-a2a on port 9003.

Features:
- Single unified MCP server connection (payment-unified)
- Streamlined validate → approve → execute flow
- Same A2A protocol for compatibility with supervisor
- Same port 9003 (no supervisor changes needed)
"""

import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from agent_handler import PaymentAgentHandler

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)

# Silence noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("mcp.client.streamable_http").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Configuration
A2A_SERVER_PORT = int(os.getenv("PAYMENT_AGENT_PORT", "9003"))
A2A_SERVER_HOST = os.getenv("PAYMENT_AGENT_HOST", "0.0.0.0")
AGENT_NAME = "payment-agent-v2"
AGENT_VERSION = "2.0.0"


# Pydantic models for A2A protocol
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    thread_id: str | None = None
    customer_id: str | None = None
    user_email: str | None = None


class ChatResponse(BaseModel):
    response: str
    thread_id: str
    success: bool
    error: str | None = None


# Agent card for A2A discovery
AGENT_CARD = {
    "name": "Payment Agent v2",
    "description": (
        "Simplified banking agent for money transfers. "
        "Validates transfers, gets user approval, and executes payments. "
        "Streamlined flow with single unified MCP server."
    ),
    "url": f"http://localhost:{A2A_SERVER_PORT}",
    "version": AGENT_VERSION,
    "capabilities": [
        "transfer_validation",
        "payment_transfer",
        "limit_checking",
        "beneficiary_lookup"
    ],
    "agent_id": f"{AGENT_NAME}:{AGENT_VERSION}",
    "endpoints": {
        "chat": f"http://localhost:{A2A_SERVER_PORT}/a2a/invoke",
        "health": f"http://localhost:{A2A_SERVER_PORT}/health",
    },
    "protocol": "a2a",
    "platform": "Azure AI Foundry",
    "mcp_backed": True,
    "metadata": {
        "project": "BankX",
        "role": "payment_specialist",
        "mcp_servers": ["payment-unified"],
        "agent_name": AGENT_NAME,
        "agent_version": AGENT_VERSION,
        "simplified": True,
        "replaces": "payment-agent-a2a"
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    logger.info("🚀 Starting Payment Agent v2 A2A Microservice...")
    
    # Validate required environment variables
    required_vars = ["AZURE_PROJECT_ENDPOINT", "AZURE_OPENAI_DEPLOYMENT"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"❌ Missing required environment variables: {missing_vars}")
        raise ValueError(f"Missing environment variables: {missing_vars}")
    
    logger.info("✅ Configuration validated")
    logger.info(f"✅ Payment Agent v2 A2A Server ready on {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
    logger.info(f"   Agent Card: http://localhost:{A2A_SERVER_PORT}/.well-known/agent.json")
    logger.info(f"   Chat Endpoint: http://localhost:{A2A_SERVER_PORT}/a2a/invoke")
    logger.info(f"   MCP Server: {os.getenv('PAYMENT_UNIFIED_MCP_URL', 'http://localhost:8076/mcp')}")
    
    yield
    
    # Cleanup on shutdown
    logger.info("🛑 Shutting down Payment Agent v2 A2A Microservice...")
    logger.info("✅ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Payment Agent v2 A2A Server",
    description="Simplified banking transfer agent exposed via A2A protocol",
    version=AGENT_VERSION,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """
    A2A Protocol: Agent Card Discovery Endpoint
    Returns agent metadata for discovery by other agents
    """
    logger.info("📋 Agent card requested")
    return JSONResponse(content=AGENT_CARD)


@app.post("/a2a/invoke")
async def chat_endpoint(request: ChatRequest) -> JSONResponse:
    """
    A2A Protocol: Chat Invocation Endpoint
    Processes messages and returns agent responses
    """
    logger.info(
        f"💬 Chat request received: "
        f"thread={request.thread_id}, "
        f"customer={request.customer_id}, "
        f"email={request.user_email}"
    )
    
    try:
        # Validate request
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        last_message = request.messages[-1]
        if last_message.role != "user":
            raise HTTPException(status_code=400, detail="Last message must be from user")
        
        user_message = last_message.content
        
        # Get or default identifiers
        customer_id = request.customer_id or "CUST-001"
        user_email = request.user_email or "user@bankx.com"
        thread_id = request.thread_id
        
        # Create handler
        handler = PaymentAgentHandler(
            customer_id=customer_id,
            user_email=user_email,
            thread_id=thread_id
        )
        
        # Process message
        logger.info(f"[A2A] Processing message for {customer_id}: {user_message[:100]}...")
        result = await handler.handle_message(user_message)
        
        if not result["success"]:
            logger.error(f"[A2A] ❌ Handler error: {result.get('error')}")
        else:
            logger.info(f"[A2A] ✅ Response generated ({len(result['response'])} chars)")
        
        # Return response in A2A format
        return JSONResponse(
            content={
                "messages": [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": result["response"]},
                ],
                "thread_id": result["thread_id"],
                "agent": AGENT_NAME,
                "version": AGENT_VERSION
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing request: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        content={
            "status": "healthy",
            "agent": AGENT_NAME,
            "version": AGENT_VERSION,
            "port": A2A_SERVER_PORT,
            "mcp_url": os.getenv("PAYMENT_UNIFIED_MCP_URL", "http://localhost:8076/mcp")
        }
    )


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return JSONResponse(
        content={
            "service": "Payment Agent v2 A2A Microservice",
            "version": AGENT_VERSION,
            "description": "Simplified transfer agent with unified MCP server",
            "agent_card": f"http://localhost:{A2A_SERVER_PORT}/.well-known/agent.json",
            "endpoints": {
                "chat": "/a2a/invoke",
                "health": "/health",
                "agent_card": "/.well-known/agent.json",
            },
            "metadata": {
                "replaces": "payment-agent-a2a",
                "same_port": True,
                "mcp_servers": 1,
                "flow": "validate → approve → execute"
            }
        }
    )


if __name__ == "__main__":
    logger.info("Starting Payment Agent v2 A2A server...")
    logger.info(f"Port: {A2A_SERVER_PORT}")
    logger.info(f"Host: {A2A_SERVER_HOST}")
    
    uvicorn.run(
        "main:app",
        host=A2A_SERVER_HOST,
        port=A2A_SERVER_PORT,
        reload=False,  # Set to True for development
        log_level="info",
    )
