"""Registry service for managing agent lifecycle."""
import logging
from datetime import datetime
from typing import List, Optional

from ..models import (
    AgentRegistration,
    AgentRegistrationRequest,
    AgentDiscoveryRequest,
)
from ..storage import RedisStore, CosmosStore

logger = logging.getLogger(__name__)


class RegistryService:
    """Service for managing agent registry."""

    def __init__(self, redis_store: RedisStore, cosmos_store: Optional[CosmosStore] = None):
        """Initialize registry service.

        Args:
            redis_store: Redis store for fast lookups
            cosmos_store: Cosmos DB store for persistence (optional)
        """
        self.redis_store = redis_store
        self.cosmos_store = cosmos_store

    async def register_agent(self, request: AgentRegistrationRequest) -> AgentRegistration:
        """Register a new agent.

        Args:
            request: Agent registration request

        Returns:
            Registered agent with generated ID

        Raises:
            Exception: If registration fails
        """
        try:
            # Create agent registration
            agent = AgentRegistration(
                agent_name=request.agent_name,
                agent_type=request.agent_type,
                version=request.version,
                capabilities=request.capabilities,
                capabilities_detailed=request.capabilities_detailed,
                endpoints=request.endpoints,
                health_check_url=request.endpoints.health,
                metadata=request.metadata or {},
                tags=request.tags,
                status="active",
                registered_at=datetime.utcnow(),
                last_heartbeat=datetime.utcnow(),
            )

            # Store in Redis (fast lookups)
            redis_success = await self.redis_store.set_agent(agent)
            if not redis_success:
                logger.warning(f"Failed to store agent in Redis: {agent.agent_id}")

            # Store in Cosmos DB (persistence)
            if self.cosmos_store:
                cosmos_success = await self.cosmos_store.create_agent(agent)
                if not cosmos_success:
                    logger.warning(f"Failed to store agent in Cosmos DB: {agent.agent_id}")

            logger.info(
                f"Registered agent: {agent.agent_name} "
                f"(ID: {agent.agent_id}, Type: {agent.agent_type})"
            )

            return agent

        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            raise

    async def get_agent(self, agent_id: str) -> Optional[AgentRegistration]:
        """Get agent by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent registration if found, None otherwise
        """
        try:
            # Try Redis first (fast)
            agent = await self.redis_store.get_agent(agent_id)

            # Fallback to Cosmos DB if not in Redis
            if not agent and self.cosmos_store:
                agent = await self.cosmos_store.get_agent(agent_id)
                # Repopulate Redis cache
                if agent:
                    await self.redis_store.set_agent(agent)

            return agent

        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            return None

    async def discover_agents(self, request: AgentDiscoveryRequest) -> List[AgentRegistration]:
        """Discover agents matching criteria.

        Args:
            request: Discovery request with filters

        Returns:
            List of matching agents
        """
        try:
            # Try Redis first (fast)
            agents = await self.redis_store.find_agents(
                capability=request.capability,
                agent_type=request.agent_type,
                status=request.status,
            )

            # If Redis returns nothing, try Cosmos DB
            if not agents and self.cosmos_store:
                agents = await self.cosmos_store.query_agents(
                    capability=request.capability,
                    agent_type=request.agent_type,
                    status=request.status,
                )
                # Repopulate Redis cache
                for agent in agents:
                    await self.redis_store.set_agent(agent)

            # Filter by tags if specified
            if request.tags:
                agents = [
                    agent
                    for agent in agents
                    if any(tag in agent.tags for tag in request.tags)
                ]

            logger.info(
                f"Discovered {len(agents)} agents "
                f"(capability: {request.capability}, type: {request.agent_type})"
            )

            return agents

        except Exception as e:
            logger.error(f"Failed to discover agents: {e}")
            return []

    async def update_heartbeat(self, agent_id: str, status: str = "active") -> bool:
        """Update agent heartbeat.

        Args:
            agent_id: Agent ID
            status: Optional status update

        Returns:
            True if successful
        """
        try:
            # Get agent
            agent = await self.get_agent(agent_id)
            if not agent:
                logger.warning(f"Agent not found for heartbeat: {agent_id}")
                return False

            # Update heartbeat
            agent.last_heartbeat = datetime.utcnow()
            if status:
                agent.status = status

            # Update in both stores
            redis_success = await self.redis_store.set_agent(agent)
            if self.cosmos_store:
                cosmos_success = await self.cosmos_store.update_agent(agent)

            logger.debug(f"Updated heartbeat for agent: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to update heartbeat for {agent_id}: {e}")
            return False

    async def deregister_agent(self, agent_id: str) -> bool:
        """Deregister an agent.

        Args:
            agent_id: Agent ID to deregister

        Returns:
            True if successful
        """
        try:
            # Delete from Redis
            await self.redis_store.delete_agent(agent_id)

            # Delete from Cosmos DB
            if self.cosmos_store:
                await self.cosmos_store.delete_agent(agent_id)

            logger.info(f"Deregistered agent: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to deregister agent {agent_id}: {e}")
            return False

    async def get_all_agents(self) -> List[AgentRegistration]:
        """Get all registered agents.

        Returns:
            List of all agents
        """
        try:
            if self.cosmos_store:
                agents = await self.cosmos_store.get_all_agents()
            else:
                agents = await self.redis_store.find_agents()

            return agents

        except Exception as e:
            logger.error(f"Failed to get all agents: {e}")
            return []

    async def update_agent_status(self, agent_id: str, status: str) -> bool:
        """Update agent status.

        Args:
            agent_id: Agent ID
            status: New status (active, inactive, maintenance, degraded)

        Returns:
            True if successful
        """
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                logger.warning(f"Agent not found: {agent_id}")
                return False

            agent.status = status

            # Update in both stores
            await self.redis_store.set_agent(agent)
            if self.cosmos_store:
                await self.cosmos_store.update_agent(agent)

            logger.info(f"Updated agent {agent_id} status to: {status}")
            return True

        except Exception as e:
            logger.error(f"Failed to update agent status: {e}")
            return False
