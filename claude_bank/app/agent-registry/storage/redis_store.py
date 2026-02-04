"""Redis storage for agent registry."""
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None

from ..models import AgentRegistration

logger = logging.getLogger(__name__)


class RedisStore:
    """Redis-based storage for fast agent lookups."""

    def __init__(self, redis_url: str = "redis://localhost:6379", ttl_seconds: int = 300):
        """Initialize Redis store.

        Args:
            redis_url: Redis connection URL
            ttl_seconds: Time-to-live for entries (default: 5 minutes)
        """
        if not REDIS_AVAILABLE:
            logger.warning("Redis not available, using in-memory store")
            self.client = None
            self._memory_store: Dict[str, Dict] = {}
        else:
            self.redis_url = redis_url
            self.client = None  # Will be initialized in connect()

        self.ttl_seconds = ttl_seconds
        self._connected = False

    async def connect(self):
        """Connect to Redis."""
        if not REDIS_AVAILABLE:
            logger.info("Using in-memory store (Redis not available)")
            self._connected = True
            return

        try:
            self.client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            # Test connection
            await self.client.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Falling back to in-memory store")
            self.client = None
            self._memory_store = {}
            self._connected = True

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.client:
            await self.client.close()
            self._connected = False
            logger.info("Disconnected from Redis")

    async def set_agent(self, agent: AgentRegistration) -> bool:
        """Store agent registration.

        Args:
            agent: Agent registration to store

        Returns:
            True if successful
        """
        try:
            agent_data = agent.model_dump(mode='json')
            # Convert datetime objects to ISO strings
            agent_data['registered_at'] = agent_data['registered_at'].isoformat() if isinstance(agent_data['registered_at'], datetime) else agent_data['registered_at']
            agent_data['last_heartbeat'] = agent_data['last_heartbeat'].isoformat() if isinstance(agent_data['last_heartbeat'], datetime) else agent_data['last_heartbeat']

            if self.client:
                # Store in Redis
                await self.client.setex(
                    f"agent:{agent.agent_id}",
                    self.ttl_seconds,
                    json.dumps(agent_data)
                )
                # Add to index by type
                await self.client.sadd(f"agents:type:{agent.agent_type}", agent.agent_id)
                # Add to index by status
                await self.client.sadd(f"agents:status:{agent.status}", agent.agent_id)
                # Index capabilities
                for capability in agent.capabilities:
                    await self.client.sadd(f"agents:capability:{capability}", agent.agent_id)
            else:
                # Use in-memory store
                self._memory_store[f"agent:{agent.agent_id}"] = agent_data

            return True
        except Exception as e:
            logger.error(f"Failed to store agent {agent.agent_id}: {e}")
            return False

    async def get_agent(self, agent_id: str) -> Optional[AgentRegistration]:
        """Retrieve agent by ID.

        Args:
            agent_id: Agent ID to retrieve

        Returns:
            AgentRegistration if found, None otherwise
        """
        try:
            if self.client:
                data = await self.client.get(f"agent:{agent_id}")
                if data:
                    agent_dict = json.loads(data)
                    return AgentRegistration(**agent_dict)
            else:
                data = self._memory_store.get(f"agent:{agent_id}")
                if data:
                    return AgentRegistration(**data)
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve agent {agent_id}: {e}")
            return None

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete agent from registry.

        Args:
            agent_id: Agent ID to delete

        Returns:
            True if successful
        """
        try:
            if self.client:
                # Get agent first to remove from indexes
                agent = await self.get_agent(agent_id)
                if agent:
                    # Remove from indexes
                    await self.client.srem(f"agents:type:{agent.agent_type}", agent_id)
                    await self.client.srem(f"agents:status:{agent.status}", agent_id)
                    for capability in agent.capabilities:
                        await self.client.srem(f"agents:capability:{capability}", agent_id)

                # Delete main entry
                await self.client.delete(f"agent:{agent_id}")
            else:
                self._memory_store.pop(f"agent:{agent_id}", None)

            return True
        except Exception as e:
            logger.error(f"Failed to delete agent {agent_id}: {e}")
            return False

    async def find_agents(
        self,
        capability: Optional[str] = None,
        agent_type: Optional[str] = None,
        status: str = "active"
    ) -> List[AgentRegistration]:
        """Find agents matching criteria.

        Args:
            capability: Filter by capability
            agent_type: Filter by agent type
            status: Filter by status (default: active)

        Returns:
            List of matching agents
        """
        try:
            agent_ids = set()

            if self.client:
                # Build query using set operations
                if capability:
                    capability_ids = await self.client.smembers(f"agents:capability:{capability}")
                    agent_ids = set(capability_ids)

                if agent_type:
                    type_ids = await self.client.smembers(f"agents:type:{agent_type}")
                    if agent_ids:
                        agent_ids = agent_ids.intersection(type_ids)
                    else:
                        agent_ids = set(type_ids)

                if status:
                    status_ids = await self.client.smembers(f"agents:status:{status}")
                    if agent_ids:
                        agent_ids = agent_ids.intersection(status_ids)
                    else:
                        agent_ids = set(status_ids)

                # If no filters, get all active agents
                if not agent_ids and not capability and not agent_type:
                    agent_ids = await self.client.smembers(f"agents:status:{status}")
            else:
                # In-memory search
                all_agents = []
                for key, data in self._memory_store.items():
                    if key.startswith("agent:"):
                        agent = AgentRegistration(**data)
                        if status and agent.status != status:
                            continue
                        if agent_type and agent.agent_type != agent_type:
                            continue
                        if capability and capability not in agent.capabilities:
                            continue
                        all_agents.append(agent)
                return all_agents

            # Retrieve full agent data
            agents = []
            for agent_id in agent_ids:
                agent = await self.get_agent(agent_id)
                if agent:
                    agents.append(agent)

            return agents

        except Exception as e:
            logger.error(f"Failed to find agents: {e}")
            return []

    async def update_heartbeat(self, agent_id: str) -> bool:
        """Update agent heartbeat timestamp.

        Args:
            agent_id: Agent ID

        Returns:
            True if successful
        """
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                return False

            agent.last_heartbeat = datetime.utcnow()
            return await self.set_agent(agent)

        except Exception as e:
            logger.error(f"Failed to update heartbeat for {agent_id}: {e}")
            return False
