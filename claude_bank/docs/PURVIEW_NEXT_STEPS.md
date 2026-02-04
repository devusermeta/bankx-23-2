# Purview Integration - Next Steps

**Status**: ✅ Purview account created, ⏳ Provisioning in progress  
**Date**: November 17, 2025

---

## 📍 Current Status

- ✅ **Purview Account**: Created (`bankx-purview`)
- ✅ **Location**: Southeast Asia
- ✅ **Endpoints**: Available
  - Catalog: https://bankx-purview.purview.azure.com/catalog
  - Scan: https://bankx-purview.purview.azure.com/scan
- ⏳ **Provisioning State**: Creating (check status with `.\scripts\check_purview_status.ps1`)
- ⏳ **Role Assignments**: Pending (do after provisioning completes)
- ✅ **Configuration**: Updated in `.env.dev.example`

---

## 🎯 What to Do Now

### **Step 1: Monitor Provisioning** (5-10 minutes)

Run this command to check status:
```powershell
.\scripts\check_purview_status.ps1
```

Wait until status shows **"Succeeded"** before proceeding to Step 2.

---

### **Step 2: Assign Roles to 7 Service Principals** (15 minutes)

Once provisioning completes:

#### **A. Open Purview Governance Portal**
1. Go to Azure Portal → Search "bankx-purview"
2. Click **"Open Microsoft Purview Governance Portal (new)"**
3. Or directly: https://bankx-purview.purview.azure.com

#### **B. Navigate to Role Assignments**
1. In Purview Portal, click **Data Map** (left sidebar)
2. Click **Collections**
3. Select **"bankx-purview"** (root collection)
4. Click **"Role assignments"** tab

#### **C. Add Each Service Principal**

For EACH of the 7 service principals below:
1. Click **"Add"** button
2. Select role: **"Data curator"**
3. In search box, paste the **App ID**
4. Select the service principal from results
5. Click **"OK"**

**Service Principals to Add:**

```
1. BankX-AccountAgent-SP
   App ID: f7219061-e3db-4dfb-a8de-2b5fa4b98ccf

2. BankX-TransactionAgent-SP
   App ID: abdde3bd-954f-4626-be85-c995faeec314

3. BankX-PaymentAgent-SP
   App ID: 19c0d01f-228b-45e0-b337-291679acb75c

4. BankX-ProdInfoAgent-SP
   App ID: cd8e9191-1d08-4bd2-9dbe-e23139dcbd90

5. BankX-MoneyCoachAgent-SP
   App ID: b81a5e18-1760-4836-8a5e-e4ef2e8f1113

6. BankX-EscalationAgent-SP
   App ID: 019b1746-a104-437a-b1ff-a911ba8c356c

7. BankX-SupervisorAgent-SP
   App ID: cbb7c307-5c43-4999-ada4-63a934853ec5
```

**Shortcut**: Copy App IDs from `docs/PURVIEW_ROLE_ASSIGNMENT_CHECKLIST.txt`

---

### **Step 3: Register Data Sources** (10 minutes)

After role assignments:

#### **Option A: Manual Registration (Recommended for now)**

1. In Purview Portal → **Data Map** → **Sources**
2. Click **"Register"** button
3. For each data source:

**JSON Files** (4 sources):
- Select source type: **"Files"**
- Name: `accounts-json`
- Path: `d:/Metakaal/BankX/data/accounts.json`
- Classification: PII, PCI_DSS, GDPR_PERSONAL_DATA

Repeat for:
- `transactions.json` (PCI_DSS, FINANCIAL_DATA)
- `beneficiaries.json` (PCI_DSS, FINANCIAL_DATA)
- `limits.json` (BUSINESS_RULE)

**Cosmos DB** (if using):
- Select source type: **"Azure Cosmos DB"**
- Name: `cosmos-support-tickets`
- Database: bankx
- Container: support_tickets
- Enable scan to auto-discover schema

#### **Option B: Automated Registration (Future)**
Once we implement the integration code, data sources will be automatically registered when first accessed.

---

### **Step 4: Test Service Principal Authentication** (5 minutes)

After role assignments complete, test that service principals can authenticate:

```powershell
# Test AccountAgent SP
$clientId = "f7219061-e3db-4dfb-a8de-2b5fa4b98ccf"
$clientSecret = "<get-from-PURVIEW_SERVICE_PRINCIPALS_CREDENTIALS.md>"
$tenantId = "c1e8c736-fd22-4d7b-a7a2-12c6f36ac388"

$body = @{
    client_id = $clientId
    client_secret = $clientSecret
    grant_type = "client_credentials"
    scope = "https://purview.azure.net/.default"
}

$tokenResponse = Invoke-RestMethod `
    -Uri "https://login.microsoftonline.com/$tenantId/oauth2/v2.0/token" `
    -Method Post `
    -Body $body

if ($tokenResponse.access_token) {
    Write-Host "✅ Authentication successful!" -ForegroundColor Green
    Write-Host "Token: $($tokenResponse.access_token.Substring(0,20))..." -ForegroundColor Gray
} else {
    Write-Host "❌ Authentication failed" -ForegroundColor Red
}
```

---

### **Step 5: Update Integration Vision Document** (Optional)

Review and update `docs/PURVIEW_INTEGRATION_VISION.md` with:
- ✅ Actual Purview account name: `bankx-purview`
- ✅ Actual endpoints
- ✅ Actual location: Southeast Asia
- Update any references to "bankx-purview-eastus" → "bankx-purview"

---

## 📚 Reference Documents

- **Purview Account Details**: `docs/PURVIEW_ACCOUNT_CREATION_COMPLETE.md`
- **Role Assignment Checklist**: `docs/PURVIEW_ROLE_ASSIGNMENT_CHECKLIST.txt`
- **Service Principal Credentials**: `PURVIEW_SERVICE_PRINCIPALS_CREDENTIALS.md` (DO NOT COMMIT)
- **Integration Vision**: `docs/PURVIEW_INTEGRATION_VISION.md`
- **Option B Implementation**: `docs/PURVIEW_OPTION_B_IMPLEMENTATION_GUIDE.md`

---

## 🔄 After Completing All Steps

Once Steps 1-4 are complete:

1. **Come back here** and we'll implement the integration code:
   - `app/purview/agent_purview_service.py`
   - `app/purview/purview_service_factory.py`
   - `app/purview/batch_lineage_tracker.py`
   - Update `AuditedMCPTool` to send to Purview

2. **Test lineage tracking**:
   - Make a test API call through an agent
   - Check Purview Portal for lineage data
   - Verify field-level tracking

3. **Configure batch mode** (5-minute interval as selected)

---

## ⚠️ Important Notes

- **Provisioning takes 5-10 minutes**: Be patient, check with `.\scripts\check_purview_status.ps1`
- **Role assignments are in Purview Portal**: NOT Azure Portal (different RBAC system)
- **Secrets in Key Vault**: Service principal secrets already stored in `kv-bankx-9843`
- **Location is Southeast Asia**: Not East US (free tier limitation)

---

## ✅ Checklist

- [ ] Provisioning completed (status = "Succeeded")
- [ ] Opened Purview Governance Portal
- [ ] Assigned "Data curator" role to 7 service principals
- [ ] Registered data sources (JSON files, Cosmos DB)
- [ ] Tested service principal authentication
- [ ] Updated configuration files
- [ ] Ready for integration code implementation

**Current Progress**: Step 1 in progress (provisioning)

**Next Action**: Wait for provisioning to complete, then assign roles in Step 2
