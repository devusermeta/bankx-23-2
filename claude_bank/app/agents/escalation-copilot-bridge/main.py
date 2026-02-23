"""
FastAPI server for Escalation Copilot Bridge - A2A compatible escalation agent.

This service receives A2A requests from other agents (like ProdInfo)
and creates support tickets via Power Automate → Copilot Studio (handles Excel + Outlook).
"""

import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config import settings, validate_settings
from models import ChatRequest, ChatResponse, AgentCard, AgentEndpoints
from a2a_handler import get_a2a_handler
from power_automate_client import get_power_automate_client

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
    description="Escalation agent bridge - calls Copilot Studio via Power Automate (Outlook + Excel)",
    capabilities=[
        "escalation.create_ticket",
        "ticket.create",
        "support.escalate",
        "power_automate_integration",
        "copilot_studio_integration"
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
    
    # Test Power Automate connection
    try:
        pa_client = await get_power_automate_client()
        logger.info(f"Power Automate client initialized")
        logger.info(f"Bot Name: {settings.COPILOT_BOT_NAME}")
        logger.info(f"Flow URL: {settings.POWER_AUTOMATE_FLOW_URL[:50]}...")
        
        # Try to test connection (non-blocking)
        try:
            test_result = await pa_client.test_connection(raise_on_error=False)
            
            if test_result.get("success"):
                logger.info(test_result["message"])
                response_time = test_result.get("diagnostics", {}).get("response_time_ms", 0)
                if response_time > 0:
                    logger.info(f"   Response time: {response_time:.1f}ms")
            else:
                # Log detailed diagnostics for failures
                logger.warning(test_result["message"])
                logger.warning(f"   Error: {test_result.get('error', 'Unknown')}")
                
                # Log diagnostic information
                diagnostics = test_result.get("diagnostics", {})
                if "likely_causes" in diagnostics:
                    logger.warning("   Likely causes:")
                    for cause in diagnostics["likely_causes"][:3]:  # Show top 3 causes
                        logger.warning(f"     • {cause}")
                        
                if "recommended_actions" in diagnostics:
                    logger.warning("   Recommended actions:")
                    for action in diagnostics["recommended_actions"][:2]:  # Show top 2 actions
                        logger.warning(f"     • {action}")
                        
                logger.warning("   ℹ️  Service will start anyway - fix Power Automate and retry")
                logger.warning("   📋 Use /test/power-automate endpoint to test connection later")
                
        except Exception as e:
            logger.warning(f"Could not test Power Automate connection: {e}")
            logger.warning("Service will start but ticket creation may fail")
    except Exception as e:
        logger.error(f"Failed to initialize Power Automate client: {e}")
        logger.warning("Service will start but ticket creation will fail")
    
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

# Add CORS middleware to handle OPTIONS preflight requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods including OPTIONS
    allow_headers=["*"],  # Allow all headers
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
        # Test Power Automate connection
        pa_client = await get_power_automate_client()
        
        return {
            "status": "healthy",
            "service": settings.SERVICE_NAME,
            "version": settings.VERSION,
            "power_automate": "configured",
            "copilot_studio": "via_power_automate",
            "bot_name": settings.COPILOT_BOT_NAME
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


@app.post("/test/power-automate")
async def test_power_automate():
    """
    Enhanced test endpoint to verify Power Automate connection with full diagnostics.
    
    Usage: POST /test/power-automate
    Returns detailed diagnostic information about connection status.
    """
    try:
        pa_client = await get_power_automate_client()
        result = await pa_client.test_connection(raise_on_error=False)
        
        # Add timestamp and additional context
        result["timestamp"] = datetime.now().isoformat()
        result["test_type"] = "manual_api_test"
        
        # Return with appropriate HTTP status
        if result.get("success"):
            return result
        else:
            # Return diagnostics even for failures (don't raise HTTP error)
            return result
    
    except Exception as e:
        logger.error(f"Power Automate test failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "❌ Test endpoint failed", 
            "timestamp": datetime.now().isoformat(),
            "test_type": "manual_api_test"
        }


@app.post("/test/escalation")
async def test_escalation():
    """
    Test endpoint to create a dummy escalation ticket via Power Automate → Copilot Studio.
    
    Usage: POST /test/escalation
    """
    try:
        pa_client = await get_power_automate_client()
        
        # Create test ticket
        result = await pa_client.create_escalation_ticket(
            customer_id="TEST-CUST-001",
            customer_email="test@example.com",
            customer_name="Test Customer",
            description="This is a test escalation from the A2A bridge via Power Automate",
            priority="Medium"
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Escalation test failed: {e}")
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
            "power_automate_configured": bool(settings.POWER_AUTOMATE_FLOW_URL),
            "copilot_bot_name": settings.COPILOT_BOT_NAME,
            "flow_url_configured": bool(settings.POWER_AUTOMATE_FLOW_URL),
            "azure_tenant_id": settings.AZURE_TENANT_ID[:8] + "..." if settings.AZURE_TENANT_ID else "not set"
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
