# Use Case 2 & 3 Implementation Guide - CORRECTED

## Overview

This document describes the **correct** implementation of Use Case 2 (Product Info & FAQ) and Use Case 3 (AI Money Coach) for the BankX Multi-Agent Banking System, following the official specifications.

---

## Use Case 2: Product Info & FAQ

### Purpose
RAG-based information retrieval for banking product information and FAQ content. Offers to create support ticket when answer not found.

### Key Principles
- **RAG Pattern**: Azure AI Search with vector embeddings
- **Static Knowledge**: Pre-indexed documents (5 account docs + FAQ)
- **Grounded Responses**: All answers must cite source documents
- **Ticket Creation**: When answer not found (confidence < 0.3), offer support ticket

### Architecture

#### Agents
1. **ProdInfoFAQ Agent** (`prodinfo_faq_agent.py`)
   - Role: Information retrieval, synthesis, and ticket management
   - A2A Connection: YES (called by Supervisor)
   - MCP Connection: YES via Azure AI Search and CosmosDB

2. **EscalationComms Agent** (`escalation_comms_agent.py`)
   - Role: Email communication via Azure Communication Services
   - A2A Connection: YES (called by ProdInfoFAQ Agent)
   - MCP Connection: YES via Azure Communication Services

#### MCP Tools - ProdInfoFAQ Agent
- `ProdInfoFAQ.searchDocuments` - Vector search in indexed docs
- `ProdInfoFAQ.getDocumentById` - Retrieve specific document section
- `ProdInfoFAQ.getContentUnderstanding` - AI Foundry synthesis
- `ProdInfoFAQ.writeToCosmosDB` - Store support tickets
- `ProdInfoFAQ.readFromCosmosDB` - Check cache/history

#### MCP Tool - EscalationComms Agent
- `escalationcomms.sendemail` - Send emails via Azure Communication Services

### Knowledge Base Content
1. **Current Account** (current-account-en.pdf)
2. **Normal Savings Account** (normal-savings-account-en.pdf)
3. **Normal Fixed Account** (normal-fixed-account-en.pdf)
4. **TD Bonus 24 Months** (td-bonus-24months-en.pdf)
5. **TD Bonus 36 Months** (td-bonus-36months-en.pdf)
6. **FAQ Document** (https://www.scb.co.th/en/personal-banking/faq/deposit-faq.html)

### User Stories

#### US 2.1: Answer Product Information Queries
- "What is the interest rate for a 12-month fixed deposit?"
- "What's the minimum amount to open a current account?"
- Output: **KNOWLEDGE_CARD**

#### US 2.2: Answer FAQ Questions
- "Can I withdraw from my bonus deposit before 24 months?"
- "How do I register for online banking?"
- Output: **FAQ_CARD**

#### US 2.3: Compare Account Types
- "Compare savings account and fixed deposit"
- "Difference between 24-month and 36-month bonus deposits?"
- Output: **COMPARISON_CARD**

#### US 2.4: Handle Unknown Queries with Ticket Creation
- When confidence < 0.3
- Create ticket in CosmosDB
- Send email via EscalationComms
- Output: **TICKET_CARD**

#### US 2.5: Explain Banking Terms and Calculations
- "How is compound interest calculated?"
- "What is withholding tax?"
- Output: **EXPLANATION_CARD**

### Output Schemas
```json
{
  "KNOWLEDGE_CARD": "Product information with source citations",
  "FAQ_CARD": "FAQ responses with document references",
  "COMPARISON_CARD": "Account type comparisons",
  "EXPLANATION_CARD": "Banking term explanations",
  "TICKET_CARD": "Support ticket creation confirmation"
}
```

### Workflow
1. Receive query from Supervisor
2. Check cache (readFromCosmosDB)
3. RAG search (searchDocuments)
4. Evaluate confidence:
   - If >= 0.3: Synthesize answer (getContentUnderstanding)
   - If < 0.3: Offer ticket creation
5. If ticket created:
   - Store in CosmosDB (writeToCosmosDB)
   - Call EscalationComms to send emails
6. Return appropriate card type

### Out of Scope Handling
- For non-banking/product queries: "I cannot handle that kind of information"
- Offer support ticket creation

---

## Use Case 3: AI Money Coach

### Purpose
AI-powered personal finance advisory based on "Debt-Free to Financial Freedom" document. Provides grounded, actionable coaching through clarification-first approach.

### Key Principles
- **Data-Driven**: All insights from provided personal finance document
- **Personalized Guidance**: Tailored through clarifying questions first
- **Actionable Recommendations**: Practical, implementable advice
- **Privacy Protection**: Work with percentages and ratios only

### Architecture

#### Agent
1. **AIMoneyCoach Agent** (`ai_money_coach_agent.py`)
   - Role: Personal finance coaching grounded in book content
   - A2A Connection: YES (called by Supervisor)
   - MCP Connection: YES via Azure AI Search and AI Foundry
   - Shared: Uses EscalationComms Agent for ticket creation

#### MCP Tools - AIMoneyCoach Agent
- `Retrieve.AISearchRAGResults` - Search Money Coach document
- `Retrieve.AIFoundryContentUnderstanding` - Synthesize personalized advice

### Knowledge Base
Complete "Debt-Free to Financial Freedom" guide with 12 chapters:
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

### Clarification-First Approach
**ALWAYS** start by understanding customer's situation:
1. Ask clarifying questions
2. Identify financial health level (Ordinary vs Critical Patient)
3. Understand goals and concerns
4. THEN provide tailored advice from document

### User Stories

#### UC3-001: Basic Debt Management Advice
- Help prioritize debt payments (Chapter 6, Step 3)
- Provide debt listing template
- High-interest first strategy

#### UC3-002: Emergency Financial Situation (Debt Detox)
- Identify critical patient status
- Provide "Strong Medicine Plan" (Chapter 7)
- Create recovery timeline
- Escalate if severe

#### UC3-003: Good Debt vs Bad Debt Education
- Explain consumption vs production debt (Chapter 8)
- Farmer/fisherman analogy
- Evaluate loan purposes

#### UC3-004: Building Emergency Fund Guidance
- 3-6 months fund target (Chapter 10)
- Create positive cash flow (Chapter 6, Step 4)

#### UC3-005: Mindset and Psychological Support
- "Broke but not mentally poor" concept (Chapter 5)
- Encouragement and hope
- Escalate if mental health concerns

#### UC3-006: Multiple Income Stream Strategy
- Income diversity (Chapter 10)
- Side businesses, skill monetization
- "Getting rich without money" (Chapter 9)

#### UC3-007: Sufficiency Economy Application
- Three pillars: moderation, reasonableness, resilience
- Address comparison trap
- Happiness equation

#### UC3-008: Financial Intelligence Development
- Four components: earning, spending, saving, investing
- Practical development tips

#### UC3-009: Out-of-Scope Query Handling
- Recognize non-finance questions
- "I cannot handle that kind of information"
- Offer support ticket

#### UC3-010: Debt Consolidation Inquiry
- Negotiation strategies (Chapter 7)
- Consolidation risks
- Stop new debt first

#### UC3-011: Investment Readiness While in Debt
- "Even in Debt, You Can Be Rich" (Chapter 8)
- Good debt that generates income
- Prioritize debt repayment

#### UC3-012: Complex Multi-Topic Consultation
- Thorough discovery
- Priority order
- Phased approach
- Escalation for detailed planning

### Response Format
- Conversational with empathy
- ASCII tables and visual elements
- Clear section headers with separators: `━━━━━━━━━━━`
- Box drawing for emphasis:
  ```
  ┌────────────────────┐
  │ Important Message  │
  └────────────────────┘
  ```
- Always include chapter references
- End with actionable next steps

### Financial Health Assessment
- **Ordinary Patient**: Debt payment < 40% of income (Safe Zone)
- **Critical Patient**: Debt payment > 40% of income (Danger Zone)

### Key Concepts
- **Good Debt**: Borrowing for production (generates value)
- **Bad Debt**: Borrowing for consumption (loses value)
- **Three Real Assets**: Time, Knowledge/Skills, Reputation/Relationships
- **Financial Intelligence**: Earn wisely, spend intelligently, save/protect, invest/multiply

### Out of Scope Handling
- For non-finance queries: "I cannot handle that kind of information"
- Offer support ticket via EscalationComms

---

## Multi-Agent Architecture

```
SupervisorAgent (Meta-Orchestrator)
├── AccountAgent (UC1)
├── TransactionAgent (UC1)
├── PaymentAgent (UC1)
├── ProdInfoFAQAgent (UC2) ← NEW
│   └── EscalationCommsAgent (shared)
└── AIMoneyCoachAgent (UC3) ← NEW
    └── EscalationCommsAgent (shared)
```

---

## Integration & Deployment

### Dependency Injection (`container_azure_chat.py`)

```python
# Shared agent for email notifications
escalation_comms_agent = providers.Singleton(
    EscalationCommsAgent,
    azure_chat_client=_azure_chat_client,
    escalation_comms_mcp_server_url=f"{settings.ESCALATION_COMMS_MCP_URL}/mcp"
)

# UC2 agent with RAG
prodinfo_faq_agent = providers.Singleton(
    ProdInfoFAQAgent,
    azure_chat_client=_azure_chat_client,
    prodinfo_faq_mcp_server_url=f"{settings.PRODINFO_FAQ_MCP_URL}/mcp",
    escalation_comms_agent=escalation_comms_agent
)

# UC3 agent with RAG
ai_money_coach_agent = providers.Singleton(
    AIMoneyCoachAgent,
    azure_chat_client=_azure_chat_client,
    ai_money_coach_mcp_server_url=f"{settings.AI_MONEY_COACH_MCP_URL}/mcp",
    escalation_comms_agent=escalation_comms_agent
)
```

### Environment Variables Required

```env
# UC2 - ProdInfoFAQ MCP Server (Azure AI Search + CosmosDB)
PRODINFO_FAQ_MCP_URL=http://localhost:8074

# UC3 - AIMoneyCoach MCP Server (Azure AI Search + AI Foundry)
AI_MONEY_COACH_MCP_URL=http://localhost:8075

# Shared - EscalationComms MCP Server (Azure Communication Services)
ESCALATION_COMMS_MCP_URL=http://localhost:8076
```

---

## Files Created/Modified

### New Files
- `app/copilot/app/agents/azure_chat/prodinfo_faq_agent.py` - UC2 agent
- `app/copilot/app/agents/azure_chat/ai_money_coach_agent.py` - UC3 agent
- `app/copilot/app/agents/azure_chat/escalation_comms_agent.py` - Shared email agent
- `docs/uc2_uc3_correct_implementation.md` - This documentation

### Modified Files
- `app/copilot/app/agents/azure_chat/supervisor_agent.py` - Updated routing
- `app/copilot/app/config/container_azure_chat.py` - Added new agents

---

## MCP Server Requirements

### UC2 - ProdInfoFAQ MCP Server
Must implement:
- `ProdInfoFAQ.searchDocuments` - Azure AI Search vector search
- `ProdInfoFAQ.getDocumentById` - Document retrieval
- `ProdInfoFAQ.getContentUnderstanding` - AI Foundry synthesis
- `ProdInfoFAQ.writeToCosmosDB` - Ticket storage
- `ProdInfoFAQ.readFromCosmosDB` - Cache/history retrieval

### UC3 - AIMoneyCoach MCP Server
Must implement:
- `Retrieve.AISearchRAGResults` - Azure AI Search for Money Coach doc
- `Retrieve.AIFoundryContentUnderstanding` - AI Foundry synthesis

### Shared - EscalationComms MCP Server
Must implement:
- `escalationcomms.sendemail` - Azure Communication Services email

---

## Testing Scenarios

### UC2 Testing
1. **Product Query**: "What is the interest rate for savings account?"
2. **FAQ Query**: "Can I withdraw early from fixed deposit?"
3. **Comparison**: "Compare current account vs savings account"
4. **Unknown Query**: "Tell me about mortgage loans" (should offer ticket)
5. **Out of Scope**: "What's the weather?" (should reject and offer ticket)

### UC3 Testing
1. **Debt Management**: "I have 3 credit cards, how to prioritize?"
2. **Emergency**: "My expenses exceed income, help!"
3. **Good vs Bad Debt**: "Should I take loan for new iPhone?"
4. **Emergency Fund**: "How to start saving with no money left?"
5. **Out of Scope**: "How to book flight?" (should reject and offer ticket)

---

## Key Differences from Previous Implementation

| Aspect | Previous (WRONG) | Current (CORRECT) |
|--------|------------------|-------------------|
| UC2 Agent Name | KnowledgeAgent | ProdInfoFAQAgent |
| UC2 Data Source | Local JSON files | Azure AI Search RAG |
| UC2 Tools | Python functions | MCP tools via APIM |
| UC2 Ticket Creation | Not implemented | Yes, with email |
| UC3 Agent Name | MoneyCoachAgent | AIMoneyCoachAgent |
| UC3 Data Source | Local JSON files | Azure AI Search RAG |
| UC3 Approach | Direct answers | Clarification-first |
| UC3 Tools | Python functions | MCP tools via APIM |
| Email Agent | Not implemented | EscalationCommsAgent |
| Architecture | Standalone agents | RAG + MCP + Escalation |

---

## Next Steps

1. **MCP Server Development**:
   - Implement ProdInfoFAQ MCP server with Azure AI Search + CosmosDB
   - Implement AIMoneyCoach MCP server with Azure AI Search + AI Foundry
   - Implement EscalationComms MCP server with Azure Communication Services

2. **Knowledge Base Indexing**:
   - Index 5 product PDFs in Azure AI Search (UC2)
   - Index FAQ document in Azure AI Search (UC2)
   - Index "Debt-Free to Financial Freedom" in Azure AI Search (UC3)

3. **Testing**:
   - Test all UC2 user stories with real queries
   - Test all UC3 user stories with coaching scenarios
   - Test ticket creation and email workflows

4. **Frontend Updates**:
   - Render KNOWLEDGE_CARD, FAQ_CARD, COMPARISON_CARD, EXPLANATION_CARD
   - Render TICKET_CARD
   - Support ASCII tables and visual elements from UC3

---

**Implementation Date**: November 2025
**Version**: 2.0 (CORRECTED)
**Status**: ✅ Agent Implementation Complete - MCP Servers Required
