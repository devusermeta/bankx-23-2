"""A2A client for agent-to-agent communication."""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional

import httpx
from opentelemetry import trace

from ..models import A2AMessage, A2AResponse, AgentIdentifier, A2AMetadata
from ..utils import CircuitBreaker, CircuitBreakerError
from .registry_client import RegistryClient

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class A2AConfig:
    """Configuration for A2A client."""

    def __init__(
        self,
        timeout_seconds: int = 30,
        max_retries: int = 3,
        retry_backoff_seconds: int = 2,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout_seconds: int = 60,
        enable_tracing: bool = True,
    ):
        """Initialize A2A config.

        Args:
            timeout_seconds: Request timeout
            max_retries: Maximum retry attempts
            retry_backoff_seconds: Base backoff time for retries
            circuit_breaker_threshold: Failures before opening circuit
            circuit_breaker_timeout_seconds: Circuit breaker timeout
            enable_tracing: Enable distributed tracing
        """
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_backoff_seconds = retry_backoff_seconds
        self.circuit_breaker_threshold = circuit_breaker_threshold
        self.circuit_breaker_timeout_seconds = circuit_breaker_timeout_seconds
        self.enable_tracing = enable_tracing


class A2AClient:
    """Client for agent-to-agent communication."""

    def __init__(
        self,
        agent_id: str,
        agent_name: str,
        registry_client: RegistryClient,
        config: Optional[A2AConfig] = None,
    ):
        """Initialize A2A client.

        Args:
            agent_id: Current agent's ID
            agent_name: Current agent's name
            registry_client: Registry client for service discovery
            config: Optional A2A configuration
        """
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.registry_client = registry_client
        self.config = config or A2AConfig()

        self._http_client = httpx.AsyncClient(timeout=self.config.timeout_seconds)
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

    def _get_circuit_breaker(self, target_agent_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for target agent.

        Args:
            target_agent_id: Target agent ID

        Returns:
            Circuit breaker instance
        """
        if target_agent_id not in self._circuit_breakers:
            self._circuit_breakers[target_agent_id] = CircuitBreaker(
                failure_threshold=self.config.circuit_breaker_threshold,
                timeout_seconds=self.config.circuit_breaker_timeout_seconds,
            )
        return self._circuit_breakers[target_agent_id]

    async def send_message(
        self,
        target_capability: str,
        intent: str,
        payload: Dict,
        target_agent_id: Optional[str] = None,
        target_agent_name: Optional[str] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> A2AResponse:
        """Send A2A message to another agent.

        Args:
            target_capability: Capability to invoke
            intent: Intent/operation to perform
            payload: Message payload
            target_agent_id: Optional specific target agent ID
            target_agent_name: Optional specific target agent name
            trace_id: Optional distributed trace ID
            span_id: Optional trace span ID

        Returns:
            A2A response

        Raises:
            Exception: If message send fails
        """
        span_name = f"a2a.send.{intent}"

        if self.config.enable_tracing:
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("target.capability", target_capability)
                span.set_attribute("intent", intent)
                return await self._send_message_internal(
                    target_capability,
                    intent,
                    payload,
                    target_agent_id,
                    target_agent_name,
                    trace_id,
                    span_id,
                )
        else:
            return await self._send_message_internal(
                target_capability,
                intent,
                payload,
                target_agent_id,
                target_agent_name,
                trace_id,
                span_id,
            )

    async def _send_message_internal(
        self,
        target_capability: str,
        intent: str,
        payload: Dict,
        target_agent_id: Optional[str],
        target_agent_name: Optional[str],
        trace_id: Optional[str],
        span_id: Optional[str],
    ) -> A2AResponse:
        """Internal message sending logic.

        Args:
            target_capability: Capability to invoke
            intent: Intent/operation to perform
            payload: Message payload
            target_agent_id: Optional specific target agent ID
            target_agent_name: Optional specific target agent name
            trace_id: Optional distributed trace ID
            span_id: Optional trace span ID

        Returns:
            A2A response

        Raises:
            CircuitBreakerError: If circuit breaker is open
            Exception: If all retries fail
        """
        # Discover target agent if not specified
        if not target_agent_id:
            agents = await self.registry_client.discover(capability=target_capability)
            if not agents:
                raise Exception(f"No agent found with capability: {target_capability}")

            # Use first available agent (could implement load balancing here)
            target_agent = agents[0]
            target_agent_id = target_agent["agent_id"]
            target_agent_name = target_agent["agent_name"]
            target_endpoint = target_agent["endpoints"]["a2a"]
        else:
            # Get target agent details
            target_agent = await self.registry_client.get_agent(target_agent_id)
            if not target_agent:
                raise Exception(f"Agent not found: {target_agent_id}")

            target_endpoint = target_agent["endpoints"]["a2a"]
            if not target_agent_name:
                target_agent_name = target_agent["agent_name"]

        # Check circuit breaker
        circuit_breaker = self._get_circuit_breaker(target_agent_id)
        if not circuit_breaker.can_execute():
            raise CircuitBreakerError(
                f"Circuit breaker open for agent {target_agent_name}"
            )

        # Build A2A message
        message = A2AMessage(
            source=AgentIdentifier(agent_id=self.agent_id, agent_name=self.agent_name),
            target=AgentIdentifier(agent_id=target_agent_id, agent_name=target_agent_name),
            intent=intent,
            payload=payload,
            metadata=A2AMetadata(
                timeout_seconds=self.config.timeout_seconds,
                trace_id=trace_id,
                span_id=span_id,
            ),
        )

        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.config.max_retries):
            try:
                message.metadata.retry_count = attempt

                logger.debug(
                    f"Sending A2A message to {target_agent_name} "
                    f"(attempt {attempt + 1}/{self.config.max_retries})"
                )

                # Send HTTP request
                start_time = datetime.utcnow()
                response = await self._http_client.post(
                    target_endpoint,
                    json=message.model_dump(mode='json'),
                    timeout=self.config.timeout_seconds,
                )
                end_time = datetime.utcnow()
                latency_ms = int((end_time - start_time).total_seconds() * 1000)

                response.raise_for_status()

                # Parse response
                response_data = response.json()
                a2a_response = A2AResponse(**response_data)

                # Record success in circuit breaker
                circuit_breaker.record_success()

                logger.info(
                    f"A2A call successful: {self.agent_name} -> {target_agent_name} "
                    f"({intent}, {latency_ms}ms)"
                )

                # Add latency to metadata
                if not a2a_response.metadata:
                    a2a_response.metadata = {}
                a2a_response.metadata["processing_time_ms"] = latency_ms

                return a2a_response

            except httpx.TimeoutException as e:
                last_exception = e
                circuit_breaker.record_failure()
                logger.warning(
                    f"A2A timeout: {self.agent_name} -> {target_agent_name} "
                    f"(attempt {attempt + 1})"
                )

            except httpx.HTTPStatusError as e:
                last_exception = e
                circuit_breaker.record_failure()
                logger.error(
                    f"A2A HTTP error: {self.agent_name} -> {target_agent_name} "
                    f"(status: {e.response.status_code}, attempt {attempt + 1})"
                )

            except Exception as e:
                last_exception = e
                circuit_breaker.record_failure()
                logger.error(
                    f"A2A error: {self.agent_name} -> {target_agent_name} "
                    f"(attempt {attempt + 1}): {str(e)}"
                )

            # Exponential backoff before retry
            if attempt < self.config.max_retries - 1:
                backoff_time = self.config.retry_backoff_seconds * (2**attempt)
                logger.debug(f"Retrying in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)

        # All retries failed
        logger.error(
            f"A2A call failed after {self.config.max_retries} attempts: "
            f"{self.agent_name} -> {target_agent_name}"
        )

        raise Exception(
            f"Failed to send A2A message after {self.config.max_retries} attempts: "
            f"{str(last_exception)}"
        )

    async def close(self):
        """Close the HTTP client."""
        await self._http_client.aclose()
        await self.registry_client.close()
