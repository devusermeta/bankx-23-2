# Azure AD App Registration - Setup Summary

## ✅ Completed Steps

### App Registration Created
- **App Name:** EscalationBridgeApp
- **App (Client) ID:** 5617a009-e330-4535-8431-98415c884b60
- **Object ID:** 205b6bbf-e9b1-4bcc-bf4d-ce763fb3faed
- **Tenant ID:** c1e8c736-fd22-4d7b-a7a2-12c6f36ac388

### Client Secret Created
- **Secret Name:** EscalationBridgeSecret
- **Secret Value:** sR38Q~_CR3-pky7PFo5OHpkVTEYigPPyzrHO0a3N
- **Expires:** February 10, 2028 (2 years)

### API Permissions Added
- ✅ Microsoft Graph - Files.ReadWrite.All (Application)
- ✅ Microsoft Graph - Mail.Send (Application)

### Service Principal Created
- ✅ Service Principal ID: 8123cc22-aedd-4b17-9ac8-2ab58c723a76

---

## ⚠️ IMPORTANT: Admin Consent Required

**The API permissions have been added but NOT yet consented.**

### Why Admin Consent is Needed
Application permissions (like Files.ReadWrite.All and Mail.Send) require an administrator to grant consent before they can be used.

### How to Grant Admin Consent

**Option 1: Azure Portal (Recommended)**

1. Go to https://portal.azure.com
2. Navigate to **Azure Active Directory** → **App registrations**
3. Search for and click on **EscalationBridgeApp**
4. Go to **API permissions** (left sidebar)
5. You should see:
   - Files.ReadWrite.All - ⚠️ Not granted
   - Mail.Send - ⚠️ Not granted
6. Click **"✓ Grant admin consent for Metakaal Pte Ltd"**
7. Click **"Yes"** to confirm
8. Wait for green checkmarks ✅ to appear

**Option 2: Azure CLI (if you have admin rights)**

```bash
az ad app permission admin-consent --id 5617a009-e330-4535-8431-98415c884b60
```

**Option 3: Contact Your Admin**

If you don't have admin rights, send this information to your IT administrator:

```
Application Name: EscalationBridgeApp
Application ID: 5617a009-e330-4535-8431-98415c884b60
Permissions Needed:
- Microsoft Graph - Files.ReadWrite.All (Application)
- Microsoft Graph - Mail.Send (Application)

Purpose: To access Excel Online files and send email notifications for the escalation agent
```

### Verify Admin Consent Was Granted

After admin consent, verify in Azure Portal:
- API permissions should show **Status: Granted for Metakaal Pte Ltd** with green checkmarks ✅

---

## ✅ Environment Configuration

The `.env` file has been created with:

**Configured:**
- ✅ Azure AD credentials (Client ID, Secret, Tenant ID)
- ✅ Service port (9006)
- ✅ Default values

**Needs Your Input:**
- ⚠️ Excel file path verification (currently set to use your OneDrive)
- ⚠️ Email sender address verification

### Current Excel Configuration

The `.env` file is configured to use:
```
EXCEL_USER_ID=Abhinav@metakaal.com
EXCEL_FILE_PATH=/tickets.xlsx
```

This assumes your `tickets.xlsx` file is in the root of your OneDrive.

**If the file is in a different location:**
1. Open the file in OneDrive/SharePoint
2. Note the actual path (e.g., `/Documents/tickets.xlsx`)
3. Update `EXCEL_FILE_PATH` in `.env`

---

## 📋 Next Steps

### 1. Get Admin Consent (REQUIRED)
Follow the instructions above to get admin consent for the API permissions.

### 2. Verify Excel File Location
```bash
# Make sure you're in the correct directory
cd d:\Metakaal\Updated_BankX\claude_bank\app\agents\escalation-copilot-bridge

# Run the setup checker
python setup_check.py
```

This will:
- ✅ Test Azure AD authentication
- ✅ Test Excel file access
- ✅ Verify table structure
- ✅ Optionally send test email

### 3. If Setup Check Passes
```bash
# Start the service
python main.py
```

### 4. If Setup Check Fails

**Common Issues:**

**"Failed to authenticate"**
- Check that admin consent was granted (see above)
- Verify credentials in `.env` are correct

**"Could not access Excel file"**
- Check `EXCEL_FILE_PATH` is correct
- Try opening the file in OneDrive to verify location
- Update `.env` if path is different

**"Failed to send email"**
- Verify `EMAIL_SENDER_ADDRESS` is correct
- Check admin consent was granted for Mail.Send

---

## 🔐 Security Notes

### Protect Your Credentials

The `.env` file contains sensitive credentials:
- ⚠️ **DO NOT commit `.env` to Git**
- ⚠️ **DO NOT share the client secret**
- ⚠️ Keep this file secure

The `.gitignore` should already exclude `.env` files.

### Client Secret Expiry

- **Expires:** February 10, 2028
- **Set Calendar Reminder:** January 2028 to rotate secret

To create a new secret before expiry:
```bash
az ad app credential reset --id 5617a009-e330-4535-8431-98415c884b60 --append
```

---

## 📞 Support

If you encounter issues:

1. **Run setup checker:** `python setup_check.py`
2. **Check logs:** Service logs show detailed error messages
3. **Verify admin consent:** Most issues are due to missing admin consent
4. **Test endpoints:** Use `/test/excel` and `/test/email` endpoints

---

## Summary

✅ **Completed:**
- App registration created
- Client secret generated
- API permissions added
- Service principal created
- `.env` file configured with credentials

⚠️ **Action Required:**
- **Get admin consent for API permissions** (CRITICAL)
- Verify Excel file path in `.env`
- Run `python setup_check.py` to validate

Once admin consent is granted and setup check passes, you're ready to start the service! 🚀
