# Copilot Studio - Required Information Checklist

## What You Need to Get from Copilot Studio

Before you can run the bridge, gather these pieces of information:

---

### ✅ 1. Direct Line Secret Key (REQUIRED)

**Where to get it:**
1. Open [Copilot Studio](https://copilotstudio.microsoft.com/)
2. Sign in with **metakaal.com** account
3. Select your environment
4. Open your **Escalation Agent**
5. Go to **Settings** → **Channels**
6. Find **Direct Line** channel
7. Click **Turn on** if not already enabled
8. Click **Show** next to **Key 1** or **Key 2**
9. Copy the entire key (long string)

**What it looks like:**
```
abc123XYZ...very-long-string-of-characters...xyz789
```

**Where to put it:**
```dotenv
# In your .env file:
COPILOT_DIRECT_LINE_SECRET=paste-the-key-here
```

---

### ✅ 2. Bot/Agent Name (REQUIRED)

**Where to get it:**
- This is the name you gave your agent in Copilot Studio
- You can see it in the Copilot Studio home page

**Example:**
```
EscalationAgent
```

**Where to put it:**
```dotenv
# In your .env file:
COPILOT_BOT_NAME=EscalationAgent
```

---

### ✅ 3. Azure Tenant ID (REQUIRED)

**Where to get it:**
1. Go to [Azure Portal](https://portal.azure.com)
2. Sign in with **metakaal.com** account
3. Click **Microsoft Entra ID** (or Azure Active Directory)
4. In the Overview page, find **Tenant ID**
5. Copy the GUID

**What it looks like:**
```
12345678-1234-1234-1234-123456789abc
```

**Where to put it:**
```dotenv
# In your .env file:
AZURE_TENANT_ID=12345678-1234-1234-1234-123456789abc
```

---

### 📋 4. Environment ID (OPTIONAL but helpful)

**Where to get it:**
- In Copilot Studio, look at the browser URL
- The URL contains: `https://copilotstudio.microsoft.com/environments/{environment-id}/...`
- Copy the GUID from the URL

**Example:**
```
Default-87654321-4321-4321-4321-abcdef123456
```

**Where to put it:**
```dotenv
# In your .env file (optional):
COPILOT_ENVIRONMENT_ID=Default-87654321-4321-4321-4321-abcdef123456
```

---

### 📋 5. Bot ID (OPTIONAL)

**Where to get it:**
- Sometimes shown in Copilot Studio settings
- Not always easily visible
- This is optional and mostly for reference

**Where to put it:**
```dotenv
# In your .env file (optional):
COPILOT_BOT_ID=your-bot-id-if-you-have-it
```

---

## Quick Checklist

Print this and check off as you get each item:

- [ ] **Direct Line Secret Key** - from Copilot Studio → Settings → Channels → Direct Line
- [ ] **Bot/Agent Name** - the name of your Copilot Studio agent
- [ ] **Azure Tenant ID** - from Azure Portal → Entra ID → Overview
- [ ] Environment ID (optional)
- [ ] Bot ID (optional)

---

## What If I Can't Find Something?

### Can't find Direct Line channel?

**Solution:**
- In Copilot Studio, go to **Settings** → **Channels**
- Scroll through the list to find "Direct Line"
- If not visible, check:
  - Are you an owner/contributor of the agent?
  - Is the agent published?
  - Are you in the correct environment?

### Don't have permissions?

**Requirements:**
- You need **Owner** or **Contributor** access to the Copilot Studio agent
- You need **Reader** access to Azure tenant (for Tenant ID)

**Who can help:**
- Azure administrator for metakaal.com tenant
- Copilot Studio agent owner/creator

### Agent not showing up?

**Check:**
- Are you signed in with the correct account? (metakaal.com)
- Are you in the correct environment?
- Did someone else create the agent?

---

## Test Your Credentials

Once you have the credentials, test them:

### Test 1: Direct Line API (manual)

```powershell
# Replace YOUR_SECRET with your Direct Line secret
curl -X POST "https://directline.botframework.com/v3/directline/conversations" `
  -H "Authorization: Bearer YOUR_SECRET"
```

**Expected result:** You should get back JSON with a `conversationId`

### Test 2: Configuration Check

```powershell
cd d:\Metakaal\Updated_BankX\claude_bank\app\agents\escalation-copilot-bridge

# After creating .env file
python -c "from config import settings, validate_settings; is_valid, errors = validate_settings(); print('Valid:', is_valid); [print(f'  Error: {e}') for e in errors]"
```

**Expected result:** `Valid: True`

---

## Sample .env File

Here's what your `.env` should look like with real values:

```dotenv
# Copilot Studio Configuration
COPILOT_DIRECT_LINE_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6.q7r8s9t0u1v2w3x4y5z6
COPILOT_DIRECT_LINE_ENDPOINT=https://directline.botframework.com/v3/directline
COPILOT_BOT_NAME=EscalationAgent
COPILOT_BOT_ID=12345678-abcd-1234-abcd-123456789abc (optional)
COPILOT_ENVIRONMENT_ID=Default-87654321-4321-4321-4321-abcdef123456 (optional)
COPILOT_TIMEOUT_SECONDS=30
COPILOT_MAX_RESPONSE_WAIT=30

# Azure Configuration
AZURE_TENANT_ID=98765432-dcba-4321-dcba-abcdef654321

# Service Configuration
A2A_SERVER_PORT=9006
AGENT_REGISTRY_URL=http://localhost:9000
LOG_LEVEL=INFO
```

---

## That's It!

Once you have these credentials, you're ready to:

1. Create the `.env` file with your values
2. Run `pip install -r requirements.txt`
3. Run `python main.py`
4. Test with `python test_a2a_escalation.py`

---

## Important Notes

⚠️ **Keep your Direct Line Secret secure!**
- Don't commit it to Git
- Don't share it publicly
- Store it securely

✅ **The bridge will:**
- Use the same Excel file your Copilot Studio agent uses
- Use the same Outlook account your Copilot Studio agent uses
- Call your existing Copilot Studio agent (no changes needed there)

✅ **You don't need to:**
- Duplicate any resources
- Change your Copilot Studio agent
- Create new Excel files or email accounts
- Deploy anything to Azure (bridge runs locally)

---

## Need Help?

If you're stuck getting these credentials:

1. **Check Copilot Studio documentation** for Direct Line channel setup
2. **Contact your Azure administrator** for tenant information
3. **Ask the Copilot Studio agent owner** if you don't have permissions
4. **Check the full setup guide** in `COPILOT_STUDIO_SETUP.md`

---

**Summary:** You need 3 things (2 mandatory, 1 optional):
1. ✅ **Direct Line Secret** (from Copilot Studio)
2. ✅ **Bot Name** (from Copilot Studio)
3. ✅ **Tenant ID** (from Azure Portal)

That's all you need to get started! 🚀
