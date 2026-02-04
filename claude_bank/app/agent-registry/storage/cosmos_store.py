"""Cosmos DB storage for agent registry persistence."""
import logging
from typing import Dict, List, Optional
from datetime import datetime

try:
    from azure.cosmos.aio import CosmosClient
    from azure.cosmos import PartitionKey
    COSMOS_AVAILABLE = True
except ImportError:
    COSMOS_AVAILABLE = False
    CosmosClient = None

from ..models import AgentRegistration

logger = logging.getLogger(__name__)


class CosmosStore:
    """Cosmos DB storage for persistent agent registry."""

    def __init__(
        self,
        endpoint: str,
        key: str,
        database_name: str = "bankx_db",
        container_name: str = "agent_registry"
    ):
        """Initialize Cosmos DB store.

        Args:
            endpoint: Cosmos DB endpoint URL
            key: Cosmos DB access key
            database_name: Database name (default: bankx_db)
            container_name: Container name (default: agent_registry)
        """
        if not COSMOS_AVAILABLE:
            logger.warning("Cosmos DB SDK not available, using in-memory store")
            self.client = None
            self._memory_store: Dict[str, Dict] = {}
        else:
            self.endpoint = endpoint
            self.key = key
            self.database_name = database_name
            self.container_name = container_name
            self.client = None
            self.database = None
            self.container = None

        self._connected = False

    async def connect(self):
        """Connect to Cosmos DB and ensure database/container exist."""
        if not COSMOS_AVAILABLE:
            logger.info("Using in-memory store (Cosmos DB SDK not available)")
            self._connected = True
            return

        try:
            self.client = CosmosClient(self.endpoint, self.key)

            # Create database if not exists
            self.database = await self.client.create_database_if_not_exists(self.database_name)

            # Create container if not exists
            self.container = await self.database.create_container_if_not_exists(
                id=self.container_name,
                partition_key=PartitionKey(path="/agent_id")
            )

            self._connected = True
            logger.info(f"Connected to Cosmos DB: {self.database_name}/{self.container_name}")

        except Exception as e:
            logger.error(f"Failed to connect to Cosmos DB: {e}")
            logger.warning("Falling back to in-memory store")
            self.client = None
            self._memory_store = {}
            self._connected = True

    async def disconnect(self):
        """Disconnect from Cosmos DB."""
        if self.client:
            await self.client.close()
            self._connected = False
            logger.info("Disconnected from Cosmos DB")

    async def create_agent(self, agent: AgentRegistration) -> bool:
        """Create agent record in Cosmos DB.

        Args:
            agent: Agent registration to store

        Returns:
            True if successful
        """
        try:
            agent_dict = agent.model_dump(mode='json')
            # Cosmos DB requires 'id' field
            agent_dict['id'] = agent.agent_id

            # Convert datetime to ISO strings
            agent_dict['registered_at'] = agent_dict['registered_at'].isoformat() if isinstance(agent_dict['registered_at'], datetime) else agent_dict['registered_at']
            agent_dict['last_heartbeat'] = agent_dict['last_heartbeat'].isoformat() if isinstance(agent_dict['last_heartbeat'], datetime) else agent_dict['last_heartbeat']

            if self.container:
                await self.container.create_item(body=agent_dict)
            else:
                self._memory_store[agent.agent_id] = agent_dict

            logger.info(f"Created agent record: {agent.agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to create agent {agent.agent_id}: {e}")
            return False

    async def get_agent(self, agent_id: str) -> Optional[AgentRegistration]:
        """Retrieve agent by ID.

        Args:
            agent_id: Agent ID to retrieve

        Returns:
            AgentRegistration if found, None otherwise
        """
        try:
            if self.container:
                item = await self.container.read_item(
                    item=agent_id,
                    partition_key=agent_id
                )
                # Remove Cosmos DB metadata
                item.pop('_rid', None)
                item.pop('_self', None)
                item.pop('_etag', None)
                item.pop('_attachments', None)
                item.pop('_ts', None)
                return AgentRegistration(**item)
            else:
                item = self._memory_store.get(agent_id)
                if item:
                    return AgentRegistration(**item)
            return None

        except Exception as e:
            if "Resource Not Found" not in str(e):
                logger.error(f"Failed to retrieve agent {agent_id}: {e}")
            return None

    async def update_agent(self, agent: AgentRegistration) -> bool:
        """Update agent record.

        Args:
            agent: Updated agent registration

        Returns:
            True if successful
        """
        try:
            agent_dict = agent.model_dump(mode='json')
            agent_dict['id'] = agent.agent_id

            # Convert datetime to ISO strings
            agent_dict['registered_at'] = agent_dict['registered_at'].isoformat() if isinstance(agent_dict['registered_at'], datetime) else agent_dict['registered_at']
            agent_dict['last_heartbeat'] = agent_dict['last_heartbeat'].isoformat() if isinstance(agent_dict['last_heartbeat'], datetime) else agent_dict['last_heartbeat']

            if self.container:
                await self.container.upsert_item(body=agent_dict)
            else:
                self._memory_store[agent.agent_id] = agent_dict

            return True

        except Exception as e:
            logger.error(f"Failed to update agent {agent.agent_id}: {e}")
            return False

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete agent record.

        Args:
            agent_id: Agent ID to delete

        Returns:
            True if successful
        """
        try:
            if self.container:
                await self.container.delete_item(
                    item=agent_id,
                    partition_key=agent_id
                )
            else:
                self._memory_store.pop(agent_id, None)

            logger.info(f"Deleted agent record: {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete agent {agent_id}: {e}")
            return False

    async def query_agents(
        self,
        capability: Optional[str] = None,
        agent_type: Optional[str] = None,
        status: str = "active"
    ) -> List[AgentRegistration]:
        """Query agents with filters.

        Args:
            capability: Filter by capability
            agent_type: Filter by agent type
            status: Filter by status

        Returns:
            List of matching agents
        """
        try:
            if self.container:
                # Build SQL query
                query = "SELECT * FROM c WHERE c.status = @status"
                parameters = [{"name": "@status", "value": status}]

                if agent_type:
                    query += " AND c.agent_type = @agent_type"
                    parameters.append({"name": "@agent_type", "value": agent_type})

                if capability:
                    query += " AND ARRAY_CONTAINS(c.capabilities, @capability)"
                    parameters.append({"name": "@capability", "value": capability})

                items = self.container.query_items(
                    query=query,
                    parameters=parameters,
                    enable_cross_partition_query=True
                )

                agents = []
                async for item in items:
                    # Remove Cosmos DB metadata
                    item.pop('_rid', None)
                    item.pop('_self', None)
                    item.pop('_etag', None)
                    item.pop('_attachments', None)
                    item.pop('_ts', None)
                    agents.append(AgentRegistration(**item))

                return agents
            else:
                # In-memory query
                agents = []
                for agent_dict in self._memory_store.values():
                    agent = AgentRegistration(**agent_dict)
                    if status and agent.status != status:
                        continue
                    if agent_type and agent.agent_type != agent_type:
                        continue
                    if capability and capability not in agent.capabilities:
                        continue
                    agents.append(agent)
                return agents

        except Exception as e:
            logger.error(f"Failed to query agents: {e}")
            return []

    async def get_all_agents(self) -> List[AgentRegistration]:
        """Get all agents.

        Returns:
            List of all agents
        """
        try:
            if self.container:
                items = self.container.query_items(
                    query="SELECT * FROM c",
                    enable_cross_partition_query=True
                )

                agents = []
                async for item in items:
                    # Remove Cosmos DB metadata
                    item.pop('_rid', None)
                    item.pop('_self', None)
                    item.pop('_etag', None)
                    item.pop('_attachments', None)
                    item.pop('_ts', None)
                    agents.append(AgentRegistration(**item))

                return agents
            else:
                return [AgentRegistration(**data) for data in self._memory_store.values()]

        except Exception as e:
            logger.error(f"Failed to get all agents: {e}")
            return []
