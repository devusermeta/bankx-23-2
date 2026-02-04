from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging
import asyncio
from pydantic import BaseModel
from agent_framework import MCPStreamableHTTPTool


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
    port: int
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


# MCP service configuration - simplified without hardcoded tools
MCP_SERVICES_CONFIG = [
    {"name": "Account", "port": 8070, "agents": ["AccountAgent", "PaymentAgent"]},
    {"name": "Transaction", "port": 8071, "agents": ["TransactionAgent", "PaymentAgent"]},
    {"name": "Payment", "port": 8072, "agents": ["PaymentAgent"]},
    {"name": "Limits", "port": 8073, "agents": ["AccountAgent"]},
    {"name": "Contacts", "port": 8074, "agents": ["PaymentAgent"]},
    {"name": "Audit", "port": 8075, "agents": []},  # System-wide
    {"name": "ProdInfo", "port": 8076, "agents": ["ProdInfoFAQAgent"]},
    {"name": "AIMoneyCoach", "port": 8077, "agents": ["AIMoneyCoachAgent"]},
    {"name": "EscalationComms", "port": 8078, "agents": ["EscalationCommsAgent"]},
]


async def discover_mcp_service(
    service_name: str, 
    port: int, 
    used_by_agents: List[str],
    timeout: float = 10.0
) -> MCPService:
    """
    Dynamically discover tools from MCP service using agent_framework's MCPStreamableHTTPTool.
    
    Args:
        service_name: Name of the MCP service
        port: Port number the service is running on
        used_by_agents: List of agent names that use this service
        timeout: Connection timeout in seconds
        
    Returns:
        MCPService object with status and discovered tools
    """
    url = f"http://localhost:{port}/mcp"
    
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
        logger.warning(f"MCP service {service_name} (port {port}) connection timeout")
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
        logger.error(f"Error discovering MCP service {service_name} (port {port}): {str(e)}")
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
        # Discover all services concurrently
        discovery_tasks = [
            discover_mcp_service(
                service_name=config["name"],
                port=config["port"],
                used_by_agents=config["agents"]
            )
            for config in MCP_SERVICES_CONFIG
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
    # Find service config
    service_config = next(
        (s for s in MCP_SERVICES_CONFIG if s["name"].lower() == service_name.lower()),
        None
    )
    
    if not service_config:
        raise HTTPException(status_code=404, detail=f"MCP service '{service_name}' not found")
    
    # Discover service
    service = await discover_mcp_service(
        service_name=service_config["name"],
        port=service_config["port"],
        used_by_agents=service_config["agents"]
    )
    
    return service
