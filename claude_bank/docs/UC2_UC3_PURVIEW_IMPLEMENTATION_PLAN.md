# UC2, UC3, and Purview Implementation Plan
## BankX Multi-Agent Banking System

**Document Version**: 1.0
**Date**: November 7, 2025
**Status**: Implementation Specification
**Author**: BankX Development Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State](#current-state)
3. [Target State](#target-state)
4. [Architecture Overview](#architecture-overview)
5. [Implementation Phases](#implementation-phases)
6. [UC2: ProdInfoFAQ MCP Server](#uc2-prodinfofaq-mcp-server)
7. [UC3: AIMoneyCoach MCP Server](#uc3-aimoneycoach-mcp-server)
8. [EscalationComms MCP Server](#escalationcomms-mcp-server)
9. [Azure Purview Integration](#azure-purview-integration)
10. [Configuration & Deployment](#configuration--deployment)
11. [Testing Strategy](#testing-strategy)
12. [Success Criteria](#success-criteria)

---

## Executive Summary

This document provides a comprehensive implementation plan for completing Use Case 2 (Product Info & FAQ), Use Case 3 (AI Money Coach), and Azure Purview data lineage integration for the BankX Multi-Agent Banking System.

### Scope
- **UC2**: Implement RAG-based product information and FAQ service with ticket escalation
- **UC3**: Implement AI-powered personal finance coaching with clarification-first approach
- **Purview**: Implement complete data lineage tracking for compliance and governance
- **Shared**: Implement email escalation service for UC2/UC3 ticket creation

### Timeline Estimate
- **Phase 1** (UC2 MCP Server): 2-3 days
- **Phase 2** (UC3 MCP Server): 2-3 days
- **Phase 3** (EscalationComms MCP Server): 1-2 days
- **Phase 4** (Purview Integration): 3-4 days
- **Phase 5** (Integration & Testing): 2-3 days
- **Total**: 10-15 days

---

## Current State

### What's Complete ✅
- UC1 (Financial Operations): 100% implemented and production-ready
- All UC1 user stories (5 customer + 3 agent + 5 teller): Fully implemented
- Agent framework: 7 agents defined (4 operational, 3 framework-only)
- Decision Ledger: Complete audit trail for UC1
- MCP Infrastructure: 6 services operational (ports 8070-8075)

### What's Missing 🟡
- **UC2**: Agent code exists, but NO MCP server implementation
- **UC3**: Agent code exists, but NO MCP server implementation
- **EscalationComms**: Agent code exists, but NO MCP server implementation
- **Purview**: Package included, architecture documented, but NO code implementation
- **Supervisor Routing**: UC2/UC3 not wired to routing logic

### Port Assignments
| Service | Current Port | Conflict | Proposed Port |
|---------|--------------|----------|---------------|
| Account | 8070 | None | 8070 ✅ |
| Transaction | 8071 | None | 8071 ✅ |
| Payment | 8072 | None | 8072 ✅ |
| Limits | 8073 | None | 8073 ✅ |
| Contacts | 8074 | None | 8074 ✅ |
| Audit | 8075 | None | 8075 ✅ |
| **ProdInfoFAQ** | **N/A** | **None** | **8076** 🆕 |
| **AIMoneyCoach** | **N/A** | **None** | **8077** 🆕 |
| **EscalationComms** | **N/A** | **None** | **8078** 🆕 |

---

## Target State

### Architecture Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                        COPILOT BACKEND (8080)                        │
│  ┌────────────────┐  ┌──────────────────────────────────────────┐  │
│  │ Supervisor     │  │ 7 Domain Agents                          │  │
│  │ Agent          │  │ - AccountAgent                           │  │
│  │ (Router)       │  │ - TransactionAgent                       │  │
│  │                │  │ - PaymentAgent                           │  │
│  │                │──│ - ProdInfoFAQAgent      (UC2) 🆕         │  │
│  │                │  │ - AIMoneyCoachAgent     (UC3) 🆕         │  │
│  │                │  │ - EscalationCommsAgent  (UC2/3) 🆕       │  │
│  └────────────────┘  └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  │ MCP/HTTP
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         MCP SERVICES LAYER                           │
├──────────────┬──────────────┬──────────────┬────────────────────────┤
│ UC1 Services │ UC2 Services │ UC3 Services │ Shared Services        │
├──────────────┼──────────────┼──────────────┼────────────────────────┤
│ Account      │ ProdInfoFAQ  │ AIMoneyCoach │ EscalationComms 🆕     │
│ (8070) ✅    │ (8076) 🆕    │ (8077) 🆕    │ (8078) 🆕              │
│              │              │              │                        │
│ Transaction  │              │              │ Purview SDK 🆕         │
│ (8071) ✅    │              │              │ (Embedded)             │
│              │              │              │                        │
│ Payment      │              │              │                        │
│ (8072) ✅    │              │              │                        │
│              │              │              │                        │
│ Limits       │              │              │                        │
│ (8073) ✅    │              │              │                        │
│              │              │              │                        │
│ Contacts     │              │              │                        │
│ (8074) ✅    │              │              │                        │
│              │              │              │                        │
│ Audit        │              │              │                        │
│ (8075) ✅    │              │              │                        │
└──────────────┴──────────────┴──────────────┴────────────────────────┘
                                  │
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    AZURE CLOUD SERVICES                              │
├──────────────────┬──────────────────┬────────────────┬──────────────┤
│ Azure AI Search  │ Cosmos DB        │ Communication  │ Purview      │
│ (UC2/UC3 RAG)    │ (Ticket Storage) │ Services       │ (Lineage)    │
│                  │                  │ (Email)        │              │
└──────────────────┴──────────────────┴────────────────┴──────────────┘
```

---

## Implementation Phases

### Phase 1: UC2 ProdInfoFAQ MCP Server (2-3 days)
1. Create directory structure and base files
2. Implement Azure AI Search integration for document RAG
3. Implement CosmosDB ticket storage
4. Implement 5 MCP tools
5. Index 5 product PDFs + FAQ HTML
6. Unit testing

### Phase 2: UC3 AIMoneyCoach MCP Server (2-3 days)
1. Create directory structure and base files
2. Implement Azure AI Search integration for Money Coach document
3. Implement 2 MCP tools with clarification-first logic
4. Index "Debt-Free to Financial Freedom" document
5. Unit testing

### Phase 3: EscalationComms MCP Server (1-2 days)
1. Create directory structure and base files
2. Implement Azure Communication Services integration
3. Implement email sending MCP tool
4. Create email templates for customers and bank employees
5. Unit testing

### Phase 4: Purview Integration (3-4 days)
1. Create Purview service wrapper
2. Implement lineage tracking for all MCP tools
3. Integrate with Decision Ledger
4. Create lineage visualization queries
5. Testing and validation

### Phase 5: Integration & Testing (2-3 days)
1. Wire UC2/UC3 agents to Supervisor routing
2. Update environment variables and configuration
3. Update azure.yaml deployment
4. End-to-end testing of all user stories
5. Documentation updates

---

## UC2: ProdInfoFAQ MCP Server

### Service Specification

**Port**: 8076
**Technology**: FastMCP + Azure AI Search + CosmosDB
**Purpose**: RAG-based product information and FAQ retrieval with ticket escalation

### Directory Structure
```
app/business-api/python/prodinfo_faq/
├── main.py                          # FastMCP server entry point
├── mcp_tools.py                     # 5 MCP tool definitions
├── services.py                      # Business logic (ProdInfoFAQService)
├── models.py                        # Pydantic models
├── azure_ai_search_service.py       # Azure AI Search integration
├── cosmos_ticket_service.py         # CosmosDB ticket storage
├── config.py                        # Configuration and settings
├── pyproject.toml                   # Dependencies
├── .env.example                     # Environment template
└── README.md                        # Service documentation
```

### MCP Tools to Implement

#### 1. `searchDocuments`
**Purpose**: Vector search in indexed product documents

**Parameters**:
- `query` (str): User's question
- `topK` (int, optional): Number of results (default: 5)
- `minScore` (float, optional): Minimum relevance score (default: 0.3)

**Returns**:
```json
{
  "results": [
    {
      "document_id": "current-account-en-p3",
      "title": "Current Account Interest Rates",
      "content": "...",
      "score": 0.85,
      "source": "current-account-en.pdf",
      "page": 3
    }
  ],
  "total_count": 5,
  "max_score": 0.85
}
```

**Implementation**:
```python
# Azure AI Search vector search
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

async def search_documents(query: str, top_k: int = 5, min_score: float = 0.3):
    search_client = SearchClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        index_name="bankx-products-index",
        credential=AzureKeyCredential(settings.AZURE_SEARCH_KEY)
    )

    # Perform vector search
    results = search_client.search(
        search_text=query,
        top=top_k,
        select=["document_id", "title", "content", "source", "page"],
        query_type="semantic"
    )

    # Filter by minimum score
    filtered = [r for r in results if r["@search.score"] >= min_score]

    return {
        "results": filtered,
        "total_count": len(filtered),
        "max_score": max([r["@search.score"] for r in filtered]) if filtered else 0.0
    }
```

#### 2. `getDocumentById`
**Purpose**: Retrieve specific document section by ID

**Parameters**:
- `documentId` (str): Document ID from search results

**Returns**:
```json
{
  "document_id": "current-account-en-p3",
  "title": "Current Account Interest Rates",
  "content": "Full content...",
  "metadata": {
    "source": "current-account-en.pdf",
    "page": 3,
    "section": "Interest Rates"
  }
}
```

#### 3. `getContentUnderstanding`
**Purpose**: AI Foundry synthesis of search results into answer

**Parameters**:
- `query` (str): Original user question
- `searchResults` (list): Results from searchDocuments

**Returns**:
```json
{
  "answer": "Based on the Current Account documentation...",
  "confidence": 0.85,
  "sources": ["current-account-en.pdf (p. 3)", "FAQ (Section: Interest)"],
  "card_type": "KNOWLEDGE_CARD"
}
```

**Implementation**:
```python
# Use Azure OpenAI for synthesis
from openai import AzureOpenAI

async def get_content_understanding(query: str, search_results: list):
    client = AzureOpenAI(...)

    # Build context from search results
    context = "\n\n".join([
        f"[{r['source']} p.{r['page']}]: {r['content']}"
        for r in search_results
    ])

    # Synthesis prompt
    prompt = f"""Based on the following product documentation, answer the user's question.

Question: {query}

Documentation:
{context}

Provide a clear, accurate answer citing the source documents.
"""

    response = client.chat.completions.create(
        model=settings.FOUNDRY_MODEL_DEPLOYMENT_NAME,
        messages=[{"role": "user", "content": prompt}]
    )

    answer = response.choices[0].message.content
    confidence = calculate_confidence(search_results)

    return {
        "answer": answer,
        "confidence": confidence,
        "sources": [f"{r['source']} (p. {r['page']})" for r in search_results],
        "card_type": determine_card_type(query, answer)
    }
```

#### 4. `writeToCosmosDB`
**Purpose**: Store support ticket when answer not found

**Parameters**:
- `customerId` (str): Customer ID
- `query` (str): Original question
- `reason` (str): Why ticket was created (e.g., "Low confidence", "Out of scope")
- `metadata` (dict, optional): Additional context

**Returns**:
```json
{
  "ticket_id": "TICKET-UC2-20251107-001",
  "status": "created",
  "created_at": "2025-11-07T14:30:00+07:00"
}
```

**Implementation**:
```python
from azure.cosmos import CosmosClient, PartitionKey

async def write_to_cosmos_db(customer_id: str, query: str, reason: str, metadata: dict = None):
    client = CosmosClient(settings.COSMOS_ENDPOINT, settings.COSMOS_KEY)
    database = client.get_database_client("bankx")
    container = database.get_container_client("support_tickets")

    ticket_id = f"TICKET-UC2-{datetime.now().strftime('%Y%m%d')}-{generate_uuid()}"

    ticket = {
        "id": ticket_id,
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "use_case": "UC2",
        "query": query,
        "reason": reason,
        "status": "OPEN",
        "created_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
        "metadata": metadata or {}
    }

    container.create_item(ticket)

    return {
        "ticket_id": ticket_id,
        "status": "created",
        "created_at": ticket["created_at"]
    }
```

#### 5. `readFromCosmosDB`
**Purpose**: Check if similar query was previously answered (cache)

**Parameters**:
- `customerId` (str): Customer ID
- `query` (str): User's question

**Returns**:
```json
{
  "found": true,
  "cached_answer": "...",
  "ticket_id": "TICKET-UC2-20251107-001",
  "created_at": "2025-11-07T14:30:00+07:00"
}
```

### Dependencies (pyproject.toml)
```toml
[project]
name = "prodinfo-faq-mcp"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0.0",
    "pydantic>=2.0",
    "azure-search-documents>=11.4.0",
    "azure-cosmos>=4.5.0",
    "azure-identity>=1.24.0",
    "openai>=1.0.0",
    "httpx>=0.28.0"
]
```

### Environment Variables
```env
# UC2 ProdInfoFAQ MCP Server
PROFILE=dev
AZURE_SEARCH_ENDPOINT=https://bankx-search.search.windows.net
AZURE_SEARCH_KEY=<key>
AZURE_SEARCH_INDEX_NAME=bankx-products-index
COSMOS_ENDPOINT=https://bankx-cosmos.documents.azure.com:443/
COSMOS_KEY=<key>
COSMOS_DATABASE_NAME=bankx
COSMOS_CONTAINER_NAME=support_tickets
FOUNDRY_PROJECT_ENDPOINT=https://...
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-4o
```

### Document Indexing Pipeline

**Knowledge Base Files**:
1. `current-account-en.pdf`
2. `normal-savings-account-en.pdf`
3. `normal-fixed-account-en.pdf`
4. `td-bonus-24months-en.pdf`
5. `td-bonus-36months-en.pdf`
6. FAQ HTML: https://www.scb.co.th/en/personal-banking/faq/deposit-faq.html

**Indexing Script**: `scripts/index_uc2_documents.py`
```python
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile
)
import PyPDF2

async def index_documents():
    # Create index
    index_client = SearchIndexClient(...)

    fields = [
        SearchField(name="document_id", type=SearchFieldDataType.String, key=True),
        SearchField(name="title", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="content", type=SearchFieldDataType.String, searchable=True),
        SearchField(name="source", type=SearchFieldDataType.String, filterable=True),
        SearchField(name="page", type=SearchFieldDataType.Int32),
        SearchField(name="embedding", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), vector_search_dimensions=1536)
    ]

    index = SearchIndex(name="bankx-products-index", fields=fields)
    index_client.create_index(index)

    # Index PDFs
    for pdf_file in PDF_FILES:
        extract_and_index_pdf(pdf_file)

    # Index FAQ HTML
    extract_and_index_html(FAQ_URL)
```

### Testing Scenarios
1. **Product Query**: "What is the interest rate for savings account?"
2. **FAQ Query**: "Can I withdraw early from fixed deposit?"
3. **Comparison**: "Compare current account vs savings account"
4. **Unknown Query**: "Tell me about mortgage loans" (should offer ticket)
5. **Out of Scope**: "What's the weather?" (should reject and offer ticket)

---

## UC3: AIMoneyCoach MCP Server

### Service Specification

**Port**: 8077
**Technology**: FastMCP + Azure AI Search
**Purpose**: AI-powered personal finance coaching with clarification-first approach

### Directory Structure
```
app/business-api/python/ai_money_coach/
├── main.py                          # FastMCP server entry point
├── mcp_tools.py                     # 2 MCP tool definitions
├── services.py                      # Business logic (AIMoneyCoachService)
├── models.py                        # Pydantic models
├── azure_ai_search_service.py       # Azure AI Search integration
├── clarification_engine.py          # Clarification-first logic
├── config.py                        # Configuration
├── pyproject.toml                   # Dependencies
├── .env.example                     # Environment template
└── README.md                        # Service documentation
```

### MCP Tools to Implement

#### 1. `AISearchRAGResults`
**Purpose**: Search "Debt-Free to Financial Freedom" document

**Parameters**:
- `query` (str): User's financial question
- `topK` (int, optional): Number of results (default: 5)
- `chapters` (list, optional): Filter by specific chapters

**Returns**:
```json
{
  "results": [
    {
      "chapter": "Chapter 6: Five Steps to Debt-Free Living",
      "section": "Step 3: Prioritize High-Interest Debt",
      "content": "...",
      "score": 0.92,
      "page": 45
    }
  ],
  "total_count": 5
}
```

#### 2. `AIFoundryContentUnderstanding`
**Purpose**: Synthesize personalized advice with clarification-first approach

**Parameters**:
- `query` (str): User's question
- `searchResults` (list): Results from AISearchRAGResults
- `conversationHistory` (list, optional): Previous messages for context
- `customerProfile` (dict, optional): Financial health level (Ordinary/Critical)

**Returns**:
```json
{
  "response_type": "CLARIFICATION" | "ADVICE",
  "content": "Before I provide advice, I'd like to understand your situation better...",
  "clarifying_questions": [
    "What percentage of your monthly income goes to debt payments?",
    "How many different debts do you currently have?"
  ],
  "advice": {
    "summary": "...",
    "action_steps": ["Step 1: ...", "Step 2: ..."],
    "relevant_chapters": ["Chapter 6", "Chapter 10"],
    "financial_health_level": "ORDINARY" | "CRITICAL"
  }
}
```

**Implementation**:
```python
async def get_content_understanding(
    query: str,
    search_results: list,
    conversation_history: list = None,
    customer_profile: dict = None
):
    # Determine if clarification needed
    needs_clarification = await check_if_needs_clarification(
        query, conversation_history
    )

    if needs_clarification:
        # Generate clarifying questions
        questions = await generate_clarifying_questions(query, search_results)
        return {
            "response_type": "CLARIFICATION",
            "content": "Before I provide advice, I'd like to understand...",
            "clarifying_questions": questions
        }

    # Build context from document
    context = build_context_from_search_results(search_results)

    # Assess financial health
    financial_health = assess_financial_health(customer_profile)

    # Generate personalized advice
    advice = await synthesize_advice(
        query=query,
        context=context,
        financial_health=financial_health,
        conversation_history=conversation_history
    )

    return {
        "response_type": "ADVICE",
        "content": advice["summary"],
        "advice": advice
    }
```

### Key Principles Implementation

#### Clarification-First Logic
```python
async def check_if_needs_clarification(query: str, history: list) -> bool:
    """Determine if we need more information before giving advice"""

    # Check if customer profile exists
    if not has_customer_profile(history):
        return True

    # Check if query is specific enough
    specificity_score = analyze_query_specificity(query)
    if specificity_score < 0.6:
        return True

    # Check if we have financial health context
    if not has_financial_health_context(history):
        return True

    return False

async def generate_clarifying_questions(query: str, search_results: list) -> list:
    """Generate 2-3 clarifying questions"""

    # Analyze query intent
    intent = classify_intent(query)

    questions = []

    if intent == "DEBT_MANAGEMENT":
        questions = [
            "What percentage of your monthly income goes to debt payments?",
            "How many different debts do you currently have?",
            "What are the interest rates on your highest debts?"
        ]
    elif intent == "EMERGENCY_FUND":
        questions = [
            "Do you currently have any emergency savings?",
            "What are your essential monthly expenses?",
            "How stable is your current income?"
        ]
    elif intent == "DEBT_VS_SAVINGS":
        questions = [
            "What's your current debt-to-income ratio?",
            "Are you currently making minimum payments or more?",
            "Do you have any high-interest debt (>15% APR)?"
        ]

    return questions[:3]  # Return max 3 questions
```

#### Financial Health Assessment
```python
def assess_financial_health(customer_profile: dict) -> str:
    """Determine if customer is Ordinary or Critical Patient"""

    debt_payment_ratio = customer_profile.get("debt_payment_ratio", 0)

    # Critical Patient: Debt payment > 40% of income (Danger Zone)
    if debt_payment_ratio > 0.40:
        return "CRITICAL"

    # Ordinary Patient: Debt payment < 40% of income (Safe Zone)
    return "ORDINARY"
```

### Dependencies (pyproject.toml)
```toml
[project]
name = "ai-money-coach-mcp"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0.0",
    "pydantic>=2.0",
    "azure-search-documents>=11.4.0",
    "azure-identity>=1.24.0",
    "openai>=1.0.0",
    "httpx>=0.28.0"
]
```

### Environment Variables
```env
# UC3 AIMoneyCoach MCP Server
PROFILE=dev
AZURE_SEARCH_ENDPOINT=https://bankx-search.search.windows.net
AZURE_SEARCH_KEY=<key>
AZURE_SEARCH_INDEX_NAME=bankx-moneycoach-index
FOUNDRY_PROJECT_ENDPOINT=https://...
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-4o
```

### Document Indexing

**Knowledge Base**: "Debt-Free to Financial Freedom" (12 chapters)

**Indexing Script**: `scripts/index_uc3_documents.py`
```python
async def index_money_coach_document():
    # Create index with chapter-level granularity
    index_client = SearchIndexClient(...)

    # Index each chapter with sections
    for chapter in MONEY_COACH_CHAPTERS:
        index_chapter(chapter)

    # Index key concepts separately for quick retrieval
    index_key_concepts()
```

### Testing Scenarios
1. **Debt Management**: "I have 3 credit cards, how to prioritize?"
2. **Emergency**: "My expenses exceed income, help!"
3. **Good vs Bad Debt**: "Should I take loan for new iPhone?"
4. **Emergency Fund**: "How to start saving with no money left?"
5. **Out of Scope**: "How to book flight?" (should reject and offer ticket)

---

## EscalationComms MCP Server

### Service Specification

**Port**: 8078
**Technology**: FastMCP + Azure Communication Services
**Purpose**: Email communication for ticket escalation (UC2/UC3)

### Directory Structure
```
app/business-api/python/escalation_comms/
├── main.py                          # FastMCP server entry point
├── mcp_tools.py                     # 1 MCP tool definition
├── services.py                      # Business logic (EmailService)
├── models.py                        # Pydantic models
├── email_templates.py               # Email templates
├── config.py                        # Configuration
├── pyproject.toml                   # Dependencies
├── .env.example                     # Environment template
└── README.md                        # Service documentation
```

### MCP Tool to Implement

#### `sendemail`
**Purpose**: Send email via Azure Communication Services

**Parameters**:
- `ticketId` (str): Support ticket ID
- `customerId` (str): Customer ID
- `customerEmail` (str): Customer email address
- `query` (str): Original customer question
- `useCase` (str): "UC2" or "UC3"
- `reason` (str): Why ticket was created

**Returns**:
```json
{
  "email_id": "EMAIL-UC2-20251107-001",
  "status": "sent",
  "sent_at": "2025-11-07T14:30:00+07:00",
  "recipients": {
    "customer": "customer@example.com",
    "bank_team": "support@bankx.com"
  }
}
```

**Implementation**:
```python
from azure.communication.email import EmailClient

async def send_email(
    ticket_id: str,
    customer_id: str,
    customer_email: str,
    query: str,
    use_case: str,
    reason: str
):
    email_client = EmailClient.from_connection_string(
        settings.AZURE_COMMUNICATION_CONNECTION_STRING
    )

    # Build email content
    customer_email_content = build_customer_email(
        ticket_id=ticket_id,
        query=query,
        use_case=use_case
    )

    bank_email_content = build_bank_team_email(
        ticket_id=ticket_id,
        customer_id=customer_id,
        query=query,
        use_case=use_case,
        reason=reason
    )

    # Send to customer
    customer_message = {
        "content": {
            "subject": f"Support Ticket Created: {ticket_id}",
            "plainText": customer_email_content["plain_text"],
            "html": customer_email_content["html"]
        },
        "recipients": {
            "to": [{"address": customer_email}]
        },
        "senderAddress": "noreply@bankx.com"
    }

    customer_poller = email_client.begin_send(customer_message)
    customer_result = customer_poller.result()

    # Send to bank team
    bank_message = {
        "content": {
            "subject": f"New Support Ticket: {ticket_id} ({use_case})",
            "plainText": bank_email_content["plain_text"],
            "html": bank_email_content["html"]
        },
        "recipients": {
            "to": [{"address": "support@bankx.com"}]
        },
        "senderAddress": "noreply@bankx.com"
    }

    bank_poller = email_client.begin_send(bank_message)
    bank_result = bank_poller.result()

    return {
        "email_id": f"EMAIL-{use_case}-{datetime.now().strftime('%Y%m%d')}-{generate_uuid()}",
        "status": "sent",
        "sent_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
        "recipients": {
            "customer": customer_email,
            "bank_team": "support@bankx.com"
        }
    }
```

### Email Templates

#### Customer Email Template
```python
def build_customer_email(ticket_id: str, query: str, use_case: str) -> dict:
    uc_name = "Product Information" if use_case == "UC2" else "Money Coach"

    plain_text = f"""
Dear Valued Customer,

Thank you for contacting BankX {uc_name} Service.

Your Question:
{query}

We've created a support ticket for your inquiry. Our team will review your question and provide a detailed response within 24-48 hours.

Ticket ID: {ticket_id}

You can track your ticket status at: https://bankx.com/support/tickets/{ticket_id}

Best regards,
BankX Support Team
"""

    html = f"""
<!DOCTYPE html>
<html>
<body>
    <h2>Dear Valued Customer,</h2>
    <p>Thank you for contacting BankX {uc_name} Service.</p>

    <h3>Your Question:</h3>
    <blockquote>{query}</blockquote>

    <p>We've created a support ticket for your inquiry. Our team will review your question and provide a detailed response within <strong>24-48 hours</strong>.</p>

    <p><strong>Ticket ID:</strong> {ticket_id}</p>

    <p><a href="https://bankx.com/support/tickets/{ticket_id}">Track your ticket status</a></p>

    <p>Best regards,<br>BankX Support Team</p>
</body>
</html>
"""

    return {"plain_text": plain_text, "html": html}
```

#### Bank Team Email Template
```python
def build_bank_team_email(
    ticket_id: str,
    customer_id: str,
    query: str,
    use_case: str,
    reason: str
) -> dict:
    uc_name = "Product Information & FAQ" if use_case == "UC2" else "AI Money Coach"

    plain_text = f"""
New Support Ticket: {ticket_id}

Use Case: {use_case} - {uc_name}
Customer ID: {customer_id}
Reason: {reason}

Customer Query:
{query}

Action Required:
1. Review the customer's question
2. Prepare a comprehensive response
3. Update ticket status in system
4. Respond within 24-48 hours

Ticket Dashboard: https://bankx.com/admin/tickets/{ticket_id}
"""

    html = f"""
<!DOCTYPE html>
<html>
<body>
    <h2>New Support Ticket: {ticket_id}</h2>

    <table>
        <tr><td><strong>Use Case:</strong></td><td>{use_case} - {uc_name}</td></tr>
        <tr><td><strong>Customer ID:</strong></td><td>{customer_id}</td></tr>
        <tr><td><strong>Reason:</strong></td><td>{reason}</td></tr>
    </table>

    <h3>Customer Query:</h3>
    <blockquote>{query}</blockquote>

    <h3>Action Required:</h3>
    <ol>
        <li>Review the customer's question</li>
        <li>Prepare a comprehensive response</li>
        <li>Update ticket status in system</li>
        <li>Respond within 24-48 hours</li>
    </ol>

    <p><a href="https://bankx.com/admin/tickets/{ticket_id}">Open Ticket Dashboard</a></p>
</body>
</html>
"""

    return {"plain_text": plain_text, "html": html}
```

### Dependencies (pyproject.toml)
```toml
[project]
name = "escalation-comms-mcp"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = [
    "fastmcp>=2.0.0",
    "pydantic>=2.0",
    "azure-communication-email>=1.0.0",
    "azure-identity>=1.24.0",
    "httpx>=0.28.0"
]
```

### Environment Variables
```env
# EscalationComms MCP Server
PROFILE=dev
AZURE_COMMUNICATION_CONNECTION_STRING=<connection-string>
SENDER_EMAIL=noreply@bankx.com
SUPPORT_TEAM_EMAIL=support@bankx.com
```

### Testing
```python
# Test email sending
test_send_email(
    ticket_id="TICKET-UC2-TEST-001",
    customer_id="CUST-001",
    customer_email="test@example.com",
    query="What is the interest rate for savings account?",
    use_case="UC2",
    reason="Low confidence (0.2)"
)
```

---

## Azure Purview Integration

### Overview

Azure Purview provides comprehensive data lineage tracking for compliance, governance, and audit purposes. This integration will track the complete data flow from user queries through agents, MCP tools, to underlying data sources.

### Service Specification

**Integration Type**: Embedded SDK (no separate service)
**Package**: `azure-purview-account==1.0.0` (already in requirements.txt)
**Purpose**: Track data lineage for all MCP tool calls and agent actions

### Architecture

```
User Query
    │
    ▼
Supervisor Agent ──────────────┐
    │                          │
    ▼                          │
Domain Agent                   │ Purview Lineage
    │                          │ Tracking
    ▼                          │
MCP Tool Call ─────────────────┤
    │                          │
    ▼                          │
Data Source (CSV/DB) ──────────┘
    │
    ▼
Decision Ledger + Purview Lineage
```

### Directory Structure
```
app/copilot/app/purview/
├── __init__.py
├── purview_service.py               # Main Purview service
├── lineage_tracker.py                # Lineage event creation
├── models.py                         # Lineage event models
└── config.py                         # Purview configuration
```

### Implementation Components

#### 1. Purview Service (`purview_service.py`)
```python
from azure.purview.account import PurviewAccountClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import AzureError
import logging

class PurviewService:
    """
    Azure Purview service for data lineage tracking.

    Tracks:
    - User queries → Agent routing
    - Agent actions → MCP tool calls
    - MCP tool calls → Data sources
    - Complete data flow for compliance
    """

    def __init__(self, account_name: str, credential=None):
        self.account_name = account_name
        self.credential = credential or DefaultAzureCredential()
        self.client = PurviewAccountClient(
            endpoint=f"https://{account_name}.purview.azure.com",
            credential=self.credential
        )
        self.logger = logging.getLogger(__name__)

    async def track_lineage(
        self,
        source_entity: dict,
        target_entity: dict,
        process_entity: dict,
        metadata: dict = None
    ):
        """
        Track data lineage from source to target via process.

        Args:
            source_entity: Input data source (e.g., user query, CSV file)
            target_entity: Output data (e.g., agent response, aggregation)
            process_entity: Transformation process (e.g., agent, MCP tool)
            metadata: Additional context (latency, request_id, etc.)
        """
        try:
            lineage_event = self._create_lineage_event(
                source=source_entity,
                target=target_entity,
                process=process_entity,
                metadata=metadata
            )

            # Send to Purview
            response = await self.client.lineage.create_or_update(lineage_event)

            self.logger.info(
                f"Lineage tracked: {source_entity['name']} → "
                f"{process_entity['name']} → {target_entity['name']}"
            )

            return response

        except AzureError as e:
            self.logger.error(f"Failed to track lineage: {e}")
            # Don't fail the main operation if Purview fails
            return None

    def _create_lineage_event(
        self,
        source: dict,
        target: dict,
        process: dict,
        metadata: dict = None
    ) -> dict:
        """Create Purview lineage event"""
        return {
            "typeName": "Process",
            "attributes": {
                "name": process["name"],
                "qualifiedName": process["qualified_name"],
                "inputs": [self._create_entity(source)],
                "outputs": [self._create_entity(target)],
                "description": process.get("description", ""),
                "metadata": metadata or {}
            }
        }

    def _create_entity(self, entity: dict) -> dict:
        """Create Purview entity"""
        return {
            "typeName": entity["type"],
            "uniqueAttributes": {
                "qualifiedName": entity["qualified_name"]
            },
            "attributes": {
                "name": entity["name"],
                **entity.get("attributes", {})
            }
        }
```

#### 2. Lineage Tracker (`lineage_tracker.py`)
```python
from typing import Optional
from datetime import datetime, timezone, timedelta
import hashlib

class LineageTracker:
    """
    Helper class for creating lineage events from agent/MCP actions.
    """

    def __init__(self, purview_service: PurviewService):
        self.purview = purview_service

    async def track_mcp_tool_call(
        self,
        tool_name: str,
        agent_name: str,
        input_params: dict,
        output_data: dict,
        data_source: str,
        request_id: str,
        latency_ms: float
    ):
        """
        Track lineage for MCP tool call.

        Example:
            User Query → TransactionAgent → searchTransactions → transactions.csv
        """

        # Source: Input parameters
        source_entity = {
            "type": "DataSet",
            "name": f"{agent_name}_Input",
            "qualified_name": f"bankx://{agent_name}/input/{request_id}",
            "attributes": {
                "parameters": input_params,
                "timestamp": datetime.now(timezone(timedelta(hours=7))).isoformat()
            }
        }

        # Target: Data source (CSV, database, etc.)
        target_entity = {
            "type": "DataSet",
            "name": data_source,
            "qualified_name": f"bankx://datasources/{data_source}",
            "attributes": {
                "format": self._get_format(data_source),
                "location": f"schemas/tools-sandbox/uc1_synthetic_data/{data_source}"
            }
        }

        # Process: MCP tool
        process_entity = {
            "type": "Process",
            "name": tool_name,
            "qualified_name": f"bankx://mcp/{tool_name}/{request_id}",
            "description": f"{agent_name} called {tool_name}"
        }

        # Metadata
        metadata = {
            "agent_name": agent_name,
            "request_id": request_id,
            "latency_ms": latency_ms,
            "timestamp": datetime.now(timezone(timedelta(hours=7))).isoformat(),
            "output_hash": hashlib.sha256(str(output_data).encode()).hexdigest()[:16]
        }

        await self.purview.track_lineage(
            source_entity=source_entity,
            target_entity=target_entity,
            process_entity=process_entity,
            metadata=metadata
        )

    async def track_agent_routing(
        self,
        user_query: str,
        supervisor_agent: str,
        target_agent: str,
        intent: str,
        conversation_id: str
    ):
        """
        Track lineage for agent routing.

        Example:
            User Query → Supervisor → TransactionAgent
        """

        # Source: User query
        source_entity = {
            "type": "DataSet",
            "name": "UserQuery",
            "qualified_name": f"bankx://queries/{conversation_id}",
            "attributes": {
                "query": user_query,
                "intent": intent
            }
        }

        # Target: Agent invocation
        target_entity = {
            "type": "Process",
            "name": target_agent,
            "qualified_name": f"bankx://agents/{target_agent}/{conversation_id}"
        }

        # Process: Supervisor routing
        process_entity = {
            "type": "Process",
            "name": supervisor_agent,
            "qualified_name": f"bankx://agents/{supervisor_agent}/routing/{conversation_id}",
            "description": f"Route intent '{intent}' to {target_agent}"
        }

        await self.purview.track_lineage(
            source_entity=source_entity,
            target_entity=target_entity,
            process_entity=process_entity,
            metadata={"conversation_id": conversation_id}
        )

    async def track_rag_search(
        self,
        query: str,
        index_name: str,
        results_count: int,
        agent_name: str,
        request_id: str
    ):
        """
        Track lineage for RAG search (UC2/UC3).

        Example:
            User Query → ProdInfoFAQAgent → Azure AI Search → product-docs
        """

        # Source: User query
        source_entity = {
            "type": "DataSet",
            "name": "RAGQuery",
            "qualified_name": f"bankx://rag/query/{request_id}",
            "attributes": {"query": query}
        }

        # Target: Azure AI Search index
        target_entity = {
            "type": "DataSet",
            "name": index_name,
            "qualified_name": f"bankx://search/{index_name}",
            "attributes": {
                "type": "AzureAISearch",
                "results_count": results_count
            }
        }

        # Process: RAG search
        process_entity = {
            "type": "Process",
            "name": f"{agent_name}_RAGSearch",
            "qualified_name": f"bankx://rag/{agent_name}/{request_id}",
            "description": f"{agent_name} RAG search in {index_name}"
        }

        await self.purview.track_lineage(
            source_entity=source_entity,
            target_entity=target_entity,
            process_entity=process_entity,
            metadata={"request_id": request_id, "results_count": results_count}
        )

    def _get_format(self, filename: str) -> str:
        """Get file format from filename"""
        if filename.endswith(".csv"):
            return "CSV"
        elif filename.endswith(".json"):
            return "JSON"
        elif filename.endswith(".pdf"):
            return "PDF"
        return "UNKNOWN"
```

#### 3. Models (`models.py`)
```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class PurviewEntity(BaseModel):
    """Purview entity model"""
    type: str = Field(..., description="Entity type (DataSet, Process, etc.)")
    name: str = Field(..., description="Entity name")
    qualified_name: str = Field(..., description="Unique qualified name")
    attributes: Dict[str, Any] = Field(default_factory=dict)

class LineageEvent(BaseModel):
    """Lineage event model"""
    source_entity: PurviewEntity
    target_entity: PurviewEntity
    process_entity: PurviewEntity
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

#### 4. Configuration (`config.py`)
```python
from pydantic_settings import BaseSettings

class PurviewSettings(BaseSettings):
    """Purview configuration"""
    PURVIEW_ACCOUNT_NAME: str = "bankx-purview"
    PURVIEW_ENABLED: bool = True

    class Config:
        env_file = ".env"
```

### Integration Points

#### 1. MCP Tools Integration
Add lineage tracking to all MCP tool calls:

```python
# Example: Transaction MCP Tool with Purview
from app.copilot.app.purview.lineage_tracker import LineageTracker

async def search_transactions(account_id: str, from_date: str, to_date: str):
    start_time = time.time()
    request_id = generate_request_id()

    # Execute MCP tool
    results = await transaction_service.search(account_id, from_date, to_date)

    latency_ms = (time.time() - start_time) * 1000

    # Track lineage
    if settings.PURVIEW_ENABLED:
        await lineage_tracker.track_mcp_tool_call(
            tool_name="searchTransactions",
            agent_name="TransactionAgent",
            input_params={
                "account_id": account_id,
                "from_date": from_date,
                "to_date": to_date
            },
            output_data={"count": len(results)},
            data_source="transactions.csv",
            request_id=request_id,
            latency_ms=latency_ms
        )

    return results
```

#### 2. Agent Integration
Add lineage tracking to agent routing:

```python
# Example: Supervisor Agent with Purview
async def route_to_agent(user_query: str, intent: str, conversation_id: str):
    target_agent = determine_target_agent(intent)

    # Track routing lineage
    if settings.PURVIEW_ENABLED:
        await lineage_tracker.track_agent_routing(
            user_query=user_query,
            supervisor_agent="SupervisorAgent",
            target_agent=target_agent,
            intent=intent,
            conversation_id=conversation_id
        )

    return await invoke_agent(target_agent, user_query, conversation_id)
```

#### 3. RAG Search Integration (UC2/UC3)
```python
# Example: ProdInfoFAQ Agent with Purview
async def search_documents(query: str):
    request_id = generate_request_id()

    # Perform RAG search
    results = await azure_search_client.search(query)

    # Track lineage
    if settings.PURVIEW_ENABLED:
        await lineage_tracker.track_rag_search(
            query=query,
            index_name="bankx-products-index",
            results_count=len(results),
            agent_name="ProdInfoFAQAgent",
            request_id=request_id
        )

    return results
```

### Environment Variables
```env
# Azure Purview Configuration
PURVIEW_ACCOUNT_NAME=bankx-purview
PURVIEW_ENABLED=true
AZURE_PURVIEW_ENDPOINT=https://bankx-purview.purview.azure.com
```

### Dependencies
```toml
# Already in requirements.txt
azure-purview-account==1.0.0
azure-identity==1.24.0
```

### Lineage Visualization

Example lineage query in Purview:

```
User Query: "Show my transactions from last week"
    │
    ▼
Supervisor Agent
    │ Intent: Transactions.View
    ▼
Transaction Agent
    │ Tool: searchTransactions
    ▼
Transaction MCP Service
    │ Data Source: transactions.csv
    ▼
Result: 10 transactions (TXN_TABLE)
```

### Testing
```python
# Test Purview integration
async def test_purview_lineage():
    purview_service = PurviewService(account_name="bankx-purview")
    lineage_tracker = LineageTracker(purview_service)

    # Test MCP tool lineage
    await lineage_tracker.track_mcp_tool_call(
        tool_name="searchTransactions",
        agent_name="TransactionAgent",
        input_params={"account_id": "CHK-001"},
        output_data={"count": 10},
        data_source="transactions.csv",
        request_id="REQ-TEST-001",
        latency_ms=250
    )

    print("Purview lineage tracking test passed!")
```

---

## Configuration & Deployment

### Updated Environment Variables

Create `.env` file in project root:

```env
# Copilot Backend
PROFILE=dev
FOUNDRY_PROJECT_ENDPOINT=https://...
FOUNDRY_MODEL_DEPLOYMENT_NAME=gpt-4o

# UC1 MCP Services (Existing)
ACCOUNT_MCP_URL=http://localhost:8070
TRANSACTION_MCP_URL=http://localhost:8071
PAYMENT_MCP_URL=http://localhost:8072
LIMITS_MCP_URL=http://localhost:8073
CONTACTS_MCP_URL=http://localhost:8074
AUDIT_MCP_URL=http://localhost:8075

# UC2 MCP Service (New)
PRODINFO_FAQ_MCP_URL=http://localhost:8076

# UC3 MCP Service (New)
AI_MONEY_COACH_MCP_URL=http://localhost:8077

# EscalationComms MCP Service (New)
ESCALATION_COMMS_MCP_URL=http://localhost:8078

# Azure AI Search (UC2/UC3)
AZURE_SEARCH_ENDPOINT=https://bankx-search.search.windows.net
AZURE_SEARCH_KEY=<key>
AZURE_SEARCH_PRODUCTS_INDEX=bankx-products-index
AZURE_SEARCH_MONEYCOACH_INDEX=bankx-moneycoach-index

# Cosmos DB (UC2 Ticket Storage)
COSMOS_ENDPOINT=https://bankx-cosmos.documents.azure.com:443/
COSMOS_KEY=<key>
COSMOS_DATABASE_NAME=bankx
COSMOS_CONTAINER_NAME=support_tickets

# Azure Communication Services (EscalationComms)
AZURE_COMMUNICATION_CONNECTION_STRING=<connection-string>
SENDER_EMAIL=noreply@bankx.com
SUPPORT_TEAM_EMAIL=support@bankx.com

# Azure Purview (Data Lineage)
PURVIEW_ACCOUNT_NAME=bankx-purview
PURVIEW_ENABLED=true
AZURE_PURVIEW_ENDPOINT=https://bankx-purview.purview.azure.com

# Existing Azure Services
AZURE_STORAGE_ACCOUNT=...
AZURE_DOCUMENT_INTELLIGENCE_SERVICE=...
APPLICATIONINSIGHTS_CONNECTION_STRING=...
AZURE_CLIENT_ID=system-managed-identity
```

### Update azure.yaml

Add new services to deployment configuration:

```yaml
name: bankx-multi-agent

services:
  # Existing services...

  # UC2: ProdInfoFAQ MCP Service
  prodinfo-faq:
    project: ./app/business-api/python/prodinfo_faq
    language: python
    host: containerapp
    env:
      PROFILE: prod
      AZURE_SEARCH_ENDPOINT: ${AZURE_SEARCH_ENDPOINT}
      AZURE_SEARCH_KEY: ${AZURE_SEARCH_KEY}
      COSMOS_ENDPOINT: ${COSMOS_ENDPOINT}
      COSMOS_KEY: ${COSMOS_KEY}
    containerApp:
      targetPort: 8076
      minReplicas: 1
      maxReplicas: 10

  # UC3: AIMoneyCoach MCP Service
  ai-money-coach:
    project: ./app/business-api/python/ai_money_coach
    language: python
    host: containerapp
    env:
      PROFILE: prod
      AZURE_SEARCH_ENDPOINT: ${AZURE_SEARCH_ENDPOINT}
      AZURE_SEARCH_KEY: ${AZURE_SEARCH_KEY}
    containerApp:
      targetPort: 8077
      minReplicas: 1
      maxReplicas: 10

  # EscalationComms MCP Service
  escalation-comms:
    project: ./app/business-api/python/escalation_comms
    language: python
    host: containerapp
    env:
      PROFILE: prod
      AZURE_COMMUNICATION_CONNECTION_STRING: ${AZURE_COMMUNICATION_CONNECTION_STRING}
    containerApp:
      targetPort: 8078
      minReplicas: 1
      maxReplicas: 5
```

### Dependency Injection Updates

Update `app/copilot/app/config/container_azure_chat.py`:

```python
# UC2: ProdInfoFAQ Agent
prodinfo_faq_agent = providers.Singleton(
    ProdInfoFAQAgent,
    azure_chat_client=_azure_chat_client,
    prodinfo_faq_mcp_server_url=f"{settings.PRODINFO_FAQ_MCP_URL}/mcp",
    escalation_comms_agent=escalation_comms_agent
)

# UC3: AIMoneyCoach Agent
ai_money_coach_agent = providers.Singleton(
    AIMoneyCoachAgent,
    azure_chat_client=_azure_chat_client,
    ai_money_coach_mcp_server_url=f"{settings.AI_MONEY_COACH_MCP_URL}/mcp",
    escalation_comms_agent=escalation_comms_agent
)

# Shared: EscalationComms Agent
escalation_comms_agent = providers.Singleton(
    EscalationCommsAgent,
    azure_chat_client=_azure_chat_client,
    escalation_comms_mcp_server_url=f"{settings.ESCALATION_COMMS_MCP_URL}/mcp"
)

# Purview Service
purview_service = providers.Singleton(
    PurviewService,
    account_name=settings.PURVIEW_ACCOUNT_NAME
)

lineage_tracker = providers.Singleton(
    LineageTracker,
    purview_service=purview_service
)
```

### Supervisor Routing Updates

Update `app/copilot/app/agents/azure_chat/supervisor_agent.py`:

```python
async def classify_intent(self, user_query: str) -> str:
    """Classify user intent with UC2/UC3 support"""

    # Existing UC1 intents...

    # UC2: Product Info & FAQ
    if any(keyword in query_lower for keyword in [
        "interest rate", "account type", "fixed deposit",
        "savings account", "current account", "faq",
        "product information", "account features"
    ]):
        return "ProductInfo.Query"

    # UC3: AI Money Coach
    if any(keyword in query_lower for keyword in [
        "debt", "financial advice", "money coach",
        "emergency fund", "savings tips", "budget",
        "financial planning", "debt management"
    ]):
        return "MoneyCoach.Advice"

    return "Unknown"

async def route_to_agent(self, intent: str, user_query: str, conversation_id: str):
    """Route to appropriate agent based on intent"""

    if intent.startswith("ProductInfo."):
        return await self.prodinfo_faq_agent.process(user_query, conversation_id)
    elif intent.startswith("MoneyCoach."):
        return await self.ai_money_coach_agent.process(user_query, conversation_id)
    # Existing UC1 routing...
```

---

## Testing Strategy

### Phase 1: Unit Testing

#### UC2 ProdInfoFAQ Tests
```python
# tests/test_prodinfo_faq.py
import pytest

@pytest.mark.asyncio
async def test_search_documents():
    result = await search_documents(query="What is savings account interest rate?")
    assert result["total_count"] > 0
    assert result["max_score"] > 0.3

@pytest.mark.asyncio
async def test_write_ticket_to_cosmos():
    ticket = await write_to_cosmos_db(
        customer_id="CUST-001",
        query="Tell me about mortgage loans",
        reason="Out of scope"
    )
    assert ticket["ticket_id"].startswith("TICKET-UC2-")
    assert ticket["status"] == "created"
```

#### UC3 AIMoneyCoach Tests
```python
# tests/test_ai_money_coach.py
@pytest.mark.asyncio
async def test_clarification_first():
    result = await get_content_understanding(
        query="I have debt problems",
        search_results=[],
        conversation_history=[]
    )
    assert result["response_type"] == "CLARIFICATION"
    assert len(result["clarifying_questions"]) > 0

@pytest.mark.asyncio
async def test_financial_health_assessment():
    profile = {"debt_payment_ratio": 0.45}
    health = assess_financial_health(profile)
    assert health == "CRITICAL"
```

#### EscalationComms Tests
```python
# tests/test_escalation_comms.py
@pytest.mark.asyncio
async def test_send_email():
    result = await send_email(
        ticket_id="TICKET-UC2-TEST-001",
        customer_id="CUST-001",
        customer_email="test@example.com",
        query="Test query",
        use_case="UC2",
        reason="Testing"
    )
    assert result["status"] == "sent"
    assert "email_id" in result
```

#### Purview Tests
```python
# tests/test_purview.py
@pytest.mark.asyncio
async def test_track_mcp_lineage():
    await lineage_tracker.track_mcp_tool_call(
        tool_name="searchTransactions",
        agent_name="TransactionAgent",
        input_params={"account_id": "CHK-001"},
        output_data={"count": 10},
        data_source="transactions.csv",
        request_id="REQ-TEST-001",
        latency_ms=250
    )
    # Verify lineage event was created
```

### Phase 2: Integration Testing

#### End-to-End UC2 Test
```python
@pytest.mark.e2e
async def test_uc2_product_query_flow():
    # 1. User asks product question
    query = "What is the interest rate for savings account?"

    # 2. Supervisor routes to ProdInfoFAQ agent
    response = await supervisor_agent.process(query)

    # 3. Verify response
    assert response["type"] == "KNOWLEDGE_CARD"
    assert "interest rate" in response["content"].lower()
    assert len(response["sources"]) > 0
```

#### End-to-End UC3 Test
```python
@pytest.mark.e2e
async def test_uc3_debt_advice_flow():
    # 1. User asks for debt advice
    query = "I have 3 credit cards with high balances, what should I do?"

    # 2. Supervisor routes to AIMoneyCoach agent
    response = await supervisor_agent.process(query)

    # 3. Verify clarification response
    assert response["response_type"] == "CLARIFICATION"
    assert len(response["clarifying_questions"]) >= 2

    # 4. Provide answers and get advice
    # ... (follow-up conversation)
```

#### Ticket Creation Flow Test
```python
@pytest.mark.e2e
async def test_ticket_creation_and_email():
    # 1. Ask out-of-scope question
    query = "Tell me about mortgage loans"

    # 2. Process through UC2 agent
    response = await prodinfo_faq_agent.process(query)

    # 3. Verify ticket card
    assert response["type"] == "TICKET_CARD"
    assert "ticket_id" in response

    # 4. Verify email was sent
    # ... (check email service logs)
```

### Phase 3: Performance Testing

```python
@pytest.mark.performance
async def test_uc2_latency():
    start = time.time()
    result = await search_documents(query="interest rate")
    latency = (time.time() - start) * 1000
    assert latency < 1000  # < 1 second

@pytest.mark.performance
async def test_purview_overhead():
    # Measure latency with Purview disabled
    settings.PURVIEW_ENABLED = False
    start = time.time()
    await search_transactions("CHK-001", "2025-10-20", "2025-10-26")
    latency_without = (time.time() - start) * 1000

    # Measure latency with Purview enabled
    settings.PURVIEW_ENABLED = True
    start = time.time()
    await search_transactions("CHK-001", "2025-10-20", "2025-10-26")
    latency_with = (time.time() - start) * 1000

    # Purview overhead should be < 100ms
    overhead = latency_with - latency_without
    assert overhead < 100
```

### Test Data Setup

#### UC2 Test Queries
```python
UC2_TEST_QUERIES = [
    ("What is the interest rate for savings account?", "KNOWLEDGE_CARD"),
    ("Can I withdraw early from fixed deposit?", "FAQ_CARD"),
    ("Compare current account vs savings account", "COMPARISON_CARD"),
    ("What is compound interest?", "EXPLANATION_CARD"),
    ("Tell me about mortgage loans", "TICKET_CARD"),  # Out of scope
]
```

#### UC3 Test Scenarios
```python
UC3_TEST_SCENARIOS = [
    {
        "query": "I have debt problems",
        "expected_response_type": "CLARIFICATION",
        "expected_questions": ["debt-to-income", "debt count"]
    },
    {
        "query": "Should I take loan for iPhone?",
        "expected_chapter": "Chapter 8",
        "expected_concept": "good debt vs bad debt"
    }
]
```

---

## Success Criteria

### UC2 Success Criteria
✅ All 5 MCP tools implemented and functional
✅ Azure AI Search index created with 5 PDFs + FAQ
✅ All 5 user stories (US 2.1-2.5) passing tests
✅ Ticket creation and email sending working
✅ Response latency < 2 seconds for searches
✅ Confidence threshold correctly identifying unknown queries

### UC3 Success Criteria
✅ All 2 MCP tools implemented and functional
✅ Azure AI Search index created with Money Coach document
✅ All 12 user stories (UC3-001 to UC3-012) passing tests
✅ Clarification-first approach working correctly
✅ Financial health assessment accurate
✅ Response latency < 2 seconds

### EscalationComms Success Criteria
✅ Email sending to customers working
✅ Email sending to bank team working
✅ Email templates properly formatted
✅ Integration with UC2/UC3 seamless

### Purview Success Criteria
✅ Lineage tracking for all MCP tool calls
✅ Lineage tracking for agent routing
✅ Lineage tracking for RAG searches
✅ Lineage events visible in Purview dashboard
✅ Performance overhead < 100ms
✅ No failures in main operations if Purview fails

### Overall Success Criteria
✅ All UC2/UC3 user stories covered (17 total)
✅ All 3 new MCP servers deployed and operational
✅ Supervisor routing correctly for UC2/UC3
✅ Complete data lineage tracked in Purview
✅ End-to-end testing passing for all scenarios
✅ Documentation complete and up-to-date
✅ Deployment configuration updated (azure.yaml)
✅ All environment variables configured

---

## Implementation Timeline

| Phase | Duration | Tasks | Deliverables |
|-------|----------|-------|--------------|
| **Phase 1** | 2-3 days | UC2 MCP Server | - 5 MCP tools<br>- Azure AI Search index<br>- CosmosDB integration<br>- Unit tests |
| **Phase 2** | 2-3 days | UC3 MCP Server | - 2 MCP tools<br>- Azure AI Search index<br>- Clarification engine<br>- Unit tests |
| **Phase 3** | 1-2 days | EscalationComms | - Email MCP tool<br>- Email templates<br>- Integration tests |
| **Phase 4** | 3-4 days | Purview Integration | - Purview service<br>- Lineage tracker<br>- All integrations<br>- Testing |
| **Phase 5** | 2-3 days | Integration & Testing | - Supervisor routing<br>- E2E tests<br>- Documentation<br>- Deployment |
| **Total** | **10-15 days** | | **Complete UC2/UC3/Purview** |

---

## Risk Mitigation

### Technical Risks
1. **Azure AI Search performance**: Mitigate with proper indexing and caching
2. **Purview overhead**: Implement async tracking to avoid blocking operations
3. **Email delivery failures**: Implement retry logic with exponential backoff
4. **CosmosDB costs**: Use TTL for automatic cleanup of old tickets

### Operational Risks
1. **Service dependencies**: Implement circuit breakers for all external services
2. **Data lineage gaps**: Ensure Purview failures don't break main operations
3. **Knowledge base updates**: Create automated indexing pipeline

---

## Appendix

### A. Port Assignment Summary
| Port | Service | Status |
|------|---------|--------|
| 8070 | Account | ✅ Operational |
| 8071 | Transaction | ✅ Operational |
| 8072 | Payment | ✅ Operational |
| 8073 | Limits | ✅ Operational |
| 8074 | Contacts | ✅ Operational |
| 8075 | Audit | ✅ Operational |
| 8076 | ProdInfoFAQ | 🆕 To Implement |
| 8077 | AIMoneyCoach | 🆕 To Implement |
| 8078 | EscalationComms | 🆕 To Implement |
| 8080 | Copilot Backend | ✅ Operational |
| 8081 | Frontend | ✅ Operational |

### B. Knowledge Base Files
**UC2**:
- current-account-en.pdf
- normal-savings-account-en.pdf
- normal-fixed-account-en.pdf
- td-bonus-24months-en.pdf
- td-bonus-36months-en.pdf
- FAQ: https://www.scb.co.th/en/personal-banking/faq/deposit-faq.html

**UC3**:
- Debt-Free to Financial Freedom (12 chapters)

### C. Azure Resources Required
- Azure AI Search: 2 indexes (products, moneycoach)
- Cosmos DB: 1 database, 1 container (support_tickets)
- Azure Communication Services: Email sending
- Azure Purview: Data lineage tracking
- Azure OpenAI: Already provisioned for agents

---

**Document End**
