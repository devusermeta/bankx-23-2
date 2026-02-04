"""
Lineage tracker helper for creating lineage events from agent/MCP actions.
"""

import logging
import hashlib
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from .purview_service import PurviewService
from .config import purview_settings

logger = logging.getLogger(__name__)


class LineageTracker:
    """
    Helper class for creating and tracking lineage events from various
    agent and MCP tool operations.
    """

    def __init__(self, purview_service: PurviewService):
        """
        Initialize lineage tracker.

        Args:
            purview_service: PurviewService instance
        """
        self.purview = purview_service
        self.enabled = purview_settings.PURVIEW_ENABLED

    async def track_mcp_tool_call(
        self,
        tool_name: str,
        agent_name: str,
        input_params: Dict[str, Any],
        output_data: Dict[str, Any],
        data_source: str,
        request_id: str,
        latency_ms: float
    ) -> Optional[Dict[str, Any]]:
        """
        Track lineage for MCP tool call.

        Example flow:
            Input Parameters → MCP Tool → Data Source (CSV/DB)

        Args:
            tool_name: Name of MCP tool (e.g., "searchTransactions")
            agent_name: Name of calling agent (e.g., "TransactionAgent")
            input_params: Tool input parameters
            output_data: Tool output data
            data_source: Data source accessed (e.g., "transactions.csv")
            request_id: Request ID for tracking
            latency_ms: Tool execution latency in milliseconds

        Returns:
            Lineage response or None if disabled
        """
        if not self.enabled or not purview_settings.PURVIEW_TRACK_MCP_CALLS:
            return None

        try:
            # Source: Input parameters
            source_entity = {
                "type": "DataSet",
                "name": f"{agent_name}_Input",
                "qualified_name": self.purview.create_entity_qualified_name(
                    "input",
                    f"{agent_name}/{request_id}"
                ),
                "attributes": {
                    "parameters": input_params,
                    "timestamp": self._get_timestamp()
                }
            }

            # Target: Data source
            target_entity = {
                "type": "DataSet",
                "name": data_source,
                "qualified_name": self.purview.create_entity_qualified_name(
                    "datasource",
                    data_source
                ),
                "attributes": {
                    "format": self._get_format(data_source),
                    "location": f"schemas/tools-sandbox/uc1_synthetic_data/{data_source}"
                }
            }

            # Process: MCP tool
            process_entity = {
                "name": tool_name,
                "qualified_name": self.purview.create_entity_qualified_name(
                    "mcp",
                    f"{tool_name}/{request_id}"
                ),
                "description": f"{agent_name} called {tool_name}"
            }

            # Metadata
            metadata = {
                "agent_name": agent_name,
                "request_id": request_id,
                "latency_ms": latency_ms,
                "timestamp": self._get_timestamp(),
                "output_hash": self._hash_output(output_data)
            }

            return await self.purview.track_lineage(
                source_entity=source_entity,
                target_entity=target_entity,
                process_entity=process_entity,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to track MCP lineage: {e}")
            return None

    async def track_agent_routing(
        self,
        user_query: str,
        supervisor_agent: str,
        target_agent: str,
        intent: str,
        conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Track lineage for agent routing.

        Example flow:
            User Query → Supervisor → Target Agent

        Args:
            user_query: User's original query
            supervisor_agent: Supervisor agent name
            target_agent: Target agent name
            intent: Classified intent
            conversation_id: Conversation ID

        Returns:
            Lineage response or None if disabled
        """
        if not self.enabled or not purview_settings.PURVIEW_TRACK_AGENT_ROUTING:
            return None

        try:
            # Source: User query
            source_entity = {
                "type": "DataSet",
                "name": "UserQuery",
                "qualified_name": self.purview.create_entity_qualified_name(
                    "query",
                    conversation_id
                ),
                "attributes": {
                    "query": user_query,
                    "intent": intent,
                    "timestamp": self._get_timestamp()
                }
            }

            # Target: Agent invocation
            target_entity = {
                "type": "Process",
                "name": target_agent,
                "qualified_name": self.purview.create_entity_qualified_name(
                    "agent",
                    f"{target_agent}/{conversation_id}"
                ),
                "attributes": {
                    "agent_type": target_agent,
                    "intent": intent
                }
            }

            # Process: Supervisor routing
            process_entity = {
                "name": f"{supervisor_agent}_Routing",
                "qualified_name": self.purview.create_entity_qualified_name(
                    "routing",
                    f"{supervisor_agent}/{conversation_id}"
                ),
                "description": f"Route intent '{intent}' to {target_agent}"
            }

            metadata = {
                "conversation_id": conversation_id,
                "intent": intent,
                "timestamp": self._get_timestamp()
            }

            return await self.purview.track_lineage(
                source_entity=source_entity,
                target_entity=target_entity,
                process_entity=process_entity,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to track routing lineage: {e}")
            return None

    async def track_rag_search(
        self,
        query: str,
        index_name: str,
        results_count: int,
        agent_name: str,
        request_id: str,
        use_case: str = "UC2"
    ) -> Optional[Dict[str, Any]]:
        """
        Track lineage for RAG search (UC2/UC3).

        Example flow:
            User Query → Agent → Azure AI Search → Knowledge Base

        Args:
            query: Search query
            index_name: Azure AI Search index name
            results_count: Number of results returned
            agent_name: Agent performing search
            request_id: Request ID
            use_case: Use case (UC2 or UC3)

        Returns:
            Lineage response or None if disabled
        """
        if not self.enabled or not purview_settings.PURVIEW_TRACK_RAG_SEARCHES:
            return None

        try:
            # Source: User query
            source_entity = {
                "type": "DataSet",
                "name": "RAGQuery",
                "qualified_name": self.purview.create_entity_qualified_name(
                    "rag_query",
                    request_id
                ),
                "attributes": {
                    "query": query,
                    "use_case": use_case
                }
            }

            # Target: Azure AI Search index
            target_entity = {
                "type": "DataSet",
                "name": index_name,
                "qualified_name": self.purview.create_entity_qualified_name(
                    "search_index",
                    index_name
                ),
                "attributes": {
                    "type": "AzureAISearch",
                    "results_count": results_count,
                    "use_case": use_case
                }
            }

            # Process: RAG search
            process_entity = {
                "name": f"{agent_name}_RAGSearch",
                "qualified_name": self.purview.create_entity_qualified_name(
                    "rag",
                    f"{agent_name}/{request_id}"
                ),
                "description": f"{agent_name} RAG search in {index_name}"
            }

            metadata = {
                "request_id": request_id,
                "results_count": results_count,
                "use_case": use_case,
                "timestamp": self._get_timestamp()
            }

            return await self.purview.track_lineage(
                source_entity=source_entity,
                target_entity=target_entity,
                process_entity=process_entity,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to track RAG lineage: {e}")
            return None

    async def track_decision_ledger(
        self,
        conversation_id: str,
        customer_id: str,
        agent_name: str,
        action: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        ledger_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Track lineage for Decision Ledger entries.

        Example flow:
            Agent Action → Decision Ledger → Audit Log

        Args:
            conversation_id: Conversation ID
            customer_id: Customer ID
            agent_name: Agent name
            action: Action performed
            input_data: Input parameters
            output_data: Output result
            ledger_id: Decision ledger entry ID

        Returns:
            Lineage response or None if disabled
        """
        if not self.enabled:
            return None

        try:
            # Source: Agent action
            source_entity = {
                "type": "Process",
                "name": f"{agent_name}_{action}",
                "qualified_name": self.purview.create_entity_qualified_name(
                    "action",
                    f"{agent_name}/{action}/{conversation_id}"
                ),
                "attributes": {
                    "agent_name": agent_name,
                    "action": action,
                    "customer_id": customer_id,
                    "input": input_data
                }
            }

            # Target: Decision ledger
            target_entity = {
                "type": "DataSet",
                "name": "DecisionLedger",
                "qualified_name": self.purview.create_entity_qualified_name(
                    "ledger",
                    "decision_ledger"
                ),
                "attributes": {
                    "ledger_id": ledger_id,
                    "format": "JSON"
                }
            }

            # Process: Logging
            process_entity = {
                "name": "LogDecision",
                "qualified_name": self.purview.create_entity_qualified_name(
                    "logging",
                    ledger_id
                ),
                "description": f"Log {action} to Decision Ledger"
            }

            metadata = {
                "conversation_id": conversation_id,
                "customer_id": customer_id,
                "ledger_id": ledger_id,
                "timestamp": self._get_timestamp()
            }

            return await self.purview.track_lineage(
                source_entity=source_entity,
                target_entity=target_entity,
                process_entity=process_entity,
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to track ledger lineage: {e}")
            return None

    def _get_timestamp(self) -> str:
        """Get current timestamp in Asia/Bangkok timezone"""
        return datetime.now(timezone(timedelta(hours=7))).isoformat()

    def _get_format(self, filename: str) -> str:
        """Get file format from filename"""
        if filename.endswith(".csv"):
            return "CSV"
        elif filename.endswith(".json"):
            return "JSON"
        elif filename.endswith(".pdf"):
            return "PDF"
        return "UNKNOWN"

    def _hash_output(self, output_data: Dict[str, Any]) -> str:
        """Generate hash of output data for tracking"""
        output_str = str(output_data)
        return hashlib.sha256(output_str.encode()).hexdigest()[:16]
