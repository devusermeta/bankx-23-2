# Escalation Copilot Bridge

**A2A-compatible escalation agent using Microsoft Graph API for ticket storage and email notifications.**

This service replaces the MCP-based escalation agent and provides the same functionality using Microsoft Graph API to directly access Excel Online and Outlook, making it faster and more maintainable.

---

## Overview

**Architecture:**
```
ProdInfo/Other Agents (A2A) → Port 9006 → Escalation Bridge → Microsoft Graph API → Excel + Outlook
```

**What it does:**
1. ✅ Receives A2A requests from other agents (ProdInfo, AIMoneyCoach, etc.)
2. ✅ Parses customer information from messages
3. ✅ Generates unique ticket IDs (`TKT-YYYY-MMDDHHMMSS`)
4. ✅ Stores tickets in Excel Online (SharePoint/OneDrive)
5. ✅ Sends email notifications via Outlook
6. ✅ Returns confirmation to calling agent

**Key Features:**
- Native A2A protocol support
- Direct Microsoft Graph API integration (no Copilot Studio required)
- Runs on port 9006 (compatible with existing agents)
- Sub-10 second response times
- Full observability and logging

---

## Prerequisites

### 1. Excel File Setup

You should already have this from the Copilot Studio setup:

- ✅ Excel file named `tickets.xlsx` on OneDrive/SharePoint
- ✅ Excel table named `TicketsTable`
- ✅ 8 columns: Ticket ID, Customer ID, Customer Email, Customer Name, Description, Priority, Status, Created Date

**Location:** The file you created earlier at your SharePoint site.

### 2. Azure AD App Registration

You need to create an Azure AD app registration to access Microsoft Graph API:

**Required API Permissions:**
- `Files.ReadWrite.All` (for Excel access)
- `Mail.Send` (for sending emails)

📖 **See detailed instructions below** in the "Azure AD Setup" section.

---

## Quick Start

### Step 1: Install Dependencies

```bash
cd d:\Metakaal\Updated_BankX\claude_bank\app\agents\escalation-copilot-bridge
pip install -r requirements.txt
```

### Step 2: Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit .env with your details
notepad .env
```

### Step 3: Run the Service

```bash
python main.py
```

The service will start on **port 9006**.

### Step 4: Test the Service

**Test health:**
```bash
curl http://localhost:9006/health
```

**Test configuration:**
```bash
curl http://localhost:9006/config/status
```

**Test Excel access:**
```bash
curl http://localhost:9006/test/excel
```

**Test email:**
```bash
curl -X POST "http://localhost:9006/test/email?email_address=your@email.com"
```

**Test A2A ticket creation:**
```bash
curl -X POST http://localhost:9006/a2a/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Create ticket: Cannot login to account. Email: test@example.com, Name: Test User"}
    ],
    "customer_id": "CUST-001",
    "thread_id": "test-123"
  }'
```

---

## Azure AD Setup (Detailed Instructions)

### Step 1: Create App Registration

1. Go to **Azure Portal**: https://portal.azure.com
2. Navigate to **Azure Active Directory**
3. Click **App registrations** (left sidebar)
4. Click **+ New registration**

**Register an application:**
- **Name:** `EscalationBridgeApp` (or any name)
- **Supported account types:** Select "Accounts in this organizational directory only"
- **Redirect URI:** Leave blank (not needed for server-to-server)
- Click **Register**

### Step 2: Copy Application Details

After registration, you'll see the **Overview** page:

1. Copy **Application (client) ID** → This is `AZURE_CLIENT_ID`
2. Copy **Directory (tenant) ID** → This is `AZURE_TENANT_ID`

### Step 3: Create Client Secret

1. In your app registration, go to **Certificates & secrets** (left sidebar)
2. Click **+ New client secret**
3. **Description:** `EscalationBridgeSecret`
4. **Expires:** 24 months (or as per your policy)
5. Click **Add**
6. **IMPORTANT:** Copy the **Value** immediately → This is `AZURE_CLIENT_SECRET`
   - ⚠️ You won't be able to see it again!

### Step 4: Grant API Permissions

1. Go to **API permissions** (left sidebar)
2. Click **+ Add a permission**

**Add Files.ReadWrite.All:**
1. Select **Microsoft Graph**
2. Select **Application permissions** (not Delegated)
3. Search for **Files**
4. Expand **Files** and check ✅ **Files.ReadWrite.All**
5. Click **Add permissions**

**Add Mail.Send:**
1. Click **+ Add a permission** again
2. Select **Microsoft Graph**
3. Select **Application permissions**
4. Search for **Mail**
5. Expand **Mail** and check ✅ **Mail.Send**
6. Click **Add permissions**

### Step 5: Grant Admin Consent

1. In the **API permissions** page, click **✓ Grant admin consent for [Your Organization]**
2. Click **Yes** to confirm
3. Wait for the status to show green checkmarks ✅

### Step 6: Verify Permissions

Your API permissions list should show:

| Permission | Type | Status |
|------------|------|--------|
| Files.ReadWrite.All | Application | ✅ Granted |
| Mail.Send | Application | ✅ Granted |

---

## Excel File Configuration

You need to tell the bridge where your Excel file is located. There are 3 options:

### Option 1: Using Drive ID (Recommended)

**Find your Drive ID:**

```bash
# Using Graph Explorer (https://developer.microsoft.com/en-us/graph/graph-explorer)
GET /me/drive
```

Or using PowerShell:
```powershell
# Install Microsoft Graph PowerShell
Install-Module Microsoft.Graph -Scope CurrentUser

# Connect
Connect-MgGraph -Scopes "Files.Read"

# Get drive ID
Get-MgUserDrive -UserId "your-email@example.com"
```

**Set in .env:**
```env
EXCEL_DRIVE_ID=b!abc123...xyz789
EXCEL_FILE_PATH=/tickets.xlsx
```

### Option 2: Using SharePoint Site ID

**Find your SharePoint Site ID:**

Visit your SharePoint site and copy the URL. It will be something like:
```
https://yourcompany.sharepoint.com/sites/YourSite
```

Then use Graph Explorer:
```bash
GET /sites/yourcompany.sharepoint.com:/sites/YourSite
```

Copy the `id` field.

**Set in .env:**
```env
EXCEL_SITE_ID=yourcompany.sharepoint.com,abc-123-def,xyz-789-ghi
EXCEL_FILE_PATH=/Shared Documents/tickets.xlsx
```

### Option 3: Using User ID

**Set in .env:**
```env
EXCEL_USER_ID=your-email@example.com
EXCEL_FILE_PATH=/tickets.xlsx
```

---

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `AZURE_CLIENT_ID` | ✅ | Application (client) ID from Azure AD | `abc-123-def` |
| `AZURE_CLIENT_SECRET` | ✅ | Client secret value | `xyz~789...` |
| `AZURE_TENANT_ID` | ✅ | Directory (tenant) ID | `def-456-ghi` |
| `EXCEL_DRIVE_ID` | ⚠️ * | Drive ID for Excel file | `b!abc123...` |
| `EXCEL_SITE_ID` | ⚠️ * | SharePoint site ID | `site.sharepoint.com,...` |
| `EXCEL_USER_ID` | ⚠️ * | User email or ID | `user@example.com` |
| `EXCEL_FILE_PATH` | ✅ | Path to tickets.xlsx | `/tickets.xlsx` |
| `EXCEL_TABLE_NAME` | ✅ | Excel table name | `TicketsTable` |
| `EMAIL_SENDER_ADDRESS` | ✅ | Sender email address | `support@bankx.com` |
| `EMAIL_SENDER_NAME` | ❌ | Sender display name | `BankX Support Team` |
| `A2A_SERVER_PORT` | ❌ | Server port | `9006` |
| `LOG_LEVEL` | ❌ | Logging level | `INFO` |

**⚠️ * = One of EXCEL_DRIVE_ID, EXCEL_SITE_ID, or EXCEL_USER_ID must be set**

---

## API Endpoints

### A2A Endpoints

**POST `/a2a/invoke`** - Main A2A endpoint
- Receives ticket creation requests from other agents
- Parses customer information from message
- Creates ticket and sends email
- Returns confirmation

**GET `/.well-known/agent.json`** - Agent discovery
- Returns agent card for A2A registry
- Lists capabilities and endpoints

### Test Endpoints

**GET `/health`** - Health check
- Returns service health status
- Tests Microsoft Graph connection

**GET `/config/status`** - Configuration status
- Validates environment configuration
- Shows what's configured correctly

**GET `/test/excel`** - Test Excel access
- Tries to access Excel file
- Returns file information and columns

**POST `/test/email?email_address=YOUR_EMAIL`** - Test email
- Sends test email to verify configuration

### Utility Endpoints

**GET `/`** - Root endpoint
- Returns service information

---

## Message Format

### Request Format (from ProdInfo)

```json
{
  "messages": [
    {
      "role": "user",
      "content": "Create a support ticket for this issue: Cannot reset password. Customer email: customer@example.com, Customer name: John Doe"
    }
  ],
  "customer_id": "CUST-001",
  "thread_id": "thread-uuid-12345",
  "stream": false
}
```

### Response Format

```json
{
  "role": "assistant",
  "content": "Support ticket TKT-2026-02101430 created successfully. Email notification sent to customer. Our support team will contact the customer within 24 business hours.",
  "agent": "EscalationAgent"
}
```

---

## Integration with Existing Agents

### ProdInfo Agent

ProdInfo already calls the escalation agent on port 9006. No changes needed!

**Current code** (in `app/agents/prodinfo-faq-agent-a2a/agent_handler.py`):
```python
ESCALATION_AGENT_A2A_URL = "http://localhost:9006"

response = await client.post(
    f"{ESCALATION_AGENT_A2A_URL}/a2a/invoke",
    json={...}
)
```

### AIMoneyCoach Agent

Same - no changes needed if it calls port 9006.

### Supervisor Agent

Will automatically discover the escalation agent via agent registry.

---

## Deployment

### Running as Windows Service

1. Install NSSM: https://nssm.cc/download
2. Create service:

```powershell
nssm install EscalationBridge "C:\Python\python.exe" "d:\Metakaal\Updated_BankX\claude_bank\app\agents\escalation-copilot-bridge\main.py"
nssm set EscalationBridge AppDirectory "d:\Metakaal\Updated_BankX\claude_bank\app\agents\escalation-copilot-bridge"
nssm start EscalationBridge
```

### Running in Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

```bash
docker build -t escalation-bridge .
docker run -p 9006:9006 --env-file .env escalation-bridge
```

---

## Troubleshooting

### Issue: "Failed to authenticate with Microsoft Graph"

**Check:**
1. `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` are correct
2. Client secret hasn't expired
3. App has required permissions (Files.ReadWrite.All, Mail.Send)
4. Admin consent has been granted

**Test:**
```bash
curl http://localhost:9006/config/status
```

### Issue: "Failed to access Excel file"

**Check:**
1. One of `EXCEL_DRIVE_ID`, `EXCEL_SITE_ID`, or `EXCEL_USER_ID` is set
2. `EXCEL_FILE_PATH` is correct (must start with `/`)
3. File exists at the specified location
4. Table name matches (`TicketsTable`)

**Test:**
```bash
curl http://localhost:9006/test/excel
```

### Issue: "Failed to send email"

**Check:**
1. `EMAIL_SENDER_ADDRESS` is correct and exists
2. App has `Mail.Send` permission
3. The email account is in the same tenant

**Test:**
```bash
curl -X POST "http://localhost:9006/test/email?email_address=YOUR_EMAIL"
```

### Issue: "No user message found in request"

**Check:**
- Calling agent is sending messages array with at least one message with `role: "user"`

### Getting Help

Enable debug logging:
```env
LOG_LEVEL=DEBUG
```

Check logs for detailed error messages.

---

## Comparison with Old Escalation Agent

| Feature | Old (MCP-based) | New (Graph API) |
|---------|----------------|-----------------|
| Port | 9006 | 9006 ✅ |
| A2A Compatible | ✅ Yes | ✅ Yes |
| Storage | Cosmos DB | Excel Online |
| Email | Azure Comm Services | Outlook (Graph API) |
| Response Time | ~8-10 seconds | ~5-7 seconds ⚡ |
| Dependencies | MCP server, Cosmos, ACS | Only Microsoft Graph |
| Setup Complexity | High (5+ services) | Low (1 app registration) |
| Monthly Cost | $$$ | $ (included in M365) |
| Maintenance | Complex | Simple |

---

## Next Steps

1. ✅ Complete Azure AD app registration
2. ✅ Configure environment variables
3. ✅ Test all endpoints
4. ✅ Stop old escalation agent (port 9006)
5. ✅ Start new bridge
6. ✅ Test from ProdInfo agent
7. ✅ Monitor logs for 24 hours
8. ✅ Update documentation

---

## Support

- **Logs:** Check console output or log files
- **Configuration:** Run `/config/status` endpoint
- **Testing:** Use `/test/*` endpoints
- **Documentation:** Microsoft Graph API docs: https://learn.microsoft.com/en-us/graph/

---

**Ready to deploy! 🚀**
