"""API routes for agent registry operations."""
import logging
import httpx
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..models import (
    AgentRegistration,
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    AgentDiscoveryRequest,
    AgentDiscoveryResponse,
    HeartbeatRequest,
    HeartbeatResponse,
)
from ..services import RegistryService
from .auth import get_current_agent, verify_agent_or_skip, create_agent_token

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


def get_registry_service() -> RegistryService:
    """Dependency injection for registry service."""
    from ..main import registry_service

    return registry_service


@router.post(
    "/register",
    response_model=AgentRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_agent(
    request: AgentRegistrationRequest,
    registry: RegistryService = Depends(get_registry_service),
    _current_agent: Optional[dict] = Depends(verify_agent_or_skip),
):
    """Register a new agent.

    Args:
        request: Agent registration request
        registry: Registry service
        _current_agent: Current authenticated agent (if auth enabled)

    Returns:
        Registration response with agent ID and token
    """
    try:
        agent = await registry.register_agent(request)

        # Generate JWT token for the agent
        token = create_agent_token(agent.agent_id, agent.agent_name)

        return AgentRegistrationResponse(
            agent_id=agent.agent_id,
            status="registered",
            message=f"Agent {agent.agent_name} registered successfully",
            registered_at=agent.registered_at,
        )

    except Exception as e:
        logger.error(f"Failed to register agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register agent: {str(e)}",
        )


@router.get("/discover", response_model=AgentDiscoveryResponse)
async def discover_agents(
    capability: Optional[str] = Query(None, description="Filter by capability"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    status_filter: str = Query("active", alias="status", description="Filter by status"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    registry: RegistryService = Depends(get_registry_service),
    _current_agent: Optional[dict] = Depends(verify_agent_or_skip),
):
    """Discover agents matching the specified criteria.

    Args:
        capability: Filter by capability
        agent_type: Filter by agent type
        status_filter: Filter by status
        tags: Filter by tags
        registry: Registry service
        _current_agent: Current authenticated agent

    Returns:
        Discovery response with matching agents
    """
    try:
        request = AgentDiscoveryRequest(
            capability=capability,
            agent_type=agent_type,
            status=status_filter,
            tags=tags,
        )

        agents = await registry.discover_agents(request)

        return AgentDiscoveryResponse(agents=agents, count=len(agents))

    except Exception as e:
        logger.error(f"Failed to discover agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to discover agents: {str(e)}",
        )


@router.get("/{agent_id}", response_model=AgentRegistration)
async def get_agent(
    agent_id: str,
    registry: RegistryService = Depends(get_registry_service),
    _current_agent: Optional[dict] = Depends(verify_agent_or_skip),
):
    """Get agent details by ID.

    Args:
        agent_id: Agent ID
        registry: Registry service
        _current_agent: Current authenticated agent

    Returns:
        Agent registration details
    """
    agent = await registry.get_agent(agent_id)

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found",
        )

    return agent


@router.get("", response_model=AgentDiscoveryResponse)
async def list_all_agents(
    registry: RegistryService = Depends(get_registry_service),
    _current_agent: Optional[dict] = Depends(verify_agent_or_skip),
):
    """List all registered agents.

    Args:
        registry: Registry service
        _current_agent: Current authenticated agent

    Returns:
        All registered agents
    """
    try:
        agents = await registry.get_all_agents()
        return AgentDiscoveryResponse(agents=agents, count=len(agents))

    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list agents: {str(e)}",
        )


@router.post("/{agent_id}/heartbeat", response_model=HeartbeatResponse)
async def agent_heartbeat(
    agent_id: str,
    request: Optional[HeartbeatRequest] = None,
    registry: RegistryService = Depends(get_registry_service),
    _current_agent: Optional[dict] = Depends(verify_agent_or_skip),
):
    """Record agent heartbeat.

    Args:
        agent_id: Agent ID
        request: Heartbeat request (optional)
        registry: Registry service
        _current_agent: Current authenticated agent

    Returns:
        Heartbeat response
    """
    try:
        status_update = request.status if request else "active"
        success = await registry.update_heartbeat(agent_id, status_update)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )

        # Get updated agent
        agent = await registry.get_agent(agent_id)

        return HeartbeatResponse(
            status="alive",
            last_heartbeat=agent.last_heartbeat,
            message="Heartbeat acknowledged",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to record heartbeat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record heartbeat: {str(e)}",
        )


@router.delete("/{agent_id}", status_code=status.HTTP_200_OK)
async def deregister_agent(
    agent_id: str,
    registry: RegistryService = Depends(get_registry_service),
    current_agent: dict = Depends(get_current_agent),
):
    """Deregister an agent.

    Args:
        agent_id: Agent ID to deregister
        registry: Registry service
        current_agent: Current authenticated agent

    Returns:
        Success message
    """
    try:
        # Verify agent exists
        agent = await registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )

        # Deregister
        success = await registry.deregister_agent(agent_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deregister agent",
            )

        return {
            "status": "deregistered",
            "message": f"Agent {agent_id} removed from registry",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to deregister agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deregister agent: {str(e)}",
        )


@router.put("/{agent_id}/status", status_code=status.HTTP_200_OK)
async def update_agent_status(
    agent_id: str,
    new_status: str = Query(..., description="New agent status"),
    registry: RegistryService = Depends(get_registry_service),
    current_agent: dict = Depends(get_current_agent),
):
    """Update agent status.

    Args:
        agent_id: Agent ID
        new_status: New status (active, inactive, maintenance, degraded)
        registry: Registry service
        current_agent: Current authenticated agent

    Returns:
        Success message
    """
    try:
        success = await registry.update_agent_status(agent_id, new_status)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found",
            )

        return {
            "status": "updated",
            "agent_id": agent_id,
            "new_status": new_status,
            "message": f"Agent status updated to {new_status}",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update agent status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update agent status: {str(e)}",
        )


# ==============================================================================
# Dynamic Agent Card Discovery
# ==============================================================================

# Known agent URLs - can be moved to config or fetched from registry
AGENT_URLS = {
    "supervisor": "http://localhost:9000",
    "account": "http://localhost:9001",
    "transaction": "http://localhost:9002",
    "payment": "http://localhost:9003",
    "prodinfo": "http://localhost:9004",
    "coach": "http://localhost:9005",
    "escalation": "http://localhost:9006",
}


@router.get("/cards", response_model=Dict[str, Any])
async def get_all_agent_cards(
    _current_agent: Optional[dict] = Depends(verify_agent_or_skip),
):
    """Fetch agent cards dynamically from all running agents.

    This endpoint queries each agent's /.well-known/agent.json endpoint
    and aggregates the results. Only returns data for agents that are
    currently running and responding.

    Returns:
        Dictionary mapping agent IDs to their agent card details
    """
    agent_cards = {}
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for agent_id, base_url in AGENT_URLS.items():
            try:
                response = await client.get(f"{base_url}/.well-known/agent.json")
                
                if response.status_code == 200:
                    card_data = response.json()
                    agent_cards[agent_id] = {
                        **card_data,
                        "status": "online",
                        "base_url": base_url,
                    }
                    logger.info(f"✅ Fetched agent card for {agent_id}")
                else:
                    logger.warning(f"❌ Agent {agent_id} returned status {response.status_code}")
                    agent_cards[agent_id] = {
                        "status": "error",
                        "error": f"HTTP {response.status_code}",
                        "base_url": base_url,
                    }
                    
            except httpx.ConnectError:
                logger.warning(f"⚠️  Agent {agent_id} is offline")
                agent_cards[agent_id] = {
                    "status": "offline",
                    "error": "Connection refused",
                    "base_url": base_url,
                }
            except httpx.TimeoutException:
                logger.warning(f"⏱️  Agent {agent_id} timed out")
                agent_cards[agent_id] = {
                    "status": "timeout",
                    "error": "Request timeout",
                    "base_url": base_url,
                }
            except Exception as e:
                logger.error(f"❌ Error fetching card for {agent_id}: {e}")
                agent_cards[agent_id] = {
                    "status": "error",
                    "error": str(e),
                    "base_url": base_url,
                }
    
    return {
        "agents": agent_cards,
        "total": len(agent_cards),
        "online": sum(1 for card in agent_cards.values() if card.get("status") == "online"),
        "offline": sum(1 for card in agent_cards.values() if card.get("status") == "offline"),
    }


@router.get("/cards/{agent_id}", response_model=Dict[str, Any])
async def get_agent_card(
    agent_id: str,
    _current_agent: Optional[dict] = Depends(verify_agent_or_skip),
):
    """Fetch a single agent's card dynamically.

    Args:
        agent_id: Agent identifier (e.g., 'account', 'payment')

    Returns:
        Agent card details

    Raises:
        404: If agent ID is not recognized or agent is not responding
    """
    if agent_id not in AGENT_URLS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown agent ID: {agent_id}. Available: {list(AGENT_URLS.keys())}",
        )
    
    base_url = AGENT_URLS[agent_id]
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/.well-known/agent.json")
            response.raise_for_status()
            
            card_data = response.json()
            return {
                **card_data,
                "status": "online",
                "base_url": base_url,
            }
            
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch agent card for {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent {agent_id} is not responding: {str(e)}",
        )
