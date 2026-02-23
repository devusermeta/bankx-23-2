"""
Payment Agent v2 A2A Microservice - FastAPI Server

Simplified A2A protocol server for transfers/payments.
REPLACES the old payment-agent-a2a on port 9003.

Pattern: References existing agent in Azure AI Foundry (created via create_agent_in_foundry.py)
"""

import os
import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent_handler_new import PaymentAgentHandler
from config import PAYMENT_AGENT_PORT, PAYMENT_AGENT_HOST, PAYMENT_AGENT_NAME, PAYMENT_AGENT_VERSION

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)

# Silence noisy loggers
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Global handler instance
payment_handler: PaymentAgentHandler | None = None


# Pydantic models for A2A protocol
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    thread_id: str | None = None
    customer_id: str | None = None
    user_email: str | None = None


# Agent card for A2A discovery
AGENT_CARD = {
    "name": "Payment Agent v2",
    "description": (
        "Simplified banking agent for money transfers. "
        "Validates transfers, gets user approval, and executes payments. "
        "Streamlined flow with single unified MCP server."
    ),
    "url": f"http://localhost:{PAYMENT_AGENT_PORT}",
    "version": PAYMENT_AGENT_VERSION,
    "capabilities": [
        "transfer_validation",
        "payment_transfer",
        "limit_checking",
        "beneficiary_lookup"
    ],
    "agent_id": f"{PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION}",
    "endpoints": {
        "chat": f"http://localhost:{PAYMENT_AGENT_PORT}/a2a/invoke",
        "health": f"http://localhost:{PAYMENT_AGENT_PORT}/health",
    },
    "protocol": "a2a",
    "platform": "Azure AI Foundry",
    "mcp_backed": True,
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
    global payment_handler
    
    logger.info("🚀 Starting Payment Agent v2 A2A Microservice...")
    
    # Initialize handler
    payment_handler = PaymentAgentHandler()
    await payment_handler.initialize()
    
    logger.info("✅ Payment Agent v2 A2A Server ready")
    logger.info(f"   Server: http://{PAYMENT_AGENT_HOST}:{PAYMENT_AGENT_PORT}")
    logger.info(f"   Agent Card: http://localhost:{PAYMENT_AGENT_PORT}/.well-known/agent.json")
    logger.info(f"   Chat Endpoint: http://localhost:{PAYMENT_AGENT_PORT}/a2a/invoke")
    logger.info(f"   Agent: {PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION}")
    
    yield
    
    # Cleanup on shutdown
    logger.info("🛑 Shutting down Payment Agent v2 A2A Microservice...")
    if payment_handler:
        await payment_handler.cleanup()
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
    """A2A Protocol: Agent Card Discovery Endpoint"""
    logger.info("📋 Agent card requested")
    return JSONResponse(content=AGENT_CARD)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "agent": f"{PAYMENT_AGENT_NAME}:{PAYMENT_AGENT_VERSION}"}


@app.post("/a2a/invoke")
async def chat_endpoint(request: ChatRequest):
    """
    A2A Protocol: Chat Invocation Endpoint
    Processes messages and returns agent responses (streaming)
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
        thread_id = request.thread_id or f"thread_{customer_id}"
        
        logger.info(f"[A2A] Processing: {user_message[:100]}...")
        
        # Process message with streaming
        async def response_generator():
            """Generate streaming response"""
            full_response = []
            
            try:
                async for chunk in payment_handler.process_message(
                    user_message=user_message,
                    thread_id=thread_id,
                    customer_id=customer_id,
                    user_email=user_email
                ):
                    full_response.append(chunk)
                    # For A2A, we collect all chunks and return as single response
                
                # Build final A2A response
                response_text = "".join(full_response)
                
                # A2A format: return messages array with assistant response
                result = {
                    "messages": request.messages + [
                        {"role": "assistant", "content": response_text}
                    ],
                    "thread_id": thread_id,
                    "success": True
                }
                
                logger.info(f"[A2A] ✅ Response completed ({len(response_text)} chars)")
                
                yield_json = __import__("json").dumps(result)
                yield yield_json
                
            except Exception as e:
                logger.error(f"[A2A] ❌ Error: {e}", exc_info=True)
                error_result = {
                    "messages": request.messages,
                    "thread_id": thread_id,
                    "success": False,
                    "error": str(e)
                }
                yield __import__("json").dumps(error_result)
        
        # For A2A, we still return JSON (not SSE)
        # Collect all chunks into single response
        chunks = []
        async for chunk in response_generator():
            chunks.append(chunk)
        
        response_json = "".join(chunks)
        return JSONResponse(content=__import__("json").loads(response_json))
        
    except Exception as e:
        logger.error(f"[A2A] ❌ Request error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=PAYMENT_AGENT_HOST,
        port=PAYMENT_AGENT_PORT,
        log_level="info"
    )
