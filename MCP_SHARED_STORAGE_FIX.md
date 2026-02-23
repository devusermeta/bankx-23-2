# MCP Shared Storage Configuration - Fix Guide

## 🔍 Problem Identified

Your MCP servers are **NOT sharing data** because:

1. **Wrong Mount Path**: Volume is mounted to `/app/data` but StateManager expects `/app/dynamic_data`
2. **No Initial Data**: JSON files were not uploaded to Azure Files share
3. **Isolated Containers**: Each container was using its own baked-in copy of JSON files

### Evidence:
- Payment agent showed balance = THB 10,000 (hallucinated/old data)
- Actual CUST-002 balance in local file = THB 74,270
- Changes to accounts.json in payment-mcp were NOT visible to account-mcp

---

## ✅ Solution

The fix involves 3 steps:

### Step 1: Upload JSON Files to Azure Files
Upload the current JSON files from `claude_bank/dynamic_data/` to the Azure Files share `dynamicdata` in storage account `bankxstorage776`.

### Step 2: Fix Volume Mount Path
Update all MCP container apps to mount the shared volume to `/app/dynamic_data` instead of `/app/data`.

### Step 3: Verify Configuration
Confirm all MCP servers can access the shared files and that changes are visible across containers.

---

## 🚀 How to Fix

### Run the Fix Script:

```powershell
cd D:\Metakaal\Updated_BankX
.\fix-mcp-shared-storage.ps1
```

This script will:
1. ✅ Upload all JSON files to Azure Files share
2. ✅ Update volume mounts for all 5 MCP servers
3. ✅ Restart containers with correct configuration
4. ✅ Verify everything is working

### Verify the Fix:

```powershell
.\verify-mcp-shared-storage.ps1
```

This will check:
- ✅ JSON files exist in Azure Files
- ✅ All MCP servers have correct mounts to `/app/dynamic_data`
- ✅ Files are readable and contain valid data

---

## 📊 MCP Servers Updated

The following Container Apps will be updated:

| Container App | Purpose | Volume Mount |
|---------------|---------|--------------|
| `account-mcp` | Account operations | `/app/dynamic_data` |
| `payment-mcp` | Payment processing | `/app/dynamic_data` |
| `contacts-mcp` | Beneficiary management | `/app/dynamic_data` |
| `limits-mcp` | Transaction limits | `/app/dynamic_data` |
| `escalation-mcp` | Escalation handling | `/app/dynamic_data` |

---

## 🔄 Expected Behavior After Fix

### Before Fix (❌ Not Working):
```
User makes payment
  → payment-mcp updates accounts.json (only in its container)
  → account-mcp reads accounts.json (old data from its container)
  → ❌ Balance shown is stale/incorrect
```

### After Fix (✅ Working):
```
User makes payment
  → payment-mcp updates accounts.json (in Azure Files)
  → account-mcp reads accounts.json (from Azure Files)
  → ✅ Balance is current and correct across all servers
```

---

## 📝 Storage Configuration

| Property | Value |
|----------|-------|
| Storage Account | `bankxstorage776` |
| Resource Group | `rg-a2a-test` |
| File Share | `dynamicdata` |
| Access Mode | ReadWrite |
| Mount Path | `/app/dynamic_data` |
| Storage Type | Azure Files |

---

## 🧪 Testing After Fix

1. **Run verification script**:
   ```powershell
   .\verify-mcp-shared-storage.ps1
   ```

2. **Test payment workflow**:
   - Login as CUST-002 (nattaporn@bankxthb.onmicrosoft.com)
   - Current balance should show THB 74,270
   - Transfer 300 THB to Somchai Rattankorn
   - New balance should be THB 73,970

3. **Verify persistence**:
   - Check accounts.json in Azure Files
   - Restart one of the MCP containers
   - Balance should still show updated value

4. **Check logs**:
   - Payment agent should show actual MCP tool calls (not text)
   - No more hallucinated balances
   - StateManager should log file read/write operations

---

## 🔍 How to Check Azure Files Contents

### Using Azure CLI:

```powershell
# List files
az storage file list `
    --share-name dynamicdata `
    --account-name bankxstorage776 `
    --account-key <key> `
    --output table

# Download a file to inspect
az storage file download `
    --share-name dynamicdata `
    --path accounts.json `
    --dest temp-accounts.json `
    --account-name bankxstorage776 `
    --account-key <key>
```

### Using Azure Portal:

1. Go to Storage Account: `bankxstorage776`
2. Navigate to: **Data storage → File shares**
3. Click on: `dynamicdata`
4. View and download JSON files

---

## ⚠️ Important Notes

1. **Persistence**: After this fix, all data changes are persistent. Even if containers restart, data remains in Azure Files.

2. **Shared State**: All MCP servers see the SAME data. A change by one server is immediately visible to others.

3. **No Blob Storage**: We're using Azure Files (SMB mount), not Blob Storage, for direct file system access.

4. **StateManager Compatibility**: The `/app/dynamic_data` path is what StateManager expects (configured in `path_utils.py`).

5. **Container Restart**: Containers may take 1-2 minutes to restart after volume mount changes.

---

## 🐛 Troubleshooting

### If verification fails:

1. **Check storage account access**:
   ```powershell
   az storage account show --name bankxstorage776 --resource-group rg-a2a-test
   ```

2. **Verify file share exists**:
   ```powershell
   az storage share show --name dynamicdata --account-name bankxstorage776
   ```

3. **Check container app status**:
   ```powershell
   az containerapp show --name account-mcp --resource-group rg-banking-new
   ```

4. **View container logs**:
   ```powershell
   az containerapp logs show --name account-mcp --resource-group rg-banking-new --follow
   ```

### Common issues:

- **"Volume not found"**: The storage mount needs to be recreated in Container Apps environment
- **"Permission denied"**: Storage account key might be incorrect
- **"File not found"**: JSON files weren't uploaded correctly

---

## 📚 Related Files

- `fix-mcp-shared-storage.ps1` - Main fix script
- `verify-mcp-shared-storage.ps1` - Verification script
- `claude_bank/dynamic_data/` - Source JSON files
- `claude_bank/app/common/state_manager.py` - StateManager that reads/writes JSONs
- `claude_bank/app/common/path_utils.py` - Path configuration

---

## ✅ Success Criteria

After running the fix, you should see:

- ✅ All 5 JSON files uploaded to Azure Files
- ✅ All 5 MCP containers mounted to `/app/dynamic_data`
- ✅ Payment workflow updates accounts.json
- ✅ Balance changes visible across all MCP servers
- ✅ Data persists after container restarts
- ✅ No hallucinated data in payment agent responses
