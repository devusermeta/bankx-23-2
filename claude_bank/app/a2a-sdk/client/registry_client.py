"""Client for interacting with Agent Registry."""
import logging
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)


class RegistryClient:
    """Client for agent registry service."""

    def __init__(self, registry_url: str, auth_token: Optional[str] = None, timeout: int = 10):
        """Initialize registry client.

        Args:
            registry_url: Base URL of registry service
            auth_token: Optional JWT token for authentication
            timeout: Request timeout in seconds
        """
        self.registry_url = registry_url.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    def _get_headers(self) -> dict:
        """Get request headers with auth."""
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        return headers

    async def register(
        self,
        agent_name: str,
        agent_type: str,
        capabilities: List[str],
        endpoints: dict,
        version: str = "1.0.0",
        metadata: Optional[dict] = None,
        tags: Optional[List[str]] = None,
    ) -> dict:
        """Register agent with registry.

        Args:
            agent_name: Agent name
            agent_type: Agent type (supervisor, domain, knowledge)
            capabilities: List of capabilities
            endpoints: Agent endpoints (http, health, a2a)
            version: Agent version
            metadata: Optional metadata
            tags: Optional tags

        Returns:
            Registration response with agent_id

        Raises:
            Exception: If registration fails
        """
        try:
            registration_data = {
                "agent_name": agent_name,
                "agent_type": agent_type,
                "version": version,
                "capabilities": capabilities,
                "endpoints": endpoints,
                "metadata": metadata or {},
                "tags": tags or [],
            }

            response = await self._client.post(
                f"{self.registry_url}/api/v1/agents/register",
                json=registration_data,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            logger.info(f"Registered with registry: {agent_name} (ID: {data.get('agent_id')})")
            return data

        except Exception as e:
            logger.error(f"Failed to register with registry: {e}")
            raise

    async def discover(
        self,
        capability: Optional[str] = None,
        agent_type: Optional[str] = None,
        status: str = "active",
        tags: Optional[List[str]] = None,
    ) -> List[dict]:
        """Discover agents matching criteria.

        Args:
            capability: Filter by capability
            agent_type: Filter by agent type
            status: Filter by status (default: active)
            tags: Filter by tags

        Returns:
            List of matching agents

        Raises:
            Exception: If discovery fails
        """
        try:
            params = {"status": status}
            if capability:
                params["capability"] = capability
            if agent_type:
                params["agent_type"] = agent_type
            if tags:
                params["tags"] = tags

            response = await self._client.get(
                f"{self.registry_url}/api/v1/agents/discover",
                params=params,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            data = response.json()
            agents = data.get("agents", [])

            logger.debug(
                f"Discovered {len(agents)} agents "
                f"(capability: {capability}, type: {agent_type})"
            )

            return agents

        except Exception as e:
            logger.error(f"Failed to discover agents: {e}")
            raise

    async def get_agent(self, agent_id: str) -> Optional[dict]:
        """Get agent details by ID.

        Args:
            agent_id: Agent ID

        Returns:
            Agent details or None if not found
        """
        try:
            response = await self._client.get(
                f"{self.registry_url}/api/v1/agents/{agent_id}",
                headers=self._get_headers(),
            )

            if response.status_code == 404:
                return None

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"Failed to get agent {agent_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            raise

    async def heartbeat(self, agent_id: str, status: str = "active") -> dict:
        """Send heartbeat to registry.

        Args:
            agent_id: Agent ID
            status: Current agent status

        Returns:
            Heartbeat response

        Raises:
            Exception: If heartbeat fails
        """
        try:
            request_data = {"agent_id": agent_id, "status": status}

            response = await self._client.post(
                f"{self.registry_url}/api/v1/agents/{agent_id}/heartbeat",
                json=request_data,
                headers=self._get_headers(),
            )
            response.raise_for_status()

            logger.debug(f"Heartbeat sent for agent {agent_id}")
            return response.json()

        except Exception as e:
            logger.warning(f"Failed to send heartbeat for {agent_id}: {e}")
            # Don't raise - heartbeat failures shouldn't crash the agent
            return {"status": "failed", "error": str(e)}

    async def deregister(self, agent_id: str) -> bool:
        """Deregister agent from registry.

        Args:
            agent_id: Agent ID

        Returns:
            True if successful

        Raises:
            Exception: If deregistration fails
        """
        try:
            response = await self._client.delete(
                f"{self.registry_url}/api/v1/agents/{agent_id}",
                headers=self._get_headers(),
            )
            response.raise_for_status()

            logger.info(f"Deregistered agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to deregister agent {agent_id}: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()
