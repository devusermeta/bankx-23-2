# A2A Escalation Integration Guide

## 🎯 Overview

You've successfully replaced your MCP-based escalation agent with a **Copilot Studio escalation agent** that works via A2A protocol. This allows your other banking agents to create support tickets through the more robust Copilot Studio infrastructure.

## 📋 Architecture Flow

```
┌─────────────────┐    A2A Protocol    ┌─────────────────────┐    Power Automate    ┌─────────────────┐
│  Other Agents   │ ─────────────────► │  Escalation Bridge  │ ──────────────────► │ Copilot Studio  │
│ (ProdInfo, etc) │                    │    (Port 9006)      │                     │     Agent       │
└─────────────────┘                    └─────────────────────┘                     └─────────────────┘
                                                                                           │
                                                                                           ▼
                                                                             ┌─────────────────┐
                                                                             │ Outlook + Excel │
                                                                             │  Integration    │
                                                                             └─────────────────┘
```

## 🚀 Quick Start

### 1. Start the A2A Bridge

```powershell
# Navigate to escalation bridge
cd claude_bank\app\agents\escalation-copilot-bridge

# Start the bridge service (Port 9006)
python main.py
```

### 2. Test the Integration

```powershell
# Run the enhanced test suite
python test_a2a_escalation.py

# Or use the PowerShell runner
.\run_a2a_test.ps1
```

### 3. Verify Results

1. **Check Console Output**: Look for ticket ID (e.g., `TKT-20260213105201`)
2. **Check Email**: Verify email sent to customer email address
3. **Check Excel**: Verify ticket entry in Excel spreadsheet

## 📝 Test Cases

### Manual Test Replication
Your exact manual test scenario:
- **Customer**: Abhinav (CUST-001)
- **Email**: purohitabhinav01@gmail.com
- **Issue**: Login problems
- **Expected Result**: High-priority ticket with email notification

### A2A Protocol Format
```json
{
  "messages": [
    {
      "role": "user",
      "content": "I want to raise a ticket. My name is Abhinav, emailID is purohitabhinav01@gmail.com, I am not able to login to the bank application, my customer ID is CUST-001"
    }
  ],
  "customer_id": "CUST-001",
  "thread_id": "manual-test-replica-20260213105500"
}
```

## 🔄 Integration with Other Agents

### How Other Agents Call the Escalation Bridge

```python
import httpx

async def escalate_to_support(customer_info, issue_description):
    """Call escalation bridge from any agent"""
    
    escalation_url = "http://localhost:9006/a2a/invoke"
    
    payload = {
        "messages": [
            {
                "role": "user", 
                "content": f"I want to raise a ticket. {issue_description}. {customer_info}"
            }
        ],
        "customer_id": customer_info.get("customer_id"),
        "thread_id": f"auto-escalation-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(escalation_url, json=payload)
        return response.json()
```

### Example: ProdInfo Agent → Escalation

```python
# When ProdInfo agent needs to escalate
customer_data = {
    "name": "John Doe",
    "email": "john.doe@example.com", 
    "customer_id": "CUST-123"
}

issue = "Customer experiencing login issues after password reset"

# Call escalation bridge
result = await escalate_to_support(customer_data, issue)

# Result will contain ticket ID and confirmation
```

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# Copilot Studio Configuration
COPILOT_BOT_ID=your-bot-id
COPILOT_BOT_TENANT_ID=your-tenant-id
COPILOT_DIRECT_LINE_SECRET=your-direct-line-secret

# Power Automate Configuration (Alternative)
POWER_AUTOMATE_FLOW_URL=your-flow-url

# A2A Configuration
A2A_SERVER_PORT=9006
AGENT_REGISTRY_URL=http://localhost:9000
```

### Agent Registry Registration
The bridge automatically registers with your agent registry:
```json
{
  "agent_name": "EscalationCopilotBridge",
  "agent_type": "escalation",  
  "version": "1.0.0",
  "capabilities": [
    "escalation.create_ticket",
    "ticket.create", 
    "support.escalate"
  ],
  "endpoints": {
    "a2a": "http://localhost:9006/a2a/invoke",
    "health": "http://localhost:9006/health"
  }
}
```

## 🎛️ Available Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/a2a/invoke` | POST | **Main A2A escalation endpoint** |
| `/health` | GET | Health check |
| `/.well-known/agent.json` | GET | Agent discovery |
| `/test/power-automate` | POST | Test Power Automate connection |
| `/config/status` | GET | Check configuration |

## 🧪 Testing Scenarios

### Scenario 1: Login Issues (Your Manual Test)
```bash
Customer: Abhinav
Email: purohitabhinav01@gmail.com  
Issue: Cannot login to bank application
Priority: High (login issues are high priority)
Expected: TKT-XXXXXX created, email sent
```

### Scenario 2: Payment Failures
```bash
Customer: Alice Smith
Email: alice.smith@example.com
Issue: Payment transactions failing
Priority: High (payment issues)
Expected: TKT-XXXXXX created, priority escalation
```

### Scenario 3: Card Issues
```bash
Customer: Bob Johnson  
Issue: Lost credit card, needs blocking
Priority: Critical (security issue)
Expected: Immediate ticket creation
```

## 🔍 Troubleshooting

### Common Issues

1. **Bridge Not Starting**
   - Check port 9006 availability
   - Verify .env configuration
   - Check Python dependencies

2. **Copilot Studio Not Responding**  
   - Verify Direct Line secret
   - Check bot publication status
   - Test Power Automate flow

3. **No Email Sent**
   - Check Outlook connector in Power Automate
   - Verify email permissions
   - Test flow manually in Power Platform

4. **Excel Not Updated**
   - Check Excel connector permissions
   - Verify file path and table ID
   - Test Excel access manually

### Debug Commands

```powershell
# Check bridge health
curl http://localhost:9006/health

# Check configuration  
curl http://localhost:9006/config/status

# Test Power Automate connection
curl -X POST http://localhost:9006/test/power-automate

# View logs
python main.py # Watch console output
```

## 🎉 Success Criteria

Your A2A → Copilot Studio integration is working correctly when:

✅ **Bridge Health**: `/health` endpoint returns healthy status  
✅ **A2A Processing**: Messages processed correctly  
✅ **Ticket Creation**: TKT-XXXXXX ID generated  
✅ **Email Notification**: Customer receives email  
✅ **Excel Storage**: Ticket logged in spreadsheet  
✅ **Response Format**: Proper A2A response returned  

## 📞 Support

If you encounter issues:

1. **Check Logs**: Monitor console output for errors
2. **Test Components**: Use individual test endpoints  
3. **Verify Configuration**: Run `/config/status`
4. **Manual Testing**: Test Copilot Studio agent directly

---

**🚀 You're now ready to replace your MCP escalation agent with this more robust Copilot Studio solution!**