# EscalationComms Agent - A2A Integration

**Document Version:** 1.0
**Last Updated:** November 7, 2025
**Status:** ✅ Implementation Complete

---

## Executive Summary

This document describes the complete implementation of the **EscalationComms Agent** as an A2A-enabled microservice, serving as the shared email notification service for **Use Case 2 (ProdInfoFAQ)** and **Use Case 3 (AIMoneyCoach)**.

### Key Features
- ✅ **A2A-Enabled Microservice**: Full agent-to-agent communication support
- ✅ **Shared Service**: Used by both ProdInfoFAQ and AIMoneyCoach agents
- ✅ **Email Notifications**: Customer and bank employee notifications via Azure Communication Services
- ✅ **Service Discovery**: Registered with Agent Registry
- ✅ **Health Monitoring**: Health checks and observability
- ✅ **Zero Direct Dependencies**: No direct Python imports; all communication via A2A protocol

---

## Architecture Overview

### Multi-Agent Communication Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                   SUPERVISOR AGENT                               │
│              (Intent Classification & Routing)                   │
└──────────────┬──────────────────┬──────────────────────────────┘
               │                  │
               ▼                  ▼
    ┌──────────────────┐  ┌──────────────────┐
    │  ProdInfoFAQ     │  │  AIMoneyCoach    │
    │  Agent (UC2)     │  │  Agent (UC3)     │
    │                  │  │                  │
    │  Port: 8103      │  │  Port: 8105      │
    └────────┬─────────┘  └─────────┬────────┘
             │                      │
             │   A2A Protocol       │
             │   (HTTP/JSON)        │
             │                      │
             └──────────┬───────────┘
                        │
                        ▼
             ┌────────────────────┐
             │ EscalationComms    │
             │ Agent (Shared)     │
             │                    │
             │ Port: 8104         │
             │                    │
             │ A2A Capabilities:  │
             │ • send_email       │
             │ • send_ticket_email│
             └─────────┬──────────┘
                       │
                       ▼
           ┌────────────────────────┐
           │ Azure Communication    │
           │ Services MCP Server    │
           │                        │
           │ Port: 8076             │
           └────────────────────────┘
```

---

## EscalationComms Agent Specification

### Agent Information

**Agent Name:** `EscalationCommsAgent`
**Agent Type:** `communication`
**Version:** `1.0.0`
**Port:** `8104`

### Capabilities

1. **escalation.send_email** - Generic email sending
2. **email.send** - Alias for send_email
3. **notification.send** - Alias for send_email
4. **escalation.send_ticket_email** - Support ticket notification emails
5. **ticket.notify** - Alias for send_ticket_email

### A2A Endpoints

- **A2A Invoke:** `http://localhost:8104/a2a/invoke`
- **Health Check:** `http://localhost:8104/health`
- **Metrics:** `http://localhost:8104/metrics`
- **Root Info:** `http://localhost:8104/`

### MCP Tools

- **escalationcomms.sendemail** - Azure Communication Services email API

---

## A2A Integration Implementation

### 1. EscalationComms Microservice

#### File Structure

```
app/agents/escalation-comms-agent/
├── main.py                    # FastAPI application with A2A endpoints
├── a2a_handler.py             # A2A message handler
├── config.py                  # Configuration
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Container image
└── .dockerignore              # Docker ignore rules
```

#### Key Components

**main.py:**
- FastAPI application with A2A `/a2a/invoke` endpoint
- Agent Registry registration on startup
- Heartbeat loop for health monitoring
- Observability with Application Insights

**a2a_handler.py:**
- Handles A2A messages based on intent
- Routes to appropriate email sending methods
- Calls MCP EscalationComms service
- Returns structured responses

**config.py:**
- Agent configuration
- Environment variable management
- Port: 8104 (default)

### 2. ProdInfoFAQ Agent Integration

#### A2A Function Tool

**File:** `app/copilot/app/agents/azure_chat/prodinfo_faq_agent.py`

```python
async def send_ticket_notification_email(
    self,
    ticket_id: str,
    customer_email: str,
    customer_name: str,
    customer_id: str,
    query: str,
    category: str = "product_info",
    priority: str = "normal"
) -> Dict[str, Any]:
    """
    Send ticket notification emails via EscalationComms Agent using A2A communication.
    """
    # Builds A2A message and sends to EscalationComms agent
    # Returns email confirmation
```

#### Usage in Agent Instructions

```python
### STEP 5 (After ticket created): send_ticket_notification_email
After creating ticket in CosmosDB, IMMEDIATELY call send_ticket_notification_email function:
- ticket_id: Ticket ID from write_to_cosmosdb response
- customer_email: Customer's email address (use user_mail or ask user)
- customer_name: Customer's name (use user_mail or "Customer")
- customer_id: Customer identifier
- query: Original user question
- category: Ticket category (e.g., "product_info", "faq")
- priority: "normal", "high", or "urgent"

This function calls EscalationComms Agent via A2A to send email notifications to both
customer and bank employees
```

### 3. AIMoneyCoach Agent Integration

#### A2A Function Tool

**File:** `app/copilot/app/agents/azure_chat/ai_money_coach_agent.py`

```python
async def send_ticket_notification_email(
    self,
    ticket_id: str,
    customer_email: str,
    customer_name: str,
    customer_id: str,
    query: str,
    category: str = "financial_advice",
    priority: str = "normal"
) -> Dict[str, Any]:
    """
    Send ticket notification emails via EscalationComms Agent using A2A communication.
    """
    # Builds A2A message and sends to EscalationComms agent
    # Returns email confirmation
```

#### Usage in Agent Instructions

```python
If is_grounded=false OR contains_non_book_content=true:
- Use exact standard_output from tool response
- Offer to create support ticket
- If customer agrees, call send_ticket_notification_email function with:
  * ticket_id: Generate unique ticket ID (format: TKT-YYYY-NNNNNN)
  * customer_email: Customer's email address
  * customer_name: Customer's name
  * customer_id: Customer identifier
  * query: Original user question
  * category: "financial_advice", "debt_management", etc.
  * priority: "normal", "high" (use "high" for critical financial situations)
```

---

## A2A Message Protocol

### Request Message Format

**Intent:** `escalation.send_ticket_email`

```json
{
  "message_id": "msg-TKT-2024-001234",
  "correlation_id": "TKT-2024-001234",
  "protocol_version": "1.0",
  "timestamp": "2025-11-07T10:00:00Z",
  "source": {
    "agent_id": "prodinfo-faq-agent",
    "agent_name": "ProdInfoFAQAgent"
  },
  "target": {
    "agent_id": "escalation-comms-agent",
    "agent_name": "EscalationCommsAgent"
  },
  "intent": "escalation.send_ticket_email",
  "payload": {
    "ticket_id": "TKT-2024-001234",
    "customer_email": "customer@example.com",
    "customer_name": "John Doe",
    "customer_id": "CUST-001",
    "query": "What is the interest rate for savings account?",
    "category": "product_info",
    "priority": "normal"
  },
  "metadata": {
    "timeout_seconds": 30,
    "retry_count": 0
  }
}
```

### Response Message Format

**Status:** `success`

```json
{
  "message_id": "resp-msg-TKT-2024-001234",
  "correlation_id": "TKT-2024-001234",
  "protocol_version": "1.0",
  "timestamp": "2025-11-07T10:00:01Z",
  "source": {
    "agent_id": "escalation-comms-agent-001",
    "agent_name": "EscalationCommsAgent"
  },
  "target": {
    "agent_id": "prodinfo-faq-agent",
    "agent_name": "ProdInfoFAQAgent"
  },
  "status": "success",
  "response": {
    "type": "TICKET_EMAIL_CONFIRMATION",
    "ticket_id": "TKT-2024-001234",
    "emails_sent": [
      {
        "recipient": "customer@example.com",
        "type": "customer",
        "sent": true
      },
      {
        "recipient": "support@bankx.com",
        "type": "bank_employee",
        "sent": true
      }
    ],
    "recipients": ["customer@example.com", "support@bankx.com"],
    "timestamp": "2025-11-07T10:00:01+07:00",
    "all_sent": true
  },
  "metadata": {
    "processing_time_ms": 245
  }
}
```

---

## Email Templates

### Customer Email Template

**Subject:** `Support Ticket Created - {ticket_id}`

```
Dear {customer_name},

Thank you for contacting BankX support. Your support ticket has been created successfully.

Ticket ID: {ticket_id}
Category: {category}
Priority: {priority}

Your Query:
{query}

Expected Response Time: 24 hours

Our support team will review your query and respond as soon as possible. You can reference the ticket ID {ticket_id} in any follow-up communications.

If you have any urgent concerns, please contact our customer service hotline.

Best regards,
BankX Support Team
```

### Bank Employee Email Template

**Subject:** `New Support Ticket - {ticket_id} - {category.upper()}`

```
New Support Ticket Created

Ticket ID: {ticket_id}
Priority: {priority}
Category: {category}
Created: {timestamp}

Customer Information:
- Customer ID: {customer_id}
- Name: {customer_name}
- Email: {customer_email}

Customer Query:
{query}

Action Required:
Please review and respond to this ticket within 24 hours. Use ticket ID {ticket_id} for tracking.

---
BankX Ticketing System
```

---

## Use Case Scenarios

### Use Case 2: ProdInfoFAQ - Ticket Creation Flow

1. **User Query:** "Tell me about mortgage loans"
2. **ProdInfoFAQ Agent:**
   - Searches Azure AI Search (search_documents)
   - Validates grounding (get_content_understanding)
   - Result: confidence < 0.3 (not grounded)
3. **Agent Response:** "I cannot find information about mortgage loans in my current knowledge base. Would you like me to create a support ticket?"
4. **User:** "Yes, please"
5. **ProdInfoFAQ Agent:**
   - Creates ticket in CosmosDB (write_to_cosmosdb)
   - Calls `send_ticket_notification_email()` via A2A
6. **EscalationComms Agent:**
   - Receives A2A message
   - Sends customer email
   - Sends bank employee email
   - Returns confirmation
7. **ProdInfoFAQ Agent Returns:**
   ```json
   {
     "type": "TICKET_CARD",
     "ticket_id": "TKT-2024-001234",
     "status": "created",
     "message": "Support ticket created successfully",
     "email_sent": true,
     "recipients": ["customer@email.com", "support@bankx.com"],
     "expected_response": "24 hours"
   }
   ```

### Use Case 3: AIMoneyCoach - Escalation Flow

1. **User Query:** "Should I invest in cryptocurrency?"
2. **AIMoneyCoach Agent:**
   - Searches book content (ai_search_rag_results)
   - Validates grounding (ai_foundry_content_understanding)
   - Result: is_grounded=false (topic not in book)
3. **Agent Response:** "I cannot find information about cryptocurrency investment in my knowledge base (Debt-Free to Financial Freedom). Would you like me to create a support ticket for a specialist to help?"
4. **User:** "Yes"
5. **AIMoneyCoach Agent:**
   - Calls `send_ticket_notification_email()` via A2A
   - Priority set to "normal"
6. **EscalationComms Agent:**
   - Receives A2A message
   - Sends customer email
   - Sends bank employee email
   - Returns confirmation
7. **AIMoneyCoach Agent Returns:** Confirmation message with ticket details

---

## Deployment Configuration

### Environment Variables

#### EscalationComms Agent
```env
AGENT_ID=escalation-comms-agent-001
HOST=0.0.0.0
PORT=8104
AGENT_REGISTRY_URL=http://localhost:9000
MCP_ESCALATION_COMMS_URL=http://localhost:8076
LOG_LEVEL=INFO
ENVIRONMENT=development
APPLICATIONINSIGHTS_CONNECTION_STRING=<app-insights-connection-string>
```

#### ProdInfoFAQ Agent
```env
ESCALATION_COMMS_A2A_URL=http://localhost:8104/a2a/invoke
```

#### AIMoneyCoach Agent
```env
ESCALATION_COMMS_A2A_URL=http://localhost:8104/a2a/invoke
```

### Docker Deployment

#### Build EscalationComms Agent
```bash
cd app
docker build -f agents/escalation-comms-agent/Dockerfile -t bankx/escalation-comms-agent:1.0.0 .
```

#### Run EscalationComms Agent
```bash
docker run -d \
  --name escalation-comms-agent \
  -p 8104:8104 \
  -e AGENT_REGISTRY_URL=http://agent-registry:9000 \
  -e MCP_ESCALATION_COMMS_URL=http://escalation-comms-mcp:8076 \
  bankx/escalation-comms-agent:1.0.0
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: escalation-comms-agent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: escalation-comms-agent
  template:
    metadata:
      labels:
        app: escalation-comms-agent
    spec:
      containers:
      - name: escalation-comms-agent
        image: bankx/escalation-comms-agent:1.0.0
        ports:
        - containerPort: 8104
        env:
        - name: AGENT_REGISTRY_URL
          value: "http://agent-registry:9000"
        - name: MCP_ESCALATION_COMMS_URL
          value: "http://escalation-comms-mcp:8076"
        livenessProbe:
          httpGet:
            path: /health
            port: 8104
          initialDelaySeconds: 10
          periodSeconds: 30
---
apiVersion: v1
kind: Service
metadata:
  name: escalation-comms-agent
spec:
  selector:
    app: escalation-comms-agent
  ports:
  - port: 8104
    targetPort: 8104
  type: ClusterIP
```

---

## Testing

### Manual Testing

#### 1. Health Check
```bash
curl http://localhost:8104/health
```

Expected Response:
```json
{
  "status": "healthy",
  "agent": "EscalationCommsAgent",
  "version": "1.0.0",
  "mcp_service": "healthy"
}
```

#### 2. Send Test A2A Message
```bash
curl -X POST http://localhost:8104/a2a/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "test-msg-001",
    "correlation_id": "test-corr-001",
    "protocol_version": "1.0",
    "source": {
      "agent_id": "test-agent",
      "agent_name": "TestAgent"
    },
    "target": {
      "agent_id": "escalation-comms-agent",
      "agent_name": "EscalationCommsAgent"
    },
    "intent": "escalation.send_ticket_email",
    "payload": {
      "ticket_id": "TKT-TEST-001",
      "customer_email": "test@example.com",
      "customer_name": "Test User",
      "customer_id": "CUST-TEST",
      "query": "Test query",
      "category": "test",
      "priority": "normal"
    },
    "metadata": {
      "timeout_seconds": 30,
      "retry_count": 0
    }
  }'
```

### Integration Testing

See test scenarios in:
- `tests/integration/test_uc2_escalation.py`
- `tests/integration/test_uc3_escalation.py`

---

## Monitoring & Observability

### Key Metrics

1. **A2A Request Rate:** Requests per second to EscalationComms agent
2. **A2A Success Rate:** Percentage of successful A2A calls
3. **Email Delivery Rate:** Percentage of successfully sent emails
4. **Response Latency:** P50, P95, P99 latency for A2A calls
5. **Error Rate:** Failed requests and reasons

### Application Insights Queries

```kql
// A2A requests to EscalationComms
traces
| where message contains "EscalationComms"
| where message contains "A2A"
| summarize count() by bin(timestamp, 5m)

// Email sending errors
exceptions
| where outerMessage contains "Failed to send"
| project timestamp, outerMessage, customDimensions
```

### Health Check Monitoring

```bash
# Check agent health every 30 seconds
while true; do
  curl -s http://localhost:8104/health | jq '.status'
  sleep 30
done
```

---

## Troubleshooting

### Common Issues

#### 1. EscalationComms Agent Not Reachable

**Symptoms:**
- A2A calls from ProdInfoFAQ/AIMoneyCoach fail
- Connection refused errors

**Solutions:**
- Check if agent is running: `curl http://localhost:8104/health`
- Verify ESCALATION_COMMS_A2A_URL environment variable
- Check network connectivity
- Review logs: `docker logs escalation-comms-agent`

#### 2. Emails Not Sending

**Symptoms:**
- A2A call succeeds but emails not delivered
- `all_sent: false` in response

**Solutions:**
- Check MCP EscalationComms service health
- Verify Azure Communication Services credentials
- Review EscalationComms agent logs
- Check email addresses are valid

#### 3. Agent Registry Connection Failed

**Symptoms:**
- Agent starts but not registered
- "Failed to register with agent registry" in logs

**Solutions:**
- Check AGENT_REGISTRY_URL environment variable
- Verify agent registry is running
- Check network connectivity to registry
- Review agent startup logs

---

## Security Considerations

### Authentication

- A2A messages currently use service-to-service trust
- Future enhancement: JWT or Azure Entra ID tokens

### Data Privacy

- Customer email addresses transmitted via A2A
- Ensure HTTPS in production
- Implement encryption at rest for ticket data

### Rate Limiting

- Implement rate limiting on A2A endpoint
- Prevent email spam from malicious agents
- Configure Azure Communication Services quotas

---

## Future Enhancements

1. **Service Discovery:** Use Agent Registry for dynamic endpoint resolution
2. **Circuit Breaker:** Implement circuit breaker pattern for MCP calls
3. **Email Templates:** Dynamic template management
4. **Retry Logic:** Automatic retry for failed email deliveries
5. **Email Tracking:** Track email open rates and responses
6. **Multiple Channels:** SMS, push notifications, webhooks
7. **Priority Queues:** Separate queues for high-priority tickets
8. **Bulk Operations:** Send multiple emails in batch

---

## References

- **A2A Implementation Plan:** `docs/A2A_IMPLEMENTATION_PLAN.md`
- **UC2/UC3 Specification:** `docs/uc2_uc3_correct_implementation.md`
- **Agent Registry:** `app/agent-registry/`
- **A2A SDK:** `app/a2a-sdk/`

---

## Summary

The EscalationComms agent is now fully implemented as an A2A-enabled microservice and integrated with both ProdInfoFAQ (UC2) and AIMoneyCoach (UC3) agents. Key achievements:

✅ **Complete A2A Integration:** All communication via A2A protocol
✅ **Zero Direct Dependencies:** No Python imports between agents
✅ **Shared Service:** Single agent serves multiple use cases
✅ **Production-Ready:** Health checks, monitoring, observability
✅ **Scalable:** Can be deployed independently and scaled horizontally
✅ **Testable:** Comprehensive testing support

**Status:** Ready for deployment and testing
**Next Steps:** Deploy to development environment and run integration tests

---

**Document Maintained By:** BankX Architecture Team
**Last Review:** November 7, 2025
**Next Review:** After Phase 2A completion
