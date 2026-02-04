"""
UC2 Document Preprocessing Script
Processes product DOCX files and FAQ content for Product Info & FAQ Agent.

Usage:
    python prepdocs_uc2.py [--recreate-index]

Process:
1. Parse DOCX files from data/ folder
2. Split text into semantic chunks
3. Generate vector embeddings
4. Create uc2_docs index in Azure AI Search
5. Upload documents with embeddings
"""

import os
import sys
import logging
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add parent directory to path for shared modules
sys.path.insert(0, str(Path(__file__).parent / "shared"))

from text_splitter import SentenceTextSplitter, Page, Chunk
from embedding_generator import EmbeddingGenerator
from index_manager import IndexManager
from document_processor import DocumentProcessor

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data"
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_AI_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_AI_SEARCH_INDEX_UC2", "uc2_docs")
VECTOR_DIMENSIONS = int(os.getenv("AZURE_OPENAI_EMB_DIMENSIONS", "3072"))

# Product documents to process
PRODUCT_DOCS = [
    "current-account-en.docx",
    "normal-savings-account-en.docx",
    "normal-fixed-account-en.docx",
    "td-bonus-24months-en.docx",
    "td-bonus-36months-en.docx",
]

# Product type mapping (for filterable field)
PRODUCT_TYPE_MAP = {
    "current-account-en.docx": "current-account",
    "normal-savings-account-en.docx": "savings",
    "normal-fixed-account-en.docx": "fixed-deposit",
    "td-bonus-24months-en.docx": "term-deposit-24m",
    "td-bonus-36months-en.docx": "term-deposit-36m",
}


def process_document(
    file_path: Path,
    doc_processor: DocumentProcessor,
    text_splitter: SentenceTextSplitter
) -> List[Chunk]:
    """Process a single document: parse and split into chunks."""
    logger.info(f"Processing document: {file_path.name}")
    
    # Parse DOCX
    pages = doc_processor.parse_docx(str(file_path))
    logger.info(f"  Extracted {len(pages)} pages")
    
    # Split into chunks
    chunks = list(text_splitter.split_pages(pages))
    logger.info(f"  Created {len(chunks)} chunks")
    
    return chunks


def create_search_documents(
    file_path: Path,
    chunks: List[Chunk],
    embeddings: List[List[float]]
) -> List[Dict[str, Any]]:
    """Create search documents with embeddings."""
    documents = []
    source_file = file_path.name
    product_type = PRODUCT_TYPE_MAP.get(source_file, "unknown")
    
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        doc_id = f"{source_file.replace('.', '_')}_chunk_{i}"
        
        document = {
            "id": doc_id,
            "content": chunk.text,
            "content_vector": embedding,
            "source_file": source_file,
            "page_number": chunk.page_num,
            "chunk_id": f"chunk_{i}",
            "product_type": product_type,
            "metadata": json.dumps({
                "token_count": chunk.token_count or 0,
                "chunk_index": i,
                "total_chunks": len(chunks)
            })
        }
        documents.append(document)
    
    return documents


def main(recreate_index: bool = False):
    """Main preprocessing pipeline."""
    logger.info("=" * 80)
    logger.info("UC2 Document Preprocessing - Product Info & FAQ")
    logger.info("=" * 80)
    
    # Validate configuration
    if not AZURE_SEARCH_ENDPOINT:
        logger.error("AZURE_AI_SEARCH_ENDPOINT not configured")
        sys.exit(1)
    
    if not DATA_DIR.exists():
        logger.error(f"Data directory not found: {DATA_DIR}")
        sys.exit(1)
    
    # Initialize services
    logger.info("\n📦 Initializing services...")
    doc_processor = DocumentProcessor()
    text_splitter = SentenceTextSplitter(
        max_tokens_per_section=500,
        max_section_length=1000,
        semantic_overlap_percent=10
    )
    embedding_generator = EmbeddingGenerator()
    index_manager = IndexManager(
        endpoint=AZURE_SEARCH_ENDPOINT,
        api_key=AZURE_SEARCH_KEY
    )
    
    # Create or recreate index
    logger.info(f"\n🔍 Managing index: {INDEX_NAME}")
    if recreate_index and index_manager.index_exists(INDEX_NAME):
        logger.info("  Deleting existing index...")
        index_manager.delete_index(INDEX_NAME)
    
    if not index_manager.index_exists(INDEX_NAME):
        logger.info("  Creating new index...")
        index_manager.create_uc2_index(INDEX_NAME, VECTOR_DIMENSIONS)
    else:
        logger.info("  Index already exists")
    
    # Process all documents
    logger.info("\n📄 Processing documents...")
    all_documents = []
    
    for doc_name in PRODUCT_DOCS:
        doc_path = DATA_DIR / doc_name
        
        if not doc_path.exists():
            logger.warning(f"  ⚠️  Document not found: {doc_name}")
            continue
        
        try:
            # Parse and chunk
            chunks = process_document(doc_path, doc_processor, text_splitter)
            
            # Generate embeddings
            logger.info(f"  Generating embeddings for {len(chunks)} chunks...")
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = embedding_generator.generate_embeddings_batch(
                chunk_texts,
                batch_size=16
            )
            
            # Create search documents
            documents = create_search_documents(doc_path, chunks, embeddings)
            all_documents.extend(documents)
            
            logger.info(f"  ✅ Processed {doc_name}: {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"  ❌ Error processing {doc_name}: {e}", exc_info=True)
            continue
    
    # Upload to index
    if all_documents:
        logger.info(f"\n📤 Uploading {len(all_documents)} documents to index...")
        try:
            index_manager.upload_documents(
                INDEX_NAME,
                all_documents,
                batch_size=100,
                api_key=AZURE_SEARCH_KEY
            )
            logger.info("✅ Upload complete!")
        except Exception as e:
            logger.error(f"❌ Error uploading documents: {e}", exc_info=True)
            sys.exit(1)
    else:
        logger.warning("⚠️  No documents to upload")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Index: {INDEX_NAME}")
    logger.info(f"Total documents indexed: {len(all_documents)}")
    logger.info(f"Source files processed: {len([d for d in PRODUCT_DOCS if (DATA_DIR / d).exists()])}")
    logger.info("=" * 80)
    logger.info("✅ UC2 preprocessing complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Preprocess UC2 documents for Product Info & FAQ Agent"
    )
    parser.add_argument(
        "--recreate-index",
        action="store_true",
        help="Delete and recreate the search index"
    )
    
    args = parser.parse_args()
    main(recreate_index=args.recreate_index)
