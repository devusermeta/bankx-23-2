"""
Azure Purview service for data lineage tracking.
"""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone, timedelta

from azure.purview.account import PurviewAccountClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import AzureError

from .models import PurviewEntity, LineageEvent
from .config import purview_settings

logger = logging.getLogger(__name__)


class PurviewService:
    """
    Azure Purview service for data lineage tracking.

    Tracks complete data flow through the BankX multi-agent system:
    - User queries → Agent routing
    - Agent actions → MCP tool calls
    - MCP tool calls → Data sources
    - RAG searches → Knowledge bases
    """

    def __init__(self, account_name: Optional[str] = None, credential=None):
        """
        Initialize Purview service.

        Args:
            account_name: Purview account name (default: from settings)
            credential: Azure credential (default: DefaultAzureCredential)
        """
        self.account_name = account_name or purview_settings.PURVIEW_ACCOUNT_NAME
        self.credential = credential or DefaultAzureCredential()
        self.enabled = purview_settings.PURVIEW_ENABLED

        if not self.enabled:
            logger.info("Purview lineage tracking is DISABLED")
            return

        try:
            # Initialize Purview client
            endpoint = purview_settings.AZURE_PURVIEW_ENDPOINT or f"https://{self.account_name}.purview.azure.com"
            self.client = PurviewAccountClient(
                endpoint=endpoint,
                credential=self.credential
            )
            logger.info(f"Purview service initialized: {endpoint}")

        except Exception as e:
            logger.error(f"Failed to initialize Purview client: {e}")
            logger.warning("Purview lineage tracking will be disabled")
            self.enabled = False

    async def track_lineage(
        self,
        source_entity: Dict[str, Any],
        target_entity: Dict[str, Any],
        process_entity: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Track data lineage from source to target via process.

        Args:
            source_entity: Input data source (e.g., user query, CSV file)
            target_entity: Output data (e.g., agent response, aggregation)
            process_entity: Transformation process (e.g., agent, MCP tool)
            metadata: Additional context (latency, request_id, etc.)

        Returns:
            Lineage response from Purview API, or None if disabled/failed
        """
        if not self.enabled:
            return None

        try:
            # Create lineage event
            lineage_event = self._create_lineage_event(
                source=source_entity,
                target=target_entity,
                process=process_entity,
                metadata=metadata or {}
            )

            # Track asynchronously if configured
            if purview_settings.PURVIEW_ASYNC_MODE:
                asyncio.create_task(self._send_lineage_async(lineage_event))
                return {"status": "queued"}
            else:
                return await self._send_lineage(lineage_event)

        except Exception as e:
            logger.error(f"Failed to track lineage: {e}")
            # Don't fail the main operation if Purview fails
            return None

    async def _send_lineage(self, lineage_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Send lineage event to Purview (synchronous)"""
        try:
            # Send to Purview Atlas API
            # Note: azure-purview-account SDK may not have direct lineage methods
            # May need to use REST API directly via httpx or azure.core
            response = await self._call_purview_api(lineage_event)

            logger.info(
                f"Lineage tracked: {lineage_event['attributes']['inputs'][0]['attributes']['name']} → "
                f"{lineage_event['attributes']['name']} → "
                f"{lineage_event['attributes']['outputs'][0]['attributes']['name']}"
            )

            return response

        except AzureError as e:
            logger.error(f"Purview API error: {e}")
            return None

    async def _send_lineage_async(self, lineage_event: Dict[str, Any]):
        """Send lineage event asynchronously (fire and forget)"""
        try:
            await self._send_lineage(lineage_event)
        except Exception as e:
            logger.error(f"Async lineage tracking failed: {e}")

    async def _call_purview_api(self, lineage_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call Purview REST API to create lineage.

        Note: This is a placeholder. Actual implementation depends on Purview API version.
        """
        # For now, log the lineage event instead of sending to API
        # In production, use Purview REST API or SDK methods

        logger.debug(f"Lineage event: {lineage_event}")

        # Simulate API response
        return {
            "status": "success",
            "lineage_id": lineage_event["attributes"]["qualifiedName"],
            "timestamp": datetime.now(timezone(timedelta(hours=7))).isoformat()
        }

    def _create_lineage_event(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        process: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create Purview lineage event in Atlas format.

        Returns Atlas Process entity with inputs and outputs.
        """
        return {
            "typeName": "Process",
            "attributes": {
                "name": process["name"],
                "qualifiedName": process["qualified_name"],
                "description": process.get("description", ""),
                "inputs": [self._create_entity_ref(source)],
                "outputs": [self._create_entity_ref(target)],
                "metadata": metadata,
                "createTime": datetime.now(timezone(timedelta(hours=7))).isoformat()
            }
        }

    def _create_entity_ref(self, entity: Dict[str, Any]) -> Dict[str, Any]:
        """Create Purview entity reference"""
        return {
            "typeName": entity["type"],
            "uniqueAttributes": {
                "qualifiedName": entity["qualified_name"]
            },
            "attributes": {
                "name": entity["name"],
                **entity.get("attributes", {})
            }
        }

    async def get_lineage(
        self,
        entity_qualified_name: str,
        direction: str = "BOTH",
        depth: int = 3
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve lineage for a specific entity.

        Args:
            entity_qualified_name: Qualified name of the entity
            direction: Lineage direction ("INPUT", "OUTPUT", "BOTH")
            depth: Depth of lineage graph to retrieve

        Returns:
            Lineage graph or None if not found/disabled
        """
        if not self.enabled:
            return None

        try:
            # Call Purview lineage API
            # Placeholder implementation
            logger.info(f"Retrieving lineage for: {entity_qualified_name} (direction={direction}, depth={depth})")

            return {
                "entity": entity_qualified_name,
                "direction": direction,
                "depth": depth,
                "nodes": [],
                "relationships": []
            }

        except Exception as e:
            logger.error(f"Failed to retrieve lineage: {e}")
            return None

    def create_entity_qualified_name(
        self,
        entity_type: str,
        name: str,
        scope: str = "bankx"
    ) -> str:
        """
        Create a standardized qualified name for Purview entities.

        Format: bankx://<scope>/<type>/<name>

        Args:
            entity_type: Type of entity (agent, mcp, datasource)
            name: Entity name
            scope: Scope/namespace (default: bankx)

        Returns:
            Qualified name string
        """
        return f"{scope}://{entity_type}/{name}"
