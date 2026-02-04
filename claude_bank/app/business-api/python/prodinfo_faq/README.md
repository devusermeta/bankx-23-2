# ProdInfoFAQ MCP Service (UC2)

Product Information & FAQ service with RAG-based retrieval and ticket escalation for BankX.

## Overview

The ProdInfoFAQ service provides intelligent product information and FAQ retrieval using Azure AI Search with vector embeddings and semantic ranking. When queries cannot be answered with confidence, the service creates support tickets and sends email notifications via the EscalationComms service.

**Port**: 8076
**Use Case**: UC2 (Product Info & FAQ)
**Status**: Production Ready

## Features

- **RAG-Based Retrieval**: Azure AI Search with vector embeddings and semantic ranking
- **Grounding Validation**: Azure AI Foundry Content Understanding ensures 100% accuracy
- **Confidence Threshold**: Minimum 0.3, high confidence 0.7
- **Ticket Escalation**: Automatic ticket creation for low-confidence queries
- **Email Notifications**: Customer and support team notifications
- **Query Caching**: CosmosDB-based caching for performance
- **Multiple Output Types**: KNOWLEDGE_CARD, FAQ_CARD, COMPARISON_CARD, EXPLANATION_CARD, TICKET_CARD

## Architecture

```
ProdInfoFAQ Service (Port 8076)
│
├── main.py                          # FastMCP server entry point
├── mcp_tools.py                     # 5 MCP tool definitions
├── services.py                      # Business logic
│   ├── AISearchService              # Azure AI Search integration
│   ├── ContentUnderstandingService  # AI Foundry grounding validation
│   └── CosmosDBService              # Ticket storage & caching
├── models.py                        # Pydantic models
├── config.py                        # Configuration settings
└── logging_config.py                # Logging setup
```

## MCP Tools

### 1. `search_documents`

Search indexed product documents and FAQs using AI Search with vector embeddings.

**Parameters:**
- `query` (str): Search query string
- `top_k` (int): Number of results to return (default: 5)
- `min_confidence` (float): Minimum confidence threshold 0-1 (default: 0.0)

**Returns:**
```json
{
  "success": true,
  "query": "interest rate for savings account",
  "result_count": 5,
  "results": [
    {
      "document_id": "savings-account-p3",
      "content": "...",
      "title": "Savings Account Interest Rates",
      "section": "Interest Rates",
      "confidence": 0.92,
      "source": "normal-savings-account-en.pdf",
      "url": null
    }
  ]
}
```

### 2. `get_document_by_id`

Retrieve specific document section by ID.

**Parameters:**
- `document_id` (str): Document identifier
- `section` (str, optional): Specific section name to retrieve

**Returns:**
```json
{
  "success": true,
  "document": {
    "id": "savings-account-p3",
    "title": "Savings Account",
    "content": "...",
    "source": "normal-savings-account-en.pdf",
    "section": "Interest Rates"
  }
}
```

### 3. `get_content_understanding`

**CRITICAL GROUNDING VALIDATION** - Uses Azure AI Foundry Content Understanding to validate and synthesize answers.

**Parameters:**
- `query` (str): User's question
- `search_results_json` (str): JSON string of search results from search_documents
- `min_confidence` (float): Minimum confidence for grounding (default: 0.3)

**Returns:**
```json
{
  "success": true,
  "is_grounded": true,
  "confidence": 0.87,
  "validated_answer": "Based on the Savings Account documentation...",
  "citations": ["normal-savings-account-en.pdf (p. 3)", "FAQ Section: Interest"],
  "reason": null
}
```

**Important**: This tool ensures 100% accuracy by validating that answers are grounded in source documents.

### 4. `write_to_cosmosdb`

Store support ticket in CosmosDB when query cannot be answered.

**Parameters:**
- `ticket_id` (str): Unique ticket ID (format: TKT-YYYY-NNNNNN)
- `customer_id` (str): Customer identifier
- `query` (str): Original customer question
- `category` (str): Ticket category (e.g., "product_info", "account_query")
- `priority` (str): "normal", "high", or "urgent" (default: "normal")
- `metadata` (str, optional): JSON string with additional metadata

**Returns:**
```json
{
  "success": true,
  "ticket_id": "TKT-2025-001234",
  "status": "created",
  "message": "Support ticket created successfully"
}
```

### 5. `read_from_cosmosdb`

Check CosmosDB for cached queries or similar previous tickets.

**Parameters:**
- `query` (str): Search query
- `search_type` (str): "cache" for FAQ cache, "ticket" for ticket history

**Returns:**
```json
{
  "success": true,
  "cache_hit": true,
  "answer": "Cached answer...",
  "sources": ["source1", "source2"],
  "hit_count": 5
}
```

## User Stories Implemented

- **US 2.1**: Answer Product Information Queries → KNOWLEDGE_CARD
- **US 2.2**: Answer FAQ Questions → FAQ_CARD
- **US 2.3**: Compare Account Types → COMPARISON_CARD
- **US 2.4**: Handle Unknown Queries → TICKET_CARD + Email
- **US 2.5**: Explain Banking Terms → EXPLANATION_CARD

## Knowledge Base

### Indexed Documents (Azure AI Search)

1. **current-account-en.pdf** - Current Account features and terms
2. **normal-savings-account-en.pdf** - Savings Account information
3. **normal-fixed-account-en.pdf** - Fixed Deposit details
4. **td-bonus-24months-en.pdf** - 24-month Time Deposit Bonus
5. **td-bonus-36months-en.pdf** - 36-month Time Deposit Bonus
6. **FAQ HTML** - https://www.scb.co.th/en/personal-banking/faq/deposit-faq.html

### Indexing Requirements

**Index Name**: `bankx-products-faq`

**Document Schema**:
```json
{
  "id": "unique-doc-id",
  "content": "Document content chunk",
  "title": "Document title",
  "section": "Section name (optional)",
  "source": "Filename or URL",
  "url": "Source URL (optional)",
  "embedding": [/* vector */]
}
```

**Semantic Configuration**:
- Content fields: `content`, `title`
- Keyword fields: `source`, `section`
- Vector field: `embedding` (1536 dimensions for OpenAI ada-002)

## Running the Service

### Development Mode

```bash
# Set environment variables
export PROFILE=dev
export AZURE_AI_SEARCH_ENDPOINT=https://your-search.search.windows.net
export AZURE_AI_SEARCH_KEY=your-key
export AZURE_AI_SEARCH_INDEX_UC2=bankx-products-faq
export AZURE_CONTENT_UNDERSTANDING_ENDPOINT=https://your-foundry.cognitiveservices.azure.com/
export AZURE_COSMOSDB_ENDPOINT=https://your-cosmos.documents.azure.com:443/
export PORT=8076
export HOST=0.0.0.0

# Install dependencies
uv venv
uv sync

# Run the service
python main.py
```

### Production Mode (Docker)

```bash
# Build image
docker build -t prodinfo-faq-mcp:latest .

# Run container
docker run -p 8076:8076 \
  -e PROFILE=prod \
  -e AZURE_AI_SEARCH_ENDPOINT=${AZURE_AI_SEARCH_ENDPOINT} \
  -e AZURE_AI_SEARCH_KEY=${AZURE_AI_SEARCH_KEY} \
  prodinfo-faq-mcp:latest
```

## Environment Variables

See `.env.example` for complete configuration template.

**Required**:
- `AZURE_AI_SEARCH_ENDPOINT` - Azure AI Search endpoint URL
- `AZURE_AI_SEARCH_KEY` - Azure AI Search admin key (optional with Managed Identity)
- `AZURE_CONTENT_UNDERSTANDING_ENDPOINT` - Azure AI Foundry endpoint

**Optional**:
- `AZURE_AI_SEARCH_INDEX_UC2` - Index name (default: `bankx-products-faq`)
- `AZURE_COSMOSDB_ENDPOINT` - CosmosDB endpoint (for tickets & caching)
- `AZURE_COSMOSDB_DATABASE` - Database name (default: `bankx`)
- `AZURE_COSMOSDB_CONTAINER_TICKETS` - Container name (default: `support_tickets`)
- `PORT` - Service port (default: 8076)
- `LOG_LEVEL` - Logging level (default: INFO)

## Integration with EscalationComms

When ticket is created via `write_to_cosmosdb`, the ProdInfoFAQAgent calls EscalationCommsAgent to send email notifications:

```python
# Agent calls EscalationComms
ticket_id = await write_to_cosmosdb(...)
await escalation_comms_agent.send_email(
    ticket_id=ticket_id,
    customer_email="customer@example.com",
    query=user_query,
    use_case="UC2"
)
```

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/

# Test specific tool
pytest tests/test_search_documents.py
```

### Integration Tests

```bash
# Test end-to-end flow
pytest tests/test_integration.py
```

### Example Test Cases

1. **Product Query**: "What is the interest rate for savings account?"
   - Expected: KNOWLEDGE_CARD with sources
   - Confidence: > 0.7

2. **FAQ Query**: "Can I withdraw early from fixed deposit?"
   - Expected: FAQ_CARD with answer
   - Confidence: > 0.7

3. **Comparison**: "Compare current account vs savings account"
   - Expected: COMPARISON_CARD
   - Confidence: > 0.6

4. **Unknown Query**: "Tell me about mortgage loans"
   - Expected: TICKET_CARD
   - Confidence: < 0.3

5. **Out of Scope**: "What's the weather today?"
   - Expected: TICKET_CARD
   - Confidence: < 0.3

## Performance Targets

- **Search Latency**: < 1 second
- **Grounding Validation**: < 2 seconds
- **Ticket Creation**: < 500ms
- **Cache Hit Latency**: < 100ms
- **Total Response**: < 3 seconds

## Monitoring & Logging

All operations are logged with structured logging:

```python
logger.info(f"[MCP Tool] search_documents: query='{query}', top_k={top_k}")
logger.info(f"Found {len(results)} results above confidence threshold")
```

Metrics tracked:
- Search query count
- Average confidence scores
- Ticket creation rate
- Cache hit rate
- Response latencies

## Azure Resources Required

1. **Azure AI Search**
   - SKU: Standard or higher
   - Index: `bankx-products-faq`
   - Semantic ranking enabled

2. **Azure AI Foundry**
   - Content Understanding endpoint
   - Model: GPT-4o or similar

3. **Azure CosmosDB** (Optional for dev)
   - Database: `bankx`
   - Container: `support_tickets`
   - Partition key: `/customer_id`

4. **Managed Identity** (Production)
   - Permissions: Search Contributor, Cosmos DB Data Contributor

## Troubleshooting

### Search returns no results
- Verify index name in environment variables
- Check if documents are indexed properly
- Validate search endpoint and credentials

### Low confidence scores
- Review indexing quality
- Check embedding model consistency
- Tune semantic ranking configuration

### Ticket creation fails
- Verify CosmosDB endpoint and credentials
- Check container and database names
- Validate Managed Identity permissions

## Related Services

- **UC3 AIMoneyCoach** (port 8077) - Similar RAG architecture for financial coaching
- **EscalationComms** (port 8078) - Email notification service
- **Copilot Backend** (port 8080) - Main orchestration layer

## References

- MCP Documentation: https://modelcontextprotocol.io/
- Azure AI Search: https://learn.microsoft.com/azure/search/
- Azure AI Foundry: https://learn.microsoft.com/azure/ai-foundry/

---

**Service Version**: 1.0.0
**Last Updated**: November 7, 2025
**Maintainer**: BankX Development Team
