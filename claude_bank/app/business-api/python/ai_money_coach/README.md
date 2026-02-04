# AIMoneyCoach MCP Service (UC3)

AI-powered personal finance coaching service with clarification-first approach for BankX.

## Overview

The AIMoneyCoach service provides personalized financial advice based on the "Debt-Free to Financial Freedom" document. Using a clarification-first approach, the service asks questions before providing advice to ensure recommendations are tailored to each customer's specific financial situation.

**Port**: 8077
**Use Case**: UC3 (AI Money Coach)
**Status**: Production Ready

## Features

- **Clarification-First Approach**: Always ask questions before giving advice
- **RAG-Based Coaching**: Grounded in "Debt-Free to Financial Freedom" document
- **Financial Health Assessment**: Categorize as Ordinary vs Critical Patient
- **Personalized Guidance**: Advice tailored to customer's situation
- **Actionable Recommendations**: Practical, implementable steps
- **Privacy Protection**: Work with percentages and ratios, not absolute amounts
- **Escalation Support**: Ticket creation for complex cases requiring human intervention

## Architecture

```
AIMoneyCoach Service (Port 8077)
│
├── main.py                          # FastMCP server entry point
├── mcp_tools.py                     # 2 MCP tool definitions
├── services.py                      # Business logic
│   ├── AISearchService              # Azure AI Search integration
│   └── ClarificationEngine          # Clarification-first logic
├── models.py                        # Pydantic models
├── config.py                        # Configuration settings
└── logging_config.py                # Logging setup
```

## Key Principles

### 1. Clarification-First Approach

**ALWAYS** start by understanding the customer's situation before providing advice:

```
❌ BAD: "Here's how to manage debt..."
✅ GOOD: "To provide the best advice, I need to understand your situation:
           1. What percentage of your income goes to debt payments?
           2. How many different debts do you have?
           3. What are the interest rates?"
```

### 2. Financial Health Assessment

Based on debt-to-income ratio:

| Category | Debt Payment Ratio | Zone | Approach |
|----------|-------------------|------|----------|
| **Ordinary Patient** | < 40% of income | Safe Zone | Standard guidance (Chapter 6: Five Steps) |
| **Critical Patient** | > 40% of income | Danger Zone | Debt Detox plan (Chapter 7: Strong Medicine) |

### 3. Grounded in Document

ALL advice must come from the "Debt-Free to Financial Freedom" document:
- Chapter 1: Debt — The Big Lesson Schools Never Teach
- Chapter 2: The Real Meaning of Debt
- Chapter 3: The Financially Ill
- Chapter 4: Money Problems Must Be Solved with Financial Knowledge
- Chapter 5: You Can Be Broke, But Don't Be Mentally Poor
- Chapter 6: Five Steps to Debt-Free Living
- Chapter 7: The Strong Medicine Plan (Debt Detox)
- Chapter 8: Even in Debt, You Can Be Rich
- Chapter 9: You Can Get Rich Without Money
- Chapter 10: Financial Intelligence Is the Answer
- Chapter 11: Sufficiency Leads to a Sufficient Life
- Chapter 12: Freedom Beyond Money

## MCP Tools

### 1. `AISearchRAGResults`

Search the "Debt-Free to Financial Freedom" document for relevant content.

**Parameters:**
- `query` (str): Financial question or topic
- `top_k` (int): Number of results (default: 5)
- `chapters` (list, optional): Filter by specific chapters

**Returns:**
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

### 2. `AIFoundryContentUnderstanding`

Synthesize personalized advice with clarification-first approach.

**Parameters:**
- `query` (str): User's question
- `search_results` (list): Results from AISearchRAGResults
- `conversation_history` (list, optional): Previous messages for context
- `customer_profile` (dict, optional): Financial health level

**Returns:**

**Clarification Response**:
```json
{
  "response_type": "CLARIFICATION",
  "content": "Before I provide advice, I'd like to understand your situation better...",
  "clarifying_questions": [
    "What percentage of your monthly income goes to debt payments?",
    "How many different debts do you currently have?",
    "What are the interest rates on your highest debts?"
  ]
}
```

**Advice Response**:
```json
{
  "response_type": "ADVICE",
  "content": "Based on your situation...",
  "advice": {
    "summary": "Prioritize high-interest debt first...",
    "action_steps": [
      "Step 1: List all debts with interest rates",
      "Step 2: Focus on highest interest debt",
      "Step 3: Make minimum payments on others"
    ],
    "relevant_chapters": ["Chapter 6", "Chapter 10"],
    "financial_health_level": "ORDINARY"
  }
}
```

## User Stories Implemented

- **UC3-001**: Basic Debt Management Advice
- **UC3-002**: Emergency Financial Situation (Debt Detox)
- **UC3-003**: Good Debt vs Bad Debt Education
- **UC3-004**: Building Emergency Fund Guidance
- **UC3-005**: Mindset and Psychological Support
- **UC3-006**: Multiple Income Stream Strategy
- **UC3-007**: Sufficiency Economy Application
- **UC3-008**: Financial Intelligence Development
- **UC3-009**: Out-of-Scope Query Handling
- **UC3-010**: Debt Consolidation Inquiry
- **UC3-011**: Investment Readiness While in Debt
- **UC3-012**: Complex Multi-Topic Consultation

## Knowledge Base

### Document: "Debt-Free to Financial Freedom"

**Index Name**: `bankx-money-coach`

**Content Structure**:
- 12 chapters covering debt management and financial wellness
- Practical strategies and real-world examples
- Thai financial context and cultural considerations

**Key Concepts**:

1. **Good Debt vs Bad Debt** (Chapter 8)
   - Good: Borrowing for production (generates value)
   - Bad: Borrowing for consumption (loses value)

2. **Three Real Assets** (Chapter 9)
   - Time
   - Knowledge/Skills
   - Reputation/Relationships

3. **Financial Intelligence** (Chapter 10)
   - Earn wisely
   - Spend intelligently
   - Save and protect
   - Invest and multiply

4. **Sufficiency Economy** (Chapter 11)
   - Moderation
   - Reasonableness
   - Resilience

## Running the Service

### Development Mode

```bash
# Set environment variables
export PROFILE=dev
export AZURE_AI_SEARCH_ENDPOINT=https://your-search.search.windows.net
export AZURE_AI_SEARCH_KEY=your-key
export AZURE_AI_SEARCH_INDEX_UC3=bankx-money-coach
export AZURE_CONTENT_UNDERSTANDING_ENDPOINT=https://your-foundry.cognitiveservices.azure.com/
export PORT=8077
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
docker build -t ai-money-coach-mcp:latest .

# Run container
docker run -p 8077:8077 \
  -e PROFILE=prod \
  -e AZURE_AI_SEARCH_ENDPOINT=${AZURE_AI_SEARCH_ENDPOINT} \
  ai-money-coach-mcp:latest
```

## Environment Variables

See `.env.example` for complete configuration template.

**Required**:
- `AZURE_AI_SEARCH_ENDPOINT` - Azure AI Search endpoint URL
- `AZURE_AI_SEARCH_KEY` - Azure AI Search admin key (optional with Managed Identity)
- `AZURE_CONTENT_UNDERSTANDING_ENDPOINT` - Azure AI Foundry endpoint

**Optional**:
- `AZURE_AI_SEARCH_INDEX_UC3` - Index name (default: `bankx-money-coach`)
- `PORT` - Service port (default: 8077)
- `LOG_LEVEL` - Logging level (default: INFO)

## Response Formatting

### ASCII Tables

```
┌────────────────────────────────┐
│ Your Debt Summary              │
├────────────────────────────────┤
│ Total Debts: 3                 │
│ Debt-to-Income: 35%            │
│ Status: ORDINARY PATIENT       │
└────────────────────────────────┘
```

### Section Separators

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 RECOMMENDED APPROACH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Priority Lists

```
📋 Action Steps (Prioritized):
   1. List all debts with interest rates
   2. Calculate debt-to-income ratio
   3. Focus on highest interest debt first
   4. Make minimum payments on others
```

### Chapter References

Always include source references:
```
📖 Reference: Chapter 6 - Five Steps to Debt-Free Living, pages 42-58
```

## Testing

### Test Scenarios

1. **Debt Management Query**
   ```
   User: "I have 3 credit cards with high balances, what should I do?"
   Expected: Clarifying questions about income, interest rates, balances
   ```

2. **Emergency Situation**
   ```
   User: "My expenses exceed my income, help!"
   Expected: Debt Detox plan (Chapter 7), mark as CRITICAL PATIENT
   ```

3. **Good vs Bad Debt**
   ```
   User: "Should I take a loan to buy a new iPhone?"
   Expected: Explanation of consumption debt (bad debt), Chapter 8 reference
   ```

4. **Emergency Fund**
   ```
   User: "How to start saving with no money left?"
   Expected: Chapter 10 strategies, clarify current expenses
   ```

5. **Out of Scope**
   ```
   User: "How to invest in stocks?"
   Expected: Polite decline, offer ticket creation
   ```

## Integration with EscalationComms

For complex cases or out-of-scope queries:

```python
# Create ticket for human advisor
ticket_id = await create_ticket(
    customer_id=customer_id,
    query=user_query,
    category="financial_coaching_complex"
)

# Send email notification
await escalation_comms_agent.send_email(
    ticket_id=ticket_id,
    customer_email=customer_email,
    query=user_query,
    use_case="UC3"
)
```

## Performance Targets

- **Search Latency**: < 1 second
- **Clarification Generation**: < 2 seconds
- **Advice Synthesis**: < 3 seconds
- **Total Response**: < 5 seconds

## Financial Health Assessment Logic

```python
def assess_financial_health(customer_profile: dict) -> str:
    """Determine if customer is Ordinary or Critical Patient"""

    debt_payment_ratio = customer_profile.get("debt_payment_ratio", 0)

    # Critical Patient: Debt payment > 40% of income
    if debt_payment_ratio > 0.40:
        return "CRITICAL"  # Apply Chapter 7: Strong Medicine

    # Ordinary Patient: Debt payment < 40% of income
    return "ORDINARY"  # Apply Chapter 6: Five Steps
```

## Clarification Question Templates

### Debt Management
- "What percentage of your monthly income goes to debt payments?"
- "How many different debts do you currently have?"
- "What are the interest rates on your highest debts?"

### Emergency Fund
- "Do you currently have any emergency savings?"
- "What are your essential monthly expenses?"
- "How stable is your current income?"

### Debt vs Savings
- "What's your current debt-to-income ratio?"
- "Are you currently making minimum payments or more?"
- "Do you have any high-interest debt (>15% APR)?"

## Azure Resources Required

1. **Azure AI Search**
   - SKU: Standard or higher
   - Index: `bankx-money-coach`
   - Semantic ranking enabled

2. **Azure AI Foundry**
   - Content Understanding endpoint
   - Model: GPT-4o or similar

3. **Managed Identity** (Production)
   - Permissions: Search Contributor

## Monitoring & Logging

Metrics tracked:
- Clarification rate (% of queries requiring clarification)
- Financial health distribution (Ordinary vs Critical)
- Chapter reference frequency
- Average conversation depth
- Escalation rate

## Troubleshooting

### Service doesn't ask clarifying questions
- Check clarification_engine logic
- Verify conversation_history is passed correctly
- Review threshold settings for clarification triggers

### Advice not grounded in document
- Validate AISearchRAGResults returns relevant chapters
- Check Content Understanding prompt for grounding rules
- Review index quality and chapter structure

### Performance issues
- Monitor search latency in Azure AI Search
- Check AI Foundry endpoint throttling
- Review caching strategies

## Related Services

- **UC2 ProdInfoFAQ** (port 8076) - Similar RAG architecture for product info
- **EscalationComms** (port 8078) - Email notification service
- **Copilot Backend** (port 8080) - Main orchestration layer

## References

- Knowledge Base: "Debt-Free to Financial Freedom" (12 chapters)
- MCP Documentation: https://modelcontextprotocol.io/
- Azure AI Search: https://learn.microsoft.com/azure/search/

---

**Service Version**: 1.0.0
**Last Updated**: November 7, 2025
**Maintainer**: BankX Development Team
