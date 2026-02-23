"""
Payment Agent v2 A2A Microservice - FastAPI Server

Simplified A2A protocol server for transfers/payments.
REPLACES the old payment-agent-a2a on port 9003.

Features:
- Single unified MCP server connection (payment-unified)
- Streamlined validate → approve → execute flow
- References existing Foundry agent (created once)
- Same port 9003 (no supervisor changes needed)
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agent_handler import PaymentAgentHandler
from config import (
    A2A_SERVER_PORT,
    A2A_SERVER_HOST,
    PAYMENT_AGENT_NAME,
    PAYMENT_AGENT_VERSION,
    PAYMENT_UNIFIED_MCP_URL,
    validate_config,
)

# Singleton handler
_handler_instance: PaymentAgentHandler | None = None


async def get_payment_agent_handler() -> PaymentAgentHandler:
    """Get singleton Payment Agent handler instance"""
    global _handler_instance
    if _handler_instance is None:
        _handler_instance = PaymentAgentHandler()
        await _handler_instance.initialize()
    return _handler_instance


async def cleanup_handler():
    """Cleanup handler resources"""
    global _handler_instance
    if _handler_instance:
        await _handler_instance.cleanup()
        _handler_instance = None

# Setup logging
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
    user_email: str | None = None
    stream: bool = True


class ChatResponse(BaseModel):
    role: str
    content: str
    agent: str


# Agent card for A2A discovery
AGENT_CARD = {
    "name": "Payment Agent v2",
    "description": (
        "Simplified banking agent for money transfers. "
        "Validates transfers, gets user approval, and executes payments. "
        "Streamlined flow with single unified MCP server."
    ),
    "url": f"http://localhost:{A2A_SERVER_PORT}",
    "version": PAYMENT_AGENT_VERSION,
    "capabilities": [
        "transfer_validation",
        "payment_transfer",
        "limit_checking",
        "beneficiary_lookup"
    ],
    "agent_id": f"{PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION}",
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
        "role": "payment_specialist",
        "mcp_servers": ["payment-unified"],
        "agent_name": PAYMENT_AGENT_NAME,
        "agent_version": PAYMENT_AGENT_VERSION,
        "simplified": True,
        "replaces": "payment-agent-a2a"
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    logger.info("🚀 Starting Payment Agent v2 A2A Microservice...")
    
    # Validate configuration
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        raise
    
    # Initialize handler
    handler = await get_payment_agent_handler()
    logger.info("✅ Payment Agent v2 Handler initialized")
    
    logger.info(f"✅ Payment Agent v2 A2A Server ready on {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
    logger.info(f"   Agent Card: http://localhost:{A2A_SERVER_PORT}/.well-known/agent.json")
    logger.info(f"   Chat Endpoint: http://localhost:{A2A_SERVER_PORT}/a2a/invoke")
    
    yield
    
    # Cleanup on shutdown
    logger.info("🛑 Shutting down Payment Agent v2 A2A Microservice...")
    await cleanup_handler()
    logger.info("✅ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Payment Agent v2 A2A Server",
    description="Simplified banking transfer agent exposed via A2A protocol",
    version=PAYMENT_AGENT_VERSION,
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
async def chat_endpoint(request: ChatRequest):
    """
    A2A Protocol: Chat Invocation Endpoint
    Processes messages and returns agent responses (streaming or non-streaming)
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"[A2A INVOKE] 💬 CHAT REQUEST RECEIVED")
    logger.info(f"[A2A INVOKE]   thread_id: {request.thread_id}")
    logger.info(f"[A2A INVOKE]   customer_id: {request.customer_id}")
    logger.info(f"[A2A INVOKE]   user_email: {request.user_email}")
    logger.info(f"[A2A INVOKE]   stream: {request.stream}")
    logger.info(f"[A2A INVOKE]   messages: {len(request.messages)} messages")
    logger.info(f"{'='*80}\n")
    
    try:
        # Get handler
        logger.info(f"[A2A INVOKE] 🔧 Getting payment agent handler...")
        handler = await get_payment_agent_handler()
        logger.info(f"[A2A INVOKE] ✅ Handler obtained")
        
        # Extract last user message
        if not request.messages:
            logger.error(f"[A2A INVOKE] ❌ No messages provided")
            raise HTTPException(status_code=400, detail="No messages provided")
        
        last_message = request.messages[-1]
        if last_message.role != "user":
            logger.error(f"[A2A INVOKE] ❌ Last message is not from user (role={last_message.role})")
            raise HTTPException(status_code=400, detail="Last message must be from user")
        
        user_message = last_message.content
        logger.info(f"[A2A INVOKE] 📝 User message: {user_message[:100]}...")
        
        # Generate thread_id if not provided
        thread_id = request.thread_id or f"thread_{asyncio.current_task().get_name()}"
        customer_id = request.customer_id or "CUST-001"
        user_email = request.user_email
        
        logger.info(f"[A2A INVOKE] 🎯 Processing parameters:")
        logger.info(f"[A2A INVOKE]   thread_id: {thread_id}")
        logger.info(f"[A2A INVOKE]   customer_id: {customer_id}")
        logger.info(f"[A2A INVOKE]   user_email: {user_email}")
        logger.info(f"[A2A INVOKE]   stream: {request.stream}")
        
        # Process message with streaming support
        if request.stream:
            logger.info(f"[A2A INVOKE] 📤 STREAMING mode - creating StreamingResponse")
            
            async def stream_response():
                """Stream agent response chunks"""
                try:
                    logger.info(f"[A2A INVOKE] 🔄 Starting streaming loop...")
                    chunk_count = 0
                    async for chunk in handler.process_message(
                        message=user_message,
                        thread_id=thread_id,
                        customer_id=customer_id,
                        user_email=user_email,
                        stream=True,
                    ):
                        chunk_count += 1
                        logger.debug(f"[A2A INVOKE] 📦 Chunk {chunk_count}: {len(chunk)} chars")
                        # A2A protocol: stream chunks as SSE
                        yield f"data: {chunk}\n\n"
                    
                    logger.info(f"[A2A INVOKE] ✅ Streaming completed - {chunk_count} chunks sent")
                    # End of stream marker
                    yield "data: [DONE]\n\n"
                    
                except Exception as e:
                    logger.error(f"[A2A INVOKE] ❌ Error during streaming: {e}", exc_info=True)
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
            logger.info(f"[A2A INVOKE] 📥 NON-STREAMING mode - collecting full response")
            full_response = ""
            chunk_count = 0
            async for chunk in handler.process_message(
                message=user_message,
                thread_id=thread_id,
                customer_id=customer_id,
                user_email=user_email,
                stream=False,
            ):
                chunk_count += 1
                full_response += chunk
                logger.debug(f"[A2A INVOKE] 📦 Chunk {chunk_count}: {len(chunk)} chars")
            
            logger.info(f"[A2A INVOKE] ✅ Response collected - {len(full_response)} chars from {chunk_count} chunks")
            logger.info(f"[A2A INVOKE] 📤 Returning JSON response")
            
            # Return A2A format response
            return JSONResponse(
                content={
                    "messages": [
                        {"role": "user", "content": user_message},
                        {"role": "assistant", "content": full_response},
                    ],
                    "thread_id": thread_id,
                    "agent": PAYMENT_AGENT_NAME,
                    "version": PAYMENT_AGENT_VERSION
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[A2A INVOKE] ❌ Error processing request: {e}", exc_info=True)
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
            "agent": PAYMENT_AGENT_NAME,
            "version": PAYMENT_AGENT_VERSION,
            "port": A2A_SERVER_PORT,
            "mcp_url": PAYMENT_UNIFIED_MCP_URL
        }
    )


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return JSONResponse(
        content={
            "service": "Payment Agent v2 A2A Microservice",
            "version": PAYMENT_AGENT_VERSION,
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
    logger.info(f"Agent: {PAYMENT_AGENT_NAME} v{PAYMENT_AGENT_VERSION}")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=A2A_SERVER_PORT,
        reload=False,  # Set to True for development
        log_level="info",
    )
