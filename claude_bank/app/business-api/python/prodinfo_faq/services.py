"""Business logic for ProdInfoFAQ MCP server."""

import os
import logging
import hashlib
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.ai.evaluation import GroundednessEvaluator
from azure.cosmos import CosmosClient, PartitionKey
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from models import SearchResult, GroundingValidationResult, SupportTicket, CachedQuery

logger = logging.getLogger(__name__)


class AISearchService:
    """Service for Azure AI Search operations."""

    def __init__(self, endpoint: str, key: Optional[str], index_name: str):
        """Initialize AI Search client."""
        self.endpoint = endpoint
        self.index_name = index_name

        # Use key if provided, otherwise use managed identity
        if key:
            credential = AzureKeyCredential(key)
        else:
            credential = DefaultAzureCredential()

        self.search_client = SearchClient(
            endpoint=endpoint,
            index_name=index_name,
            credential=credential
        )
        logger.info(f"Initialized AI Search client for index: {index_name}")

    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
        min_confidence: float = 0.0
    ) -> List[SearchResult]:
        """
        Search indexed documents using vector search.

        Args:
            query: Search query string
            top_k: Number of results to return
            min_confidence: Minimum confidence threshold (0-1)

        Returns:
            List of search results with confidence scores
        """
        try:
            logger.info(f"Searching for: '{query}' (top_k={top_k}, min_confidence={min_confidence})")

            # Perform hybrid search (text + vector)
            results = self.search_client.search(
                search_text=query,
                top=top_k,
                select=["id", "content", "source_file", "page_number", "chunk_id", "product_type", "metadata"]
            )

            search_results = []
            for result in results:
                # Get search score (hybrid search score)
                raw_score = result.get("@search.score", 0.0)

                # Normalize hybrid search score to 0-1 range
                # Hybrid scores typically range from 0-10+, normalize by dividing by 10
                normalized_confidence = min(raw_score / 10.0, 1.0)

                # Filter by minimum confidence
                if normalized_confidence < min_confidence:
                    continue

                # Map index fields to SearchResult model
                source_file = result.get("source_file", "unknown")
                product_type = result.get("product_type", "product")
                
                search_results.append(SearchResult(
                    document_id=result.get("id", "unknown"),
                    content=result.get("content", ""),
                    title=f"{product_type} - {source_file}",  # Construct title from product_type and source
                    section=result.get("chunk_id"),  # Use chunk_id as section
                    confidence=normalized_confidence,
                    source=source_file,
                    url=None  # No URL field in index
                ))

            logger.info(f"Found {len(search_results)} results above confidence threshold")
            return search_results

        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            return []

    async def get_document_by_id(self, document_id: str, section: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve specific document by ID.

        Args:
            document_id: Document identifier
            section: Optional section name

        Returns:
            Document content or None if not found
        """
        try:
            result = self.search_client.get_document(key=document_id)

            # If section specified, filter content
            if section and "sections" in result:
                sections = result.get("sections", {})
                if section in sections:
                    result["content"] = sections[section]

            return result

        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None


class ContentUnderstandingService:
    """Service for Azure AI Foundry RAG Grounding Evaluation."""

    def __init__(self, project_config: Dict[str, str], model_deployment: str):
        """Initialize Azure AI Evaluation client for groundedness checking."""
        self.project_config = project_config
        credential = DefaultAzureCredential()

        # Use Azure AI Evaluation SDK for RAG grounding validation
        # This is purpose-built for preventing hallucinations in RAG systems
        self.evaluator = GroundednessEvaluator(
            model_config={
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "azure_deployment": model_deployment,
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
                "api_key": os.getenv("AZURE_OPENAI_API_KEY")
            }
        )
        logger.info(f"✅ Initialized Azure AI Evaluation (Groundedness) with model: {model_deployment}")

    async def validate_grounding(
        self,
        query: str,
        response: str,
        search_results: List[SearchResult],
        min_confidence: float = 3.0
    ) -> GroundingValidationResult:
        """
        Validate that the response is grounded in source documents using Azure AI Evaluation.

        Args:
            query: User's question
            response: Generated answer to validate
            search_results: Search results from AI Search (used as context)
            min_confidence: Minimum groundedness score (1-5 scale, default 3.0 = moderate)

        Returns:
            Validation result with groundedness score and reasoning
        """
        try:
            # Build context from search results
            context = self._build_context(search_results)

            # Debug logging
            logger.info("="*80)
            logger.info("🔍 AZURE AI EVALUATION - RAG GROUNDEDNESS CHECK")
            logger.info(f"Project: {self.project_config['project_name']}")
            logger.info(f"Query: {query}")
            logger.info(f"Response length: {len(response)} chars")
            logger.info(f"Context length: {len(context)} chars")
            logger.info(f"Search results: {len(search_results)}")
            logger.info(f"Min confidence threshold: {min_confidence}/5.0")
            logger.info("="*80)

            # Call Azure AI Evaluation Groundedness Evaluator
            # This is the proper way to validate RAG grounding
            try:
                eval_result = self.evaluator(
                    query=query,
                    context=context,
                    response=response
                )
                
                # Azure AI Evaluation returns scores on 1-5 scale
                # 5 = Completely grounded, no hallucinations
                # 4 = Mostly grounded with minor issues
                # 3 = Partially grounded
                # 2 = Minimally grounded
                # 1 = Not grounded / hallucinated
                groundedness_score = eval_result.get("groundedness", 0.0)
                reasoning = eval_result.get("reasoning", "No reasoning provided")
                
                logger.info(f"✅ Azure AI Evaluation completed")
                logger.info(f"📊 Groundedness Score: {groundedness_score}/5.0")
                logger.info(f"💭 Reasoning: {reasoning[:200]}...")
                logger.info("="*80)
                
                # Convert 1-5 scale to 0-1 confidence for compatibility
                confidence_normalized = groundedness_score / 5.0
                is_grounded = groundedness_score >= min_confidence
                
                # Extract citations from search results
                citations = [f"{r.source} (Section: {r.section or 'N/A'})" for r in search_results]
                
                # Log evaluation to local JSON file for debugging
                self._log_evaluation(
                    query=query,
                    response=response,
                    groundedness_score=groundedness_score,
                    is_grounded=is_grounded,
                    reasoning=reasoning,
                    citations=citations
                )
                
                return GroundingValidationResult(
                    is_grounded=is_grounded,
                    confidence=confidence_normalized,
                    validated_answer=response if is_grounded else None,
                    citations=citations,
                    reason=reasoning if not is_grounded else f"Grounded with score {groundedness_score}/5.0"
                )
                
            except Exception as api_error:
                logger.error(f"❌ Azure AI Evaluation API call failed")
                logger.error(f"Error type: {type(api_error).__name__}")
                logger.error(f"Error message: {str(api_error)}")
                logger.error(f"Project config: {self.project_config}")
                raise

        except Exception as e:
            logger.error(f"Error validating grounding: {e}")
            return GroundingValidationResult(
                is_grounded=False,
                confidence=0.0,
                reason=f"Validation error: {str(e)}"
            )

    def _log_evaluation(
        self,
        query: str,
        response: str,
        groundedness_score: float,
        is_grounded: bool,
        reasoning: str,
        citations: List[str]
    ):
        """Log evaluation results to local JSON file for debugging."""
        try:
            import json
            from pathlib import Path
            
            # Create evaluations directory in app/copilot/observability
            eval_dir = Path(__file__).parent.parent.parent.parent.parent / "app" / "copilot" / "observability"
            eval_dir.mkdir(parents=True, exist_ok=True)
            
            # Log file with date
            log_file = eval_dir / f"rag_evaluations_{datetime.now().strftime('%Y-%m-%d')}.json"
            
            # Evaluation record
            eval_record = {
                "timestamp": datetime.now().isoformat(),
                "service": "prodinfo_faq",
                "query": query,
                "response_preview": response[:200] + "..." if len(response) > 200 else response,
                "groundedness_score": groundedness_score,
                "is_grounded": is_grounded,
                "confidence_normalized": groundedness_score / 5.0,
                "reasoning": reasoning,
                "citations_count": len(citations),
                "citations": citations[:3]  # Top 3 citations
            }
            
            # Append to JSON file
            try:
                with open(log_file, 'r') as f:
                    evaluations = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                evaluations = []
            
            evaluations.append(eval_record)
            
            with open(log_file, 'w') as f:
                json.dump(evaluations, f, indent=2)
            
            logger.info(f"📝 Evaluation logged to: {log_file}")
            
        except Exception as e:
            logger.warning(f"Failed to log evaluation locally: {e}")

    def _build_context(self, search_results: List[SearchResult]) -> str:
        """Build context string from search results."""
        context_parts = []
        for idx, result in enumerate(search_results, 1):
            context_parts.append(
                f"[Source {idx}: {result.source}]\n"
                f"Title: {result.title}\n"
                f"Section: {result.section or 'N/A'}\n"
                f"Content: {result.content}\n"
                f"Confidence: {result.confidence:.2f}\n"
            )
        return "\n---\n".join(context_parts)


class CosmosDBService:
    """Service for Azure CosmosDB operations."""

    def __init__(self, endpoint: str, database: str, container: str, key: str = None):
        """Initialize CosmosDB client."""
        self.endpoint = endpoint
        self.database_name = database
        self.container_name = container

        # Use key if provided, otherwise use managed identity
        if key:
            self.client = CosmosClient(endpoint, credential=key)
        else:
            credential = DefaultAzureCredential()
            self.client = CosmosClient(endpoint, credential=credential)

        # Get or create database and container
        self.database = self.client.create_database_if_not_exists(id=database)
        self.container = self.database.create_container_if_not_exists(
            id=container,
            partition_key=PartitionKey(path="/customer_id")
        )
        logger.info(f"Initialized CosmosDB: {database}/{container}")

    async def write_ticket(self, ticket: SupportTicket) -> bool:
        """
        Write support ticket to CosmosDB.

        Args:
            ticket: Support ticket to store

        Returns:
            True if successful, False otherwise
        """
        try:
            item = ticket.model_dump()
            item["id"] = ticket.ticket_id
            # Ensure created_at is ISO 8601 timezone-aware
            if isinstance(ticket.created_at, datetime):
                created = ticket.created_at
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
            else:
                created = datetime.now(timezone.utc)

            item["created_at"] = created.isoformat()

            # Use upsert to avoid duplicate ID errors
            self.container.upsert_item(body=item)
            logger.info(f"Created/Updated ticket: {ticket.ticket_id}")
            return True

        except Exception as e:
            logger.error(f"Error writing ticket: {e}")
            return False

    async def read_cache(self, query: str) -> Optional[CachedQuery]:
        """
        Check cache for similar queries.

        Args:
            query: Query to check

        Returns:
            Cached result if found, None otherwise
        """
        try:
            query_hash = self._hash_query(query)

            # Query for cached result
            items = list(self.container.query_items(
                query="SELECT * FROM c WHERE c.query_hash = @hash",
                parameters=[{"name": "@hash", "value": query_hash}],
                enable_cross_partition_query=True
            ))

            if items:
                # Increment hit count
                item = items[0]
                item["hit_count"] = item.get("hit_count", 0) + 1
                self.container.upsert_item(item)

                return CachedQuery(**item)

            return None

        except Exception as e:
            logger.error(f"Error reading cache: {e}")
            return None

    async def write_cache(self, query: str, answer: str, sources: List[str]) -> bool:
        """
        Cache query result.

        Args:
            query: Query string
            answer: Answer to cache
            sources: Source citations

        Returns:
            True if successful, False otherwise
        """
        try:
            query_hash = self._hash_query(query)

            item = {
                "id": query_hash,
                "query_hash": query_hash,
                "query": query,
                "answer": answer,
                "sources": sources,
                # Use timezone-aware UTC timestamp
                "created_at": datetime.now(timezone.utc).isoformat(),
                "hit_count": 1,
                "customer_id": "cache"  # Use "cache" as partition key
            }

            self.container.upsert_item(item)
            logger.info(f"Cached query: {query[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Error writing cache: {e}")
            return False

    def _hash_query(self, query: str) -> str:
        """Generate hash for query caching."""
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]

    def get_next_ticket_id(self) -> str:
        """
        Generate a next ticket id based on current UTC date and the count of tickets created today.

        Format: TKT-YYYYMMDD-NNNNNN where NNNNNN is a zero-padded sequence for the day.

        NOTE: This is a best-effort sequential per-day counter by counting existing tickets for the day.
        In heavy concurrent production scenarios, consider using a dedicated counter service or CosmosDB server-side stored procedure.
        """
        try:
            # Determine today's UTC range
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            tomorrow = today_start + timedelta(days=1)
            start_iso = today_start.isoformat()
            end_iso = tomorrow.isoformat()

            query = "SELECT VALUE COUNT(1) FROM c WHERE c.created_at >= @start AND c.created_at < @end"
            parameters = [
                {"name": "@start", "value": start_iso},
                {"name": "@end", "value": end_iso}
            ]

            items = list(self.container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
            count_today = int(items[0]) if items else 0
            seq = count_today + 1

            prefix = today_start.strftime("%Y%m%d")
            ticket_id = f"TKT-{prefix}-{seq:06d}"
            return ticket_id
        except Exception as e:
            logger.warning(f"Failed to compute next ticket id, falling back to timestamp id: {e}")
            # Fallback to timestamp-based id
            return f"TKT-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
