"""Agent registration data models."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator
from uuid import uuid4


class AgentEndpoints(BaseModel):
    """Agent service endpoints."""
    http: str = Field(..., description="Primary HTTP endpoint for the agent")
    health: str = Field(..., description="Health check endpoint")
    metrics: Optional[str] = Field(None, description="Prometheus metrics endpoint")
    a2a: str = Field(..., description="A2A invocation endpoint")


class AgentCapability(BaseModel):
    """Agent capability definition."""
    name: str = Field(..., description="Capability identifier (e.g., 'account.balance')")
    description: str = Field(..., description="Human-readable description")
    input_schema: Dict[str, Any] = Field(default_factory=dict, description="Input parameters schema")
    output_schema: str = Field(..., description="Output format type")


class AgentMetadata(BaseModel):
    """Additional agent metadata."""
    description: str = Field(..., description="Agent description")
    mcp_tools: List[str] = Field(default_factory=list, description="MCP tools used by this agent")
    output_formats: List[str] = Field(default_factory=list, description="Supported output formats")
    max_concurrent_requests: int = Field(default=100, description="Max concurrent requests")
    average_response_time_ms: int = Field(default=500, description="Average response time in ms")
    owner_team: Optional[str] = Field(None, description="Team responsible for this agent")
    support_contact: Optional[str] = Field(None, description="Support contact email")


class AgentRegistration(BaseModel):
    """Complete agent registration model."""
    agent_id: str = Field(default_factory=lambda: f"agent-{uuid4().hex[:12]}", description="Unique agent ID")
    agent_name: str = Field(..., description="Human-readable agent name")
    agent_type: str = Field(..., description="Agent type: supervisor, domain, knowledge")
    version: str = Field(default="1.0.0", description="Agent version (semantic versioning)")
    capabilities: List[str] = Field(default_factory=list, description="List of capability names")
    capabilities_detailed: Optional[List[AgentCapability]] = Field(None, description="Detailed capabilities")
    endpoints: AgentEndpoints = Field(..., description="Agent endpoints")
    health_check_url: str = Field(..., description="Health check URL")
    metadata: AgentMetadata = Field(default_factory=AgentMetadata, description="Additional metadata")
    status: str = Field(default="active", description="Agent status: active, inactive, maintenance")
    registered_at: datetime = Field(default_factory=datetime.utcnow, description="Registration timestamp")
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow, description="Last heartbeat timestamp")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")

    @field_validator('agent_type')
    @classmethod
    def validate_agent_type(cls, v: str) -> str:
        """Validate agent type."""
        allowed_types = ['supervisor', 'domain', 'knowledge', 'utility']
        if v not in allowed_types:
            raise ValueError(f"Agent type must be one of {allowed_types}")
        return v

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate agent status."""
        allowed_statuses = ['active', 'inactive', 'maintenance', 'degraded']
        if v not in allowed_statuses:
            raise ValueError(f"Agent status must be one of {allowed_statuses}")
        return v

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "agent_name": "AccountAgent",
                "agent_type": "domain",
                "version": "1.0.0",
                "capabilities": ["account.balance", "account.limits"],
                "endpoints": {
                    "http": "http://localhost:8100",
                    "health": "http://localhost:8100/health",
                    "metrics": "http://localhost:8100/metrics",
                    "a2a": "http://localhost:8100/a2a/invoke"
                },
                "health_check_url": "http://localhost:8100/health",
                "tags": ["uc1", "financial-operations"]
            }
        }


class AgentRegistrationRequest(BaseModel):
    """Request to register a new agent."""
    agent_name: str
    agent_type: str
    version: str = "1.0.0"
    capabilities: List[str] = Field(default_factory=list)
    capabilities_detailed: Optional[List[AgentCapability]] = None
    endpoints: AgentEndpoints
    metadata: Optional[AgentMetadata] = None
    tags: List[str] = Field(default_factory=list)


class AgentRegistrationResponse(BaseModel):
    """Response from agent registration."""
    agent_id: str
    status: str
    message: str
    registered_at: datetime


class AgentDiscoveryRequest(BaseModel):
    """Request to discover agents."""
    capability: Optional[str] = None
    agent_type: Optional[str] = None
    status: str = "active"
    tags: Optional[List[str]] = None


class AgentDiscoveryResponse(BaseModel):
    """Response from agent discovery."""
    agents: List[AgentRegistration]
    count: int


class HeartbeatRequest(BaseModel):
    """Heartbeat request from agent."""
    agent_id: str
    status: str = "active"
    metadata: Optional[Dict[str, Any]] = None


class HeartbeatResponse(BaseModel):
    """Heartbeat response."""
    status: str
    last_heartbeat: datetime
    message: str = "Heartbeat acknowledged"
