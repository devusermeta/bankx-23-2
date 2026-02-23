"""
Payment Agent V3 A2A Microservice - FastAPI Server
Implements A2A protocol for bank transfer operations with 2-tool flow:
  - prepareTransfer  → validate + preview (READ-ONLY)
  - executeTransfer  → execute after approval (WRITE)
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agent_handler import get_payment_agent_v3_handler, cleanup_handler
from config import (
    A2A_SERVER_PORT,
    A2A_SERVER_HOST,
    PAYMENT_AGENT_NAME,
    PAYMENT_AGENT_VERSION,
    validate_config,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("azure.core").setLevel(logging.WARNING)
logging.getLogger("azure.identity").setLevel(logging.WARNING)
logging.getLogger("mcp.client.streamable_http").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


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


# A2A Agent Card
AGENT_CARD = {
    "name": "Payment Agent V3",
    "description": (
        "BankX Payment Agent V3 - streamlined 2-tool transfer flow. "
        "Calls prepareTransfer to validate and preview, then executeTransfer "
        "only after explicit user approval. Clean, secure, no hallucination."
    ),
    "url": f"http://localhost:{A2A_SERVER_PORT}",
    "version": "3.0.0",
    "capabilities": ["bank_transfer", "transfer_validation", "transfer_execution"],
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
        "role": "payment_specialist_v3",
        "mcp_servers": ["payment-unified"],
        "tools": ["prepareTransfer", "executeTransfer"],
        "agent_name": PAYMENT_AGENT_NAME,
        "agent_version": PAYMENT_AGENT_VERSION,
    },
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown"""
    logger.info("🚀 Starting Payment Agent V3 A2A Microservice...")

    try:
        validate_config()
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        raise

    await get_payment_agent_v3_handler()
    logger.info("✅ Payment Agent V3 Handler initialized")
    logger.info(f"✅ Server ready on {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
    logger.info(f"   Agent Card: http://localhost:{A2A_SERVER_PORT}/.well-known/agent.json")
    logger.info(f"   Chat Endpoint: http://localhost:{A2A_SERVER_PORT}/a2a/invoke")

    yield

    logger.info("🛑 Shutting down Payment Agent V3 A2A Microservice...")
    await cleanup_handler()
    logger.info("✅ Cleanup complete")


app = FastAPI(
    title="Payment Agent V3 A2A Server",
    description="BankX payment transfer agent with 2-tool flow (prepareTransfer + executeTransfer)",
    version="3.0.0",
    lifespan=lifespan,
)

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


@app.post("/a2a/invoke")
async def chat_endpoint(request: ChatRequest):
    """A2A Protocol: Chat Invocation Endpoint"""
    logger.info(f"💬 Chat request: thread={request.thread_id}, customer={request.customer_id}")

    try:
        handler = await get_payment_agent_v3_handler()

        if not request.messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        last_message = request.messages[-1]
        if last_message.role != "user":
            raise HTTPException(status_code=400, detail="Last message must be from user")

        user_message = last_message.content
        thread_id = request.thread_id or f"thread_{asyncio.current_task().get_name()}"
        customer_id = request.customer_id or "default_customer"

        if request.stream:
            async def stream_response():
                try:
                    async for chunk in handler.process_message(
                        message=user_message,
                        thread_id=thread_id,
                        customer_id=customer_id,
                        stream=True,
                    ):
                        yield f"data: {chunk}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    logger.error(f"❌ Streaming error: {e}", exc_info=True)
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
            full_response = ""
            async for chunk in handler.process_message(
                message=user_message,
                thread_id=thread_id,
                customer_id=customer_id,
                stream=False,
            ):
                full_response += chunk

            return ChatResponse(
                role="assistant",
                content=full_response,
                agent="PaymentAgentV3",
            )

    except Exception as e:
        logger.error(f"❌ Error processing chat request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "PaymentAgentV3",
        "version": "3.0.0",
        "protocol": "a2a",
        "tools": ["prepareTransfer", "executeTransfer"],
    }


@app.get("/")
async def root():
    return {
        "service": "Payment Agent V3 A2A Microservice",
        "version": "3.0.0",
        "agent_card": f"http://localhost:{A2A_SERVER_PORT}/.well-known/agent.json",
        "endpoints": {
            "agent_card": "/.well-known/agent.json",
            "chat": "/a2a/invoke",
            "health": "/health",
        },
    }


if __name__ == "__main__":
    logger.info(f"Starting Payment Agent V3 A2A Server on {A2A_SERVER_HOST}:{A2A_SERVER_PORT}")
    uvicorn.run(
        "main:app",
        host=A2A_SERVER_HOST,
        port=A2A_SERVER_PORT,
        reload=True,
        log_level="info",
    )
