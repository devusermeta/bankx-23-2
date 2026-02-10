# Copilot Studio Escalation Agent - Setup Guide

This guide walks you through creating the BankX Escalation Agent in Microsoft Copilot Studio with Azure Communication Services integration.

---

## Architecture Overview

```
Other A2A Agents → Azure Function (A2A Bridge) → Copilot Studio Agent
                                                        ↓
                                                  Power Automate Flow
                                                        ↓
                                    ┌──────────────────┴──────────────────┐
                                    ↓                                     ↓
                            Create Ticket                    Send Email via Azure
                        (Dataverse/SharePoint)              Communication Services
```

---

## Prerequisites

✅ **Required Resources**:
1. Microsoft Copilot Studio license
2. Azure subscription
3. Azure Communication Services resource (already deployed)
4. Power Platform environment
5. Dataverse or SharePoint for ticket storage

✅ **Access Requirements**:
- Copilot Studio maker permissions
- Power Automate flow creation access
- Azure Communication Services connection string

---

## Part 1: Create the Copilot Studio Agent

### Step 1: Create New Agent

1. Go to **Copilot Studio** (https://copilotstudio.microsoft.com)
2. Click **"Create"** → **"New copilot"**
3. **Name**: `BankX Escalation Agent`
4. **Language**: English
5. **Description**: "Handles support ticket creation and escalation for BankX customers"

### Step 2: Configure Generative AI

1. Go to **Settings** → **Generative AI**
2. Enable **"Generative answers"**
3. **Content moderation**: Enable (Recommended)
4. **How should your copilot interact with people?**
   - Upload the instructions from `escalation_cs_agent.md`
   - OR paste the instructions in the "Description" field

### Step 3: Create Global Variables

Go to **Variables** and create:

| Variable Name | Type | Scope | Default Value |
|--------------|------|-------|---------------|
| `CustomerID` | String | Global | (empty) |
| `CustomerEmail` | String | Global | (empty) |
| `CustomerName` | String | Global | (empty) |
| `TicketDescription` | String | Global | (empty) |
| `TicketPriority` | String | Global | "normal" |
| `TicketID` | String | Global | (empty) |
| `CreatedTicket` | Boolean | Global | false |

---

## Part 2: Create Topics

### Topic 1: **Greeting** (System Topic - Modify)

**Purpose**: Welcome message and context capture

**Trigger Phrases**: (Default greeting triggers)

**Conversation Nodes**:
1. **Message Node**: "Hello! I'm the BankX Escalation Agent. I can help you create support tickets for issues that need specialist attention. How can I help you today?"

---

### Topic 2: **Create Support Ticket** (Main Topic)

**Purpose**: Handle ticket creation in both A2A and interactive modes

**Trigger Phrases**:
- "Create a support ticket"
- "I need help"
- "Report an issue"
- "Create ticket"
- "Escalate this issue"

#### **Conversation Flow**:

##### Node 1: Check for A2A Pattern
**Condition Node**: Check if message contains "Create a support ticket for this issue:"

```
IF Conversation.LastUserText contains "Create a support ticket for this issue:"
    → Go to A2A Ticket Creation Flow
ELSE
    → Go to Interactive Ticket Creation Flow
```

---

#### **Branch A: A2A Ticket Creation Flow** (Agent-to-Agent)

##### Node A1: Parse A2A Message
**Power Fx Expression** (Parse customer details):

```power-fx
// Extract CustomerID (from format "[CustomerID: XXX]" if present)
Set(CustomerID,
    If(
        Find("[CustomerID: ", Conversation.LastUserText) > 0,
        Mid(
            Conversation.LastUserText,
            Find("[CustomerID: ", Conversation.LastUserText) + 13,
            Find("]", Conversation.LastUserText, Find("[CustomerID: ", Conversation.LastUserText)) - Find("[CustomerID: ", Conversation.LastUserText) - 13
        ),
        ""
    )
)

// Extract description (between "issue: " and ". Customer")
Set(TicketDescription, 
    Mid(
        Conversation.LastUserText, 
        Find("issue: ", Conversation.LastUserText) + 7,
        Find(". Customer email:", Conversation.LastUserText) - Find("issue: ", Conversation.LastUserText) - 7
    )
)

// Extract email (between "Customer email: " and ", Customer name:")
Set(CustomerEmail, 
    Mid(
        Conversation.LastUserText, 
        Find("Customer email: ", Conversation.LastUserText) + 16,
        Find(", Customer name:", Conversation.LastUserText) - Find("Customer email: ", Conversation.LastUserText) - 16
    )
)

// Extract name (after "Customer name: ")
Set(CustomerName, 
    Mid(
        Conversation.LastUserText, 
        Find("Customer name: ", Conversation.LastUserText) + 15
    )
)

// Default priority
Set(TicketPriority, "normal")
```

##### Node A2: Call Power Automate Flow
**Action**: Call "Create Ticket and Send Email" flow

**Input Parameters**:
- CustomerID: `Global.CustomerID`
- CustomerEmail: `Global.CustomerEmail`
- CustomerName: `Global.CustomerName`
- Description: `Global.TicketDescription`
- Priority: `Global.TicketPriority`

**Output**: Store in `Global.TicketID`

##### Node A3: Confirmation Message
**Message Node**:
```
✅ Ticket #{Global.TicketID} has been created successfully!
Our product specialist team will contact you at {Global.CustomerEmail} within 24 business hours.
A confirmation email has been sent with ticket details.
```

**Go to**: End of conversation

---

#### **Branch B: Interactive Ticket Creation Flow** (Direct Customer)

##### Node B1: Ask for Issue Description
**Question Node**: 
- **Message**: "I'd be happy to help create a support ticket. Could you please describe the issue you're experiencing?"
- **Identify**: Free text
- **Save response to**: `Global.TicketDescription`

##### Node B2: Determine Priority
**Condition Node**: Analyze description for urgency keywords

```
IF TicketDescription contains any ["card blocked", "locked", "unauthorized", "fraud", "cannot access", "urgent"]
    → Set Priority = "high"
ELSE IF TicketDescription contains any ["suggestion", "documentation", "feedback"]
    → Set Priority = "low"
ELSE
    → Set Priority = "normal"
```

##### Node B3: Check for Email in Context
**Condition Node**: 
```
IF Global.CustomerEmail is blank
    → Go to Node B4 (Ask for Email)
ELSE
    → Go to Node B5 (Check for Name)
```

##### Node B4: Ask for Email
**Question Node**:
- **Message**: "What email address should our team use to contact you?"
- **Identify**: Email
- **Save response to**: `Global.CustomerEmail`

##### Node B5: Check for Name in Context
**Condition Node**:
```
IF Global.CustomerName is blank
    → Go to Node B6 (Ask for Name)
ELSE
    → Go to Node B7 (Confirm Creation)
```

##### Node B6: Ask for Name
**Question Node**:
- **Message**: "And what is your full name?"
- **Identify**: Person name
- **Save response to**: `Global.CustomerName`

##### Node B7: Confirm Before Creation
**Question Node**:
- **Message**: 
```
I'll create a {Global.TicketPriority} priority support ticket for: "{Global.TicketDescription}"

Our support team will contact you at {Global.CustomerEmail} within {IF TicketPriority = "high" THEN "2-4 hours" ELSE "24 hours"}.

Shall I proceed with creating this ticket?
```
- **Identify**: Boolean (Yes/No)
- **Save response to**: `CreateConfirmed` (local variable)

##### Node B8: Conditional Creation
**Condition Node**:
```
IF CreateConfirmed = true
    → Go to Node B9 (Create Ticket)
ELSE
    → Go to Node B10 (Cancelled Message)
```

##### Node B9: Call Power Automate Flow
**Action**: Call "Create Ticket and Send Email" flow

**Input Parameters**:
- CustomerID: `Global.CustomerID`
- CustomerEmail: `Global.CustomerEmail`
- CustomerName: `Global.CustomerName`
- Description: `Global.TicketDescription`
- Priority: `Global.TicketPriority`

**Output**: Store in `Global.TicketID`

##### Node B10: Success Message
**Message Node**:
```
✅ Ticket #{Global.TicketID} has been created successfully!
Priority: {Global.TicketPriority}
Our support team will contact you at {Global.CustomerEmail} within {TimeframeBasedOnPriority}.
A confirmation email has been sent with all the details.

Is there anything else I can help you with?
```

##### Node B11: Cancelled Message
**Message Node**: "No problem! Let me know if you change your mind or need any other assistance."

---

### Topic 3: **Fallback** (System Topic - Modify)

**Purpose**: Handle unrecognized inputs

**Message Node**: 
```
I'm specifically designed to help with creating support tickets for issues that need specialist attention.

I can create a ticket for you if you describe your issue. Would you like me to create a support ticket?
```

---

## Part 2.5: Create Dataverse Table for Ticket Storage

### Purpose
Before creating the Power Automate flow, you need a place to store ticket data. This section shows how to create the required Dataverse table.

### Option A: Create Dataverse Table (Recommended)

#### Step 1: Navigate to Power Apps
1. Go to **Power Apps** (https://make.powerapps.com)
2. Select your environment (same as Copilot Studio environment)
3. Click **Tables** in left navigation
4. Click **+ New table** → **Create new table**

#### Step 2: Configure Table

**Table Properties:**
- **Display name**: `Tickets`
- **Plural name**: `Tickets`
- **Description**: `Support tickets for BankX customer issues`
- **Enable attachments**: No
- **Primary column**: Rename to `Ticket ID`

#### Step 3: Add Columns

Click **+ New column** for each of the following:

| Column Name | Data Type | Required | Additional Settings |
|-------------|-----------|----------|--------------------|
| **Customer ID** | Text | Yes | Max length: 50 |
| **Customer Email** | Email | Yes | - |
| **Customer Name** | Text | Yes | Max length: 200 |
| **Description** | Multiple lines of text | Yes | Max length: 4000 |
| **Status** | Choice | Yes | Choices: `Open` (default), `In Progress`, `Resolved`, `Closed` |
| **Priority** | Choice | Yes | Choices: `Low`, `Normal` (default), `High`, `Urgent` |
| **Category** | Text | Yes | Max length: 100, Default: "general" |
| **Assigned Team** | Text | No | Max length: 200 |
| **Created Date** | Date and Time | Yes | Behavior: User local, Default: Current date |
| **Updated Date** | Date and Time | Yes | Behavior: User local, Default: Current date |

#### Step 4: Create Choice Columns

**For Status column:**
1. Data type: **Choice**
2. Sync with global choice: **No** (create new)
3. Choices:
   - `Open` (Label: Open, Value: 1) - Set as default
   - `In Progress` (Label: In Progress, Value: 2)
   - `Resolved` (Label: Resolved, Value: 3)
   - `Closed` (Label: Closed, Value: 4)

**For Priority column:**
1. Data type: **Choice**
2. Sync with global choice: **No** (create new)
3. Choices:
   - `Low` (Label: Low, Value: 1)
   - `Normal` (Label: Normal, Value: 2) - Set as default
   - `High` (Label: High, Value: 3)
   - `Urgent` (Label: Urgent, Value: 4)

#### Step 5: Save and Publish
1. Click **Save table**
2. The table is now ready to use in Power Automate

---

### Option B: Create SharePoint List (Alternative)

If you prefer SharePoint over Dataverse:

#### Step 1: Create List
1. Go to your SharePoint site
2. Click **+ New** → **List**
3. Name: `BankX Support Tickets`
4. Description: `Customer support ticket tracking`

#### Step 2: Add Columns

| Column Name | Type | Settings |
|-------------|------|----------|
| **Ticket ID** | Single line of text | Default title column, rename it |
| **Customer ID** | Single line of text | Required |
| **Customer Email** | Single line of text | Required |
| **Customer Name** | Single line of text | Required |
| **Description** | Multiple lines of text | Required, Plain text |
| **Status** | Choice | Choices: Open (default), In Progress, Resolved, Closed |
| **Priority** | Choice | Choices: Low, Normal (default), High, Urgent |
| **Category** | Single line of text | Default: general |
| **Assigned Team** | Single line of text | Optional |

#### Step 3: Adjust Settings
1. Click **List settings**
2. Under **Advanced settings**:
   - Allow management of content types: No
   - Require content approval: No
3. Save changes

---

### Verification

✅ **Before proceeding to Part 3, ensure:**
- [ ] Table or list is created with all required columns
- [ ] Choice fields have all specified values
- [ ] Default values are set correctly
- [ ] You know the exact table/list name (you'll need it in Power Automate)

---

## Part 3: Create Power Automate Flow

### Flow Name: **Create Ticket and Send Email**

#### Trigger: **When Copilot Studio calls a flow**

**Input Parameters**:
1. `CustomerID` (String)
2. `CustomerEmail` (String)
3. `CustomerName` (String)
4. `Description` (String)
5. `Priority` (String) - Values: "low", "normal", "high"

#### Actions:

##### Action 1: Generate Ticket ID
**Compose** action:
- **Name**: GenerateTicketID
- **Inputs**: 
```
concat('TKT-', formatDateTime(utcNow(), 'yyyy'), '-', formatDateTime(utcNow(), 'MMddHHmmss'))
```
- **Output Example**: `TKT-2026-020512345`

##### Action 2: Create Ticket Record

**Option A: Using Dataverse**
- **Action**: Add a new row (Dataverse)
- **Table**: Tickets (create this table first)
- **Columns**:
  - Ticket ID: `outputs('GenerateTicketID')`
  - Customer ID: `triggerBody()['CustomerID']`
  - Customer Email: `triggerBody()['CustomerEmail']`
  - Customer Name: `triggerBody()['CustomerName']`
  - Description: `triggerBody()['Description']`
  - Priority: `triggerBody()['Priority']`
  - Status: "Open"
  - Created Date: `utcNow()`
  - Category: (determine based on description keywords)

**Option B: Using SharePoint**
- **Action**: Create item (SharePoint)
- **Site**: Your SharePoint site
- **List**: "BankX Support Tickets"
- **Fields**: Same as above

##### Action 3: Determine Response Timeframe
**Condition** action:
```
IF Priority equals "high"
    → Set ResponseTime = "2-4 business hours"
ELSE IF Priority equals "low"
    → Set ResponseTime = "48 business hours"
ELSE
    → Set ResponseTime = "24 business hours"
```

##### Action 4: Determine Team Assignment
**Switch** action based on Description keywords:

```
SWITCH (Description contains):
    "card" OR "atm" OR "credit" OR "debit"
        → Team = "Card Services Team"
        → Category = "Card Services"
    
    "account" OR "balance" OR "statement"
        → Team = "Account Specialist Team"
        → Category = "Account Services"
    
    "transaction" OR "payment" OR "transfer"
        → Team = "Fraud & Disputes Team"
        → Category = "Transaction Inquiry"
    
    "loan" OR "credit limit" OR "interest"
        → Team = "Lending Team"
        → Category = "Loan Services"
    
    DEFAULT
        → Team = "Product Specialist Team"
        → Category = "General Inquiry"
```

##### Action 5: Send Email via Azure Communication Services

**Action**: HTTP Request

**Method**: POST

**URI**: 
```
https://<your-acs-resource>.communication.azure.com/emails:send?api-version=2023-03-31
```

**Headers**:
```json
{
  "Content-Type": "application/json",
  "Authorization": "Bearer <access-token>"
}
```

**Body**:
```json
{
  "senderAddress": "support@<your-verified-domain>.com",
  "recipients": {
    "to": [
      {
        "address": "@{triggerBody()['CustomerEmail']}",
        "displayName": "@{triggerBody()['CustomerName']}"
      }
    ]
  },
  "content": {
    "subject": "BankX Support Ticket #@{outputs('GenerateTicketID')} Created",
    "html": "<html><body><h2>Support Ticket Created</h2><p>Dear @{triggerBody()['CustomerName']},</p><p>Thank you for contacting BankX Support. Your ticket has been created and assigned to our @{variables('AssignedTeam')}.</p><hr><p><strong>Ticket Details:</strong></p><ul><li><strong>Ticket ID:</strong> @{outputs('GenerateTicketID')}</li><li><strong>Priority:</strong> @{triggerBody()['Priority']}</li><li><strong>Category:</strong> @{variables('Category')}</li><li><strong>Description:</strong> @{triggerBody()['Description']}</li><li><strong>Created:</strong> @{formatDateTime(utcNow(), 'MMMM dd, yyyy h:mm tt')}</li></ul><hr><p><strong>What Happens Next:</strong></p><p>Our @{variables('AssignedTeam')} will review your ticket and contact you at this email address within <strong>@{variables('ResponseTime')}</strong>.</p><p>If you need to provide additional information, please reply to this email with your ticket number.</p><hr><p>Best regards,<br>BankX Support Team<br>support@bankx.com</p></body></html>"
  }
}
```

**Note**: Use Azure Communication Services connector if available, or HTTP action as shown above.

##### Action 6: Return Ticket ID to Copilot
**Response** action:
- **Output**: 
  - `TicketID`: `outputs('GenerateTicketID')`
  - `Success`: `true`

---

## Part 4: Configure Azure Communication Services

### Prerequisites:
1. Azure Communication Services resource deployed
2. Verified email domain configured

### Setup Steps:

#### 1. Get Connection String
```bash
# In Azure Portal
Navigate to: Communication Services resource → Keys
Copy: Primary connection string
```

#### 2. Add Domain and Verify
```bash
Navigate to: Communication Services → Email → Domains
Click: Add domain
Follow verification steps (add DNS records)
```

#### 3. Configure Sender Email
```bash
Navigate to: Domains → [your-domain] → From addresses
Add: support@[your-domain].com
Verify and enable
```

#### 4. Create Connection in Power Automate
```
Power Automate → Connections → New connection
Search: "HTTP"
Create HTTP connection for Azure Communication Services
OR
Search: "Azure Communication Services" connector (if available)
```

---

## Part 5: Create the A2A Bridge (Azure Function)

### Purpose
Translate A2A protocol requests → Copilot Studio Direct Line API

### Azure Function Code Structure

#### Function: **EscalationAgentBridge**

**File**: `escalation_bridge.py`

```python
import azure.functions as func
import json
import requests
import os
from datetime import datetime

# Copilot Studio Direct Line Configuration
DIRECT_LINE_SECRET = os.getenv("COPILOT_DIRECT_LINE_SECRET")
DIRECT_LINE_ENDPOINT = "https://directline.botframework.com/v3/directline"

def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    A2A Bridge for Escalation Agent
    Receives A2A formatted requests and forwards to Copilot Studio
    """
    
    if req.method == "POST" and req.url.endswith("/a2a/invoke"):
        return handle_a2a_invoke(req)
    
    elif req.method == "GET" and req.url.endswith("/.well-known/agent.json"):
        return handle_agent_card()
    
    elif req.method == "GET" and req.url.endswith("/health"):
        return handle_health_check()
    
    else:
        return func.HttpResponse("Not Found", status_code=404)


def handle_a2a_invoke(req: func.HttpRequest) -> func.HttpResponse:
    """Handle A2A invoke requests"""
    try:
        # Parse A2A request
        a2a_request = req.get_json()
        messages = a2a_request.get("messages", [])
        customer_id = a2a_request.get("customer_id", "")
        thread_id = a2a_request.get("thread_id", "")
        
        # Extract user message
        user_message = messages[-1]["content"] if messages else ""
        
        # Start or continue conversation with Copilot Studio
        conversation_id = thread_id  # Reuse thread_id as conversation_id
        
        if not conversation_id:
            # Start new conversation
            conversation_id = start_copilot_conversation()
        
        # Send message to Copilot Studio with customer context embedded
        # Format: [CustomerID: XXX] {original_message}
        # The Copilot Studio agent will parse this to extract customer_id
        enriched_message = f"[CustomerID: {customer_id}] {user_message}"
        copilot_response = send_to_copilot(conversation_id, enriched_message)
        
        # Convert Copilot response to A2A format
        a2a_response = {
            "role": "assistant",
            "content": copilot_response,
            "agent": "BankX Escalation Agent"
        }
        
        return func.HttpResponse(
            json.dumps(a2a_response),
            mimetype="application/json",
            status_code=200
        )
        
    except Exception as e:
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500
        )


def start_copilot_conversation():
    """Start new conversation with Copilot Studio via Direct Line"""
    headers = {
        "Authorization": f"Bearer {DIRECT_LINE_SECRET}"
    }
    
    response = requests.post(
        f"{DIRECT_LINE_ENDPOINT}/conversations",
        headers=headers
    )
    
    data = response.json()
    return data.get("conversationId")


def send_to_copilot(conversation_id, message):
    """Send message to Copilot Studio and get response"""
    headers = {
        "Authorization": f"Bearer {DIRECT_LINE_SECRET}",
        "Content-Type": "application/json"
    }
    
    # Send message
    payload = {
        "type": "message",
        "from": {"id": "user"},
        "text": message
    }
    
    requests.post(
        f"{DIRECT_LINE_ENDPOINT}/conversations/{conversation_id}/activities",
        headers=headers,
        json=payload
    )
    
    # Get response (poll for activities with retry)
    import time
    max_attempts = 5
    poll_interval = 2  # seconds
    
    for attempt in range(max_attempts):
        time.sleep(poll_interval)
        
        response = requests.get(
            f"{DIRECT_LINE_ENDPOINT}/conversations/{conversation_id}/activities",
            headers=headers
        )
        
        activities = response.json().get("activities", [])
        
        # Get last bot message
        for activity in reversed(activities):
            if activity.get("from", {}).get("id") == "bot":
                bot_message = activity.get("text", "")
                if bot_message:  # Only return non-empty messages
                    return bot_message
        
        # If no response yet and more attempts available, continue polling
        if attempt < max_attempts - 1:
            continue
    
    return "Unable to get response from Escalation Agent (timeout after 10 seconds)"


def handle_agent_card():
    """Return agent card (A2A protocol requirement)"""
    agent_card = {
        "agent_name": "BankX Escalation Agent",
        "agent_type": "domain",
        "version": "2.0.0",
        "description": "Handles support ticket creation and email escalations",
        "capabilities": [
            "create_support_ticket",
            "send_email_notification"
        ],
        "endpoints": {
            "http": os.getenv("FUNCTION_URL", "http://localhost:7071"),
            "a2a": f"{os.getenv('FUNCTION_URL')}/a2a/invoke",
            "health": f"{os.getenv('FUNCTION_URL')}/health"
        },
        "metadata": {
            "framework": "Microsoft Copilot Studio",
            "integration": "Direct Line API",
            "backend": "Azure Communication Services"
        }
    }
    
    return func.HttpResponse(
        json.dumps(agent_card, indent=2),
        mimetype="application/json",
        status_code=200
    )


def handle_health_check():
    """Health check endpoint"""
    health = {
        "status": "healthy",
        "service": "BankX Escalation Agent A2A Bridge",
        "timestamp": datetime.utcnow().isoformat(),
        "copilot_studio": "connected",
        "azure_communication_services": "enabled"
    }
    
    return func.HttpResponse(
        json.dumps(health),
        mimetype="application/json",
        status_code=200
    )
```

#### Deployment Configuration

**File**: `requirements.txt`
```
azure-functions
requests
```

**File**: `function.json`
```json
{
  "scriptFile": "escalation_bridge.py",
  "bindings": [
    {
      "authLevel": "function",
      "type": "httpTrigger",
      "direction": "in",
      "name": "req",
      "methods": ["get", "post"],
      "route": "{*route}"
    },
    {
      "type": "http",
      "direction": "out",
      "name": "$return"
    }
  ]
}
```

**Environment Variables**:
```
COPILOT_DIRECT_LINE_SECRET=<your-direct-line-secret>
FUNCTION_URL=https://<your-function-app>.azurewebsites.net
```

---

## Part 6: Connect Everything Together

### Step 1: Get Copilot Studio Direct Line Secret

1. Go to your Copilot in Copilot Studio
2. Navigate to **Settings** → **Channels**
3. Click **Direct Line**
4. Generate new secret key
5. Copy the secret

### Step 2: Deploy Azure Function

```bash
# Create Function App
az functionapp create \
  --name bankx-escalation-bridge \
  --resource-group bankx-rg \
  --storage-account bankxstorage \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4

# Set environment variables
az functionapp config appsettings set \
  --name bankx-escalation-bridge \
  --resource-group bankx-rg \
  --settings \
    COPILOT_DIRECT_LINE_SECRET="<your-secret>" \
    FUNCTION_URL="https://bankx-escalation-bridge.azurewebsites.net"

# Deploy function
func azure functionapp publish bankx-escalation-bridge
```

### Step 3: Update Agent Registry

Update other agents to point to the new escalation agent:

**File**: `agent-registry/registry.json`

```json
{
  "agents": [
    {
      "agent_name": "escalation-a2a",
      "endpoint": "https://bankx-escalation-bridge.azurewebsites.net/a2a/invoke",
      "agent_card_url": "https://bankx-escalation-bridge.azurewebsites.net/.well-known/agent.json",
      "health_url": "https://bankx-escalation-bridge.azurewebsites.net/health",
      "version": "2.0.0",
      "framework": "Copilot Studio"
    }
  ]
}
```

### Step 4: Test the Integration

```python
# Test A2A call from another agent
import requests

response = requests.post(
    "https://bankx-escalation-bridge.azurewebsites.net/a2a/invoke",
    json={
        "messages": [
            {
                "role": "user",
                "content": "Create a support ticket for this issue: What are credit card limits?. Customer email: john@example.com, Customer name: John Doe"
            }
        ],
        "customer_id": "CUST-001",
        "thread_id": "thread_123"
    }
)

print(response.json())
# Expected: {"role": "assistant", "content": "✅ Ticket #TKT-2026-... created...", "agent": "BankX Escalation Agent"}
```

---

## Part 7: Monitoring & Maintenance

### Copilot Studio Analytics
- **Navigate to**: Copilot Studio → Analytics
- **Monitor**: 
  - Total conversations
  - Ticket creation rate
  - Topic escalation paths
  - Customer satisfaction (if CSAT enabled)

### Azure Function Monitoring
```bash
# View logs
func azure functionapp logstream bankx-escalation-bridge

# Check metrics
az monitor metrics list \
  --resource /subscriptions/.../resourceGroups/bankx-rg/providers/Microsoft.Web/sites/bankx-escalation-bridge \
  --metric Requests
```

### Power Automate Flow Monitoring
- **Navigate to**: Power Automate → My flows → Create Ticket and Send Email
- **Check**: 28-day run history, failure rate, average duration

---

## Testing Checklist

✅ **Copilot Studio Agent**:
- [ ] Agent responds to greeting
- [ ] Creates ticket in interactive mode with confirmation
- [ ] Creates ticket immediately for A2A pattern
- [ ] Asks for email/name when not provided
- [ ] Determines priority correctly
- [ ] Provides ticket number in response

✅ **Power Automate Flow**:
- [ ] Generates unique ticket IDs
- [ ] Stores ticket in Dataverse/SharePoint
- [ ] Sends email via Azure Communication Services
- [ ] Email received with correct formatting
- [ ] Returns ticket ID to Copilot Studio

✅ **Azure Function Bridge**:
- [ ] Exposes A2A endpoints (invoke, agent card, health)
- [ ] Translates A2A requests to Direct Line format
- [ ] Passes customer_id in context
- [ ] Returns A2A-formatted responses
- [ ] Health check returns 200 OK

✅ **Integration**:
- [ ] Other agents can call escalation agent via A2A
- [ ] Customer context preserved throughout flow
- [ ] Email notification received within 2 minutes
- [ ] Ticket stored with all required fields

---

## Troubleshooting

### Issue: Copilot doesn't create ticket
**Solution**: Check Power Automate flow run history for errors

### Issue: Email not received
**Solution**: 
- Verify Azure Communication Services domain is verified
- Check spam folder
- Review ACS send logs in Azure Portal

### Issue: A2A bridge returns 500 error
**Solution**: 
- Check Direct Line secret is valid
- Verify function app has correct environment variables
- Review function logs for errors

### Issue: Ticket ID not returned
**Solution**: Check Power Automate flow output action includes TicketID field

---

## Next Steps

After setup is complete:

1. **Train the Copilot**: Add more sample questions to improve topic triggering
2. **Add CSAT**: Enable customer satisfaction survey after ticket creation
3. **Integrate with existing ticket system**: If you have ServiceNow/Dynamics 365, replace Dataverse storage with connector
4. **Add ticket viewing**: Create topic to view ticket status (requires additional flow)
5. **Implement SLA tracking**: Add automated priority escalation based on response time

---

## Summary

You now have:
- ✅ Copilot Studio agent with ticket creation capability
- ✅ Power Automate flow for ticket storage and email sending
- ✅ Azure Communication Services integration
- ✅ A2A bridge for backward compatibility
- ✅ Complete monitoring and testing setup

The escalation agent is now ready to handle both direct customer interactions and agent-to-agent escalations from other BankX agents!
