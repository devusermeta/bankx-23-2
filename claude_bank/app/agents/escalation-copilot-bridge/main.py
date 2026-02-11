"""
FastAPI server for Escalation Copilot Bridge - A2A compatible escalation agent.

This service receives A2A requests from other agents (like ProdInfo)
and creates support tickets using Microsoft Graph API (Excel + Outlook).
"""

import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from config import settings, validate_settings
from models import ChatRequest, ChatResponse, AgentCard, AgentEndpoints
from a2a_handler import get_a2a_handler
from excel_service import get_excel_service
from email_service import get_email_service
from graph_client import get_graph_client

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# Agent card for A2A discovery
AGENT_CARD = AgentCard(
    agent_name=settings.AGENT_NAME,
    agent_type=settings.AGENT_TYPE,
    version=settings.VERSION,
    description="Escalation agent for creating support tickets via Microsoft Graph API (Excel + Outlook)",
    capabilities=[
        "escalation.create_ticket",
        "ticket.create",
        "support.escalate"
    ],
    endpoints=AgentEndpoints(
        http=f"http://localhost:{settings.A2A_SERVER_PORT}",
        health=f"http://localhost:{settings.A2A_SERVER_PORT}/health",
        a2a=f"http://localhost:{settings.A2A_SERVER_PORT}/a2a/invoke"
    ),
    status="active"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown."""
    
    # Startup
    logger.info(f"Starting {settings.SERVICE_NAME} v{settings.VERSION}")
    logger.info(f"Port: {settings.A2A_SERVER_PORT}")
    
    # Validate configuration
    is_valid, errors = validate_settings()
    if not is_valid:
        logger.error("Configuration validation failed:")
        for error in errors:
            logger.error(f"  - {error}")
        logger.warning("Service starting with invalid configuration - some features may not work")
    else:
        logger.info("Configuration validated successfully")
    
    # Test Microsoft Graph connection
    try:
        graph_client = await get_graph_client()
        token = await graph_client.get_access_token()
        logger.info("Successfully authenticated with Microsoft Graph API")
    except Exception as e:
        logger.error(f"Failed to authenticate with Microsoft Graph: {e}")
        logger.warning("Service will start but ticket creation will fail")
    
    # Discover Excel file
    try:
        excel_service = await get_excel_service()
        file_info = await excel_service.discover_excel_file()
        logger.info(f"Excel file discovery results: {file_info}")
    except Exception as e:
        logger.warning(f"Could not discover Excel file: {e}")
    
    # Register with agent registry (if configured)
    if settings.REGISTER_WITH_REGISTRY:
        try:
            # TODO: Implement registry registration
            logger.info("Agent registry registration skipped (implement if needed)")
        except Exception as e:
            logger.warning(f"Failed to register with agent registry: {e}")
    
    logger.info(f"{settings.SERVICE_NAME} started successfully")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.SERVICE_NAME}")


# Create FastAPI app
app = FastAPI(
    title=settings.SERVICE_NAME,
    version=settings.VERSION,
    description="A2A-compatible escalation agent using Microsoft Graph API",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.SERVICE_NAME,
        "version": settings.VERSION,
        "status": "running",
        "agent": settings.AGENT_NAME
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test Microsoft Graph connection
        graph_client = await get_graph_client()
        await graph_client.get_access_token()
        
        return {
            "status": "healthy",
            "service": settings.SERVICE_NAME,
            "version": settings.VERSION,
            "graph_api": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": settings.SERVICE_NAME,
                "error": str(e)
            }
        )


@app.get("/.well-known/agent.json")
async def get_agent_card():
    """
    Agent card endpoint for A2A discovery.
    This allows other agents to discover this agent's capabilities.
    """
    return AGENT_CARD.model_dump()


@app.post("/a2a/invoke", response_model=ChatResponse)
async def a2a_invoke(request: ChatRequest):
    """
    Main A2A endpoint for processing escalation requests.
    
    This endpoint receives requests from other agents (like ProdInfo)
    and creates support tickets.
    
    Expected message format:
    {
        "messages": [
            {"role": "user", "content": "Create ticket: Issue description. Email: user@example.com, Name: John Doe"}
        ],
        "customer_id": "CUST-001",
        "thread_id": "thread-123"
    }
    """
    try:
        logger.info(f"Received A2A request for customer: {request.customer_id}")
        logger.debug(f"Messages: {request.messages}")
        
        # Process request
        handler = await get_a2a_handler()
        response = await handler.process_request(request)
        
        logger.info(f"A2A request processed successfully")
        return response
    
    except Exception as e:
        logger.error(f"Error processing A2A request: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process escalation request: {str(e)}"
        )


@app.post("/test/email")
async def test_email(email_address: str):
    """
    Test endpoint to send a test email.
    
    Usage: POST /test/email?email_address=your@email.com
    """
    try:
        email_service = await get_email_service()
        success = await email_service.send_test_email(email_address)
        
        if success:
            return {"success": True, "message": f"Test email sent to {email_address}"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send test email")
    
    except Exception as e:
        logger.error(f"Test email failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/test/excel")
async def test_excel():
    """
    Test endpoint to check Excel file access.
    
    Usage: GET /test/excel
    """
    try:
        excel_service = await get_excel_service()
        
        # Discover file
        file_info = await excel_service.discover_excel_file()
        
        # Get columns
        try:
            columns = await excel_service.get_table_columns()
            file_info["columns"] = columns
        except Exception as e:
            file_info["columns_error"] = str(e)
        
        return file_info
    
    except Exception as e:
        logger.error(f"Excel test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config/status")
async def config_status():
    """
    Check configuration status.
    
    Returns configuration validation results.
    """
    is_valid, errors = validate_settings()
    
    return {
        "valid": is_valid,
        "errors": errors if not is_valid else [],
        "settings": {
            "service_name": settings.SERVICE_NAME,
            "version": settings.VERSION,
            "port": settings.A2A_SERVER_PORT,
            "agent_name": settings.AGENT_NAME,
            "excel_configured": bool(settings.EXCEL_DRIVE_ID or settings.EXCEL_SITE_ID or settings.EXCEL_USER_ID),
            "email_configured": bool(settings.EMAIL_SENDER_ADDRESS),
            "graph_api_configured": bool(settings.AZURE_CLIENT_ID and settings.AZURE_CLIENT_SECRET and settings.AZURE_TENANT_ID)
        }
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.A2A_SERVER_PORT,
        log_level=settings.LOG_LEVEL.lower(),
        reload=False
    )
