# Escalation Copilot Bridge - Quick Start Guide

Follow these steps to get the Escalation Copilot Bridge running on port 9006.

---

## Step 1: Azure AD App Registration (15 minutes)

### 1.1 Create App Registration

1. Go to https://portal.azure.com
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **+ New registration**
   - Name: `EscalationBridgeApp`
   - Account type: "Accounts in this organizational directory only"
   - Click **Register**

### 1.2 Note These Values

From the **Overview** page, copy:
- ✏️ **Application (client) ID**: `______________________________________`
- ✏️ **Directory (tenant) ID**: `______________________________________`

### 1.3 Create Client Secret

1. Go to **Certificates & secrets**
2. Click **+ New client secret**
3. Description: `EscalationBridgeSecret`, Expires: 24 months
4. Click **Add**
5. ⚠️ **COPY THE VALUE IMMEDIATELY:**
   - ✏️ **Client secret**: `______________________________________`

### 1.4 Grant API Permissions

1. Go to **API permissions**
2. Click **+ Add a permission** → **Microsoft Graph** → **Application permissions**
3. Add these permissions:
   - ✅ **Files.ReadWrite.All** (under Files)
   - ✅ **Mail.Send** (under Mail)
4. Click **✓ Grant admin consent for [Your Organization]**
5. Confirm and verify green checkmarks appear

---

## Step 2: Find Your Excel File Details (5 minutes)

You need to find where your `tickets.xlsx` file is located.

### Option A: If file is in your OneDrive

1. Go to Graph Explorer: https://developer.microsoft.com/en-us/graph/graph-explorer
2. Sign in with your account
3. Run: `GET /me/drive`
4. Copy the **id** field:
   - ✏️ **Drive ID**: `______________________________________`

### Option B: If file is in SharePoint

1. Open your SharePoint site in browser
2. Copy the URL (e.g., `https://company.sharepoint.com/sites/MySite`)
3. In Graph Explorer, run: `GET /sites/company.sharepoint.com:/sites/MySite`
4. Copy the **id** field:
   - ✏️ **Site ID**: `______________________________________`

### File Path

Where is your `tickets.xlsx` file?
- ✏️ **File Path**: `/____________________` (e.g., `/tickets.xlsx` or `/Documents/tickets.xlsx`)

---

## Step 3: Install and Configure (5 minutes)

### 3.1 Install Dependencies

Open PowerShell:

```powershell
cd d:\Metakaal\Updated_BankX\claude_bank\app\agents\escalation-copilot-bridge
pip install -r requirements.txt
```

### 3.2 Create .env File

```powershell
# Copy template
cp .env.example .env

# Open in notepad
notepad .env
```

### 3.3 Fill in .env File

Paste in your values from above:

```env
# Azure AD
AZURE_CLIENT_ID=your-client-id-from-step-1.2
AZURE_CLIENT_SECRET=your-client-secret-from-step-1.3
AZURE_TENANT_ID=your-tenant-id-from-step-1.2

# Excel (choose ONE option based on Step 2)
EXCEL_DRIVE_ID=your-drive-id-from-step-2
EXCEL_FILE_PATH=/tickets.xlsx
EXCEL_TABLE_NAME=TicketsTable

# Email
EMAIL_SENDER_ADDRESS=your-email@example.com
EMAIL_SENDER_NAME=BankX Support Team

# Service
A2A_SERVER_PORT=9006
LOG_LEVEL=INFO
```

Save and close.

---

## Step 4: Validate Configuration (2 minutes)

Run the setup validator:

```powershell
python setup_check.py
```

This will:
- ✅ Validate your configuration
- ✅ Test Microsoft Graph authentication
- ✅ Test Excel file access
- ✅ Check table structure
- ✅ Optionally send test email

**Fix any errors before proceeding.**

---

## Step 5: Start the Service (1 minute)

```powershell
python main.py
```

You should see:

```
INFO - Starting EscalationCopilotBridge v1.0.0
INFO - Port: 9006
INFO - Configuration validated successfully
INFO - Successfully authenticated with Microsoft Graph API
INFO - EscalationCopilotBridge started successfully
```

**Leave this running.**

---

## Step 6: Test the Service (5 minutes)

Open a **new PowerShell window**.

### Test 1: Health Check

```powershell
curl http://localhost:9006/health
```

Expected: `{"status": "healthy", ...}`

### Test 2: Agent Card

```powershell
curl http://localhost:9006/.well-known/agent.json
```

Expected: JSON with agent capabilities.

### Test 3: Create a Test Ticket

```powershell
curl -X POST http://localhost:9006/a2a/invoke `
  -H "Content-Type: application/json" `
  -d '{
    "messages": [
      {"role": "user", "content": "Create ticket: Test issue from setup. Email: YOUR_EMAIL@example.com, Name: Test User"}
    ],
    "customer_id": "CUST-TEST",
    "thread_id": "test-123"
  }'
```

Expected: `{"role": "assistant", "content": "Support ticket TKT-2026-... created successfully", ...}`

### Test 4: Verify Results

1. **Check Excel file:**
   - Open `tickets.xlsx` in OneDrive/SharePoint
   - You should see a new row with ticket `TKT-2026-...`

2. **Check your email:**
   - Open your inbox
   - You should have received a "Support Ticket Created" email

---

## Step 7: Integration with ProdInfo (2 minutes)

### Stop Old Escalation Agent

If the old escalation agent is running on port 9006:

```powershell
# Find the process
Get-Process | Where-Object {$_.Name -like "*python*"}

# Stop it (replace PID with actual process ID)
Stop-Process -Id <PID>
```

### Test from ProdInfo

The ProdInfo agent is already configured to call port 9006:

1. Make sure ProdInfo agent is running (port 9004)
2. Chat with ProdInfo agent
3. Ask a question it can't answer
4. When it offers to create a ticket, say "Yes"
5. Verify ticket is created via the new bridge

---

## Step 8: Monitor and Validate (ongoing)

### Check Logs

Watch the service logs for any errors:

```
INFO - Received A2A request for customer: CUST-001
INFO - Parsed ticket: TKT-2026-02101534 for customer@example.com
INFO - Adding ticket TKT-2026-02101534 to Excel table
INFO - Successfully added ticket TKT-2026-02101534 to Excel
INFO - Sending email to ['customer@example.com']
INFO - Successfully sent email: Support Ticket Created - TKT-2026-02101534
INFO - A2A request processed successfully
```

### Verify Daily

For the first few days:
- ✅ Check Excel file has new tickets
- ✅ Verify emails are being sent
- ✅ Confirm ProdInfo integration works
- ✅ Monitor service logs for errors

---

## Troubleshooting

### Error: "Failed to authenticate with Microsoft Graph"

**Fix:**
- Verify `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` in .env
- Check client secret hasn't expired
- Ensure admin consent was granted

### Error: "Failed to access Excel file"

**Fix:**
- Verify `EXCEL_DRIVE_ID` or `EXCEL_SITE_ID` is correct
- Check `EXCEL_FILE_PATH` starts with `/`
- Ensure file exists at that location
- Run `python setup_check.py` to diagnose

### Error: "Failed to send email"

**Fix:**
- Verify `EMAIL_SENDER_ADDRESS` is correct
- Check Mail.Send permission was granted
- Ensure admin consent was granted

### Port 9006 already in use

**Fix:**
```powershell
# Find what's using port 9006
netstat -ano | findstr :9006

# Stop the old escalation agent
Stop-Process -Id <PID>
```

---

## Success Checklist

- [x] Azure AD app registered with permissions
- [x] .env file configured
- [x] `python setup_check.py` passes all checks
- [x] Service starts on port 9006
- [x] Health check returns healthy
- [x] Test ticket creation works
- [x] Excel file updated with test ticket
- [x] Email notification received
- [x] Old escalation agent stopped
- [x] ProdInfo integration tested

---

**🎉 You're all set! The Escalation Copilot Bridge is now handling your A2A ticket creation requests.**

Next: Monitor for 24-48 hours to ensure stability, then update documentation.
