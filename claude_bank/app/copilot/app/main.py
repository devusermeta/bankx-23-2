from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth_routers, chat_routers, content_routers, dashboard_routers, agent_cards_routers, mcp_routers
from app.config.settings import settings
from app.config.logging import get_logger, setup_logging
# NOTE: setup_observability not available in current agent-framework version
# from agent_framework.observability import setup_observability
import asyncio
import logging
import warnings
# Foundry based dependency injection container
from app.config.container_foundry import Container

# Suppress Azure AI Agent framework warnings about Application Insights
logging.getLogger("agent_framework_azure_ai._chat_client").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message="No Application Insights connection string found")

# Azure Chat based dependency injection container
# from app.config.container_azure_chat import Container



def create_app() -> FastAPI:
    # Initialize logging for the app
    setup_logging()
    # Get logger for this module
    logger = get_logger(__name__)

    # Setup agent framework observability only if enabled
    if settings.ENABLE_OTEL:
        # NOTE: setup_observability not available in current agent-framework version
        # setup_observability(
        #     enable_sensitive_data=settings.ENABLE_OTEL,
        #     applicationinsights_connection_string=settings.APPLICATIONINSIGHTS_CONNECTION_STRING
        # )
        logger.info("OpenTelemetry observability requested but setup_observability not available")
    else:
        logger.info("OpenTelemetry observability disabled")

    logger.info(f"Creating FastAPI application: {settings.APP_NAME}")
    
    app = FastAPI(title=settings.APP_NAME)
    
    # Add CORS middleware to allow frontend (port 8081) to call backend (port 8080)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:8081",
            "http://127.0.0.1:8081",
            "http://localhost:8080",
            "http://127.0.0.1:8080"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("✅ CORS middleware configured for frontend access")
   
    # Initialize dependency injection container
    container = Container()
    
    # ============================================================================
    # ESCALATION COMMS AGENT - Only initialize if NOT in full A2A mode
    # ============================================================================
    # In A2A mode, EscalationComms is handled by standalone A2A agent (port 9006)
    # In traditional mode, we need to initialize it here for use by other agents
    # ============================================================================
    _a2a_mode_enabled = (settings.USE_A2A_FOR_ACCOUNT_AGENT and 
                          settings.USE_A2A_FOR_TRANSACTION_AGENT and 
                          settings.USE_A2A_FOR_PAYMENT_AGENT)
    
    if not _a2a_mode_enabled:
        # TRADITIONAL MODE: Eagerly instantiate EscalationCommsAgent to create it in Azure AI Foundry
        # (other agents are instantiated via supervisor, but EscalationComms needs explicit init)
        try:
            logger.info("Initializing EscalationComms agent in Azure AI Foundry...")
            _ = container._foundry_escalation_comms_agent()
            logger.info("✅ EscalationComms agent initialized")
        except Exception as e:
            logger.warning(f"⚠️  Could not initialize EscalationComms agent: {e}")
    else:
        logger.info("🚀 A2A MODE: Skipping EscalationComms agent initialization (handled by standalone A2A agent)")
    
    # Wire dependencies to modules that need them
    container.wire(modules=[chat_routers,content_routers])
    
    # Store container in app state for potential cleanup
    app.state.container = container

    # Use FastAPI lifespan for startup and shutdown events
    from contextlib import asynccontextmanager
    from app.utils.session_memory import init_session_manager, get_session_manager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup: Initialize session memory manager
        logger.info("🚀 Starting up application...")
        
        # ============================================================================
        # AGENT PRE-WARMING - Skip in A2A mode
        # ============================================================================
        # A2A MODE: Agents run standalone, no need to pre-warm them here
        # TRADITIONAL MODE: Pre-warm agents during startup to eliminate cold start
        # ============================================================================
        _a2a_mode_enabled = (settings.USE_A2A_FOR_ACCOUNT_AGENT and 
                              settings.USE_A2A_FOR_TRANSACTION_AGENT and 
                              settings.USE_A2A_FOR_PAYMENT_AGENT)
        
        if not _a2a_mode_enabled:
            # TRADITIONAL MODE: Pre-warm in-process agents
            logger.info("⚡ Pre-warming agent cache (Traditional mode)...")
            try:
                supervisor = container.supervisor_agent()
                
                # Build supervisor agent (will be cached as Singleton)
                logger.info("Building Supervisor agent...")
                await supervisor._build_af_agent(thread_id=None, user_context=None)
                logger.info("✅ Supervisor agent cached")
                
                # Build AI Money Coach agent (slowest - 30s)
                logger.info("Building AI Money Coach agent...")
                ai_money_coach = container._foundry_ai_money_coach_agent()
                await ai_money_coach.build_af_agent(thread_id=None)
                logger.info("✅ AI Money Coach agent cached")
                
                # Build ProdInfo FAQ agent
                logger.info("Building ProdInfo FAQ agent...")
                prodinfo_faq = container._foundry_prodinfo_faq_agent()
                await prodinfo_faq.build_af_agent(thread_id=None)
                logger.info("✅ ProdInfo FAQ agent cached")
                
                logger.info("🎉 Agent cache pre-warming complete! First request will be fast.")
            except Exception as e:
                logger.warning(f"⚠️ Agent pre-warming failed (agents will build on first use): {e}")
        else:
            # A2A MODE: Skip pre-warming, agents run standalone
            logger.info("🚀 A2A MODE: Skipping agent pre-warming (agents run standalone on ports 9001-9006)")
            logger.info("   → Make sure standalone A2A agents are running before making requests")
        
        try:
            from pathlib import Path
            project_root = Path(__file__).parent.parent.parent.parent
            memory_dir = str(project_root / "memory")
            session_manager = init_session_manager(memory_dir)
            
            # Start periodic cache refresh (every 5 minutes)
            await session_manager.start_periodic_refresh(interval_minutes=5)
            logger.info("✅ Session memory manager initialized")
        except Exception as e:
            logger.error(f"❌ Error initializing session memory manager: {e}")
        
        # Startup: Initialize user cache manager and start cleanup task
        try:
            from app.cache import get_cache_manager
            from app.cache.mcp_client import (
                get_account_mcp_client,
                get_transaction_mcp_client,
                get_contacts_mcp_client,
                get_limits_mcp_client
            )
            cache_manager = get_cache_manager()
            
            # Refresh all existing caches on startup
            logger.info("🔄 Refreshing all existing caches on startup...")
            
            async def refresh_startup_caches():
                """Refresh all cache files that exist on startup"""
                try:
                    cache_files = list(cache_manager.cache_dir.glob("CUST-*.json"))
                    logger.info(f"Found {len(cache_files)} cache files to refresh")
                    
                    for cache_file in cache_files:
                        customer_id = cache_file.stem  # e.g., "CUST-002"
                        logger.info(f"Refreshing cache for {customer_id}...")
                        
                        # Read old cache to get user_email
                        try:
                            import json
                            with open(cache_file, 'r') as f:
                                old_cache = json.load(f)
                            
                            # Get user email from account details
                            user_email = old_cache.get("data", {}).get("account_details", {}).get("userName")
                            
                            if user_email:
                                mcp_clients = {
                                    "account_mcp": get_account_mcp_client(),
                                    "transaction_mcp": get_transaction_mcp_client(),
                                    "contacts_mcp": get_contacts_mcp_client(),
                                    "limits_mcp": get_limits_mcp_client()
                                }
                                
                                await cache_manager.initialize_user_cache(
                                    customer_id=customer_id,
                                    user_email=user_email,
                                    mcp_clients=mcp_clients
                                )
                                logger.info(f"✅ Refreshed cache for {customer_id}")
                            else:
                                logger.warning(f"⚠️ No email found in cache for {customer_id}, skipping")
                        
                        except Exception as e:
                            logger.error(f"❌ Failed to refresh cache for {customer_id}: {e}")
                    
                    logger.info("✅ Startup cache refresh complete")
                
                except Exception as e:
                    logger.error(f"❌ Error during startup cache refresh: {e}")
            
            # Run startup refresh in background (non-blocking)
            asyncio.create_task(refresh_startup_caches())
            
            # Start background task for cache cleanup (runs every hour)
            async def cache_cleanup_task():
                while True:
                    await asyncio.sleep(3600)  # Run every hour
                    await cache_manager.cleanup_old_caches()
            
            cleanup_task = asyncio.create_task(cache_cleanup_task())
            app.state.cache_cleanup_task = cleanup_task
            logger.info("✅ User cache manager initialized with cleanup task and startup refresh")
        except Exception as e:
            logger.error(f"❌ Error initializing user cache manager: {e}")
        
        yield
        
        # Shutdown
        logger.info("Shutting down application...")
        
        # Shutdown cache cleanup task
        try:
            if hasattr(app.state, 'cache_cleanup_task'):
                app.state.cache_cleanup_task.cancel()
                logger.info("✅ Cache cleanup task stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping cache cleanup task: {e}")
        
        # Shutdown session memory manager
        try:
            session_manager = get_session_manager()
            session_manager.stop_periodic_refresh()
            session_manager.cleanup_all_sessions()
            logger.info("✅ Session memory manager shutdown complete")
        except Exception as e:
            logger.error(f"❌ Error during session memory manager shutdown: {e}")
        
        # Shutdown conversation manager and sync to Cosmos DB
        try:
            import sys
            from pathlib import Path
            
            # Add conversations directory to path
            project_root = Path(__file__).parent.parent.parent.parent
            conversations_path = str(project_root / "conversations")
            if conversations_path not in sys.path:
                sys.path.insert(0, conversations_path)
            
            from conversation_manager import get_conversation_manager
            conversation_manager = get_conversation_manager()
            conversation_manager.shutdown()
            logger.info("✅ Conversation manager shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during conversation manager shutdown: {e}")
        
        # Unwire dependency injection
        container.unwire()
        logger.info("✅ Application shutdown complete")

    app.router.lifespan_context = lifespan

    # Include routers
    app.include_router(auth_routers.router, prefix="/api", tags=["auth"])
    app.include_router(chat_routers.router, prefix="/api", tags=["chat"])
    app.include_router(content_routers.router, prefix="/api", tags=["content"])
    app.include_router(dashboard_routers.router, tags=["dashboard"])
    app.include_router(agent_cards_routers.router, prefix="/api", tags=["agent-cards"])
    app.include_router(mcp_routers.router, prefix="/api", tags=["mcp-registry"])
    
    # Conversation history API
    from app.api import conversations as conversation_routers
    app.include_router(conversation_routers.router, tags=["conversations"])


    logger.info("FastAPI application created successfully")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        timeout_keep_alive=120
    )
