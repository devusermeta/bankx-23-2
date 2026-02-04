# Purview Account Creation - COMPLETE

**Date**: November 17, 2025  
**Status**: ✅ **SUCCESS**

---

## 🎉 Purview Account Created

**Account Details**:
- **Name**: bankx-purview
- **Resource Group**: rg-multimodaldemo
- **Location**: Southeast Asia
- **Subscription**: e0783b50-4ca5-4059-83c1-524f39faa624
- **Tenant**: c1e8c736-fd22-4d7b-a7a2-12c6f36ac388 (Metakaal)
- **SKU**: Standard
- **Provisioning State**: Creating (endpoints available)

**Managed Identity**:
- **Type**: SystemAssigned
- **Principal ID**: 8cbe4453-e80c-4041-bddf-872ca58db0c7
- **Tenant ID**: c1e8c736-fd22-4d7b-a7a2-12c6f36ac388

**Endpoints**:
- **Catalog**: https://bankx-purview.purview.azure.com/catalog
- **Scan**: https://bankx-purview.purview.azure.com/scan
- **Guardian**: https://bankx-purview.purview.azure.com/guardian

**Resource ID**:
```
/subscriptions/e0783b50-4ca5-4059-83c1-524f39faa624/resourceGroups/rg-multimodaldemo/providers/Microsoft.Purview/accounts/bankx-purview
```

---

## 📋 Next Steps: Assign Roles to Service Principals

Purview uses its **own RBAC system** (not Azure RBAC). You must assign roles through the **Purview Portal UI**.

### **Step 1: Open Purview Governance Portal**

1. Go to Azure Portal: https://portal.azure.com
2. Search for **"bankx-purview"**
3. Click on the Purview account
4. Click **"Open Microsoft Purview Governance Portal"** button
5. This will open: https://bankx-purview.purview.azure.com

### **Step 2: Assign "Data Curator" Role to Service Principals**

For each of the 7 service principals, follow these steps:

#### **A. Navigate to Role Assignments**
1. In Purview Governance Portal, click **Data map** (left sidebar)
2. Click **Collections** → **Root collection** (or your collection name)
3. Click **Role assignments** tab

#### **B. Add Service Principal to Data Curator Role**

Repeat for all 7 service principals:

**1. BankX-AccountAgent-SP**
- Role: **Data curator**
- Service Principal App ID: `f7219061-e3db-4dfb-a8de-2b5fa4b98ccf`

**2. BankX-TransactionAgent-SP**
- Role: **Data curator**
- Service Principal App ID: `abdde3bd-954f-4626-be85-c995faeec314`

**3. BankX-PaymentAgent-SP**
- Role: **Data curator**
- Service Principal App ID: `19c0d01f-228b-45e0-b337-291679acb75c`

**4. BankX-ProdInfoAgent-SP**
- Role: **Data curator**
- Service Principal App ID: `cd8e9191-1d08-4bd2-9dbe-e23139dcbd90`

**5. BankX-MoneyCoachAgent-SP**
- Role: **Data curator**
- Service Principal App ID: `b81a5e18-1760-4836-8a5e-e4ef2e8f1113`

**6. BankX-EscalationAgent-SP**
- Role: **Data curator**
- Service Principal App ID: `019b1746-a104-437a-b1ff-a911ba8c356c`

**7. BankX-SupervisorAgent-SP**
- Role: **Data curator**
- Service Principal App ID: `cbb7c307-5c43-4999-ada4-63a934853ec5`

#### **C. How to Add Each Service Principal**

1. Click **"Add"** button in Role assignments
2. Select role: **"Data curator"**
3. In the search box, paste the **App ID** (e.g., `f7219061-e3db-4dfb-a8de-2b5fa4b98ccf`)
4. Select the service principal from results (should show as "BankX-AccountAgent-SP")
5. Click **"OK"**
6. Repeat for all 7 service principals

---

## 📊 Register Data Sources

After assigning roles, register your data sources in Purview:

### **Data Sources to Register**:

1. **accounts.json** (Local JSON file)
2. **transactions.json** (Local JSON file)
3. **beneficiaries.json** (Local JSON file)
4. **limits.json** (Local JSON file)
5. **cosmos_support_tickets** (Azure Cosmos DB)

### **How to Register**:

#### **For JSON Files** (Manual Registration via UI):

1. In Purview Governance Portal, go to **Data map** → **Sources**
2. Click **"Register"**
3. Select **"Files"** as data source type
4. Fill in:
   - **Name**: accounts-json
   - **Type**: JSON
   - **Path**: `d:/Metakaal/BankX/data/accounts.json`
   - **Description**: Customer account master data
5. Click **"Register"**
6. Repeat for other JSON files

#### **For Cosmos DB** (Automated Scan):

1. In Purview Governance Portal, go to **Data map** → **Sources**
2. Click **"Register"**
3. Select **"Azure Cosmos DB"**
4. Fill in:
   - **Name**: cosmos-support-tickets
   - **Cosmos DB Account**: (your Cosmos DB account name)
   - **Database**: bankx
   - **Container**: support_tickets
5. Click **"Register"**
6. Create a **Scan** to automatically discover schema

---

## 🔐 Update Environment Variables

Add these to your `.env` file:

```bash
# Microsoft Purview Configuration
PURVIEW_ACCOUNT_NAME=bankx-purview
PURVIEW_ENDPOINT=https://bankx-purview.purview.azure.com
PURVIEW_CATALOG_ENDPOINT=https://bankx-purview.purview.azure.com/catalog
PURVIEW_SCAN_ENDPOINT=https://bankx-purview.purview.azure.com/scan
PURVIEW_TENANT_ID=c1e8c736-fd22-4d7b-a7a2-12c6f36ac388

# Service Principal Credentials (already stored in Key Vault)
# These will be retrieved from Azure Key Vault at runtime
PURVIEW_ACCOUNT_AGENT_CLIENT_ID=f7219061-e3db-4dfb-a8de-2b5fa4b98ccf
PURVIEW_TRANSACTION_AGENT_CLIENT_ID=abdde3bd-954f-4626-be85-c995faeec314
PURVIEW_PAYMENT_AGENT_CLIENT_ID=19c0d01f-228b-45e0-b337-291679acb75c
PURVIEW_PRODINFO_AGENT_CLIENT_ID=cd8e9191-1d08-4bd2-9dbe-e23139dcbd90
PURVIEW_MONEYCOACH_AGENT_CLIENT_ID=b81a5e18-1760-4836-8a5e-e4ef2e8f1113
PURVIEW_ESCALATION_AGENT_CLIENT_ID=019b1746-a104-437a-b1ff-a911ba8c356c
PURVIEW_SUPERVISOR_AGENT_CLIENT_ID=cbb7c307-5c43-4999-ada4-63a934853ec5
```

---

## ✅ Verification Steps

1. **Check Provisioning**: Wait 5-10 minutes for full provisioning
   ```powershell
   $token = az account get-access-token --query accessToken -o tsv
   $subscriptionId = "e0783b50-4ca5-4059-83c1-524f39faa624"
   $response = Invoke-RestMethod -Uri "https://management.azure.com/subscriptions/$subscriptionId/resourceGroups/rg-multimodaldemo/providers/Microsoft.Purview/accounts/bankx-purview?api-version=2021-07-01" -Method Get -Headers @{Authorization="Bearer $token"}
   Write-Host "Provisioning State: $($response.properties.provisioningState)"
   ```

2. **Access Purview Portal**: https://bankx-purview.purview.azure.com

3. **Verify Role Assignments**: Check that all 7 service principals have "Data curator" role

4. **Test Service Principal Authentication** (after role assignments):
   ```powershell
   # Test AccountAgent SP authentication
   $clientId = "f7219061-e3db-4dfb-a8de-2b5fa4b98ccf"
   $clientSecret = "<from-key-vault>"
   $tenantId = "c1e8c736-fd22-4d7b-a7a2-12c6f36ac388"
   
   # Get token for Purview
   $body = @{
       client_id = $clientId
       client_secret = $clientSecret
       grant_type = "client_credentials"
       scope = "https://purview.azure.net/.default"
   }
   
   $tokenResponse = Invoke-RestMethod -Uri "https://login.microsoftonline.com/$tenantId/oauth2/v2.0/token" -Method Post -Body $body
   Write-Host "Token acquired: $($tokenResponse.access_token.Substring(0,20))..."
   ```

---

## 🎯 Summary

✅ **Purview Account**: Created in Southeast Asia  
✅ **Endpoints**: Available and ready  
⏳ **Role Assignments**: Manual via Purview Portal (7 service principals)  
⏳ **Data Source Registration**: Manual via Purview Portal  
⏳ **Integration Code**: Ready to implement after role assignments complete

**Estimated Time to Complete**: 30-45 minutes (role assignments + data source registration)

**Next Action**: Open Purview Governance Portal and assign "Data curator" role to all 7 service principals as documented above.
