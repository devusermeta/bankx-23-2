"""
UC3 Document Preprocessing Script
Processes Money Coach book for AI Money Coach Agent.

Usage:
    python prepdocs_uc3.py [--recreate-index]

Process:
1. Parse Money Coach DOCX file
2. Detect chapter boundaries
3. Split into semantic chunks preserving chapter context
4. Generate vector embeddings
5. Create uc3_docs index in Azure AI Search
6. Upload documents with chapter metadata
"""

import os
import sys
import logging
import argparse
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
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
MONEY_COACH_FILE = "Usecase3_MoneyCoach_Debt-Free to Financial Freedom_EN_V2.docx"
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_AI_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_AI_SEARCH_KEY")
INDEX_NAME = os.getenv("AZURE_AI_SEARCH_INDEX_UC3", "uc3_docs")
VECTOR_DIMENSIONS = int(os.getenv("AZURE_OPENAI_EMB_DIMENSIONS", "3072"))

# Chapter information (from UC3 spec)
CHAPTER_INFO = {
    1: {"title": "Debt — The Big Lesson Schools Never Teach", "tags": ["debt", "education", "awareness"]},
    2: {"title": "The Real Meaning of Debt", "tags": ["debt", "concepts", "understanding"]},
    3: {"title": "The Financially Ill", "tags": ["financial-health", "diagnosis", "symptoms"]},
    4: {"title": "Money Problems Must Be Solved with Financial Knowledge", "tags": ["knowledge", "education", "problem-solving"]},
    5: {"title": "You Can Be Broke, But Don't Be Mentally Poor", "tags": ["mindset", "psychology", "mental-health"]},
    6: {"title": "Five Steps to Debt-Free Living", "tags": ["debt", "strategy", "action-plan", "repayment"]},
    7: {"title": "The Strong Medicine Plan (Debt Detox)", "tags": ["debt", "crisis", "emergency", "critical"]},
    8: {"title": "Even in Debt, You Can Be Rich", "tags": ["debt", "good-debt", "bad-debt", "investment"]},
    9: {"title": "You Can Get Rich Without Money", "tags": ["income", "side-business", "earning", "entrepreneurship"]},
    10: {"title": "Financial Intelligence Is the Answer", "tags": ["intelligence", "learning", "skills", "capability"]},
    11: {"title": "Sufficiency Leads to a Sufficient Life", "tags": ["sufficiency", "moderation", "philosophy", "happiness"]},
    12: {"title": "Freedom Beyond Money", "tags": ["freedom", "purpose", "life-satisfaction", "wealth"]},
}


def detect_chapters_enhanced(text: str, doc_processor: DocumentProcessor) -> List[Tuple[int, str, int, int]]:
    """
    Detect chapter boundaries with start and end positions.
    
    Returns:
        List of (chapter_num, title, start_pos, end_pos)
    """
    chapters_detected = doc_processor.detect_chapters(text)
    
    if not chapters_detected:
        logger.warning("No chapters detected automatically, using known chapter titles")
        # Fallback: search for known chapter titles
        chapters_detected = []
        for chap_num, chap_info in CHAPTER_INFO.items():
            title = chap_info["title"]
            # Search for title in text
            pattern = re.escape(title[:30])  # Use first 30 chars
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                chapters_detected.append((chap_num, title, match.start()))
    
    # Sort by position
    chapters_detected.sort(key=lambda x: x[2])
    
    # Add end positions
    chapters_with_ranges = []
    for i, (chap_num, title, start_pos) in enumerate(chapters_detected):
        if i < len(chapters_detected) - 1:
            end_pos = chapters_detected[i + 1][2]
        else:
            end_pos = len(text)
        chapters_with_ranges.append((chap_num, title, start_pos, end_pos))
    
    return chapters_with_ranges


def split_chapters_into_chunks(
    chapters: List[Tuple[int, str, int, int]],
    full_text: str,
    text_splitter: SentenceTextSplitter
) -> List[Tuple[int, str, Chunk]]:
    """
    Split each chapter into semantic chunks.
    
    Returns:
        List of (chapter_num, chapter_title, chunk)
    """
    all_chunks = []
    
    for chap_num, chap_title, start_pos, end_pos in chapters:
        chapter_text = full_text[start_pos:end_pos]
        logger.info(f"  Chapter {chap_num}: {chap_title}")
        logger.info(f"    Text length: {len(chapter_text)} characters")
        
        # Create Page object for this chapter
        page = Page(page_num=chap_num, text=chapter_text, offset=0)
        
        # Split into chunks
        chunks = list(text_splitter.split_pages([page]))
        logger.info(f"    Created {len(chunks)} chunks")
        
        for chunk in chunks:
            all_chunks.append((chap_num, chap_title, chunk))
    
    return all_chunks


def create_search_documents(
    chapter_chunks: List[Tuple[int, str, Chunk]],
    embeddings: List[List[float]]
) -> List[Dict[str, Any]]:
    """Create search documents with chapter metadata and embeddings."""
    documents = []
    
    for i, ((chap_num, chap_title, chunk), embedding) in enumerate(zip(chapter_chunks, embeddings)):
        doc_id = f"chapter_{chap_num}_chunk_{i}"
        
        # Get topic tags for this chapter
        chapter_info = CHAPTER_INFO.get(chap_num, {})
        topic_tags = chapter_info.get("tags", [])
        
        # Convert topic_tags list to comma-separated string for Azure Search
        if not topic_tags or not isinstance(topic_tags, list):
            topic_tags_str = "general"
        else:
            topic_tags_str = ", ".join(topic_tags)
        
        document = {
            "id": doc_id,
            "content": chunk.text,
            "content_vector": embedding,
            "chapter_number": chap_num,
            "chapter_title": chap_title,
            "page_number": chunk.page_num or 0,  # Ensure not None
            "chunk_id": f"chunk_{i}",
            "topic_tags": topic_tags_str,
            "metadata": json.dumps({
                "token_count": chunk.token_count or 0,
                "chunk_index": i,
                "source_book": "Debt-Free to Financial Freedom"
            })
        }
        documents.append(document)
    
    return documents


def main(recreate_index: bool = False):
    """Main preprocessing pipeline."""
    logger.info("=" * 80)
    logger.info("UC3 Document Preprocessing - AI Money Coach")
    logger.info("=" * 80)
    
    # Validate configuration
    if not AZURE_SEARCH_ENDPOINT:
        logger.error("AZURE_AI_SEARCH_ENDPOINT not configured")
        sys.exit(1)
    
    doc_path = DATA_DIR / MONEY_COACH_FILE
    if not doc_path.exists():
        logger.error(f"Money Coach file not found: {doc_path}")
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
        index_manager.create_uc3_index(INDEX_NAME, VECTOR_DIMENSIONS)
    else:
        logger.info("  Index already exists")
    
    # Parse document
    logger.info(f"\n📖 Parsing Money Coach book...")
    full_text = doc_processor.parse_docx_as_single_document(str(doc_path))
    logger.info(f"  Extracted {len(full_text)} characters")
    
    # Detect chapters
    logger.info("\n📑 Detecting chapters...")
    chapters = detect_chapters_enhanced(full_text, doc_processor)
    logger.info(f"  Found {len(chapters)} chapters")
    
    # Split chapters into chunks
    logger.info("\n✂️  Splitting chapters into semantic chunks...")
    chapter_chunks = split_chapters_into_chunks(chapters, full_text, text_splitter)
    logger.info(f"  Total chunks: {len(chapter_chunks)}")
    
    # Generate embeddings
    logger.info(f"\n🧮 Generating embeddings for {len(chapter_chunks)} chunks...")
    chunk_texts = [chunk.text for _, _, chunk in chapter_chunks]
    embeddings = embedding_generator.generate_embeddings_batch(
        chunk_texts,
        batch_size=16
    )
    
    # Create search documents
    logger.info("\n📝 Creating search documents...")
    documents = create_search_documents(chapter_chunks, embeddings)
    logger.info(f"  Created {len(documents)} documents")
    
    # Upload to index
    logger.info(f"\n📤 Uploading {len(documents)} documents to index...")
    try:
        index_manager.upload_documents(
            INDEX_NAME,
            documents,
            batch_size=100,
            api_key=AZURE_SEARCH_KEY
        )
        logger.info("✅ Upload complete!")
    except Exception as e:
        logger.error(f"❌ Error uploading documents: {e}", exc_info=True)
        sys.exit(1)
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("SUMMARY")
    logger.info("=" * 80)
    logger.info(f"Index: {INDEX_NAME}")
    logger.info(f"Total documents indexed: {len(documents)}")
    logger.info(f"Chapters processed: {len(chapters)}")
    logger.info("Chapter breakdown:")
    for chap_num, chap_title, _, _ in chapters:
        chapter_docs = [d for d in documents if d["chapter_number"] == chap_num]
        logger.info(f"  Chapter {chap_num}: {len(chapter_docs)} chunks - {chap_title}")
    logger.info("=" * 80)
    logger.info("✅ UC3 preprocessing complete!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Preprocess UC3 Money Coach book for AI Money Coach Agent"
    )
    parser.add_argument(
        "--recreate-index",
        action="store_true",
        help="Delete and recreate the search index"
    )
    
    args = parser.parse_args()
    main(recreate_index=args.recreate_index)
