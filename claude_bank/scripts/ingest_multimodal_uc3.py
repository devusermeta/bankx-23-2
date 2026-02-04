"""
Multimodal ingestion script for UC3 Money Coach documents.
Extracts text and images from Word document, processes with GPT-4o vision, 
and indexes to Azure AI Search with multimodal embeddings.
"""

import os
import sys
import json
import base64
import io
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from docx import Document
from docx.oxml.text.paragraph import CT_P
from docx.oxml.table import CT_Tbl
from docx.table import Table
from docx.text.paragraph import Paragraph
from PIL import Image
import hashlib

# Azure SDK imports
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage, TextContentItem, ImageContentItem, ImageUrl
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_KEY")  # Optional - will use managed identity if not provided
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_CHATGPT_DEPLOYMENT", "gpt-4.1-mini")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME") or os.getenv("AZURE_OPENAI_EMB_DEPLOYMENT", "text-embedding-3-large")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
AZURE_AI_SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT") or os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_AI_SEARCH_KEY = os.getenv("AZURE_AI_SEARCH_KEY") or os.getenv("AZURE_SEARCH_API_KEY")
INDEX_NAME = os.getenv("AZURE_AI_SEARCH_INDEX_UC3_MULTIMODAL", "uc3_docs_multimodal")

# Document path
DOC_PATH = Path(__file__).parent.parent / "data" / "Usecase3_MoneyCoach_Debt-Free to Financial Freedom_EN_V2.docx"


class MultimodalProcessor:
    """Process Word documents with text and images using GPT-4o vision."""
    
    def __init__(self):
        """Initialize Azure clients."""
        from azure.identity import DefaultAzureCredential
        
        # Use API key if provided, otherwise use managed identity
        if AZURE_OPENAI_API_KEY:
            openai_credential = AzureKeyCredential(AZURE_OPENAI_API_KEY)
        else:
            openai_credential = DefaultAzureCredential()
            logger.info("Using managed identity for Azure OpenAI")
        
        self.chat_client = ChatCompletionsClient(
            endpoint=AZURE_OPENAI_ENDPOINT,
            credential=openai_credential
        )
        
        # Use API key if provided, otherwise use managed identity
        if AZURE_AI_SEARCH_KEY:
            search_credential = AzureKeyCredential(AZURE_AI_SEARCH_KEY)
        else:
            search_credential = DefaultAzureCredential()
            logger.info("Using managed identity for Azure AI Search")
        
        self.search_index_client = SearchIndexClient(
            endpoint=AZURE_AI_SEARCH_ENDPOINT,
            credential=search_credential
        )
        self.search_client = None  # Will be initialized after index creation
        
    def extract_images_from_docx(self, doc_path: Path) -> Dict[str, bytes]:
        """Extract all images from Word document with their IDs."""
        images = {}
        doc = Document(doc_path)
        
        # Extract images from document relationships
        for rel in doc.part.rels.values():
            if "image" in rel.target_ref:
                image_id = rel.rId
                image_bytes = rel.target_part.blob
                images[image_id] = image_bytes
                logger.info(f"Extracted image: {image_id}")
                
        return images
    
    def parse_document_structure(self, doc_path: Path) -> List[Dict[str, Any]]:
        """
        Parse Word document into structured chunks with text and image references.
        Returns list of chunks with chapter info, text content, and image IDs.
        """
        doc = Document(doc_path)
        chunks = []
        current_chapter = None
        current_chapter_num = 0
        current_text = []
        current_images = []
        page_counter = 1
        
        for element in doc.element.body:
            # Check if it's a paragraph
            if isinstance(element, CT_P):
                para = Paragraph(element, doc)
                text = para.text.strip()
                
                # Detect chapter headings
                if text and (text.startswith("Chapter") or para.style.name.startswith("Heading")):
                    # Save previous chunk if exists
                    if current_text or current_images:
                        chunks.append({
                            "chapter_number": current_chapter_num,
                            "chapter_title": current_chapter or "Introduction",
                            "page_number": page_counter,
                            "text": "\n".join(current_text),
                            "image_ids": current_images.copy()
                        })
                        current_text = []
                        current_images = []
                        page_counter += 1
                    
                    # Start new chapter
                    if "Chapter" in text:
                        parts = text.split(":", 1)
                        if len(parts) == 2:
                            current_chapter_num = int(parts[0].replace("Chapter", "").strip())
                            current_chapter = parts[1].strip()
                        else:
                            current_chapter_num += 1
                            current_chapter = text
                    else:
                        current_chapter_num += 1
                        current_chapter = text
                    
                    logger.info(f"Found chapter: {current_chapter_num} - {current_chapter}")
                
                elif text:
                    current_text.append(text)
                
                # Check for images in paragraph
                for run in para.runs:
                    if 'graphic' in run.element.xml:
                        # Extract image reference
                        for rel in run.element.xpath('.//a:blip/@r:embed'):
                            current_images.append(rel)
                            logger.info(f"Found image in chapter {current_chapter_num}: {rel}")
        
        # Save final chunk
        if current_text or current_images:
            chunks.append({
                "chapter_number": current_chapter_num,
                "chapter_title": current_chapter or "Conclusion",
                "page_number": page_counter,
                "text": "\n".join(current_text),
                "image_ids": current_images.copy()
            })
        
        logger.info(f"Extracted {len(chunks)} chunks from document")
        return chunks
    
    async def analyze_image_with_vision(self, image_bytes: bytes, context: str = "") -> str:
        """
        Use GPT-4o vision to analyze and describe image.
        
        Args:
            image_bytes: Image data as bytes
            context: Surrounding text context for better understanding
            
        Returns:
            Detailed description of the image
        """
        try:
            # Convert image to base64
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            image_url = f"data:image/jpeg;base64,{image_base64}"
            
            # Create vision prompt
            system_prompt = """You are analyzing images from a financial literacy book called "Debt-Free to Financial Freedom".
Provide detailed descriptions of charts, graphs, worksheets, diagrams, and visual content.
Focus on:
- Data shown in charts/graphs (values, trends, comparisons)
- Structure of worksheets/templates (fields, categories, purposes)
- Key information in infographics
- Visual patterns and relationships
Be specific and thorough so text search can find this content."""

            user_prompt = f"""Analyze this image from the book and provide a detailed description.

Context from surrounding text:
{context[:500] if context else "No context available"}

Describe what you see in detail, including any numbers, labels, categories, or instructions shown."""

            # Call GPT-4o vision
            response = self.chat_client.complete(
                model=AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=[
                        TextContentItem(text=user_prompt),
                        ImageContentItem(image_url=ImageUrl(url=image_url))
                    ])
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            description = response.choices[0].message.content
            logger.info(f"Generated image description: {description[:100]}...")
            return description
            
        except Exception as e:
            logger.error(f"Error analyzing image with vision: {e}")
            return "Image content could not be analyzed"
    
    async def get_embedding(self, text: str) -> List[float]:
        """Get text embedding using text-embedding-3-large."""
        try:
            # Note: Azure OpenAI embeddings API is different from chat completions
            # We'll use the REST API directly
            import aiohttp
            
            # Build URL - remove trailing slash from endpoint if present
            endpoint = AZURE_OPENAI_ENDPOINT.rstrip('/')
            url = f"{endpoint}/openai/deployments/{AZURE_OPENAI_EMBEDDING_DEPLOYMENT}/embeddings?api-version={AZURE_OPENAI_API_VERSION}"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            # Add authentication header
            if AZURE_OPENAI_API_KEY:
                headers["api-key"] = AZURE_OPENAI_API_KEY
            else:
                # For managed identity, we'd need to get a token
                from azure.identity import DefaultAzureCredential
                credential = DefaultAzureCredential()
                token = credential.get_token("https://cognitiveservices.azure.com/.default")
                headers["Authorization"] = f"Bearer {token.token}"
            
            data = {
                "input": text,
                "dimensions": 3072  # text-embedding-3-large supports 3072 dimensions
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=data) as response:
                    result = await response.json()
                    if "data" in result and len(result["data"]) > 0:
                        return result["data"][0]["embedding"]
                    else:
                        logger.error(f"Unexpected embedding response: {result}")
                        return [0.0] * 3072
                        
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return [0.0] * 3072
    
    def create_multimodal_index(self):
        """Create Azure AI Search index with multimodal schema."""
        try:
            # Define index schema
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="content", type=SearchFieldDataType.String),
                SearchableField(name="chapter_title", type=SearchFieldDataType.String),
                SimpleField(name="chapter_number", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
                SimpleField(name="page_number", type=SearchFieldDataType.Int32, filterable=True, sortable=True),
                SearchableField(name="image_descriptions", type=SearchFieldDataType.String),
                SimpleField(name="has_images", type=SearchFieldDataType.Boolean, filterable=True),
                SimpleField(name="image_count", type=SearchFieldDataType.Int32),
                SearchableField(name="chunk_id", type=SearchFieldDataType.String),
                SearchableField(name="topic_tags", type=SearchFieldDataType.String),
                SearchableField(name="metadata", type=SearchFieldDataType.String),
                
                # Vector fields
                SearchField(
                    name="content_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    vector_search_dimensions=3072,
                    vector_search_profile_name="default-vector-profile"
                ),
                SearchField(
                    name="image_vector",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    vector_search_dimensions=3072,
                    vector_search_profile_name="default-vector-profile"
                ),
            ]
            
            # Vector search configuration
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(name="default-algorithm")
                ],
                profiles=[
                    VectorSearchProfile(
                        name="default-vector-profile",
                        algorithm_configuration_name="default-algorithm"
                    )
                ]
            )
            
            # Create index
            index = SearchIndex(
                name=INDEX_NAME,
                fields=fields,
                vector_search=vector_search
            )
            
            logger.info(f"Creating index: {INDEX_NAME}")
            result = self.search_index_client.create_or_update_index(index)
            logger.info(f"✅ Index created successfully: {result.name}")
            
            # Initialize search client
            self.search_client = SearchClient(
                endpoint=AZURE_AI_SEARCH_ENDPOINT,
                index_name=INDEX_NAME,
                credential=AzureKeyCredential(AZURE_AI_SEARCH_KEY)
            )
            
        except Exception as e:
            logger.error(f"Error creating index: {e}")
            raise
    
    async def process_and_index_document(self, doc_path: Path):
        """Main processing pipeline: extract -> analyze -> embed -> index."""
        logger.info(f"Starting multimodal processing of: {doc_path}")
        
        # Step 1: Extract images
        logger.info("Step 1: Extracting images...")
        images = self.extract_images_from_docx(doc_path)
        logger.info(f"Found {len(images)} images")
        
        # Step 2: Parse document structure
        logger.info("Step 2: Parsing document structure...")
        chunks = self.parse_document_structure(doc_path)
        logger.info(f"Parsed {len(chunks)} chunks")
        
        # Step 3: Process each chunk with vision
        logger.info("Step 3: Processing chunks with vision and embeddings...")
        documents = []
        
        for idx, chunk in enumerate(chunks):
            try:
                logger.info(f"Processing chunk {idx + 1}/{len(chunks)}: Chapter {chunk['chapter_number']}")
                
                # Analyze images in this chunk
                image_descriptions = []
                for image_id in chunk["image_ids"]:
                    if image_id in images:
                        logger.info(f"  Analyzing image: {image_id}")
                        description = await self.analyze_image_with_vision(
                            images[image_id],
                            context=chunk["text"][:500]
                        )
                        image_descriptions.append(description)
                    else:
                        logger.warning(f"  Image {image_id} not found in extracted images")
                
                # Combine text and image descriptions
                full_content = chunk["text"]
                if image_descriptions:
                    full_content += "\n\n[Visual Content]\n" + "\n\n".join(image_descriptions)
                
                # Get embeddings
                logger.info(f"  Generating embeddings...")
                content_vector = await self.get_embedding(chunk["text"])
                
                # If has images, create combined embedding for image content
                image_vector = None
                if image_descriptions:
                    combined_image_text = " ".join(image_descriptions)
                    image_vector = await self.get_embedding(combined_image_text)
                else:
                    image_vector = [0.0] * 3072  # Empty vector if no images
                
                # Create document for indexing
                doc_id = hashlib.md5(f"{chunk['chapter_number']}_{chunk['page_number']}_{idx}".encode()).hexdigest()
                
                document = {
                    "id": doc_id,
                    "content": full_content,
                    "chapter_title": chunk["chapter_title"],
                    "chapter_number": chunk["chapter_number"],
                    "page_number": chunk["page_number"],
                    "image_descriptions": "\n\n".join(image_descriptions) if image_descriptions else "",
                    "has_images": len(image_descriptions) > 0,
                    "image_count": len(image_descriptions),
                    "chunk_id": f"ch{chunk['chapter_number']}_p{chunk['page_number']}",
                    "topic_tags": chunk["chapter_title"],
                    "metadata": json.dumps({
                        "source": "Debt-Free to Financial Freedom",
                        "chapter": chunk["chapter_number"],
                        "page": chunk["page_number"],
                        "has_visuals": len(image_descriptions) > 0
                    }),
                    "content_vector": content_vector,
                    "image_vector": image_vector
                }
                
                documents.append(document)
                logger.info(f"  ✅ Chunk processed (text: {len(chunk['text'])} chars, images: {len(image_descriptions)})")
                
            except Exception as e:
                logger.error(f"Error processing chunk {idx}: {e}")
                continue
        
        # Step 4: Upload to Azure AI Search
        logger.info(f"Step 4: Uploading {len(documents)} documents to index...")
        try:
            result = self.search_client.upload_documents(documents=documents)
            succeeded = sum(1 for r in result if r.succeeded)
            logger.info(f"✅ Successfully indexed {succeeded}/{len(documents)} documents")
            
            # Show summary
            logger.info("\n=== Indexing Summary ===")
            logger.info(f"Total chunks: {len(documents)}")
            logger.info(f"Chunks with images: {sum(1 for d in documents if d['has_images'])}")
            logger.info(f"Total images analyzed: {sum(d['image_count'] for d in documents)}")
            logger.info(f"Index name: {INDEX_NAME}")
            
        except Exception as e:
            logger.error(f"Error uploading documents: {e}")
            raise


async def main():
    """Main entry point."""
    logger.info("🚀 Starting Multimodal UC3 Ingestion")
    
    # Validate environment
    required_vars = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_AI_SEARCH_ENDPOINT"
    ]
    
    missing = [var for var in required_vars if not os.getenv(var)]
    if missing:
        logger.error(f"Missing required environment variables: {missing}")
        logger.error("Note: AZURE_OPENAI_KEY and AZURE_AI_SEARCH_KEY are optional if using managed identity")
        sys.exit(1)
    
    # Log configuration
    logger.info(f"Azure OpenAI Endpoint: {AZURE_OPENAI_ENDPOINT}")
    logger.info(f"Chat Deployment: {AZURE_OPENAI_CHAT_DEPLOYMENT}")
    logger.info(f"Embedding Deployment: {AZURE_OPENAI_EMBEDDING_DEPLOYMENT}")
    logger.info(f"Azure AI Search Endpoint: {AZURE_AI_SEARCH_ENDPOINT}")
    logger.info(f"Target Index: {INDEX_NAME}")
    
    # Check document exists
    if not DOC_PATH.exists():
        logger.error(f"Document not found: {DOC_PATH}")
        sys.exit(1)
    
    logger.info(f"Document path: {DOC_PATH}")
    
    # Initialize processor
    processor = MultimodalProcessor()
    
    # Create index
    logger.info("Creating multimodal index...")
    processor.create_multimodal_index()
    
    # Process and index document
    await processor.process_and_index_document(DOC_PATH)
    
    logger.info("✅ Multimodal ingestion complete!")


if __name__ == "__main__":
    asyncio.run(main())
