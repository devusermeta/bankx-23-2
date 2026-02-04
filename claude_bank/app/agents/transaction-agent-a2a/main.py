"""
Transaction Agent A2A Microservice - FastAPI Server
Implements A2A protocol with agent card discovery and chat endpoints
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agent_handler import get_transaction_agent_handler, cleanup_handler
from config import (
    A2A_SERVER_PORT,
    A2A_SERVER_HOST,
    TRANSACTION_AGENT_NAME,
    TRANSACTION_AGENT_VERSION,
    validate_config,
)

# Setup logging - reduce verbosity
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)

# Silence noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("mcp.client.streamable_http").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# Pydantic models for A2A protocol
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    thread_id: str | None = None
    customer_id: str | None = None
    stream: bool = True


class ChatResponse(BaseModel):
    role: str
    content: str
    agent: str


# Agent card for A2A discovery
AGENT_CARD = {
    "name": "Transaction Agent",
    "description": (
        "Specialized banking agent for transaction history and payment records. "
        "Handles transaction queries, history retrieval, filtering, and categorization. "
        "Uses MCP tools to access account data and transaction history."
    ),
    "url": f"http://localhost:{A2A_SERVER_PORT}",
    "version": "1.0.0",
    "capabilities": ["transaction_history", "transaction_search", "transaction_filtering", "transaction_categorization"],
    "agent_id": f"{TRANSACTION_AGENT_NAME}:{TRANSACTION_AGENT_VERSION}",
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
        "role": "transaction_specialist",
        "mcp_servers": ["account", "transaction"],
        "agent_name": TRANSACTION_AGENT_NAME,
        "agent_version": TRANSACTION_AGENT_VERSION,
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    logger.info("🚀 Starting Transaction Agent A2A Microservice...")
    
    # Validate configuration
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        raise
    
    # Initialize handler
    handler = await get_transaction_agent_handler()
    logger.info("✅ Transaction Agent Handler initialized")
    
    logger.info(f"✅ Transaction Agent A2A Server ready on {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
    logger.info(f"   Agent Card: http://localhost:{A2A_SERVER_PORT}/.well-known/agent.json")
    logger.info(f"   Chat Endpoint: http://localhost:{A2A_SERVER_PORT}/a2a/invoke")
    
    yield
    
    # Cleanup on shutdown
    logger.info("🛑 Shutting down Transaction Agent A2A Microservice...")
    await cleanup_handler()
    logger.info("✅ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Transaction Agent A2A Server",
    description="Banking transaction specialist agent exposed via A2A protocol",
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


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """
    A2A Protocol: Agent Card Discovery Endpoint
    Returns agent metadata for discovery by other agents
    """
    logger.info("📋 Agent card requested")
    return JSONResponse(content=AGENT_CARD)


@app.post("/a2a/invoke")
async def chat_endpoint(request: ChatRequest):
    """
    A2A Protocol: Chat Invocation Endpoint
    Processes messages and returns agent responses
    """
    logger.info(f"💬 Chat request received: thread={request.thread_id}, customer={request.customer_id}")
    
    try:
        # Get handler
        handler = await get_transaction_agent_handler()
        
        # Extract last user message
        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")
        
        last_message = request.messages[-1]
        if last_message.role != "user":
            raise HTTPException(status_code=400, detail="Last message must be from user")
        
        user_message = last_message.content
        
        # Generate thread_id if not provided
        thread_id = request.thread_id or f"thread_{asyncio.current_task().get_name()}"
        customer_id = request.customer_id or "CUST001"
        
        # Process message with streaming
        if request.stream:
            async def stream_response():
                """Stream agent response chunks"""
                try:
                    async for chunk in handler.process_message(
                        message=user_message,
                        thread_id=thread_id,
                        customer_id=customer_id,
                        stream=True,
                    ):
                        # A2A protocol: stream chunks as SSE
                        yield f"data: {chunk}\n\n"
                    
                    # End of stream marker
                    yield "data: [DONE]\n\n"
                    
                except Exception as e:
                    logger.error(f"❌ Error during streaming: {e}", exc_info=True)
                    yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            
            return StreamingResponse(
                stream_response(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # Non-streaming response
            full_response = ""
            async for chunk in handler.process_message(
                message=user_message,
                thread_id=thread_id,
                customer_id=customer_id,
                stream=False,
            ):
                full_response += chunk
            
            return JSONResponse(
                content={
                    "messages": [
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": full_response},
                    ]
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        content={
            "status": "healthy",
            "agent": "TransactionAgent",
            "version": TRANSACTION_AGENT_VERSION,
            "port": A2A_SERVER_PORT,
        }
    )


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return JSONResponse(
        content={
            "service": "Transaction Agent A2A Microservice",
            "version": "1.0.0",
            "agent_card": f"http://localhost:{A2A_SERVER_PORT}/.well-known/agent.json",
            "endpoints": {
                "chat": "/a2a/invoke",
                "health": "/health",
                "agent_card": "/.well-known/agent.json",
            },
        }
    )


if __name__ == "__main__":
    logger.info("Starting Transaction Agent A2A server...")
    uvicorn.run(
        "main:app",
        host=A2A_SERVER_HOST,
        port=A2A_SERVER_PORT,
        reload=True,
        log_level="info",
    )
