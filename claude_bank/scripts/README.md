# Document Preprocessing Scripts for UC2 & UC3

This directory contains scripts to preprocess documents and create Azure AI Search indexes for UC2 (Product Info & FAQ) and UC3 (AI Money Coach).

## Prerequisites

Install required packages:
```bash
pip install azure-search-documents azure-identity openai tiktoken python-docx python-dotenv tenacity
```

## Configuration

Ensure these environment variables are set in `.env`:

```env
# Azure AI Search
AZURE_AI_SEARCH_ENDPOINT=https://your-search.search.windows.net
AZURE_AI_SEARCH_KEY=your-search-key
AZURE_AI_SEARCH_INDEX_UC2=uc2_docs
AZURE_AI_SEARCH_INDEX_UC3=uc3_docs

# Azure OpenAI (for embeddings)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_EMB_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_EMB_DIMENSIONS=3072
AZURE_OPENAI_API_VERSION=2024-10-21
```

## Usage

### UC2: Product Info & FAQ

Process product DOCX files and create `uc2_docs` index:

```bash
# First-time setup (creates index)
python scripts/prepdocs_uc2.py

# Recreate index (deletes and recreates)
python scripts/prepdocs_uc2.py --recreate-index
```

**Documents processed:**
- `current-account-en.docx`
- `normal-savings-account-en.docx`
- `normal-fixed-account-en.docx`
- `td-bonus-24months-en.docx`
- `td-bonus-36months-en.docx`

**Index schema:**
- `id`: Unique document ID
- `content`: Searchable text
- `content_vector`: 3072-dimensional embedding
- `source_file`: Source document name
- `page_number`: Page number
- `chunk_id`: Chunk identifier
- `product_type`: Product category (filterable)
- `metadata`: JSON metadata

### UC3: AI Money Coach

Process Money Coach book and create `uc3_docs` index:

```bash
# First-time setup (creates index)
python scripts/prepdocs_uc3.py

# Recreate index (deletes and recreates)
python scripts/prepdocs_uc3.py --recreate-index
```

**Document processed:**
- `Usecase3_MoneyCoach_Debt-Free to Financial Freedom_EN_V2.docx`

**Index schema:**
- `id`: Unique document ID
- `content`: Searchable text
- `content_vector`: 3072-dimensional embedding
- `chapter_number`: Chapter number (1-12, filterable)
- `chapter_title`: Chapter title
- `page_number`: Page number
- `chunk_id`: Chunk identifier
- `topic_tags`: Collection of topic tags (debt, savings, etc.)
- `metadata`: JSON metadata

## Shared Modules

### `shared/text_splitter.py`
Semantic text chunking based on Azure demo pattern:
- **SentenceTextSplitter**: Respects sentence boundaries, 500 tokens max
- **Semantic overlap**: 10% overlap between chunks for better context
- **Recursive splitting**: Handles oversized spans intelligently

### `shared/embedding_generator.py`
Azure OpenAI embedding generation:
- Batch processing (16 texts per batch)
- Automatic retry on failures
- Supports managed identity or API key

### `shared/index_manager.py`
Azure AI Search index management:
- Create UC2/UC3 indexes with proper schemas
- Vector search configuration (HNSW algorithm)
- Semantic search support
- Batch document upload

### `shared/document_processor.py`
DOCX parsing:
- Extract text from Word documents
- Preserve tables and formatting
- Chapter detection for structured documents

## Processing Pipeline

### UC2 Pipeline
```
DOCX Files → Parse → Semantic Chunking → Generate Embeddings → Upload to uc2_docs
```

### UC3 Pipeline
```
Book DOCX → Parse → Detect Chapters → Semantic Chunking → Generate Embeddings → Upload to uc3_docs
```

## Verification

After running preprocessing scripts:

1. **Check index exists:**
   ```bash
   # Visit Azure Portal → Search Service → Indexes
   # You should see: uc2_docs and uc3_docs
   ```

2. **Test search:**
   ```bash
   # Use Azure Portal Search Explorer or run MCP servers
   ```

3. **Start MCP servers:**
   ```bash
   # UC2
   cd app/business-api/python/prodinfo_faq
   python main.py

   # UC3
   cd app/business-api/python/ai_money_coach
   python main.py
   ```

## Troubleshooting

### Import errors
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Authentication errors
- Check API keys in `.env`
- Or use Azure CLI login for managed identity: `az login`

### No chapters detected (UC3)
- Check DOCX file has clear chapter headings
- Script will fallback to known chapter titles from spec

### Embedding API rate limits
- Script uses batch processing with retry logic
- Adjust `batch_size` parameter if needed

## Output Example

```
================================================================================
UC2 Document Preprocessing - Product Info & FAQ
================================================================================

📦 Initializing services...
🔍 Managing index: uc2_docs
  Creating new index...
  ✅ Successfully created/updated index: uc2_docs

📄 Processing documents...
Processing document: current-account-en.docx
  Extracted 3 pages
  Created 12 chunks
  Generating embeddings for 12 chunks...
  ✅ Processed current-account-en.docx: 12 documents

📤 Uploading 58 documents to index...
Batch 1/1: Uploaded 58/58 documents
✅ Upload complete!

================================================================================
SUMMARY
================================================================================
Index: uc2_docs
Total documents indexed: 58
Source files processed: 5
================================================================================
✅ UC2 preprocessing complete!
```

## Next Steps

After successful preprocessing:

1. ✅ Indexes created (`uc2_docs`, `uc3_docs`)
2. ✅ Documents uploaded with embeddings
3. 🔄 Start MCP servers (they auto-connect to indexes)
4. 🚀 Test agents with example questions from `questions_uc2_uc3.md`
