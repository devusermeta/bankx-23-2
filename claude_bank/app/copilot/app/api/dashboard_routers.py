"""
Dashboard API endpoints for observability data.
Provides access to agent decisions, RAG evaluations, triage rules, MCP audit logs, and user messages.
"""
import os
import json
from datetime import datetime, date
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.config.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

# Environment-aware path resolution
def get_observability_dir() -> Path:
    """Get observability directory - works in both local and Docker environments"""
    if os.path.exists("/.dockerenv"):
        # Running in Docker - observability is at /app/observability/
        return Path("/app/observability")
    else:
        # Running locally - observability is relative to copilot directory
        # From app/copilot/app/api/ go up 2 levels to app/copilot/ then into observability/
        return Path(__file__).parent.parent.parent / "observability"

# # Get observability directory path
# OBSERVABILITY_DIR = get_observability_dir()


# # Response Models
# class AgentDecision(BaseModel):
#     timestamp: str
#     agent_name: str
#     thread_id: Optional[str] = None
#     user_query: str
#     triage_rule: str
#     reasoning: str
#     tools_considered: List[str] = []
#     tools_invoked: List[str] = []
#     result_status: str
#     result_summary: str
#     context: Dict[str, Any] = {}
#     duration_seconds: float
#     message_type: str




OBSERVABILITY_DIR = get_observability_dir()


# Response Models
class AgentDecision(BaseModel):
    timestamp: str
    agent_name: str
    thread_id: Optional[str] = None
    user_query: str = ""
    triage_rule: str = ""
    reasoning: str = ""
    tools_considered: List[str] = []
    tools_invoked: List[Any] = []  # Can be List[str] or List[Dict] depending on source
    result_status: str = "unknown"
    result_summary: str = ""
    context: Dict[str, Any] = {}
    duration_seconds: float = 0.0
    message_type: str = "general"
    
    class Config:
        # Allow extra fields that might be in JSON but not in model
        extra = "ignore"



class RagEvaluation(BaseModel):
    timestamp: str
    service: str
    query: str
    response_preview: str = ""
    groundedness_score: float = 0.0
    is_grounded: bool = False
    confidence_normalized: float = 0.0
    reasoning: str = ""
    citations_count: int = 0
    citations: List[str] = []


class TriageRule(BaseModel):
    timestamp: str
    rule_name: str
    target_agent: str
    user_query: str
    confidence: float = 0.0


class McpAudit(BaseModel):
    timestamp: str
    operation_type: str
    mcp_server: str
    tool_name: str
    user_id: Optional[str] = None
    thread_id: Optional[str] = None
    parameters: Dict[str, Any] = {}
    data_accessed: List[Any] = []
    data_scope: str = ""
    result_status: str
    result_summary: str = ""
    error_message: Optional[str] = None
    duration_ms: float = 0.0  # Changed from int to float to handle decimal values
    compliance_flags: List[str] = []


class UserMessage(BaseModel):
    timestamp: str
    thread_id: Optional[str] = None
    user_query: str
    response_preview: Optional[str] = ""
    response_length: int = 0
    duration_seconds: float = 0.0
    message_type: str


class DashboardStats(BaseModel):
    total_conversations: int
    total_agent_decisions: int
    total_rag_queries: int
    total_mcp_calls: int
    active_agents: int


# Helper function to read NDJSON files
def read_ndjson_file(file_path: Path) -> List[Dict[str, Any]]:
    """Read NDJSON file (or JSON array) and return list of records."""
    records = []
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
                # Check if it's a JSON array (starts with [)
                if content.startswith('['):
                    try:
                        data = json.loads(content)
                        if isinstance(data, list):
                            records = [item for item in data if isinstance(item, dict)]
                            logger.info(f"Loaded {len(records)} records from JSON array in {file_path.name}")
                        return records
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing JSON array in {file_path}: {e}")
                        return records
                
                # Otherwise treat as NDJSON (one JSON object per line)
                for line in content.split('\n'):
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            # Only append if it's a dictionary
                            if isinstance(data, dict):
                                records.append(data)
                            else:
                                logger.warning(f"Skipping non-dict JSON in {file_path}: {type(data)}")
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing JSON line in {file_path}: {e}")
                            continue
        else:
            logger.warning(f"File not found: {file_path}")
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
    
    return records


def get_observability_files(data_type: str, target_date: Optional[date] = None) -> List[Path]:
    """Get list of observability files for a given data type and optional date."""
    files = []
    
    if target_date:
        # Get specific date file
        date_str = target_date.strftime("%Y-%m-%d")
        file_path = OBSERVABILITY_DIR / f"{data_type}_{date_str}.json"
        if file_path.exists():
            files.append(file_path)
    else:
        # Get all files for this data type
        pattern = f"{data_type}_*.json"
        files = sorted(OBSERVABILITY_DIR.glob(pattern), reverse=True)
    
    return files


@router.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get overall dashboard statistics."""
    try:
        # Count agent decisions
        agent_files = get_observability_files("agent_decisions")
        total_decisions = sum(len(read_ndjson_file(f)) for f in agent_files)
        
        # Count RAG evaluations
        rag_files = get_observability_files("rag_evaluations")
        total_rag = sum(len(read_ndjson_file(f)) for f in rag_files)
        
        # Count MCP audit logs
        mcp_files = get_observability_files("mcp_audit")
        total_mcp = sum(len(read_ndjson_file(f)) for f in mcp_files)
        
        # Get unique agents from agent decisions
        unique_agents = set()
        for file in agent_files[:3]:  # Check last 3 files for performance
            records = read_ndjson_file(file)
            for record in records:
                unique_agents.add(record.get("agent_name", ""))
        
        # Count conversations (use user_messages as proxy)
        msg_files = get_observability_files("user_messages")
        all_threads = set()
        for file in msg_files:
            records = read_ndjson_file(file)
            for record in records:
                all_threads.add(record.get("thread_id", ""))
        
        return DashboardStats(
            total_conversations=len(all_threads),
            total_agent_decisions=total_decisions,
            total_rag_queries=total_rag,
            total_mcp_calls=total_mcp,
            active_agents=len(unique_agents)
        )
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(e)}")


@router.get("/api/dashboard/agent-decisions", response_model=List[AgentDecision])
async def get_agent_decisions(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    limit: Optional[int] = Query(100, description="Maximum number of records to return")
):
    """Get agent decision logs."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else None
        files = get_observability_files("agent_decisions", target_date)
        
        if not files:
            logger.info(f"No agent decision files found for date: {date}")
            return []
        
        all_records = []
        for file in files:
            records = read_ndjson_file(file)
            all_records.extend(records)
        
        # Sort by timestamp descending
        all_records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Apply limit
        limited_records = all_records[:limit]
        
        # logger.info(f"Returning {len(limited_records)} agent decision records")
        # return [AgentDecision(**record) for record in limited_records]

        # Parse records with error handling
        parsed_records = []
        for record in limited_records:
            try:
                parsed_records.append(AgentDecision(**record))
            except Exception as e:
                logger.warning(f"Failed to parse agent decision record: {e}")
                logger.debug(f"Problem record: {record}")
                continue
        
        logger.info(f"Returning {len(parsed_records)} agent decision records (skipped {len(limited_records) - len(parsed_records)} invalid)")
        return parsed_records

    except ValueError as e:
        logger.error(f"Date parsing error: {e}")
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        # logger.error(f"Error getting agent decisions: {e}")
        logger.error(f"Error getting agent decisions: {e}", exc_info=True)

        raise HTTPException(status_code=500, detail=f"Error retrieving agent decisions: {str(e)}")


@router.get("/api/dashboard/rag-evaluations", response_model=List[RagEvaluation])
async def get_rag_evaluations(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    limit: Optional[int] = Query(100, description="Maximum number of records to return")
):
    """Get RAG evaluation logs."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else None
        files = get_observability_files("rag_evaluations", target_date)
        
        if not files:
            logger.info(f"No RAG evaluation files found for date: {date}")
            return []
        
        all_records = []
        for file in files:
            records = read_ndjson_file(file)
            all_records.extend(records)
        
        # Sort by timestamp descending
        all_records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Apply limit
        limited_records = all_records[:limit]
        
        logger.info(f"Returning {len(limited_records)} RAG evaluation records")
        return [RagEvaluation(**record) for record in limited_records]
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting RAG evaluations: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving RAG evaluations: {str(e)}")


@router.get("/api/dashboard/triage-rules", response_model=List[TriageRule])
async def get_triage_rules(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    limit: Optional[int] = Query(100, description="Maximum number of records to return")
):
    """Get triage rule logs."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else None
        files = get_observability_files("triage_rules", target_date)
        
        if not files:
            logger.info(f"No triage rule files found for date: {date}")
            return []
        
        all_records = []
        for file in files:
            records = read_ndjson_file(file)
            all_records.extend(records)
        
        # Sort by timestamp descending
        all_records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Apply limit
        limited_records = all_records[:limit]
        
        logger.info(f"Returning {len(limited_records)} triage rule records")
        return [TriageRule(**record) for record in limited_records]
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting triage rules: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving triage rules: {str(e)}")


@router.get("/api/dashboard/mcp-audit", response_model=List[McpAudit])
async def get_mcp_audit(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    limit: Optional[int] = Query(100, description="Maximum number of records to return")
):
    """Get MCP audit logs."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else None
        files = get_observability_files("mcp_audit", target_date)
        
        if not files:
            logger.info(f"No MCP audit files found for date: {date}")
            return []
        
        all_records = []
        for file in files:
            records = read_ndjson_file(file)
            all_records.extend(records)
        
        # Sort by timestamp descending
        all_records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Apply limit
        limited_records = all_records[:limit]
        
        logger.info(f"Returning {len(limited_records)} MCP audit records")
        return [McpAudit(**record) for record in limited_records]
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting MCP audit logs: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving MCP audit logs: {str(e)}")


@router.get("/api/dashboard/user-messages", response_model=List[UserMessage])
async def get_user_messages(
    date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format"),
    limit: Optional[int] = Query(100, description="Maximum number of records to return")
):
    """Get user message logs."""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date() if date else None
        files = get_observability_files("user_messages", target_date)
        
        if not files:
            logger.info(f"No user message files found for date: {date}")
            return []
        
        all_records = []
        for file in files:
            records = read_ndjson_file(file)
            all_records.extend(records)
        
        # Sort by timestamp descending
        all_records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Apply limit
        limited_records = all_records[:limit]
        
        logger.info(f"Returning {len(limited_records)} user message records")
        return [UserMessage(**record) for record in limited_records]
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting user messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving user messages: {str(e)}")
