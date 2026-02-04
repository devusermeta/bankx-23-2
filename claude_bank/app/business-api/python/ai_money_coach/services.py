"""Business logic for AIMoneyCoach MCP server."""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.ai.evaluation import GroundednessEvaluator
import httpx

from models import MoneyCoachSearchResult, GroundingValidationResult

# Add app directory to path for common imports
workspace_root = Path(__file__).parent.parent.parent.parent.parent
app_dir = workspace_root / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from common.observability import MCPMetrics

logger = logging.getLogger(__name__)

# Initialize metrics instance (will be created once per module)
_metrics_instance = None

def get_metrics() -> MCPMetrics:
    """Get or create metrics instance."""
    global _metrics_instance
    if _metrics_instance is None:
        _metrics_instance = MCPMetrics("ai-money-coach")
    return _metrics_instance


class MoneyCoachAISearchService:
    """Service for Azure AI Search operations on Money Coach document."""

    def __init__(self, endpoint: str, key: Optional[str], index_name: str):
        """Initialize AI Search client."""
        self.endpoint = endpoint
        self.index_name = index_name
        
        # Store OpenAI config for embeddings
        self.openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.openai_key = os.getenv("AZURE_OPENAI_API_KEY")  # Optional - will use managed identity if not set
        # Support both variable names for embedding deployment
        self.embedding_deployment = (
            os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT") or 
            os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT") or 
            "text-embedding-3-large"
        )
        
        # Log configuration status
        logger.info(f"OpenAI Endpoint: {self.openai_endpoint}")
        logger.info(f"OpenAI API Key: {'✓ Set' if self.openai_key else '✗ NOT SET (using managed identity)'}")
        logger.info(f"Embedding Deployment: {self.embedding_deployment}")

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
        logger.info(f"Initialized Money Coach AI Search client for index: {index_name}")
    
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using Azure OpenAI."""
        start_time = time.time()
        metrics = get_metrics()
        
        try:
            if not self.openai_endpoint:
                logger.error("AZURE_OPENAI_ENDPOINT not configured - cannot generate embeddings")
                raise ValueError("AZURE_OPENAI_ENDPOINT not configured")
                
            url = f"{self.openai_endpoint}/openai/deployments/{self.embedding_deployment}/embeddings?api-version=2024-10-21"
            data = {"input": text}
            
            # Use API key if available, otherwise use managed identity
            if self.openai_key:
                headers = {"api-key": self.openai_key, "Content-Type": "application/json"}
                logger.debug(f"Generating embedding with API key (length={len(text)})")
            else:
                # Use managed identity (Azure CLI credentials)
                credential = DefaultAzureCredential()
                token = credential.get_token("https://cognitiveservices.azure.com/.default")
                headers = {"Authorization": f"Bearer {token.token}", "Content-Type": "application/json"}
                logger.debug(f"Generating embedding with managed identity (length={len(text)})")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=data, timeout=30.0)
                response.raise_for_status()
                embedding = response.json()["data"][0]["embedding"]
                logger.info(f"✓ Generated embedding with {len(embedding)} dimensions")
                
                # Track metrics
                duration_ms = (time.time() - start_time) * 1000
                # Estimate tokens (rough: 1 token ≈ 4 chars)
                estimated_tokens = len(text) // 4
                metrics.record_embedding_generation(
                    model=self.embedding_deployment,
                    duration_ms=duration_ms,
                    token_count=estimated_tokens
                )
                
                # Estimate cost (text-embedding-3-large: $0.13 per 1M tokens)
                cost_usd = (estimated_tokens / 1_000_000) * 0.13
                metrics.record_cost(
                    service="azure_openai",
                    operation="embedding",
                    cost_usd=cost_usd
                )
                
                return embedding
        except Exception as e:
            logger.error(f"✗ Error generating embedding: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise  # Re-raise instead of returning empty list

    async def search_money_coach_content(
        self,
        query: str,
        chapter_filter: Optional[int] = None,
        top_k: int = 5
    ) -> List[MoneyCoachSearchResult]:
        """
        Search Money Coach document using vector search.

        Args:
            query: Search query string
            chapter_filter: Optional chapter number to filter (1-12)
            top_k: Number of results to return

        Returns:
            List of search results from the book
        """
        search_start = time.time()
        metrics = get_metrics()
        
        try:
            logger.info(f"Searching Money Coach content: '{query}' (chapter={chapter_filter}, top_k={top_k})")

            # Build filter if chapter specified
            filter_expr = None
            if chapter_filter:
                filter_expr = f"chapter_number eq {chapter_filter}"

            # Generate embedding for vector search
            try:
                query_vector = await self.get_embedding(query)
                
                # Perform hybrid search (text + vector)
                logger.info("✅ Performing hybrid search (text + vector)")
                vector_query = VectorizedQuery(
                    vector=query_vector,
                    k_nearest_neighbors=top_k,
                    fields="content_vector"
                )
                results = self.search_client.search(
                    search_text=query,
                    vector_queries=[vector_query],
                    top=top_k,
                    select=["id", "content", "chapter_number", "chapter_title", "page_number", "chunk_id", "topic_tags", "metadata"],
                    filter=filter_expr
                )
            except Exception as embed_error:
                logger.error(f"❌ Embedding generation failed: {embed_error}")
                logger.warning("⚠️  Falling back to text-only search")
                results = self.search_client.search(
                    search_text=query,
                    top=top_k,
                    select=["id", "content", "chapter_number", "chapter_title", "page_number", "chunk_id", "topic_tags", "metadata"],
                    filter=filter_expr
                )

            search_results = []
            for result in results:
                # Get search score (hybrid search)
                raw_score = result.get("@search.score", 0.0)
                normalized_confidence = min(raw_score / 10.0, 1.0)

                search_results.append(MoneyCoachSearchResult(
                    chapter=result.get("chapter_number", 0),
                    chapter_title=result.get("chapter_title", ""),
                    content=result.get("content", ""),
                    confidence=normalized_confidence,
                    page=result.get("page_number")
                ))

            logger.info(f"✅ Found {len(search_results)} results from Money Coach book")
            if search_results:
                logger.info(f"✅ Top result: Chapter {search_results[0].chapter}: {search_results[0].chapter_title}")
                logger.info(f"✅ Content preview: {search_results[0].content[:150]}...")
            
            # Track search metrics
            duration_ms = (time.time() - search_start) * 1000
            metrics.record_search_query(
                index_name=self.index_name,
                duration_ms=duration_ms,
                result_count=len(search_results)
            )
            
            # Track Azure AI Search cost (estimate: $5 per 1000 queries)
            metrics.record_cost(
                service="azure_ai_search",
                operation="hybrid_search",
                cost_usd=0.005
            )
            
            return search_results

        except Exception as e:
            logger.error(f"Error searching Money Coach content: {e}")
            return []


class MoneyCoachContentUnderstandingService:
    """Service for Azure AI Evaluation - Money Coach specific groundedness validation."""

    def __init__(self, project_config: Dict[str, str], model_deployment: str):
        """
        Initialize GroundednessEvaluator for Money Coach RAG validation.
        
        Args:
            project_config: Azure AI project configuration dict
            model_deployment: Azure OpenAI model deployment name
        """
        self.project_config = project_config
        self.model_deployment = model_deployment
        
        # Initialize GroundednessEvaluator with Azure OpenAI configuration
        self.evaluator = GroundednessEvaluator(
            model_config={
                "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
                "azure_deployment": model_deployment,
                "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
                "api_key": os.getenv("AZURE_OPENAI_API_KEY")
            }
        )
        logger.info(f"Initialized Money Coach Groundedness Evaluator with model: {model_deployment}")

    async def validate_grounding(
        self,
        query: str,
        response: str,
        search_results: List[MoneyCoachSearchResult],
        min_confidence: float = 4.0
    ) -> GroundingValidationResult:
        """
        Validate that the financial advice is 100% grounded in the book using Azure AI Evaluation.

        This is CRITICAL for UC3 - ensures we NEVER provide generic financial advice
        that's not from the "Debt-Free to Financial Freedom" book.

        Args:
            query: User's question
            response: Generated answer to validate
            search_results: Search results from AI Search (context)
            min_confidence: Minimum groundedness score (1-5 scale, default 4.0 for strict book grounding)

        Returns:
            Validation result with groundedness score and reasoning
        """
        try:
            # Build context from search results
            context = self._build_context(search_results)

            # Call GroundednessEvaluator
            eval_result = self.evaluator(
                query=query,
                context=context,
                response=response
            )

            # Extract groundedness score (1-5 scale)
            groundedness_score = eval_result.get("groundedness", 0.0)
            is_grounded = groundedness_score >= min_confidence

            # Log evaluation for observability
            self._log_evaluation(
                query=query,
                response=response,
                context=context,
                groundedness_score=groundedness_score,
                is_grounded=is_grounded,
                reasoning=eval_result.get("gpt_groundedness_reason", ""),
                min_confidence=min_confidence
            )

            # Extract chapter references from search results
            chapter_references = [
                f"Chapter {result.chapter}: {result.chapter_title}"
                for result in search_results
            ]

            return GroundingValidationResult(
                is_grounded=is_grounded,
                confidence=groundedness_score / 5.0,  # Convert to 0-1 scale for compatibility
                validated_answer=response if is_grounded else None,
                chapter_references=chapter_references,
                reason=eval_result.get("gpt_groundedness_reason") if not is_grounded else None,
                contains_non_book_content=not is_grounded
            )

        except Exception as e:
            logger.error(f"Error validating grounding: {e}")
            return GroundingValidationResult(
                is_grounded=False,
                confidence=0.0,
                reason=f"Validation error: {str(e)}",
                contains_non_book_content=False
            )

    def _log_evaluation(
        self,
        query: str,
        response: str,
        context: str,
        groundedness_score: float,
        is_grounded: bool,
        reasoning: str,
        min_confidence: float
    ):
        """Log evaluation results to local JSON file for observability."""
        try:
            log_dir = Path(__file__).parent.parent.parent.parent / "copilot" / "observability"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / f"rag_evaluations_{datetime.now().strftime('%Y-%m-%d')}.json"
            
            evaluation_entry = {
                "timestamp": datetime.now().isoformat(),
                "service": "ai_money_coach",
                "project": self.project_config.get("project_name", "unknown"),
                "query": query,
                "response": response,
                "context_preview": context[:500] + "..." if len(context) > 500 else context,
                "groundedness_score": groundedness_score,
                "min_confidence": min_confidence,
                "is_grounded": is_grounded,
                "reasoning": reasoning
            }
            
            # Append to log file
            existing_logs = []
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    existing_logs = json.load(f)
            
            existing_logs.append(evaluation_entry)
            
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(existing_logs, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Logged evaluation to {log_file}")
            
        except Exception as e:
            logger.error(f"Failed to log evaluation: {e}")

    def _build_context(self, search_results: List[MoneyCoachSearchResult]) -> str:
        """Build context string from search results."""
        context_parts = []
        for idx, result in enumerate(search_results, 1):
            context_parts.append(
                f"[Chapter {result.chapter}: {result.chapter_title}]\n"
                f"Page: {result.page or 'N/A'}\n"
                f"Content: {result.content}\n"
                f"Confidence: {result.confidence:.2f}\n"
            )
        return "\n---\n".join(context_parts)
