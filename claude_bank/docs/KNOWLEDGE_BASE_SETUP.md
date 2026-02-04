# Knowledge Base Setup & Indexing Guide

Complete guide for setting up and indexing knowledge bases for UC2 (Product Info & FAQ) and UC3 (AI Money Coach).

**Last Updated**: November 7, 2025
**Status**: Implementation Guide

---

## Table of Contents

1. [Overview](#overview)
2. [Knowledge Base Files](#knowledge-base-files)
3. [Azure AI Search Setup](#azure-ai-search-setup)
4. [UC2 Indexing (Product Info & FAQ)](#uc2-indexing-product-info--faq)
5. [UC3 Indexing (Money Coach)](#uc3-indexing-money-coach)
6. [Indexing Scripts](#indexing-scripts)
7. [Validation & Testing](#validation--testing)
8. [Maintenance](#maintenance)

---

## Overview

The BankX Multi-Agent system uses RAG (Retrieval-Augmented Generation) for UC2 and UC3. This requires:
1. Knowledge base documents stored in accessible location
2. Azure AI Search service with vector search enabled
3. Documents indexed with embeddings
4. Semantic ranking configured

**Architecture**:
```
Knowledge Base Files (PDF/HTML)
    ↓
Document Processing & Chunking
    ↓
Embedding Generation (OpenAI ada-002)
    ↓
Azure AI Search Index
    ↓
MCP Services (UC2/UC3) query via RAG
```

---

## Knowledge Base Files

### Directory Structure

```
/home/user/claude_bank/
└── knowledge-bases/
    ├── uc2-product-info/
    │   ├── current-account-en.pdf
    │   ├── normal-savings-account-en.pdf
    │   ├── normal-fixed-account-en.pdf
    │   ├── td-bonus-24months-en.pdf
    │   ├── td-bonus-36months-en.pdf
    │   └── faq.html
    └── uc3-money-coach/
        └── debt-free-to-financial-freedom.pdf
```

### UC2: Product Info & FAQ Files

| File | Description | Pages | Status |
|------|-------------|-------|--------|
| `current-account-en.pdf` | Current Account features, fees, terms | ~10 | 📄 To be added |
| `normal-savings-account-en.pdf` | Savings Account information | ~12 | 📄 To be added |
| `normal-fixed-account-en.pdf` | Fixed Deposit details | ~15 | 📄 To be added |
| `td-bonus-24months-en.pdf` | 24-month Time Deposit Bonus | ~8 | 📄 To be added |
| `td-bonus-36months-en.pdf` | 36-month Time Deposit Bonus | ~8 | 📄 To be added |
| `faq.html` | FAQ from website | ~50 Q&As | 📄 To be added |

**Source**: https://www.scb.co.th/en/personal-banking/faq/deposit-faq.html

### UC3: Money Coach Document

| File | Description | Chapters | Status |
|------|-------------|----------|--------|
| `debt-free-to-financial-freedom.pdf` | Complete financial wellness guide | 12 | 📄 To be added |

**Chapters**:
1. Debt — The Big Lesson Schools Never Teach
2. The Real Meaning of Debt
3. The Financially Ill
4. Money Problems Must Be Solved with Financial Knowledge
5. You Can Be Broke, But Don't Be Mentally Poor
6. Five Steps to Debt-Free Living
7. The Strong Medicine Plan (Debt Detox)
8. Even in Debt, You Can Be Rich
9. You Can Get Rich Without Money
10. Financial Intelligence Is the Answer
11. Sufficiency Leads to a Sufficient Life
12. Freedom Beyond Money

---

## Azure AI Search Setup

### 1. Create Azure AI Search Service

```bash
# Create resource group
az group create --name bankx-rg --location southeastasia

# Create AI Search service
az search service create \
  --name bankx-search \
  --resource-group bankx-rg \
  --sku standard \
  --location southeastasia \
  --partition-count 1 \
  --replica-count 1
```

### 2. Enable Semantic Ranking

```bash
# Enable semantic search
az search service update \
  --name bankx-search \
  --resource-group bankx-rg \
  --semantic-search free
```

### 3. Get Admin Key

```bash
# Get admin key for indexing
az search admin-key show \
  --resource-group bankx-rg \
  --service-name bankx-search
```

---

## UC2 Indexing (Product Info & FAQ)

### Index Schema

**Index Name**: `bankx-products-faq`

**Fields**:
```json
{
  "fields": [
    {
      "name": "id",
      "type": "Edm.String",
      "key": true,
      "searchable": false
    },
    {
      "name": "content",
      "type": "Edm.String",
      "searchable": true,
      "analyzer": "en.microsoft"
    },
    {
      "name": "title",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true
    },
    {
      "name": "section",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "facetable": true
    },
    {
      "name": "source",
      "type": "Edm.String",
      "filterable": true,
      "facetable": true
    },
    {
      "name": "url",
      "type": "Edm.String",
      "searchable": false
    },
    {
      "name": "embedding",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "dimensions": 1536,
      "vectorSearchProfile": "default-vector-profile"
    }
  ]
}
```

### Semantic Configuration

```json
{
  "name": "default",
  "prioritizedFields": {
    "titleField": {
      "fieldName": "title"
    },
    "contentFields": [
      {
        "fieldName": "content"
      }
    ],
    "keywordsFields": [
      {
        "fieldName": "section"
      },
      {
        "fieldName": "source"
      }
    ]
  }
}
```

### Vector Search Configuration

```json
{
  "profiles": [
    {
      "name": "default-vector-profile",
      "algorithm": "hnsw",
      "vectorizer": "openai-ada-002"
    }
  ],
  "algorithms": [
    {
      "name": "hnsw",
      "kind": "hnsw",
      "hnswParameters": {
        "metric": "cosine",
        "m": 4,
        "efConstruction": 400,
        "efSearch": 500
      }
    }
  ]
}
```

---

## UC3 Indexing (Money Coach)

### Index Schema

**Index Name**: `bankx-money-coach`

**Fields**:
```json
{
  "fields": [
    {
      "name": "id",
      "type": "Edm.String",
      "key": true,
      "searchable": false
    },
    {
      "name": "chapter",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true,
      "facetable": true
    },
    {
      "name": "section",
      "type": "Edm.String",
      "searchable": true,
      "filterable": true
    },
    {
      "name": "content",
      "type": "Edm.String",
      "searchable": true,
      "analyzer": "en.microsoft"
    },
    {
      "name": "page",
      "type": "Edm.Int32",
      "filterable": true,
      "sortable": true
    },
    {
      "name": "embedding",
      "type": "Collection(Edm.Single)",
      "searchable": true,
      "dimensions": 1536,
      "vectorSearchProfile": "default-vector-profile"
    }
  ]
}
```

---

## Indexing Scripts

### UC2 Indexing Script

**Location**: `scripts/index_uc2_documents.py`

```python
"""
Index UC2 product documents and FAQs into Azure AI Search.
"""

import os
import PyPDF2
import requests
from bs4 import BeautifulSoup
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields
)
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# Configuration
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = "bankx-products-faq"
OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")

# PDF files to index
PDF_FILES = [
    "current-account-en.pdf",
    "normal-savings-account-en.pdf",
    "normal-fixed-account-en.pdf",
    "td-bonus-24months-en.pdf",
    "td-bonus-36months-en.pdf"
]

FAQ_URL = "https://www.scb.co.th/en/personal-banking/faq/deposit-faq.html"


def create_index():
    """Create Azure AI Search index."""
    index_client = SearchIndexClient(
        endpoint=SEARCH_ENDPOINT,
        credential=AzureKeyCredential(SEARCH_KEY)
    )

    # Define fields
    fields = [
        SearchField(name="id", type=SearchFieldDataType.String, key=True),
        SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="title", type=SearchFieldDataType.String, searchable=True, filterable=True),
        SearchField(name="section", type=SearchFieldDataType.String, searchable=True, filterable=True, facetable=True),
        SearchField(name="source", type=SearchFieldDataType.String, filterable=True, facetable=True),
        SearchField(name="url", type=SearchFieldDataType.String, searchable=False),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=1536,
            vector_search_profile_name="default-vector-profile"
        )
    ]

    # Vector search config
    vector_search = VectorSearch(
        profiles=[
            VectorSearchProfile(
                name="default-vector-profile",
                algorithm_configuration_name="hnsw"
            )
        ],
        algorithms=[
            HnswAlgorithmConfiguration(
                name="hnsw",
                parameters={
                    "metric": "cosine",
                    "m": 4,
                    "efConstruction": 400,
                    "efSearch": 500
                }
            )
        ]
    )

    # Semantic config
    semantic_config = SemanticConfiguration(
        name="default",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content")],
            keywords_fields=[
                SemanticField(field_name="section"),
                SemanticField(field_name="source")
            ]
        )
    )

    # Create index
    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search={"configurations": [semantic_config]}
    )

    index_client.create_or_update_index(index)
    print(f"✅ Index '{INDEX_NAME}' created")


def extract_pdf_text(pdf_path):
    """Extract text from PDF with page and section information."""
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        chunks = []

        for page_num, page in enumerate(reader.pages, 1):
            text = page.extract_text()

            # Split into chunks (roughly 500 words each)
            words = text.split()
            for i in range(0, len(words), 500):
                chunk = ' '.join(words[i:i+500])
                chunks.append({
                    "page": page_num,
                    "content": chunk
                })

        return chunks


def generate_embedding(text):
    """Generate embedding using Azure OpenAI."""
    client = AzureOpenAI(
        api_key=OPENAI_KEY,
        api_version="2023-05-15",
        azure_endpoint=OPENAI_ENDPOINT
    )

    response = client.embeddings.create(
        input=text,
        model="text-embedding-ada-002"
    )

    return response.data[0].embedding


def index_pdfs():
    """Index all PDF files."""
    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_KEY)
    )

    documents = []
    doc_id = 1

    for pdf_file in PDF_FILES:
        pdf_path = f"knowledge-bases/uc2-product-info/{pdf_file}"
        print(f"📄 Processing {pdf_file}...")

        chunks = extract_pdf_text(pdf_path)

        for chunk in chunks:
            embedding = generate_embedding(chunk["content"])

            doc = {
                "id": f"doc-{doc_id:06d}",
                "content": chunk["content"],
                "title": pdf_file.replace("-en.pdf", "").replace("-", " ").title(),
                "section": None,
                "source": pdf_file,
                "url": None,
                "embedding": embedding
            }

            documents.append(doc)
            doc_id += 1

            if len(documents) >= 100:
                search_client.upload_documents(documents=documents)
                print(f"   ✅ Uploaded {len(documents)} documents")
                documents = []

    # Upload remaining
    if documents:
        search_client.upload_documents(documents=documents)
        print(f"   ✅ Uploaded {len(documents)} documents")

    print("✅ All PDFs indexed")


def index_faq():
    """Index FAQ from website."""
    print(f"🌐 Processing FAQ from {FAQ_URL}...")

    response = requests.get(FAQ_URL)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract Q&A pairs (adjust selectors based on actual HTML structure)
    faq_items = soup.find_all('div', class_='faq-item')

    search_client = SearchClient(
        endpoint=SEARCH_ENDPOINT,
        index_name=INDEX_NAME,
        credential=AzureKeyCredential(SEARCH_KEY)
    )

    documents = []
    doc_id = 1000  # Start FAQ IDs at 1000

    for item in faq_items:
        question = item.find('h3').text.strip()
        answer = item.find('p').text.strip()

        content = f"Q: {question}\nA: {answer}"
        embedding = generate_embedding(content)

        doc = {
            "id": f"faq-{doc_id:06d}",
            "content": content,
            "title": question,
            "section": "FAQ",
            "source": "FAQ Website",
            "url": FAQ_URL,
            "embedding": embedding
        }

        documents.append(doc)
        doc_id += 1

    search_client.upload_documents(documents=documents)
    print(f"✅ Indexed {len(documents)} FAQ items")


def main():
    """Main indexing flow."""
    print("🚀 Starting UC2 indexing process...")

    create_index()
    index_pdfs()
    index_faq()

    print("✅ UC2 indexing complete!")


if __name__ == "__main__":
    main()
```

### UC3 Indexing Script

**Location**: `scripts/index_uc3_documents.py`

```python
"""
Index UC3 Money Coach document into Azure AI Search.
"""

import os
import PyPDF2
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import SearchIndex, SearchField, SearchFieldDataType
from azure.core.credentials import AzureKeyCredential
from openai import AzureOpenAI

# Configuration
SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
INDEX_NAME = "bankx-money-coach"
MONEY_COACH_PDF = "knowledge-bases/uc3-money-coach/debt-free-to-financial-freedom.pdf"

# Chapter titles
CHAPTERS = [
    "Debt — The Big Lesson Schools Never Teach",
    "The Real Meaning of Debt",
    "The Financially Ill",
    "Money Problems Must Be Solved with Financial Knowledge",
    "You Can Be Broke, But Don't Be Mentally Poor",
    "Five Steps to Debt-Free Living",
    "The Strong Medicine Plan (Debt Detox)",
    "Even in Debt, You Can Be Rich",
    "You Can Get Rich Without Money",
    "Financial Intelligence Is the Answer",
    "Sufficiency Leads to a Sufficient Life",
    "Freedom Beyond Money"
]


def create_index():
    """Create Azure AI Search index for Money Coach."""
    # Similar to UC2 but with chapter field
    pass


def extract_pdf_by_chapters(pdf_path):
    """Extract text from PDF organized by chapters."""
    # Extract and organize by chapters
    pass


def index_money_coach_document():
    """Index Money Coach document."""
    print("🚀 Starting UC3 indexing process...")

    create_index()

    # Extract and index by chapters
    chunks = extract_pdf_by_chapters(MONEY_COACH_PDF)

    # Upload to Azure AI Search
    # ... (similar to UC2)

    print("✅ UC3 indexing complete!")


if __name__ == "__main__":
    index_money_coach_document()
```

---

## Validation & Testing

### 1. Test Index Creation

```bash
# Check if index exists
az search index show \
  --service-name bankx-search \
  --name bankx-products-faq

az search index show \
  --service-name bankx-search \
  --name bankx-money-coach
```

### 2. Test Search Queries

```python
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

client = SearchClient(
    endpoint=SEARCH_ENDPOINT,
    index_name="bankx-products-faq",
    credential=AzureKeyCredential(SEARCH_KEY)
)

# Test search
results = client.search(
    search_text="savings account interest rate",
    top=5,
    query_type="semantic",
    semantic_configuration_name="default"
)

for result in results:
    print(f"Score: {result['@search.score']:.2f}")
    print(f"Title: {result['title']}")
    print(f"Content: {result['content'][:200]}...")
    print("---")
```

### 3. Validate Embeddings

```python
# Check embedding dimensions
for result in client.search(search_text="test", top=1):
    print(f"Embedding dimensions: {len(result['embedding'])}")
    # Should be 1536 for ada-002
```

---

## Maintenance

### Re-indexing

```bash
# Delete and recreate index
az search index delete --service-name bankx-search --name bankx-products-faq
python scripts/index_uc2_documents.py
```

### Updating Documents

```python
# Update specific documents
client.merge_or_upload_documents(documents=[
    {
        "id": "doc-000001",
        "content": "Updated content...",
        # ... other fields
    }
])
```

### Monitoring

```bash
# Check index statistics
az search index statistics show \
  --service-name bankx-search \
  --name bankx-products-faq
```

---

## Troubleshooting

### Issue: Indexing fails with embedding error
**Solution**: Verify Azure OpenAI endpoint and deployment name for ada-002

### Issue: Low search relevance scores
**Solution**: Review chunking strategy, consider smaller chunks (250-300 words)

### Issue: Semantic search not working
**Solution**: Verify semantic search is enabled on the service tier

---

## References

- [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/)
- [Vector Search in Azure AI Search](https://learn.microsoft.com/azure/search/vector-search-overview)
- [Semantic Search](https://learn.microsoft.com/azure/search/semantic-search-overview)

---

**Document Version**: 1.0
**Last Updated**: November 7, 2025
