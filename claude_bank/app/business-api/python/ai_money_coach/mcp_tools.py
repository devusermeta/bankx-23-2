"""MCP tools for AIMoneyCoach agent."""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from fastmcp import FastMCP
from models import MoneyCoachSearchResult, GroundingValidationResult
from services import MoneyCoachAISearchService, MoneyCoachContentUnderstandingService

# Add app directory to path for common imports
workspace_root = Path(__file__).parent.parent.parent.parent.parent
app_dir = workspace_root / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from common.observability import trace_mcp_tool, log_custom_event

logger = logging.getLogger(__name__)


def register_tools(
    mcp: FastMCP,
    ai_search: MoneyCoachAISearchService,
    content_understanding: MoneyCoachContentUnderstandingService
):
    """Register all MCP tools for AIMoneyCoach agent."""

    @mcp.tool()
    async def ai_search_rag_results(
        query: str,
        chapter_filter: Optional[int] = None,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        **ALWAYS CALL THIS FIRST** - Search the "Debt-Free to Financial Freedom" book using AI Search with vector embeddings.
        
        YOU MUST call this tool for EVERY financial question. Do not answer without calling this tool first.

        Args:
            query: User's question or topic to search (REQUIRED)
            chapter_filter: Optional chapter number to filter (1-12)
            top_k: Number of results to return (default: 5)

        Returns:
            Relevant content chunks with chapter references and confidence scores from the book
        """
        logger.info(f"[MCP Tool] ai_search_rag_results: query='{query}', chapter={chapter_filter}")

        with trace_mcp_tool(
            tool_name="ai_search_rag_results",
            query=query,
            attributes={
                "chapter_filter": str(chapter_filter) if chapter_filter else "none",
                "top_k": top_k,
                "use_case": "UC3"
            }
        ):
            try:
                # Validate chapter filter
                if chapter_filter and (chapter_filter < 1 or chapter_filter > 12):
                    return {
                        "success": False,
                        "error": "chapter_filter must be between 1 and 12"
                    }

                results = await ai_search.search_money_coach_content(query, chapter_filter, top_k)
                
                logger.info(f"Search returned {len(results)} results")
                if results:
                    logger.info(f"First result: Chapter {results[0].chapter} - {results[0].content[:100]}...")

                response = {
                    "success": True,
                    "query": query,
                    "chapter_filter": chapter_filter,
                    "result_count": len(results),
                    "results": [r.model_dump() for r in results]
                }
                logger.info(f"Returning response with {len(response['results'])} results to agent")
                
                # Log custom event for successful search
                if results:
                    log_custom_event(
                        event_name="uc3_search_completed",
                        properties={
                            "query": query,
                            "result_count": len(results),
                            "top_chapter": results[0].chapter if results else None
                        },
                        measurements={
                            "confidence": results[0].confidence if results else 0.0
                        }
                    )
                
                return response

            except Exception as e:
                logger.error(f"Error in ai_search_rag_results: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "results": []
                }

    @mcp.tool()
    async def ai_foundry_content_understanding(
        query: str,
        search_results_json: str,
        clarifications: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        **ALWAYS CALL THIS SECOND** - Validate and get the actual answer from book content.
        
        After calling ai_search_rag_results, YOU MUST call this tool to validate and synthesize the answer.
        This returns search_results array with the actual book content you need to read and use.

        CRITICAL: This ensures 100% grounding in the book and REJECTS any generic financial advice
        not from the "Debt-Free to Financial Freedom" book.

        Args:
            query: User's question (REQUIRED)
            search_results_json: JSON string of results from ai_search_rag_results (REQUIRED - use json.dumps on the entire response)
            clarifications: Optional answers to clarifying questions

        Returns:
            search_results array with book content, chapter_references, and citations.
            READ the search_results[].content to answer the question!
        """
        logger.info(f"[MCP Tool] ai_foundry_content_understanding: query='{query}'")
        logger.info(f"[MCP Tool] Received search_results_json length: {len(search_results_json)}")

        with trace_mcp_tool(
            tool_name="ai_foundry_content_understanding",
            query=query,
            attributes={
                "has_clarifications": clarifications is not None,
                "content_understanding_enabled": content_understanding is not None,
                "use_case": "UC3"
            }
        ):
            try:
                import json

                # Parse search results
                search_results_data = json.loads(search_results_json)
                logger.info(f"[MCP Tool] Parsed search results data type: {type(search_results_data)}")
                
                # Handle both dict with "results" key and direct list
                if isinstance(search_results_data, dict):
                    results_list = search_results_data.get("results", [])
                elif isinstance(search_results_data, list):
                    results_list = search_results_data
                else:
                    results_list = []
                
                search_results = [MoneyCoachSearchResult(**r) for r in results_list]

                if not search_results:
                    return {
                        "success": False,
                        "is_grounded": False,
                        "confidence": 0.0,
                        "reason": "No search results provided for validation"
                    }

                # Fallback validation if Azure AI Evaluation not available
                if content_understanding is None:
                    logger.warning("Azure AI Evaluation not available - returning search results without validation")
                    avg_confidence = sum(r.confidence for r in search_results) / len(search_results)
                    
                    # Build chapter references
                    chapter_refs = []
                    seen_chapters = set()
                    for r in search_results:
                        if r.chapter not in seen_chapters:
                            chapter_refs.append(f"Chapter {r.chapter}: {r.chapter_title}")
                            seen_chapters.add(r.chapter)
                    
                    # Return search results for agent to synthesize answer
                    result = {
                        "success": True,
                        "is_grounded": avg_confidence >= 0.5,
                        "confidence": avg_confidence,
                        "search_results": [
                            {
                                "chapter": r.chapter,
                                "chapter_title": r.chapter_title,
                                "content": r.content,
                                "page": r.page,
                                "confidence": r.confidence
                            }
                            for r in search_results
                        ],
                        "chapter_references": chapter_refs,
                        "citations": [f"Chapter {r.chapter}, Page {r.page or 'N/A'}" for r in search_results[:3]],
                        "reason": "Azure AI Evaluation not configured - agent should synthesize answer from search results" if avg_confidence < 0.5 else None,
                        "contains_non_book_content": False
                    }
                    logger.info(f"Returning {len(result['search_results'])} search results to agent")
                    logger.info(f"First result preview: Chapter {search_results[0].chapter} - {search_results[0].content[:100]}...")
                    return result

                # Synthesize answer from search results for validation
                synthesized_answer = "\n\n".join([
                    f"From Chapter {r.chapter} ({r.chapter_title}): {r.content}"
                    for r in search_results[:3]
                ])

                # Validate strict grounding using Azure AI Evaluation (min_confidence=4.0 for strict book grounding)
                validation = await content_understanding.validate_grounding(
                    query=query,
                    response=synthesized_answer,
                    search_results=search_results,
                    min_confidence=4.0  # Strict threshold for money coach (4.0/5.0)
                )

                # Convert confidence back to groundedness score (0-1 to 1-5 scale)
                groundedness_score = validation.confidence * 5.0
                
                # If not grounded enough, reject
                if not validation.is_grounded or validation.contains_non_book_content:
                    return {
                        "success": True,
                        "is_grounded": False,
                        "confidence": validation.confidence,
                        "groundedness_score": groundedness_score,
                        "reason": validation.reason or "Answer not sufficiently grounded in the book content.",
                        "contains_non_book_content": validation.contains_non_book_content,
                        "standard_output": "I cannot find information about this topic in my knowledge base. Would you like me to create a support ticket for a specialist to help you?"
                    }

                # Return validated answer with book content
                return {
                    "success": True,
                    "is_grounded": validation.is_grounded,
                    "confidence": validation.confidence,
                    "groundedness_score": groundedness_score,
                    "search_results": [
                        {
                            "chapter": r.chapter,
                            "chapter_title": r.chapter_title,
                            "content": r.content,
                            "page": r.page,
                            "confidence": r.confidence
                        }
                        for r in search_results
                    ],
                    "chapter_references": validation.chapter_references,
                    "citations": [f"Chapter {r.chapter}, Page {r.page or 'N/A'}" for r in search_results[:3]],
                    "validated_answer": validation.validated_answer,
                    "reason": validation.reason,
                    "contains_non_book_content": validation.contains_non_book_content
                }

            except Exception as e:
                logger.error(f"Error in ai_foundry_content_understanding: {e}")
                return {
                    "success": False,
                    "is_grounded": False,
                    "confidence": 0.0,
                    "error": str(e)
                }

    logger.info("Registered 2 MCP tools for AIMoneyCoach agent")
