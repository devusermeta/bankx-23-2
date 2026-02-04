"""
Data models for Azure Purview lineage tracking.
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime


class PurviewEntity(BaseModel):
    """Purview entity model"""

    type: str = Field(..., description="Entity type (DataSet, Process, etc.)")
    name: str = Field(..., description="Entity name")
    qualified_name: str = Field(..., description="Unique qualified name")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Entity attributes")


class LineageEvent(BaseModel):
    """Lineage event model"""

    source_entity: PurviewEntity = Field(..., description="Source entity (input)")
    target_entity: PurviewEntity = Field(..., description="Target entity (output)")
    process_entity: PurviewEntity = Field(..., description="Process/transformation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Event timestamp")


class LineageRelationship(BaseModel):
    """Represents a relationship between entities in Purview"""

    relationship_type: str = Field(..., description="Type of relationship (e.g., 'input', 'output')")
    from_entity: str = Field(..., description="Source entity qualified name")
    to_entity: str = Field(..., description="Target entity qualified name")
    attributes: Dict[str, Any] = Field(default_factory=dict)


class DataLineageNode(BaseModel):
    """Represents a node in the data lineage graph"""

    node_id: str = Field(..., description="Unique node identifier")
    node_type: str = Field(..., description="Node type (agent, tool, dataset)")
    name: str = Field(..., description="Node name")
    qualified_name: str = Field(..., description="Fully qualified name")
    properties: Dict[str, Any] = Field(default_factory=dict)


class DataLineagePath(BaseModel):
    """Represents a complete lineage path from source to target"""

    path_id: str = Field(..., description="Unique path identifier")
    nodes: List[DataLineageNode] = Field(default_factory=list)
    relationships: List[LineageRelationship] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
