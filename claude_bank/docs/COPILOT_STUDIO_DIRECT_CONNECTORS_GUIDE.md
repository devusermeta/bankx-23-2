# Copilot Studio Escalation Agent - Direct Connectors Approach

**Complete Step-by-Step Guide for Building the Escalation Agent without Power Automate**

---

## Overview

This guide will help you create a Copilot Studio escalation agent that:
- ✅ Generates ticket IDs using Power Fx
- ✅ Sends emails using Outlook connector (your personal email)
- ✅ Stores tickets in Excel file on OneDrive
- ✅ Responds in <10 seconds
- ✅ Works for interactive mode (A2A bridge will be added later)

**No Power Automate. No Dataverse. No Azure Communication Services. Just simple connectors!**

---

## Prerequisites

- [ ] Copilot Studio agent already created ("Escalation Agent")
- [ ] OneDrive account (personal or business)
- [ ] Outlook/Gmail account for sending emails
- [ ] Global variables already created in Copilot Studio

---

## Part 1: Create Excel Storage

### Step 1.1: Create Excel File in OneDrive

1. Go to **OneDrive** (onedrive.live.com)
2. Sign in with your Microsoft account
3. Click **New** → **Excel workbook**
4. Name the file: **`tickets.xlsx`**

### Step 1.2: Create Table Structure

1. In the Excel file, add these column headers in **Row 1**:

   | Ticket ID | Customer ID | Customer Email | Customer Name | Description | Priority | Status | Created Date |
   |-----------|-------------|----------------|---------------|-------------|----------|--------|--------------|

2. Select the entire header row (A1:H1)
3. Click **Insert** tab → **Table**
4. Check ✅ **"My table has headers"**
5. Click **OK**

### Step 1.3: Name the Table

1. With the table selected, go to **Table Design** tab (might appear as "Table Tools")
2. Find **"Table Name"** field (usually on the left)
3. Change the name from "Table1" to: **`TicketsTable`**
4. Press **Enter**

### Step 1.4: Save and Close

1. The file auto-saves in OneDrive
2. Keep the browser tab open or note the file location
3. Location will be: **OneDrive > Documents > tickets.xlsx** (or just OneDrive root)

**✅ Excel storage is ready!**

---

## Part 2: Update Copilot Studio Topic

### Step 2.1: Open Your Topic

1. Go to **Copilot Studio** (copilotstudio.microsoft.com)
2. Select your agent: **"Escalation Agent"**
3. Go to **Topics** tab
4. Open **"Create Support Ticket"** topic

### Step 2.2: Remove Power Automate Action (if present)

1. Find the **"Call a flow"** or **"Action"** node that calls Power Automate
2. Click the **"..."** menu on that node
3. Select **"Delete"**
4. Confirm deletion

Your flow should now look like:
```
Trigger
  ↓
Question: Issue description
  ↓
Question: Email
  ↓
Question: Name
  ↓
Confirmation message
  ↓
Question: Yes/No (ConfirmCreate)
  ↓
Condition: ConfirmCreate = true?
  ├─ TRUE → (empty - we'll add nodes here)
  └─ FALSE → Message "No problem!"
```

---

## Part 3: Add Ticket ID Generation

### Step 3.1: Add Set Variable Node

1. In the **TRUE** branch of the condition (after user confirms)
2. Click **"+"** button
3. Select **"Variable management"** → **"Set a variable value"**

### Step 3.2: Configure Ticket ID Generation

1. **Variable to set:** Select `Global.TicketID` from dropdown
2. **To value:** Click the function icon **fx** 
3. Delete any existing value
4. Enter this **Power Fx formula**:

   ```
   Concatenate("TKT-", Text(Now(), "yyyy-MMddHHmmss"))
   ```

5. This will generate ticket IDs like: `TKT-2026-02091430`

### Step 3.3: Verify

1. The formula should show no errors (no red underlines)
2. Click **"Done"** or **"Save"**

**✅ Ticket ID generation is configured!**

---

## Part 4: Add Email Connector

### Step 4.1: Add Connector Action

1. Below the "Set variable" node, click **"+"**
2. Select **"Call an action"**
3. Choose **"Add a connector"**

### Step 4.2: Find Outlook Connector

1. In the search box, type: **"Office 365 Outlook"**
2. Select **"Office 365 Outlook"** from results
3. Choose action: **"Send an email (V2)"**

> **Note:** If you're using Gmail, search for **"Gmail"** connector instead and select "Send email"

### Step 4.3: Authenticate

1. Click **"Sign in"** button
2. Choose your Microsoft account (or Gmail account)
3. Grant permissions when prompted
4. Wait for "Connected" status

### Step 4.4: Configure Email Fields

**To:**
1. Click the input field
2. Select **"Insert variable"** (or use formula bar)
3. Choose: `Global.CustomerEmail`

**Subject:**
1. Click the input field
2. Enter: `Support Ticket Created - `
3. Click **"Insert variable"**
4. Choose: `Global.TicketID`
5. Final result: `Support Ticket Created - {Global.TicketID}`

**Body:**
1. Click the **"Body"** field
2. Click the **"</>**" (HTML) toggle if available, or just paste as text
3. Enter this HTML template:

```html
<html>
<body style="font-family: Arial, sans-serif; color: #333;">
  <h2 style="color: #0066cc;">Support Ticket Created</h2>
  
  <p>Dear <strong>{Global.CustomerName}</strong>,</p>
  
  <p>Your support ticket has been successfully created.</p>
  
  <table style="border-collapse: collapse; width: 100%; max-width: 600px; margin: 20px 0;">
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; background-color: #f5f5f5; width: 150px;"><strong>Ticket ID:</strong></td>
      <td style="padding: 10px; border: 1px solid #ddd;">{Global.TicketID}</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; background-color: #f5f5f5;"><strong>Description:</strong></td>
      <td style="padding: 10px; border: 1px solid #ddd;">{Global.TicketDescription}</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; background-color: #f5f5f5;"><strong>Priority:</strong></td>
      <td style="padding: 10px; border: 1px solid #ddd;">{Global.TicketPriority}</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; background-color: #f5f5f5;"><strong>Status:</strong></td>
      <td style="padding: 10px; border: 1px solid #ddd;">Open</td>
    </tr>
  </table>
  
  <p>Our support team will contact you at <strong>{Global.CustomerEmail}</strong> within 24 business hours.</p>
  
  <p style="margin-top: 30px;">
    Best regards,<br>
    <strong>BankX Support Team</strong>
  </p>
  
  <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">
  <p style="font-size: 12px; color: #999;">
    This is an automated message. Please do not reply to this email.
  </p>
</body>
</html>
```

4. **IMPORTANT:** Replace `{Global.VariableName}` placeholders with actual variables:
   - Click on `{Global.CustomerName}` text → Delete it → Insert variable → Choose `Global.CustomerName`
   - Repeat for `{Global.TicketID}`, `{Global.TicketDescription}`, `{Global.TicketPriority}`, `{Global.CustomerEmail}`

**Advanced Options (Optional):**
- **Importance:** Normal
- **Is HTML:** Yes (toggle on if available)

### Step 4.5: Save Email Action

1. Click **"Save"** or **"Done"**
2. You should see the connector node in your flow

**✅ Email connector is configured!**

---

## Part 5: Add Excel Storage Connector

### Step 5.1: Add Excel Connector Action

1. Below the email connector node, click **"+"**
2. Select **"Call an action"**
3. Choose **"Add a connector"**

### Step 5.2: Find Excel Connector

1. Search for: **"Excel Online (OneDrive)"**
2. Select **"Excel Online (OneDrive)"**
3. Choose action: **"Add a row into a table"**

### Step 5.3: Authenticate

1. Click **"Sign in"**
2. Sign in with your OneDrive account (same as where you created tickets.xlsx)
3. Grant permissions

### Step 5.4: Configure Excel Storage

**Location:**
- Select: **OneDrive**

**Document Library:**
- Select: **OneDrive**

**File:**
1. Click the dropdown (folder icon)
2. Navigate to where you saved `tickets.xlsx`
3. Click on **tickets.xlsx** to select it
4. If you don't see it, you might need to type the path: `/tickets.xlsx` or `/Documents/tickets.xlsx`

**Table:**
- After selecting the file, this dropdown should populate
- Select: **TicketsTable**

**Column Mappings:**

Now map each Excel column to Copilot Studio variables:

1. **Ticket ID:**
   - Click field → Insert variable → `Global.TicketID`

2. **Customer ID:**
   - Click field → Insert variable → `Global.CustomerID`

3. **Customer Email:**
   - Click field → Insert variable → `Global.CustomerEmail`

4. **Customer Name:**
   - Click field → Insert variable → `Global.CustomerName`

5. **Description:**
   - Click field → Insert variable → `Global.TicketDescription`

6. **Priority:**
   - Click field → Insert variable → `Global.TicketPriority`

7. **Status:**
   - Click field → Type: `Open` (hardcoded text)

8. **Created Date:**
   - Click field → Click formula bar **fx**
   - Enter: `Text(Now(), "yyyy-MM-dd HH:mm:ss")`
   - This generates: `2026-02-09 14:30:45`

### Step 5.5: Save Excel Action

1. Click **"Save"** or **"Done"**
2. Verify all fields are mapped (no red errors)

**✅ Excel storage is configured!**

---

## Part 6: Add Success Message

### Step 6.1: Add Message Node

1. Below the Excel connector, click **"+"**
2. Select **"Send a message"**

### Step 6.2: Configure Success Message

Enter this message:

```
✅ **Ticket Created Successfully!**

Your support ticket **{Global.TicketID}** has been created.

**Details:**
- Email: {Global.CustomerEmail}
- Priority: {Global.TicketPriority}

📧 A confirmation email has been sent to your address.

Our support team will contact you within **24 business hours**.

Thank you for your patience! 🙏
```

### Step 6.3: Replace Variables

1. Click on `{Global.TicketID}` → Delete → Insert variable → `Global.TicketID`
2. Repeat for `{Global.CustomerEmail}` and `{Global.TicketPriority}`

### Step 6.4: Save

Click **"Save"** or **"Done"**

**✅ Success message is configured!**

---

## Part 7: Final Topic Structure

Your complete flow should now look like:

```
[Trigger: The agent chooses]
  ↓
[Question] Describe your issue
  → Sets: Global.TicketDescription
  ↓
[Question] What is your email address?
  → Sets: Global.CustomerEmail
  ↓
[Question] What is your full name?
  → Sets: Global.CustomerName
  ↓
[Message] "I'll create a support ticket for: {description}..."
  ↓
[Question] Shall I proceed? (Yes/No)
  → Sets: ConfirmCreate (topic variable)
  ↓
[Condition] ConfirmCreate = true?
  ├─ TRUE:
  │   ↓
  │  [Set Variable] Global.TicketID = Concat("TKT-", ...)
  │   ↓
  │  [Connector: Office 365 Outlook] Send email
  │   ↓
  │  [Connector: Excel Online] Add row to TicketsTable
  │   ↓
  │  [Message] "✅ Ticket {TicketID} created successfully..."
  │
  └─ FALSE:
      ↓
     [Message] "No problem! Let me know if you need help."
```

---

## Part 8: Save and Publish

### Step 8.1: Save the Topic

1. Click **"Save"** button at the top right of the topic editor
2. Wait for "Saved successfully" confirmation

### Step 8.2: Publish the Agent

1. Click **"Publish"** button at the top right of Copilot Studio
2. Review changes
3. Click **"Publish"** to confirm
4. Wait for "Published successfully" message

**✅ Agent is live!**

---

## Part 9: Testing

### Step 9.1: Open Test Panel

1. In Copilot Studio, click **"Test"** button (top right)
2. The test panel should open on the right side
3. If you see old conversation, click **"New test session"** or **"Reset"**

### Step 9.2: Test the Complete Flow

**Test Conversation:**

**You:** `I need help with my account`

**Bot:** `I'd be happy to help! Could you please describe the issue you're experiencing?`

**You:** `I cannot login to my bank account`

**Bot:** `What is your email address?`

**You:** `purohitabhinav2001@gmail.com` (use your REAL email for testing)

**Bot:** `And what is your full name?`

**You:** `Abhinav Purohit` (use your real name)

**Bot:** `I'll create a support ticket for: I cannot login to my bank account. Our team will contact you at purohitabhinav2001@gmail.com within 24 hours. Shall I proceed with creating this ticket?`

**You:** `Yes`

**Bot:** Should show "Processing..." then:
`✅ Ticket Created Successfully! Your support ticket TKT-2026-02091445 has been created...`

### Step 9.3: Verify Results

**Check 1: Success Message**
- ✅ Did you see the success message with a ticket ID like `TKT-2026-02091445`?
- ✅ Was the ticket ID displayed correctly?

**Check 2: Email Received**
1. Open your email inbox (purohitabhinav2001@gmail.com)
2. Look for email with subject: "Support Ticket Created - TKT-XXXX"
3. Verify email contains:
   - ✅ Your name
   - ✅ Ticket ID
   - ✅ Description
   - ✅ Priority
   - ✅ Formatted HTML (not plain text)

> **Note:** Email may take 1-2 minutes to arrive. Check spam folder if not in inbox.

**Check 3: Excel Storage**
1. Go to **OneDrive** (onedrive.live.com)
2. Open **tickets.xlsx** file
3. Verify new row added with:
   - ✅ Ticket ID: TKT-2026-02091445
   - ✅ Customer ID: CUST-001 (or whatever value you set)
   - ✅ Customer Email: purohitabhinav2001@gmail.com
   - ✅ Customer Name: Abhinav Purohit
   - ✅ Description: I cannot login to my bank account
   - ✅ Priority: normal
   - ✅ Status: Open
   - ✅ Created Date: 2026-02-09 14:45:23

### Step 9.4: Test Edge Cases

**Test 2: Cancel Flow**

**You:** `I need help`

(Go through questions, but at the end...)

**You:** `No` (when asked to proceed)

**Bot:** `No problem! Let me know if you need help.`

- ✅ No email should be sent
- ✅ No ticket should be created in Excel

**Test 3: Different Priority**

(Before testing, you'll need to update CustomerID and Priority variables)

1. In the topic, before the confirmation message, add two "Set variable" nodes:
   - Set `Global.CustomerID` to `"CUST-999"`
   - Set `Global.TicketPriority` to `"high"`

2. Test again and verify Excel shows:
   - ✅ Customer ID: CUST-999
   - ✅ Priority: high

---

## Part 10: Troubleshooting

### Issue 1: Email Not Sent

**Symptoms:** Success message shows, but no email received

**Possible Causes & Solutions:**

1. **Email connector not authenticated:**
   - Go back to topic editor
   - Click on Outlook connector node
   - Check if it says "Connected"
   - If not, click "Sign in" again

2. **Wrong email address:**
   - Verify you typed your email correctly during testing
   - Check Global.CustomerEmail variable is being set

3. **Email went to spam:**
   - Check your spam/junk folder
   - Mark as "Not spam" if found

4. **Variables not inserted correctly:**
   - Edit the email action
   - Ensure `{Global.VariableName}` are replaced with actual variable tokens (they should look like small blue pills/tags, not plain text)

### Issue 2: No Row Added to Excel

**Symptoms:** Email sent, but Excel file unchanged

**Possible Causes & Solutions:**

1. **Excel connector not authenticated:**
   - Check if Excel action shows "Connected"
   - Re-authenticate if needed

2. **Wrong file or table selected:**
   - Edit Excel action
   - Verify File = tickets.xlsx
   - Verify Table = TicketsTable (not Table1 or other name)

3. **Table not created properly:**
   - Open tickets.xlsx in OneDrive
   - Check if you see "Table Design" tab when clicking on headers
   - If not, recreate the table (Part 1, Step 1.2)

4. **Column mapping errors:**
   - Edit Excel action
   - Check all columns are mapped (no red warnings)
   - Verify variable names match exactly

### Issue 3: "Processing" Hangs Forever

**Symptoms:** Bot shows "Processing..." and never responds

**Possible Causes & Solutions:**

1. **Connector timeout:**
   - Wait 30-60 seconds
   - If still processing, there's an error
   - Check connector configurations

2. **Excel file locked:**
   - Close Excel file in OneDrive (if you have it open)
   - Try again

3. **Permission issues:**
   - Re-authenticate both Outlook and Excel connectors
   - Grant all requested permissions

### Issue 4: Ticket ID Shows as Empty or "undefined"

**Symptoms:** Success message shows `Ticket {} created` or `Ticket undefined created`

**Solution:**

1. Check the "Set Variable" node for TicketID
2. Verify the Power Fx formula is exactly:
   ```
   Concat("TKT-", Text(Now(), "yyyy-MMddHHmmss"))
   ```
3. Make sure variable is set BEFORE the success message
4. Check variable name is `Global.TicketID` (capital I, capital D)

### Issue 5: Variables Not Set During Testing

**Symptoms:** CustomerID or Priority show as empty

**Solution:**

For MVP testing, you can hardcode these values:

1. Add "Set variable" nodes at the start of TRUE branch:
   ```
   Set Global.CustomerID = "CUST-001"
   Set Global.TicketPriority = "normal"
   ```

2. Later, these will be parsed from A2A messages

---

## Part 11: Performance Metrics

Expected performance:

| Metric | Target | Actual (measure yours) |
|--------|--------|------------------------|
| Total Response Time | <10 seconds | __________ |
| Email Delivery | <2 minutes | __________ |
| Excel Row Added | Instant | __________ |
| Success Rate | 100% | __________ |

**How to Measure:**
1. Note time when you click "Yes" to create ticket
2. Note time when success message appears
3. Calculate difference

---

## Part 12: What's Next?

Once testing is successful (all ✅ checks passed):

### Immediate Next Steps:
- [ ] Test with multiple tickets (create 3-5 tickets)
- [ ] Verify Excel file can handle multiple rows
- [ ] Test with different email providers (if needed)
- [ ] Document any issues encountered

### After MVP Works:
- [ ] Add trigger phrases to topic (keywords like "create ticket", "I need help")
- [ ] Add message parsing for A2A mode (extract CustomerID from messages)
- [ ] Build A2A Bridge (Azure Function) for agent-to-agent communication
- [ ] Update agent registry to point to A2A Bridge
- [ ] Test A2A integration with ProdInfo agent
- [ ] Add more features (view tickets, close tickets, etc.)

---

## Summary Checklist

**Setup:**
- [ ] Excel file created in OneDrive with TicketsTable
- [ ] Table has 8 columns: Ticket ID, Customer ID, Customer Email, Customer Name, Description, Priority, Status, Created Date
- [ ] Copilot Studio topic updated with all nodes
- [ ] Power Fx formula for ticket ID added
- [ ] Outlook connector authenticated and configured
- [ ] Excel connector authenticated and configured
- [ ] Success message added

**Testing:**
- [ ] Test conversation completed successfully
- [ ] Email received with correct information
- [ ] Excel row added with all data
- [ ] Ticket ID generated correctly (format: TKT-YYYY-MMDDHHMMSS)
- [ ] Cancel flow works (no email/storage when user says "No")

**Verification:**
- [ ] Opened tickets.xlsx and saw the new row
- [ ] Email HTML formatting looks good
- [ ] Response time was <10 seconds
- [ ] All variables populated correctly

---

## Support & Resources

**Documentation:**
- Copilot Studio Connectors: https://learn.microsoft.com/en-us/microsoft-copilot-studio/connectors
- Power Fx Functions: https://learn.microsoft.com/en-us/power-platform/power-fx/formula-reference

**Common Power Fx Functions:**
- `Now()` - Current datetime
- `Text(value, format)` - Format value as text
- `Concat(text1, text2, ...)` - Join strings

**Excel Table Requirements:**
- Must be a proper Excel Table (not just cells)
- Table must have a name (default: Table1, we changed to TicketsTable)
- All columns must have headers

---

**Once all tests pass, you're ready to build the A2A Bridge! 🚀**

Move on to the next phase: Creating the Azure Function A2A Bridge to enable agent-to-agent communication.
