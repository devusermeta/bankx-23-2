"""
Embedding generator using Azure OpenAI.
Generates vector embeddings for text chunks.
"""

import os
import logging
from typing import List, Optional
from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings using Azure OpenAI."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        api_version: Optional[str] = None,
        deployment: Optional[str] = None,
        dimensions: Optional[int] = None
    ):
        """
        Initialize embedding generator.
        
        Args:
            endpoint: Azure OpenAI endpoint
            api_key: API key (if None, uses DefaultAzureCredential)
            api_version: API version
            deployment: Deployment name
            dimensions: Embedding dimensions
        """
        self.endpoint = endpoint or os.getenv("AZURE_OPENAI_ENDPOINT")
        self.api_version = api_version or os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
        self.deployment = deployment or os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT", "text-embedding-3-large")
        self.dimensions = dimensions or int(os.getenv("AZURE_OPENAI_EMB_DIMENSIONS", "3072"))
        
        # Initialize client
        if api_key:
            self.client = AzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=api_key,
                api_version=self.api_version
            )
        else:
            # Try with API key from env
            api_key = os.getenv("AZURE_OPENAI_API_KEY")
            if api_key:
                self.client = AzureOpenAI(
                    azure_endpoint=self.endpoint,
                    api_key=api_key,
                    api_version=self.api_version
                )
            else:
                # Use managed identity
                from azure.identity import DefaultAzureCredential, get_bearer_token_provider
                credential = DefaultAzureCredential()
                token_provider = get_bearer_token_provider(
                    credential,
                    "https://cognitiveservices.azure.com/.default"
                )
                self.client = AzureOpenAI(
                    azure_endpoint=self.endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version=self.api_version
                )
        
        logger.info(f"Initialized EmbeddingGenerator with deployment: {self.deployment}, dimensions: {self.dimensions}")

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.deployment,
                dimensions=self.dimensions
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def generate_embeddings_batch(
        self,
        texts: List[str],
        batch_size: int = 16
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"Processing embedding batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
            
            try:
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.deployment,
                    dimensions=self.dimensions
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Error in batch {i//batch_size + 1}: {e}")
                # Fall back to individual generation for this batch
                for text in batch:
                    try:
                        emb = self.generate_embedding(text)
                        embeddings.append(emb)
                    except Exception as e2:
                        logger.error(f"Error generating embedding for text: {e2}")
                        # Use zero vector as fallback
                        embeddings.append([0.0] * self.dimensions)
        
        return embeddings
