# EscalationComms MCP Service

Email notification service for support ticket escalation (shared by UC2 and UC3).

## Overview

The EscalationComms service handles email notifications for support ticket creation. When UC2 (ProdInfoFAQ) or UC3 (AIMoneyCoach) encounters queries that cannot be answered, this service sends professional email notifications to both customers and the bank's support team.

**Port**: 8078
**Use Case**: Shared by UC2 and UC3
**Status**: Production Ready

## Features

- **Dual Email Notifications**: Send to both customer and support team
- **Template-Based**: Professional HTML and plain text email templates
- **Azure Communication Services Integration**: Enterprise-grade email delivery
- **Use Case Aware**: Different templates for UC2 vs UC3
- **Ticket Tracking**: Email includes ticket ID and tracking links
- **Retry Logic**: Automatic retry with exponential backoff
- **Delivery Confirmation**: Track email delivery status

## Architecture

```
EscalationComms Service (Port 8078)
│
├── main.py                          # FastMCP server entry point
├── mcp_tools.py                     # 1 MCP tool definition (sendemail)
├── services.py                      # Business logic (EmailService)
├── email_templates.py               # Email templates (HTML + plain text)
├── models.py                        # Pydantic models
├── config.py                        # Configuration settings
└── logging_config.py                # Logging setup
```

## MCP Tool

### `sendemail`

Send email notifications via Azure Communication Services.

**Parameters:**
- `ticket_id` (str): Support ticket ID (e.g., "TKT-2025-001234")
- `customer_id` (str): Customer identifier
- `customer_email` (str): Customer email address
- `query` (str): Original customer question
- `use_case` (str): "UC2" or "UC3"
- `reason` (str): Why ticket was created (e.g., "Low confidence", "Out of scope")

**Returns:**
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

**Example Usage:**
```python
result = await send_email(
    ticket_id="TKT-2025-001234",
    customer_id="CUST-001",
    customer_email="customer@example.com",
    query="What is the interest rate for mortgage loans?",
    use_case="UC2",
    reason="Out of scope - Mortgages not in knowledge base"
)
```

## Email Templates

### Customer Email (UC2 - Product Info)

**Subject**: Support Ticket Created: TKT-2025-001234

**Plain Text**:
```
Dear Valued Customer,

Thank you for contacting BankX Product Information Service.

Your Question:
What is the interest rate for mortgage loans?

We've created a support ticket for your inquiry. Our team will review
your question and provide a detailed response within 24-48 hours.

Ticket ID: TKT-2025-001234

You can track your ticket status at:
https://bankx.com/support/tickets/TKT-2025-001234

Best regards,
BankX Support Team
```

**HTML**: Professional branded email with BankX logo and styling.

### Customer Email (UC3 - Money Coach)

**Subject**: Financial Coaching Request: TKT-2025-001235

**Plain Text**:
```
Dear Valued Customer,

Thank you for contacting BankX AI Money Coach Service.

Your Request:
I need help with complex financial planning across multiple areas...

We've created a support ticket to ensure you receive personalized
guidance from our financial advisors within 24-48 hours.

Ticket ID: TKT-2025-001235

You can track your ticket status at:
https://bankx.com/support/tickets/TKT-2025-001235

Best regards,
BankX Financial Advisory Team
```

### Bank Team Email (Internal)

**Subject**: New Support Ticket: TKT-2025-001234 (UC2)

**Plain Text**:
```
New Support Ticket: TKT-2025-001234

Use Case: UC2 - Product Information & FAQ
Customer ID: CUST-001
Reason: Out of scope - Mortgages not in knowledge base

Customer Query:
What is the interest rate for mortgage loans?

Action Required:
1. Review the customer's question
2. Prepare a comprehensive response
3. Update ticket status in system
4. Respond within 24-48 hours

Ticket Dashboard:
https://bankx.com/admin/tickets/TKT-2025-001234
```

**HTML**: Formatted table with priority indicators and action buttons.

## Email Service Implementation

### Azure Communication Services Integration

```python
from azure.communication.email import EmailClient

class EmailService:
    def __init__(self, connection_string: str):
        self.client = EmailClient.from_connection_string(connection_string)

    async def send_email(self, ticket_id, customer_email, ...):
        # Build customer email
        customer_message = {
            "content": {
                "subject": f"Support Ticket Created: {ticket_id}",
                "plainText": build_customer_email_plain(),
                "html": build_customer_email_html()
            },
            "recipients": {
                "to": [{"address": customer_email}]
            },
            "senderAddress": "noreply@bankx.com"
        }

        # Send to customer
        customer_poller = self.client.begin_send(customer_message)
        customer_result = customer_poller.result()

        # Send to bank team
        # ... (similar structure)
```

### Retry Logic

```python
async def send_email_with_retry(message, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await client.begin_send(message).result()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

## Running the Service

### Development Mode

```bash
# Set environment variables
export PROFILE=dev
export AZURE_COMMUNICATION_CONNECTION_STRING="endpoint=https://..."
export SENDER_EMAIL=noreply@bankx.com
export SUPPORT_TEAM_EMAIL=support@bankx.com
export PORT=8078
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
docker build -t escalation-comms-mcp:latest .

# Run container
docker run -p 8078:8078 \
  -e PROFILE=prod \
  -e AZURE_COMMUNICATION_CONNECTION_STRING=${CONNECTION_STRING} \
  escalation-comms-mcp:latest
```

## Environment Variables

See `.env.example` for complete configuration template.

**Required**:
- `AZURE_COMMUNICATION_CONNECTION_STRING` - Azure Communication Services connection string
- `SENDER_EMAIL` - From email address (default: `noreply@bankx.com`)

**Optional**:
- `SUPPORT_TEAM_EMAIL` - Support team email (default: `support@bankx.com`)
- `PORT` - Service port (default: 8078)
- `LOG_LEVEL` - Logging level (default: INFO)
- `EMAIL_RETRY_COUNT` - Max retry attempts (default: 3)
- `EMAIL_TIMEOUT_SECONDS` - Email send timeout (default: 30)

## Email Template Customization

### Adding Custom Templates

```python
# email_templates.py
def build_custom_email(ticket_id, customer_name, ...):
    return {
        "plain_text": f"""
Dear {customer_name},

Custom email content here...

Ticket ID: {ticket_id}

Best regards,
BankX Team
""",
        "html": f"""
<!DOCTYPE html>
<html>
<body>
    <h2>Dear {customer_name},</h2>
    <p>Custom HTML content...</p>
    <p><strong>Ticket ID:</strong> {ticket_id}</p>
</body>
</html>
"""
    }
```

### Template Variables

Available in all templates:
- `{ticket_id}` - Support ticket ID
- `{customer_id}` - Customer identifier
- `{query}` - Customer's original question
- `{use_case}` - UC2 or UC3
- `{reason}` - Why ticket was created
- `{timestamp}` - Creation timestamp

## Integration with UC2/UC3

### UC2 Integration (ProdInfoFAQ)

```python
# When confidence < 0.3 or out of scope
if confidence < 0.3:
    # Create ticket in CosmosDB
    ticket_id = await write_to_cosmosdb(...)

    # Send email notifications
    await escalation_comms_agent.send_email(
        ticket_id=ticket_id,
        customer_id=customer_id,
        customer_email=customer_email,
        query=user_query,
        use_case="UC2",
        reason=f"Low confidence ({confidence:.2f})"
    )

    return TICKET_CARD
```

### UC3 Integration (AIMoneyCoach)

```python
# For complex multi-topic or out of scope queries
if requires_human_advisor:
    ticket_id = await create_ticket(...)

    await escalation_comms_agent.send_email(
        ticket_id=ticket_id,
        customer_id=customer_id,
        customer_email=customer_email,
        query=user_query,
        use_case="UC3",
        reason="Complex multi-topic requiring human advisor"
    )

    return TICKET_CARD
```

## Testing

### Unit Tests

```bash
# Test email sending
pytest tests/test_email_service.py

# Test template generation
pytest tests/test_templates.py
```

### Integration Tests

```bash
# Test with Azure Communication Services
pytest tests/test_integration.py
```

### Manual Testing

```python
# Send test email
result = await send_email(
    ticket_id="TKT-TEST-001",
    customer_id="CUST-TEST",
    customer_email="test@example.com",
    query="Test query for email service",
    use_case="UC2",
    reason="Testing email functionality"
)

print(f"Email sent: {result['status']}")
print(f"Email ID: {result['email_id']}")
```

## Performance Targets

- **Email Send Latency**: < 1 second
- **Delivery Confirmation**: < 5 seconds
- **Retry Success Rate**: > 95%
- **Template Generation**: < 100ms

## Monitoring & Logging

Metrics tracked:
- Email send count (by use case)
- Delivery success rate
- Retry rate
- Average latency
- Template rendering time

Logs include:
```python
logger.info(f"Sending email for ticket {ticket_id} (UC{use_case})")
logger.info(f"Email sent to customer: {customer_email}")
logger.info(f"Email sent to support team: {SUPPORT_TEAM_EMAIL}")
```

## Error Handling

### Common Errors

1. **Connection String Invalid**
   ```
   Error: Invalid Azure Communication Services connection string
   Solution: Verify AZURE_COMMUNICATION_CONNECTION_STRING in environment
   ```

2. **Email Delivery Failed**
   ```
   Error: Failed to deliver email after 3 retries
   Solution: Check recipient email validity, verify ACS service status
   ```

3. **Template Rendering Error**
   ```
   Error: Missing template variable
   Solution: Ensure all required variables are provided
   ```

## Azure Resources Required

1. **Azure Communication Services**
   - Email service enabled
   - Domain verified (e.g., `bankx.com`)
   - Sender address configured: `noreply@bankx.com`

2. **Email Domain Setup**
   - DNS records configured (SPF, DKIM)
   - Domain verification completed
   - Sender authentication enabled

3. **Managed Identity** (Production)
   - Permissions: Communication Services Contributor

## Email Deliverability

### Best Practices

1. **SPF Record**: Add to DNS
   ```
   v=spf1 include:azurecomm.net ~all
   ```

2. **DKIM**: Configure in Azure Communication Services portal

3. **DMARC**: Add policy to DNS
   ```
   v=DMARC1; p=quarantine; rua=mailto:dmarc@bankx.com
   ```

4. **Sender Reputation**: Monitor bounce rates and spam reports

## Troubleshooting

### Emails not being delivered
- Check Azure Communication Services quota limits
- Verify domain verification status
- Review SPF/DKIM/DMARC configuration
- Check recipient's spam folder

### Template formatting issues
- Validate HTML structure
- Test plain text fallback
- Check character encoding (UTF-8)

### Slow email delivery
- Monitor Azure Communication Services metrics
- Check network latency
- Review retry backoff settings

## Related Services

- **UC2 ProdInfoFAQ** (port 8076) - Calls this service for ticket emails
- **UC3 AIMoneyCoach** (port 8077) - Calls this service for advisor requests
- **Copilot Backend** (port 8080) - Orchestrates UC2/UC3 agents

## References

- Azure Communication Services: https://learn.microsoft.com/azure/communication-services/
- Email Best Practices: https://learn.microsoft.com/azure/communication-services/concepts/email/email-best-practices
- MCP Documentation: https://modelcontextprotocol.io/

---

**Service Version**: 1.0.0
**Last Updated**: November 7, 2025
**Maintainer**: BankX Development Team
