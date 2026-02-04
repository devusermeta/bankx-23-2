"""
Agent Cards API Router

Dynamically fetches agent cards from running A2A agents.
Provides real-time discovery of agent capabilities and status.
Supports adding custom agents and removing agents at runtime.
"""
import logging
import httpx
import json
from pathlib import Path
from typing import Dict, Any, Optional, Set, List
from pydantic import BaseModel

from fastapi import APIRouter, HTTPException, status

logger = logging.getLogger(__name__)

router = APIRouter()

# Load agent identities from JSON file
AGENT_IDENTITIES_FILE = Path(__file__).parent.parent.parent.parent.parent / "agent_identities.json"
AGENT_IDENTITIES = {}

def load_agent_identities():
    """Load agent identities from JSON file."""
    global AGENT_IDENTITIES
    try:
        if AGENT_IDENTITIES_FILE.exists():
            with open(AGENT_IDENTITIES_FILE, 'r') as f:
                AGENT_IDENTITIES = json.load(f)
            logger.info(f"✅ Loaded {len(AGENT_IDENTITIES)} agent identities from {AGENT_IDENTITIES_FILE}")
        else:
            logger.warning(f"⚠️  Agent identities file not found: {AGENT_IDENTITIES_FILE}")
    except Exception as e:
        logger.error(f"❌ Failed to load agent identities: {e}")

# Load identities on module import
load_agent_identities()

# Default agent URLs - maps agent IDs to their base URLs
DEFAULT_AGENT_URLS = {
    "supervisor": "http://localhost:9000",
    "account": "http://localhost:9001",
    "transaction": "http://localhost:9002",
    "payment": "http://localhost:9003",
    "prodinfo": "http://localhost:9004",
    "coach": "http://localhost:9005",
    "escalation": "http://localhost:9006",
}

# Runtime storage (resets on server restart)
custom_agents: Dict[str, str] = {}  # agent_id -> base_url
removed_agent_ids: Set[str] = set()  # Set of removed agent IDs


class AddAgentRequest(BaseModel):
    """Request model for adding a new agent."""
    url: str  # Base URL of the agent (e.g., http://localhost:9999)


class AddAgentResponse(BaseModel):
    """Response model for adding a new agent."""
    agent_id: str
    agent_name: str
    base_url: str
    message: str


def get_all_agent_urls() -> Dict[str, str]:
    """Get combined agent URLs (defaults + custom - removed)."""
    all_urls = {**DEFAULT_AGENT_URLS, **custom_agents}
    return {aid: url for aid, url in all_urls.items() if aid not in removed_agent_ids}


@router.get("/agent-cards")
async def get_all_agent_cards() -> Dict[str, Any]:
    """
    Fetch agent cards dynamically from all running agents.

    This endpoint queries each agent's /.well-known/agent.json endpoint
    and aggregates the results. Only returns data for agents that are
    currently running and responding.

    Returns:
        Dictionary containing:
        - agents: Map of agent_id to agent card data
        - total: Total number of agents checked
        - online: Number of agents currently online
        - offline: Number of agents currently offline
    """
    agent_cards = {}
    agent_urls = get_all_agent_urls()
    
    # Agent name mapping
    agent_name_mapping = {
        "supervisor": "SupervisorAgent",
        "account": "AccountAgent",
        "transaction": "TransactionAgent",
        "payment": "PaymentAgent",
        "prodinfo": "ProdInfoFAQAgent",
        "coach": "AIMoneyCoachAgent",
        "escalation": "EscalationAgent",
    }
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        for agent_id, base_url in agent_urls.items():
            try:
                response = await client.get(f"{base_url}/.well-known/agent.json")
                
                if response.status_code == 200:
                    card_data = response.json()
                    
                    # Use agent_id mapping to get the correct agent name for identity lookup
                    mapped_agent_name = agent_name_mapping.get(agent_id, agent_id.title() + "Agent")
                    
                    # Get identity data
                    identity_data = AGENT_IDENTITIES.get(mapped_agent_name, {})
                    
                    agent_card = {
                        **card_data,
                        "status": "online",
                        "base_url": base_url,
                    }
                    
                    # Add identity IDs if available
                    if identity_data:
                        agent_card["blueprint_id"] = identity_data.get("blueprint_id")
                        agent_card["object_id"] = identity_data.get("object_id")
                    
                    agent_cards[agent_id] = agent_card
                    logger.info(f"✅ Fetched agent card for {agent_id}")
                else:
                    logger.warning(f"❌ Agent {agent_id} returned status {response.status_code}")
                    agent_cards[agent_id] = {
                        "status": "error",
                        "error": f"HTTP {response.status_code}",
                        "base_url": base_url,
                        "name": agent_id.title() + " Agent",
                    }
                    
            except httpx.ConnectError:
                logger.warning(f"⚠️  Agent {agent_id} is offline")
                agent_cards[agent_id] = {
                    "status": "offline",
                    "error": "Connection refused",
                    "base_url": base_url,
                    "name": agent_id.title() + " Agent",
                }
            except httpx.TimeoutException:
                logger.warning(f"⏱️  Agent {agent_id} timed out")
                agent_cards[agent_id] = {
                    "status": "timeout",
                    "error": "Request timeout",
                    "base_url": base_url,
                    "name": agent_id.title() + " Agent",
                }
            except Exception as e:
                logger.error(f"❌ Error fetching card for {agent_id}: {e}")
                agent_cards[agent_id] = {
                    "status": "error",
                    "error": str(e),
                    "base_url": base_url,
                    "name": agent_id.title() + " Agent",
                }
    
    return {
        "agents": agent_cards,
        "total": len(agent_cards),
        "online": sum(1 for card in agent_cards.values() if card.get("status") == "online"),
        "offline": sum(1 for card in agent_cards.values() if card.get("status") in ["offline", "timeout", "error"]),
    }


@router.get("/agent-cards/{agent_id}")
async def get_agent_card(agent_id: str) -> Dict[str, Any]:
    """
    Fetch a single agent's card dynamically.

    Args:
        agent_id: Agent identifier (e.g., 'account', 'payment', 'escalation')

    Returns:
        Agent card details with current status

    Raises:
        404: If agent ID is not recognized or has been removed
        503: If agent is not responding
    """
    agent_urls = get_all_agent_urls()
    
    if agent_id not in agent_urls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown agent ID: {agent_id}. Available: {list(agent_urls.keys())}",
        )
    
    base_url = agent_urls[agent_id]
    
    # Get agent name from card data (need to fetch to get actual agent name)
    agent_name_mapping = {
        "supervisor": "SupervisorAgent",
        "account": "AccountAgent",
        "transaction": "TransactionAgent",
        "payment": "PaymentAgent",
        "prodinfo": "ProdInfoFAQAgent",
        "coach": "AIMoneyCoachAgent",
        "escalation": "EscalationAgent",
    }
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/.well-known/agent.json")
            response.raise_for_status()
            
            card_data = response.json()
            
            # Use agent_id mapping to get the correct agent name for identity lookup
            # (agent card may return "Account Agent" but we need "AccountAgent")
            mapped_agent_name = agent_name_mapping.get(agent_id, agent_id.title() + "Agent")
            
            # Add identity IDs if available
            identity_data = AGENT_IDENTITIES.get(mapped_agent_name, {})
            
            result = {
                **card_data,
                "status": "online",
                "base_url": base_url,
            }
            
            # Add blueprint_id and object_id if available
            if identity_data:
                result["blueprint_id"] = identity_data.get("blueprint_id")
                result["object_id"] = identity_data.get("object_id")
            
            return result
            
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch agent card for {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Agent {agent_id} is not responding: {str(e)}",
        )


@router.get("/agent-urls")
async def get_agent_urls() -> Dict[str, str]:
    """
    Get the mapping of agent IDs to their base URLs.

    Useful for frontend to know where each agent is hosted.

    Returns:
        Dictionary mapping agent_id to base_url (excluding removed agents)
    """
    return get_all_agent_urls()


@router.post("/agent-cards/add", response_model=AddAgentResponse)
async def add_agent(request: AddAgentRequest) -> AddAgentResponse:
    """
    Add a new custom agent to the system.

    Validates that the agent URL is reachable and has a valid agent card.

    Args:
        request: AddAgentRequest with agent URL

    Returns:
        AddAgentResponse with agent details

    Raises:
        400: If URL is invalid or agent card cannot be fetched
        409: If agent already exists
    """
    url = request.url.rstrip('/')
    
    try:
        # Fetch agent card to validate
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/.well-known/agent.json")
            response.raise_for_status()
            
            card_data = response.json()
            
            # Extract agent ID and name from card (accept both 'id' and 'agent_id')
            agent_id = card_data.get("id") or card_data.get("agent_id", "")
            agent_name = card_data.get("name", "Unknown Agent")
            
            if not agent_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Agent card does not contain an 'id' or 'agent_id' field",
                )
            
            # Check if agent ID already exists
            if agent_id in get_all_agent_urls():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Agent '{agent_id}' already exists. Remove it first to re-add.",
                )
            
            # Check if URL is already in use by another agent
            all_urls = get_all_agent_urls()
            for existing_id, existing_url in all_urls.items():
                if existing_url.rstrip('/') == url:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"URL '{url}' is already used by agent '{existing_id}'. Remove that agent first.",
                    )
            
            # Check if this URL matches any default agent URL
            for default_id, default_url in DEFAULT_AGENT_URLS.items():
                if default_url.rstrip('/') == url and default_id not in removed_agent_ids:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"URL '{url}' is a default agent ('{default_id}'). This agent already exists in the system.",
                    )
            
            # Add to custom agents and remove from removed list if present
            custom_agents[agent_id] = url
            removed_agent_ids.discard(agent_id)
            
            logger.info(f"✅ Added custom agent: {agent_id} ({agent_name}) at {url}")
            
            return AddAgentResponse(
                agent_id=agent_id,
                agent_name=agent_name,
                base_url=url,
                message=f"Agent '{agent_name}' added successfully",
            )
            
    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot connect to agent at {url}. Make sure the agent is running.",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Connection to {url} timed out. Agent may be unresponsive.",
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent returned HTTP {e.response.status_code}. Check agent card endpoint.",
        )
    except Exception as e:
        logger.error(f"Error adding agent from {url}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch agent card: {str(e)}",
        )


@router.delete("/agent-cards/{agent_id}")
async def remove_agent(agent_id: str) -> Dict[str, Any]:
    """
    Remove an agent from the system.

    This marks the agent as removed. Default agents can be removed but will
    reappear on server restart. Custom agents are permanently removed until re-added.

    Args:
        agent_id: Agent identifier to remove

    Returns:
        Success message with agent details

    Raises:
        404: If agent ID is not recognized or already removed
    """
    all_urls = {**DEFAULT_AGENT_URLS, **custom_agents}
    
    if agent_id not in all_urls:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown agent ID: {agent_id}",
        )
    
    if agent_id in removed_agent_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent '{agent_id}' is already removed",
        )
    
    # Mark as removed
    removed_agent_ids.add(agent_id)
    
    # If it's a custom agent, also remove from custom_agents
    if agent_id in custom_agents:
        del custom_agents[agent_id]
    
    logger.info(f"🗑️  Removed agent: {agent_id}")
    
    return {
        "message": f"Agent '{agent_id}' removed successfully",
        "agent_id": agent_id,
        "note": "Default agents will reappear on server restart",
    }
