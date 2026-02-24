from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging
import asyncio
import os
from pydantic import BaseModel
from agent_framework import MCPStreamableHTTPTool
from app.config.settings import settings


router = APIRouter()
logger = logging.getLogger(__name__)


class MCPToolParameter(BaseModel):
    """Model for MCP tool parameter"""
    name: str
    type: str
    description: str
    required: bool


class MCPTool(BaseModel):
    """Model for MCP tool"""
    name: str
    description: str
    parameters: List[MCPToolParameter]


class MCPService(BaseModel):
    """Model for MCP service"""
    name: str
    port: int  # Kept for backward compatibility, but not used for hosted services
    status: str  # "healthy", "degraded", "offline"
    url: str
    tools: List[MCPTool]
    used_by_agents: List[str]
    error_message: str | None = None


class MCPRegistryResponse(BaseModel):
    """Response model for MCP registry endpoint"""
    services: List[MCPService]
    total_services: int
    healthy_services: int
    total_tools: int


# MCP service configuration - reads from environment variables for hosted services
def get_mcp_services_config():
    """Get MCP service configuration from settings."""
    services = []
    
    # Debug logging
    logger.info(f"🔍 Looking for MCP configuration in settings...")
    logger.info(f"   ACCOUNT_MCP_URL: {settings.ACCOUNT_MCP_URL}")
    logger.info(f"   TRANSACTION_MCP_URL: {settings.TRANSACTION_MCP_URL}")
    logger.info(f"   PAYMENT_MCP_URL: {settings.PAYMENT_MCP_URL}")
    logger.info(f"   LIMITS_MCP_URL: {settings.LIMITS_MCP_URL}")
    logger.info(f"   CONTACTS_MCP_URL: {settings.CONTACTS_MCP_URL}")
    
    # Account MCP
    if settings.ACCOUNT_MCP_URL:
        account_url = settings.ACCOUNT_MCP_URL
        # Ensure URL ends with /mcp
        if not account_url.endswith("/mcp"):
            account_url = f"{account_url}/mcp"
        services.append({
            "name": "Account",
            "url": account_url,
            "agents": ["AccountAgent", "PaymentAgent"]
        })
    
    # Transaction MCP
    if settings.TRANSACTION_MCP_URL:
        transaction_url = settings.TRANSACTION_MCP_URL
        if not transaction_url.endswith("/mcp"):
            transaction_url = f"{transaction_url}/mcp"
        services.append({
            "name": "Transaction",
            "url": transaction_url,
            "agents": ["TransactionAgent", "PaymentAgent"]
        })
    
    # Payment MCP
    if settings.PAYMENT_MCP_URL:
        payment_url = settings.PAYMENT_MCP_URL
        if not payment_url.endswith("/mcp"):
            payment_url = f"{payment_url}/mcp"
        services.append({
            "name": "Payment",
            "url": payment_url,
            "agents": ["PaymentAgent"]
        })
    
    # Limits MCP
    if settings.LIMITS_MCP_URL:
        limits_url = settings.LIMITS_MCP_URL
        if not limits_url.endswith("/mcp"):
            limits_url = f"{limits_url}/mcp"
        services.append({
            "name": "Limits",
            "url": limits_url,
            "agents": ["AccountAgent"]
        })
    
    # Contacts MCP
    if settings.CONTACTS_MCP_URL:
        contacts_url = settings.CONTACTS_MCP_URL
        if not contacts_url.endswith("/mcp"):
            contacts_url = f"{contacts_url}/mcp"
        services.append({
            "name": "Contacts",
            "url": contacts_url,
            "agents": ["PaymentAgent"]
        })
    
    logger.info(f"✅ Found {len(services)} MCP services configured")
    for svc in services:
        logger.info(f"   - {svc['name']}: {svc['url']}")
    
    return services


async def discover_mcp_service(
    service_name: str, 
    url: str,
    used_by_agents: List[str],
    timeout: float = 10.0
) -> MCPService:
    """
    Dynamically discover tools from MCP service using agent_framework's MCPStreamableHTTPTool.
    
    Args:
        service_name: Name of the MCP service
        url: Full URL to the MCP service endpoint
        used_by_agents: List of agent names that use this service
        timeout: Connection timeout in seconds
        
    Returns:
        MCPService object with status and discovered tools
    """
    # Extract port from URL for display purposes (or use 0 for hosted services)
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        port = parsed.port if parsed.port else (443 if parsed.scheme == 'https' else 80)
    except:
        port = 0
    
    try:
        # Use MCPStreamableHTTPTool to connect and discover tools
        mcp_tool = MCPStreamableHTTPTool(
            name=f"{service_name} Discovery",
            url=url,
            load_tools=False,  # Don't load tools into AIFunctions, we just want the list
            load_prompts=False,  # Don't load prompts
            sse_read_timeout=15.0  # Give SSE more time to read
        )
        
        # Connect with timeout - this handles MCP protocol handshake
        await asyncio.wait_for(mcp_tool.connect(), timeout=timeout)
        
        # List tools from the MCP server session
        tools = []
        if mcp_tool.session:
            tool_list = await mcp_tool.session.list_tools()
            
            for tool in tool_list.tools if tool_list else []:
                # Extract parameters from tool's inputSchema
                parameters = []
                if tool.inputSchema:
                    schema = tool.inputSchema
                    properties = schema.get('properties', {})
                    required_fields = schema.get('required', [])
                    
                    for param_name, param_info in properties.items():
                        parameters.append(MCPToolParameter(
                            name=param_name,
                            type=param_info.get('type', 'string'),
                            description=param_info.get('description', ''),
                            required=param_name in required_fields
                        ))
                
                tools.append(MCPTool(
                    name=tool.name,
                    description=tool.description or '',
                    parameters=parameters
                ))
        
        # Clean up connection
        await mcp_tool.close()
        
        return MCPService(
            name=service_name,
            port=port,
            status="healthy",
            url=url,
            tools=tools,
            used_by_agents=used_by_agents,
            error_message=None
        )
        
    except asyncio.TimeoutError:
        logger.warning(f"MCP service {service_name} at {url} connection timeout")
        return MCPService(
            name=service_name,
            port=port,
            status="offline",
            url=url,
            tools=[],
            used_by_agents=used_by_agents,
            error_message="Connection timeout"
        )
        
    except Exception as e:
        logger.error(f"Error discovering MCP service {service_name} at {url}: {str(e)}")
        return MCPService(
            name=service_name,
            port=port,
            status="offline",
            url=url,
            tools=[],
            used_by_agents=used_by_agents,
            error_message=str(e)
        )


@router.get("/mcp-registry", response_model=MCPRegistryResponse)
async def get_mcp_registry() -> MCPRegistryResponse:
    """
    Discover and return information about all MCP services.
    
    Returns:
        MCPRegistryResponse with service status, tools, and agent mappings
    """
    try:
        # Get service configuration from environment variables
        services_config = get_mcp_services_config()
        
        if not services_config:
            logger.warning("No MCP services configured in environment variables")
            return MCPRegistryResponse(
                services=[],
                total_services=0,
                healthy_services=0,
                total_tools=0
            )
        
        # Discover all services concurrently
        discovery_tasks = [
            discover_mcp_service(
                service_name=config["name"],
                url=config["url"],
                used_by_agents=config["agents"]
            )
            for config in services_config
        ]
        
        services = await asyncio.gather(*discovery_tasks)
        
        # Calculate statistics
        healthy_services = sum(1 for s in services if s.status == "healthy")
        total_tools = sum(len(s.tools) for s in services)
        
        return MCPRegistryResponse(
            services=list(services),
            total_services=len(services),
            healthy_services=healthy_services,
            total_tools=total_tools
        )
        
    except Exception as e:
        logger.error(f"Error fetching MCP registry: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch MCP registry: {str(e)}")


@router.get("/mcp-registry/service/{service_name}")
async def get_mcp_service_details(service_name: str) -> MCPService:
    """
    Get detailed information about a specific MCP service.
    
    Args:
        service_name: Name of the MCP service
        
    Returns:
        MCPService with full details
    """
    # Get service configuration from environment variables
    services_config = get_mcp_services_config()
    
    # Find service config
    service_config = next(
        (s for s in services_config if s["name"].lower() == service_name.lower()),
        None
    )
    
    if not service_config:
        raise HTTPException(status_code=404, detail=f"MCP service '{service_name}' not found")
    
    # Discover service
    service = await discover_mcp_service(
        service_name=service_config["name"],
        url=service_config["url"],
        used_by_agents=service_config["agents"]
    )
    
    return service
