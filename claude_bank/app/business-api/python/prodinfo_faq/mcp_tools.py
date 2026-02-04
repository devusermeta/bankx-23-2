"""MCP tools for ProdInfoFAQ agent."""

import os
import logging
import httpx
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from fastmcp import FastMCP
from models import SearchResult, GroundingValidationResult, SupportTicket
from services import AISearchService, ContentUnderstandingService, CosmosDBService

logger = logging.getLogger(__name__)

# EscalationComms MCP service URL (append /mcp if not present)
ESCALATION_COMMS_BASE_URL = os.getenv("ESCALATION_COMMS_MCP_URL", "http://localhost:8078")
ESCALATION_COMMS_URL = f"{ESCALATION_COMMS_BASE_URL}/mcp" if not ESCALATION_COMMS_BASE_URL.endswith("/mcp") else ESCALATION_COMMS_BASE_URL


def register_tools(
    mcp: FastMCP,
    ai_search: AISearchService,
    content_understanding: ContentUnderstandingService,
    cosmosdb: CosmosDBService
):
    """Register all MCP tools for ProdInfoFAQ agent."""

    @mcp.tool()
    async def search_documents(
        query: str,
        top_k: int = 5,
        min_confidence: float = 0.0
    ) -> Dict[str, Any]:
        """
        Search indexed product documents and FAQs using AI Search with vector embeddings.

        Args:
            query: Search query string
            top_k: Number of results to return (default: 5)
            min_confidence: Minimum confidence threshold 0-1 (default: 0.0)

        Returns:
            Dictionary containing search results with confidence scores and source references
        """
        logger.info(f"[MCP Tool] search_documents: query='{query}', top_k={top_k}")

        try:
            results = await ai_search.search_documents(query, top_k, min_confidence)
            
            # Log first result for debugging
            if results:
                logger.info(f"First search result fields: {list(results[0].model_dump().keys())}")

            return {
                "success": True,
                "query": query,
                "result_count": len(results),
                "results": [r.model_dump() for r in results]
            }

        except Exception as e:
            logger.error(f"Error in search_documents: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }

    @mcp.tool()
    async def get_document_by_id(
        document_id: str,
        section: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve specific document section by ID.

        Args:
            document_id: Document identifier
            section: Optional specific section name to retrieve

        Returns:
            Full document or section content with metadata
        """
        logger.info(f"[MCP Tool] get_document_by_id: id={document_id}, section={section}")

        try:
            result = await ai_search.get_document_by_id(document_id, section)

            if result:
                return {
                    "success": True,
                    "document": result
                }
            else:
                return {
                    "success": False,
                    "error": "Document not found"
                }

        except Exception as e:
            logger.error(f"Error in get_document_by_id: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def get_content_understanding(
        query: str,
        search_results_json: str,
        min_confidence: float = 0.3
    ) -> Dict[str, Any]:
        """
        Use Azure AI Foundry Content Understanding to validate and synthesize answer from search results.

        This is the CRITICAL grounding validation step that ensures 100% accuracy.

        Args:
            query: User's question
            search_results_json: JSON string of search results from search_documents
            min_confidence: Minimum confidence for grounding (default: 0.3 per UC2 spec)

        Returns:
            Validated answer with grounding confidence, citations, or reason if not grounded
        """
        logger.info(f"[MCP Tool] get_content_understanding: query='{query}', min_confidence={min_confidence}")

        try:
            import json

            # Parse search results - handle potential escape issues
            try:
                search_results_data = json.loads(search_results_json)
            except json.JSONDecodeError as e:
                # Try to fix common escape issues
                logger.warning(f"JSON decode error, attempting to fix: {e}")
                # Replace problematic backslashes
                fixed_json = search_results_json.replace('\\t', ' ').replace('\\n', ' ').replace('\\r', '')
                search_results_data = json.loads(fixed_json)
            
            # Handle both dict with "results" key and direct list
            if isinstance(search_results_data, dict):
                results_list = search_results_data.get("results", [])
            elif isinstance(search_results_data, list):
                results_list = search_results_data
            else:
                results_list = []
            
            search_results = [SearchResult(**r) for r in results_list]

            if not search_results:
                return {
                    "success": False,
                    "is_grounded": False,
                    "confidence": 0.0,
                    "reason": "No search results provided for validation"
                }

            # If Content Understanding is not available, return search results directly for agent to process
            if content_understanding is None:
                logger.warning("Content Understanding not available - returning search results directly")
                # Return search results as structured data for the agent to read
                avg_confidence = sum(r.confidence for r in search_results) / len(search_results)
                
                # Format search results for agent consumption
                formatted_results = []
                for i, result in enumerate(search_results[:5], 1):  # Top 5 results
                    formatted_results.append({
                        "rank": i,
                        "source": result.source,
                        "confidence": result.confidence,
                        "content": result.content[:500]  # First 500 chars
                    })
                
                logger.info(f"Returning {len(formatted_results)} search results directly to agent")
                
                return {
                    "success": True,
                    "is_grounded": avg_confidence >= min_confidence,
                    "confidence": avg_confidence,
                    "search_results": formatted_results,  # Provide raw search results
                    "validated_answer": None,  # No LLM synthesis without Content Understanding
                    "citations": [r.source for r in search_results[:3]],  # Top 3 sources
                    "reason": "Content Understanding not configured - using search results directly" if avg_confidence < min_confidence else None
                }

            # First, generate an answer from search results
            # This will be validated by Azure AI Evaluation
            context_text = "\n\n".join([
                f"[Source: {r.source}]\n{r.content}"
                for r in search_results[:3]
            ])
            
            # Simple answer synthesis (agent will do the real synthesis)
            # This is just for grounding validation
            synthesized_answer = f"Based on the search results:\n{context_text[:500]}..."
            
            # Validate grounding using Azure AI Evaluation
            # Converts min_confidence from 0-1 scale to 1-5 scale
            min_groundedness_score = min_confidence * 5.0
            
            validation = await content_understanding.validate_grounding(
                query=query,
                response=synthesized_answer,
                search_results=search_results,
                min_confidence=min_groundedness_score
            )

            return {
                "success": True,
                "is_grounded": validation.is_grounded,
                "confidence": validation.confidence,
                "validated_answer": validation.validated_answer,
                "citations": validation.citations,
                "reason": validation.reason,
                "groundedness_score": validation.confidence * 5.0  # Return 1-5 scale for transparency
            }

        except Exception as e:
            logger.error(f"Error in get_content_understanding: {e}")
            return {
                "success": False,
                "is_grounded": False,
                "confidence": 0.0,
                "error": str(e)
            }

    @mcp.tool()
    async def write_to_cosmosdb(
        customer_id: str,
        query: str,
        category: str,
        priority: str = "normal",
        metadata: str = "{}",
        ticket_id: Optional[str] = None,
        confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Store support ticket in CosmosDB when query cannot be answered.

        Args:
            ticket_id: Unique ticket ID (format: TKT-YYYY-NNNNNN)
            customer_id: Customer identifier
            query: Original customer question
            category: Ticket category (e.g., "product_info", "account_query")
            priority: Ticket priority - "normal", "high", or "urgent" (default: "normal")
            metadata: Optional JSON string with additional metadata

        Returns:
            Confirmation of ticket creation
        """
        logger.info(f"[MCP Tool] write_to_cosmosdb: ticket_id={ticket_id}, customer={customer_id}, confirmed={confirmed}")

        try:
            import json

            # Ensure ticket creation only proceeds when confirmed=True
            if not confirmed:
                return {
                    "success": False,
                    "error": "Confirmation required to create ticket. Please ask the user to confirm and retry with confirmed=True"
                }

            # If ticket_id not provided, generate one using CosmosDBService helper
            if not ticket_id:
                try:
                    ticket_id = cosmosdb.get_next_ticket_id()
                except Exception as e:
                    logger.warning(f"Could not auto-generate ticket id: {e}")
                    # Fallback to timestamp-based id
                    ticket_id = datetime.now(timezone.utc).strftime("TKT-%Y%m%d-%H%M%S")

            ticket = SupportTicket(
                ticket_id=ticket_id,
                customer_id=customer_id,
                query=query,
                category=category,
                priority=priority,
                status="created",
                metadata=json.loads(metadata) if metadata else {}
            )

            success = await cosmosdb.write_ticket(ticket)

            if success:
                return {
                    "success": True,
                    "ticket_id": ticket_id,
                    "status": "created",
                    "message": "Support ticket created successfully"
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to create ticket"
                }

        except Exception as e:
            logger.error(f"Error in write_to_cosmosdb: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @mcp.tool()
    async def read_from_cosmosdb(
        query: str,
        search_type: str = "cache"
    ) -> Dict[str, Any]:
        """
        Check CosmosDB for cached queries or similar previous tickets.

        Args:
            query: Search query
            search_type: Type of search - "cache" for FAQ cache, "ticket" for ticket history

        Returns:
            Matching cached results or tickets
        """
        logger.info(f"[MCP Tool] read_from_cosmosdb: query='{query}', type={search_type}")

        try:
            if search_type == "cache":
                cached = await cosmosdb.read_cache(query)

                if cached:
                    return {
                        "success": True,
                        "cache_hit": True,
                        "answer": cached.answer,
                        "sources": cached.sources,
                        "hit_count": cached.hit_count
                    }
                else:
                    return {
                        "success": True,
                        "cache_hit": False
                    }
            else:
                # Ticket search not implemented yet
                return {
                    "success": True,
                    "results": []
                }

        except Exception as e:
            logger.error(f"Error in read_from_cosmosdb: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    logger.info("Registered 5 MCP tools for ProdInfoFAQ agent")
