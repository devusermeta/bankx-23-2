"""Main FastAPI application for Agent Registry."""
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config.settings import settings
from .storage import RedisStore, CosmosStore
from .services import RegistryService, HealthService
from .api import agents_router

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Global service instances
redis_store: RedisStore = None
cosmos_store: CosmosStore = None
registry_service: RegistryService = None
health_service: HealthService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global redis_store, cosmos_store, registry_service, health_service

    logger.info("Starting BankX Agent Registry...")

    # Initialize Redis store
    redis_store = RedisStore(
        redis_url=settings.redis_url,
        ttl_seconds=settings.redis_ttl_seconds
    )
    await redis_store.connect()

    # Initialize Cosmos DB store (if configured)
    if settings.use_cosmos and settings.cosmos_endpoint:
        logger.info("Initializing Cosmos DB store...")
        cosmos_store = CosmosStore(
            endpoint=settings.cosmos_endpoint,
            key=settings.cosmos_key,
            database_name=settings.cosmos_database_name,
            container_name=settings.cosmos_container_name
        )
        await cosmos_store.connect()
    else:
        logger.info("Cosmos DB not configured, using Redis only")
        cosmos_store = None

    # Initialize registry service
    registry_service = RegistryService(
        redis_store=redis_store,
        cosmos_store=cosmos_store
    )
    logger.info("Registry service initialized")

    # Initialize and start health service
    if settings.health_check_enabled:
        health_service = HealthService(
            registry_service=registry_service,
            check_interval_seconds=settings.health_check_interval_seconds
        )
        health_service.start()
        logger.info("Health service started")

    logger.info(f"Agent Registry started on {settings.host}:{settings.port}")

    yield

    # Cleanup
    logger.info("Shutting down Agent Registry...")

    if health_service:
        await health_service.stop()

    if redis_store:
        await redis_store.disconnect()

    if cosmos_store:
        await cosmos_store.disconnect()

    logger.info("Agent Registry shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Agent-to-Agent Communication Registry for BankX Multi-Agent System",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agents_router.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "online",
        "auth_enabled": settings.auth_enabled,
        "health_check_enabled": settings.health_check_enabled,
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check if stores are connected
    redis_healthy = redis_store._connected if redis_store else False
    cosmos_healthy = cosmos_store._connected if cosmos_store else True  # True if not used

    if redis_healthy and cosmos_healthy:
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "redis": "connected" if redis_healthy else "disconnected",
                "cosmos": "connected" if (cosmos_store and cosmos_healthy) else "not_configured",
            }
        )
    else:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "redis": "connected" if redis_healthy else "disconnected",
                "cosmos": "connected" if (cosmos_store and cosmos_healthy) else "not_configured",
            }
        )


@app.get("/metrics")
async def metrics():
    """Metrics endpoint for monitoring."""
    if not registry_service:
        return {"error": "Registry service not initialized"}

    try:
        all_agents = await registry_service.get_all_agents()

        # Calculate metrics
        total_agents = len(all_agents)
        active_agents = len([a for a in all_agents if a.status == "active"])
        inactive_agents = len([a for a in all_agents if a.status == "inactive"])
        degraded_agents = len([a for a in all_agents if a.status == "degraded"])

        agents_by_type = {}
        for agent in all_agents:
            agents_by_type[agent.agent_type] = agents_by_type.get(agent.agent_type, 0) + 1

        return {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "inactive_agents": inactive_agents,
            "degraded_agents": degraded_agents,
            "agents_by_type": agents_by_type,
        }

    except Exception as e:
        logger.error(f"Failed to generate metrics: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to generate metrics: {str(e)}"}
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
