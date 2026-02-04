"""
Azure AI Search index manager.
Creates and manages search indexes with vector support.
"""

import logging
from typing import List, Dict, Any, Optional
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
)
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)


class IndexManager:
    """Manages Azure AI Search indexes."""

    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        use_managed_identity: bool = False
    ):
        """
        Initialize index manager.
        
        Args:
            endpoint: Azure Search endpoint
            api_key: API key (optional if using managed identity)
            use_managed_identity: Whether to use managed identity
        """
        self.endpoint = endpoint
        
        if use_managed_identity or not api_key:
            credential = DefaultAzureCredential()
        else:
            credential = AzureKeyCredential(api_key)
        
        self.index_client = SearchIndexClient(
            endpoint=endpoint,
            credential=credential
        )
        logger.info(f"Initialized IndexManager for endpoint: {endpoint}")

    def create_uc2_index(self, index_name: str, vector_dimensions: int = 3072) -> SearchIndex:
        """
        Create index for UC2 (Product Info & FAQ).
        
        Schema:
        - id: Document chunk ID
        - content: Searchable text content
        - content_vector: Vector embedding
        - source_file: Source document name
        - page_number: Page number in source
        - chunk_id: Unique chunk identifier
        - product_type: Product category (current-account, savings, etc.)
        - metadata: Additional JSON metadata
        """
        logger.info(f"Creating UC2 index: {index_name}")

        # Define fields
        fields = [
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True
            ),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=vector_dimensions,
                vector_search_profile_name="default-vector-profile"
            ),
            SimpleField(
                name="source_file",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SimpleField(
                name="page_number",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="chunk_id",
                type=SearchFieldDataType.String,
                filterable=True
            ),
            SimpleField(
                name="product_type",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SimpleField(
                name="metadata",
                type=SearchFieldDataType.String,
                filterable=False
            )
        ]

        # Vector search configuration
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="default-vector-profile",
                    algorithm_configuration_name="hnsw-algorithm"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(name="hnsw-algorithm")
            ]
        )

        # Semantic search configuration (optional but recommended)
        semantic_config = SemanticConfiguration(
            name="default-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="source_file"),
                content_fields=[SemanticField(field_name="content")]
            )
        )
        semantic_search = SemanticSearch(configurations=[semantic_config])

        # Create index
        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )

        try:
            result = self.index_client.create_or_update_index(index)
            logger.info(f"✅ Successfully created/updated index: {index_name}")
            return result
        except Exception as e:
            logger.error(f"Error creating index {index_name}: {e}")
            raise

    def create_uc3_index(self, index_name: str, vector_dimensions: int = 3072) -> SearchIndex:
        """
        Create index for UC3 (AI Money Coach).
        
        Schema:
        - id: Document chunk ID
        - content: Searchable text content
        - content_vector: Vector embedding
        - chapter_number: Chapter number (1-12)
        - chapter_title: Chapter title
        - page_number: Page number in source
        - chunk_id: Unique chunk identifier
        - topic_tags: Collection of topic tags (debt, savings, mindset, etc.)
        - metadata: Additional JSON metadata
        """
        logger.info(f"Creating UC3 index: {index_name}")

        # Define fields
        fields = [
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True
            ),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=vector_dimensions,
                vector_search_profile_name="default-vector-profile"
            ),
            SimpleField(
                name="chapter_number",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True,
                facetable=True
            ),
            SearchableField(
                name="chapter_title",
                type=SearchFieldDataType.String,
                searchable=True,
                filterable=True
            ),
            SimpleField(
                name="page_number",
                type=SearchFieldDataType.Int32,
                filterable=True,
                sortable=True
            ),
            SimpleField(
                name="chunk_id",
                type=SearchFieldDataType.String,
                filterable=True
            ),
            SearchableField(
                name="topic_tags",
                type=SearchFieldDataType.String,
                searchable=True,
                filterable=True
            ),
            SimpleField(
                name="metadata",
                type=SearchFieldDataType.String,
                filterable=False
            )
        ]

        # Vector search configuration
        vector_search = VectorSearch(
            profiles=[
                VectorSearchProfile(
                    name="default-vector-profile",
                    algorithm_configuration_name="hnsw-algorithm"
                )
            ],
            algorithms=[
                HnswAlgorithmConfiguration(name="hnsw-algorithm")
            ]
        )

        # Semantic search configuration
        semantic_config = SemanticConfiguration(
            name="default-semantic-config",
            prioritized_fields=SemanticPrioritizedFields(
                title_field=SemanticField(field_name="chapter_title"),
                content_fields=[SemanticField(field_name="content")]
            )
        )
        semantic_search = SemanticSearch(configurations=[semantic_config])

        # Create index
        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=semantic_search
        )

        try:
            result = self.index_client.create_or_update_index(index)
            logger.info(f"✅ Successfully created/updated index: {index_name}")
            return result
        except Exception as e:
            logger.error(f"Error creating index {index_name}: {e}")
            raise

    def delete_index(self, index_name: str):
        """Delete an index."""
        try:
            self.index_client.delete_index(index_name)
            logger.info(f"Deleted index: {index_name}")
        except Exception as e:
            logger.error(f"Error deleting index {index_name}: {e}")
            raise

    def index_exists(self, index_name: str) -> bool:
        """Check if an index exists."""
        try:
            self.index_client.get_index(index_name)
            return True
        except:
            return False

    def get_search_client(self, index_name: str, api_key: Optional[str] = None) -> SearchClient:
        """Get a SearchClient for uploading documents."""
        if api_key:
            credential = AzureKeyCredential(api_key)
        else:
            credential = DefaultAzureCredential()
        
        return SearchClient(
            endpoint=self.endpoint,
            index_name=index_name,
            credential=credential
        )

    def upload_documents(
        self,
        index_name: str,
        documents: List[Dict[str, Any]],
        batch_size: int = 100,
        api_key: Optional[str] = None
    ):
        """
        Upload documents to an index in batches.
        
        Args:
            index_name: Name of the index
            documents: List of document dictionaries
            batch_size: Number of documents per batch
            api_key: Optional API key
        """
        search_client = self.get_search_client(index_name, api_key)
        
        total_docs = len(documents)
        logger.info(f"Uploading {total_docs} documents to index {index_name}...")

        for i in range(0, total_docs, batch_size):
            batch = documents[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_docs - 1) // batch_size + 1
            
            try:
                result = search_client.upload_documents(documents=batch)
                succeeded = sum(1 for r in result if r.succeeded)
                logger.info(f"Batch {batch_num}/{total_batches}: Uploaded {succeeded}/{len(batch)} documents")
            except Exception as e:
                logger.error(f"Error uploading batch {batch_num}: {e}")
                raise

        logger.info(f"✅ Successfully uploaded {total_docs} documents to {index_name}")
