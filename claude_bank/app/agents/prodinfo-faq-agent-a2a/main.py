"""
ProdInfoFAQ Agent A2A Microservice - FastAPI Server
Implements A2A protocol with agent card discovery and chat endpoints
UC2: Product Information & FAQ with native file_search
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agent_handler import ProdInfoFAQAgentHandler
from config import (
    A2A_SERVER_PORT,
    A2A_SERVER_HOST,
    PRODINFO_FAQ_AGENT_NAME,
    PRODINFO_FAQ_AGENT_VERSION,
    validate_config,
)

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

# Global handler instance
_handler: ProdInfoFAQAgentHandler | None = None


async def get_handler() -> ProdInfoFAQAgentHandler:
    """Get or create the global handler instance"""
    global _handler
    if _handler is None:
        _handler = ProdInfoFAQAgentHandler()
        await _handler.initialize()
    return _handler


# Pydantic models for A2A protocol
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str | None = None  # Simple message field
    messages: list[ChatMessage] | None = None  # Or full message history
    thread_id: str | None = None
    customer_id: str | None = None
    user_mail: str | None = None
    current_date_time: str | None = None
    stream: bool = True


class ChatResponse(BaseModel):
    role: str
    content: str
    agent: str


# Agent card for A2A discovery
AGENT_CARD = {
    "name": "Product Information & FAQ Agent",
    "description": (
        "Specialized banking agent for product information and frequently asked questions. "
        "Provides accurate information about BankX banking products using uploaded product "
        "documentation through Azure AI Foundry's file search. Handles product comparisons, "
        "eligibility queries, and creates support tickets when needed."
    ),
    "url": f"http://localhost:{A2A_SERVER_PORT}",
    "version": "1.0.0",
    "capabilities": ["product_information", "faq", "product_comparison", "ticket_creation"],
    "agent_id": f"{PRODINFO_FAQ_AGENT_NAME}:{PRODINFO_FAQ_AGENT_VERSION}",
    "endpoints": {
        "chat": f"http://localhost:{A2A_SERVER_PORT}/a2a/invoke",
        "health": f"http://localhost:{A2A_SERVER_PORT}/health",
    },
    "protocol": "a2a",
    "platform": "Azure AI Foundry",
    "file_search_enabled": True,
    "foundry_v2_hosted": True,
    "metadata": {
        "project": "BankX",
        "role": "product_specialist",
        "use_case": "UC2",
        "knowledge_source": "Product Documentation",
        "agent_name": PRODINFO_FAQ_AGENT_NAME,
        "agent_version": PRODINFO_FAQ_AGENT_VERSION,
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    logger.info("🚀 Starting ProdInfoFAQ Agent A2A Microservice...")
    
    # Validate configuration
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        raise
    
    # Initialize handler
    handler = await get_handler()
    logger.info("✅ ProdInfoFAQ Agent Handler initialized")
    
    logger.info(f"✅ ProdInfoFAQ Agent A2A Server ready on {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
    logger.info(f"   Agent Card: http://localhost:{A2A_SERVER_PORT}/.well-known/agent.json")
    logger.info(f"   Chat Endpoint: http://localhost:{A2A_SERVER_PORT}/a2a/invoke")
    
    yield
    
    # Cleanup on shutdown
    logger.info("🛑 Shutting down ProdInfoFAQ Agent A2A Microservice...")
    if _handler:
        await _handler.clear_cache()
    logger.info("✅ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="ProdInfoFAQ Agent A2A Server",
    description="Banking product information specialist agent exposed via A2A protocol",
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
        handler = await get_handler()
        
        # Extract user message (support both formats)
        if request.message:
            user_message = request.message
        elif request.messages:
            last_message = request.messages[-1]
            if last_message.role != "user":
                raise HTTPException(status_code=400, detail="Last message must be from user")
            user_message = last_message.content
        else:
            raise HTTPException(status_code=400, detail="No message provided")
        
        # Generate thread_id if not provided
        thread_id = request.thread_id or f"thread_{asyncio.current_task().get_name()}"
        customer_id = request.customer_id or "CUST001"
        
        # Process message with streaming
        if request.stream:
            async def stream_response():
                """Stream agent response chunks"""
                try:
                    # Convert messages to dict format for history
                    messages_history = [msg.dict() for msg in request.messages] if request.messages else []
                    print(f"[AGENT DEBUG] Streaming path: Converted {len(messages_history)} messages to dict format")
                    for i, msg in enumerate(messages_history):
                        print(f"[AGENT DEBUG]   Dict {i}: role={msg.get('role')}, content='{msg.get('content')}'")
                    
                    async for chunk in handler.process_message(
                        message=user_message,
                        thread_id=thread_id,
                        customer_id=customer_id,
                        user_mail=request.user_mail,
                        current_date_time=request.current_date_time,
                        stream=True,
                        messages_history=messages_history,
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
            # Convert messages to dict format for history
            messages_history = [msg.dict() for msg in request.messages] if request.messages else []
            print(f"[AGENT DEBUG] Non-streaming path: Converted {len(messages_history)} messages to dict format")
            for i, msg in enumerate(messages_history):
                print(f"[AGENT DEBUG]   Dict {i}: role={msg.get('role')}, content='{msg.get('content')}'")
            
            full_response = ""
            async for chunk in handler.process_message(
                message=user_message,
                thread_id=thread_id,
                customer_id=customer_id,
                user_mail=request.user_mail,
                current_date_time=request.current_date_time,
                stream=False,
                messages_history=messages_history,
            ):
                full_response += chunk
            
            return ChatResponse(
                role="assistant",
                content=full_response,
                agent="ProdInfoFAQAgent",
            )
    
    except Exception as e:
        logger.error(f"❌ Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "ProdInfoFAQAgent",
        "version": "1.0.0",
        "protocol": "a2a",
        "use_case": "UC2",
    }


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "ProdInfoFAQ Agent A2A Microservice",
        "version": "1.0.0",
        "use_case": "UC2",
        "agent_card": f"http://localhost:{A2A_SERVER_PORT}/.well-known/agent.json",
        "endpoints": {
            "agent_card": "/.well-known/agent.json",
            "chat": "/a2a/invoke",
            "health": "/health",
        },
    }


if __name__ == "__main__":
    # Run the server
    logger.info(f"Starting ProdInfoFAQ Agent A2A Server on {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
    
    uvicorn.run(
        "main:app",
        host=A2A_SERVER_HOST,
        port=A2A_SERVER_PORT,
        reload=True,
        log_level="info",
    )
