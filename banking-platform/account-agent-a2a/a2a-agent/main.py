"""
Account A2A Agent Server
Exposes the agent via A2A protocol with agent card discovery
"""

import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import get_settings
from agent_handler import get_agent_handler

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Suppress verbose Azure SDK logs
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.ERROR)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("azure.ai.projects").setLevel(logging.WARNING)
logging.getLogger("azure").setLevel(logging.WARNING)

logger = logging.getLogger("account-agent-a2a")


# Pydantic models for request/response
class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    thread_id: Optional[str] = None
    customer_id: Optional[str] = None
    stream: bool = False


# Agent Card for A2A Discovery
AGENT_CARD = {
    "name": "Account Agent",
    "description": "Banking account agent providing account information and transaction limits",
    "url": f"http://localhost:{settings.a2a_server_port}",
    "version": "1.0.0",
    "capabilities": [
        "account_balance",
        "account_details",
        "transaction_limits",
        "limit_validation",
        "payment_method_info"
    ],
    "agent_id": f"{settings.account_agent_name}:{settings.account_agent_version}",
    "endpoints": {
        "chat": f"http://localhost:{settings.a2a_server_port}/a2a/invoke",
        "health": f"http://localhost:{settings.a2a_server_port}/health",
    },
    "protocol": "a2a",
    "platform": "Azure AI Foundry",
    "mcp_backed": True,
    "foundry_hosted": True,
    "metadata": {
        "project": "BankX",
        "category": "banking",
        "mcp_servers": ["account"],
        "agent_name": settings.account_agent_name,
        "agent_version": settings.account_agent_version,
        "tools": [
            "getAccountsByUserName",
            "getAccountDetails",
            "getPaymentMethodDetails",
            "checkLimits",
            "getAccountLimits"
        ]
    }
}


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("=" * 80)
    logger.info("🚀 Starting Account A2A Agent Server")
    logger.info("=" * 80)
    
    # Initialize agent handler on startup
    handler = await get_agent_handler()
    logger.info("✅ Agent handler initialized")
    
    yield
    
    # Cleanup on shutdown
    logger.info("🛑 Shutting down Account A2A Agent Server")
    await handler.cleanup()
    logger.info("✅ Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Account A2A Agent",
    description="A2A-compatible Account Agent using Azure AI Foundry and MCP",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Account A2A Agent",
        "version": "1.0.0",
        "protocol": "a2a",
        "agent": f"{settings.account_agent_name}:{settings.account_agent_version}",
        "endpoints": {
            "agent_card": "/.well-known/agent.json",
            "chat": "/a2a/invoke",
            "health": "/health"
        }
    }


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """
    Agent Card endpoint for A2A discovery
    Standard endpoint where A2A clients discover agent capabilities
    """
    logger.info("[A2A] Agent card requested")
    return JSONResponse(content=AGENT_CARD)


@app.post("/a2a/invoke")
async def invoke_agent(request: ChatRequest):
    """
    Main A2A invocation endpoint
    Processes user messages and returns agent responses
    """
    try:
        logger.info(f"[A2A] Invoke request - Thread: {request.thread_id}, Stream: {request.stream}")
        logger.info(f"[A2A] Message count: {len(request.messages)}")
        
        # Get agent handler
        handler = await get_agent_handler()
        
        # Process message
        response = await handler.process_message(
            messages=request.messages,
            thread_id=request.thread_id,
            customer_id=request.customer_id,
            stream=request.stream
        )
        
        logger.info(f"[A2A] Response generated successfully")
        
        return {
            "messages": [response],
            "thread_id": response.get("thread_id"),
            "agent_name": response.get("agent_name")
        }
        
    except Exception as e:
        logger.error(f"[A2A] Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        handler = await get_agent_handler()
        is_healthy = handler._initialized
        
        return {
            "status": "healthy" if is_healthy else "initializing",
            "agent": f"{settings.account_agent_name}:{settings.account_agent_version}",
            "mcp_server": settings.account_mcp_server_url,
            "initialized": is_healthy
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 80)
    print("🚀 Starting Account A2A Agent Server")
    print("=" * 80)
    print(f"Host: {settings.a2a_server_host}")
    print(f"Port: {settings.a2a_server_port}")
    print(f"Agent: {settings.account_agent_name}:{settings.account_agent_version}")
    print(f"MCP Server: {settings.account_mcp_server_url}")
    print("=" * 80 + "\n")
    
    uvicorn.run(
        app,
        host=settings.a2a_server_host,
        port=settings.a2a_server_port,
        log_level=settings.log_level.lower()
    )
