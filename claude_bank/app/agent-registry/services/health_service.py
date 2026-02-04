"""Health monitoring service for registered agents."""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List

import httpx

from ..models import AgentRegistration
from .registry_service import RegistryService

logger = logging.getLogger(__name__)


class HealthService:
    """Service for monitoring agent health."""

    def __init__(self, registry_service: RegistryService, check_interval_seconds: int = 30):
        """Initialize health service.

        Args:
            registry_service: Registry service instance
            check_interval_seconds: How often to check health (default: 30s)
        """
        self.registry_service = registry_service
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._task = None

    async def check_agent_health(self, agent: AgentRegistration) -> bool:
        """Check if agent is healthy.

        Args:
            agent: Agent to check

        Returns:
            True if healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(agent.health_check_url)
                return response.status_code == 200

        except Exception as e:
            logger.warning(f"Health check failed for {agent.agent_name}: {e}")
            return False

    async def check_all_agents(self) -> Dict[str, bool]:
        """Check health of all registered agents.

        Returns:
            Dictionary mapping agent_id to health status
        """
        agents = await self.registry_service.get_all_agents()
        results = {}

        # Check all agents in parallel
        tasks = [self.check_agent_health(agent) for agent in agents]
        health_statuses = await asyncio.gather(*tasks, return_exceptions=True)

        for agent, health in zip(agents, health_statuses):
            if isinstance(health, Exception):
                results[agent.agent_id] = False
                logger.error(f"Health check exception for {agent.agent_name}: {health}")
            else:
                results[agent.agent_id] = health

                # Update agent status based on health
                if not health:
                    await self.registry_service.update_agent_status(
                        agent.agent_id, "degraded"
                    )
                elif agent.status == "degraded":
                    # Restore to active if recovered
                    await self.registry_service.update_agent_status(agent.agent_id, "active")

        return results

    async def remove_stale_agents(self, stale_threshold_minutes: int = 5):
        """Remove agents that haven't sent heartbeat recently.

        Args:
            stale_threshold_minutes: Minutes before considering agent stale
        """
        agents = await self.registry_service.get_all_agents()
        threshold = datetime.utcnow() - timedelta(minutes=stale_threshold_minutes)

        for agent in agents:
            if agent.last_heartbeat < threshold:
                logger.warning(
                    f"Removing stale agent {agent.agent_name} "
                    f"(last heartbeat: {agent.last_heartbeat})"
                )
                await self.registry_service.deregister_agent(agent.agent_id)

    async def _health_check_loop(self):
        """Background loop for periodic health checks."""
        logger.info("Starting health check loop")

        while self._running:
            try:
                # Check all agents
                results = await self.check_all_agents()

                healthy_count = sum(1 for h in results.values() if h)
                total_count = len(results)

                logger.info(
                    f"Health check complete: {healthy_count}/{total_count} agents healthy"
                )

                # Remove stale agents
                await self.remove_stale_agents()

            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

            # Wait before next check
            await asyncio.sleep(self.check_interval_seconds)

    def start(self):
        """Start the health monitoring service."""
        if self._running:
            logger.warning("Health service already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._health_check_loop())
        logger.info("Health service started")

    async def stop(self):
        """Stop the health monitoring service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Health service stopped")
