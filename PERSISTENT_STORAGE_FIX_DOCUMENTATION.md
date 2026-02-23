# BankX MCP Persistent Storage Fix Documentation

**Date:** February 23, 2026  
**Issue:** Payment agent hallucinating balance values instead of using real MCP tool data  
**Status:** ✅ RESOLVED

---

## 📋 Table of Contents
1. [Problem Statement](#problem-statement)
2. [Root Cause Analysis](#root-cause-analysis)
3. [Solution Overview](#solution-overview)
4. [Detailed Fix Steps](#detailed-fix-steps)
5. [Verification](#verification)
6. [Final Configuration](#final-configuration)
7. [Troubleshooting](#troubleshooting)

---

## 🚨 Problem Statement

### Symptoms
- Payment agent showing incorrect balance (THB 9,700 instead of THB 74,270)
- Balance information being hallucinated instead of retrieved from MCP tools
- MCP servers not sharing persistent data across containers
- Each container using isolated copies of JSON files baked into Docker images

### User Impact
- Incorrect account balances displayed
- Payment operations not updating shared state
- Data inconsistency across different MCP servers
- Unable to track real-time balance changes

---

## 🔍 Root Cause Analysis

### Investigation Steps

**Step 1: Checked Volume Mount Configuration**
```bash
az containerapp list --query "[].{Name:name,ResourceGroup:resourceGroup,Volumes:properties.template.volumes,VolumeMounts:properties.template.containers[0].volumeMounts}" -o json
```

**Findings:**
- `payment-mcp`: **NO volumes** configured (volumeMounts: null)
- `transaction`: **NO volumes** configured (volumeMounts: null)
- `account-mcp`, `limits-mcp`, `contacts-mcp`, `escalation-mcp`: Volumes mounted at **WRONG PATH** (`/app/data`)

**Step 2: Verified StateManager Expected Path**
```python
# File: claude_bank/app/common/path_utils.py
def get_dynamic_data_dir():
    return get_base_dir() / "dynamic_data"  # Returns /app/dynamic_data
```

**Root Cause Identified:**
1. ❌ MCP containers NOT reading from Azure Files share
2. ❌ Volume mounts pointing to `/app/data` instead of `/app/dynamic_data`
3. ❌ StateManager expecting files at `/app/dynamic_data`
4. ❌ Each container using isolated JSON files from Docker image (COPY command)
5. ❌ No shared persistent storage configured correctly

---

## 🎯 Solution Overview

### Architecture
```
┌─────────────────────────────────────────────┐
│   Azure Files Storage                       │
│   Account: bankxstorage776                  │
│   Share: dynamicdata                        │
│   ├── accounts.json                         │
│   ├── contacts.json                         │
│   ├── customers.json                        │
│   ├── limits.json                           │
│   └── transactions.json                     │
└─────────────────────────────────────────────┘
                    ↓
      ┌─────────────────────────────┐
      │  Environment Storage Mount   │
      │  Name: bankx-shared-data     │
      │  Type: AzureFile             │
      └─────────────────────────────┘
                    ↓
    ┌───────────────────────────────────┐
    │  All MCP Container Volume Mounts  │
    │  Mount Path: /app/dynamic_data    │
    └───────────────────────────────────┘
                    ↓
┌────────┬────────┬────────┬────────┬────────┬────────┐
│payment │account │limits  │contacts│escalate│transact│
│  -mcp  │ -mcp   │ -mcp   │ -mcp   │ion-mcp │  ion   │
└────────┴────────┴────────┴────────┴────────┴────────┘
```

### Solution Components
1. ✅ Upload latest JSON files to Azure Files
2. ✅ Add volume mounts to containers without them
3. ✅ Fix mount paths from `/app/data` → `/app/dynamic_data`
4. ✅ Verify all containers using shared storage

---

## 🔧 Detailed Fix Steps

### Step 1: Verify Azure Files Storage

**Check if storage account and file share exist:**
```bash
# Verify storage account
az storage account show --name bankxstorage776 --resource-group rg-banking-new --query "{Name:name,Location:location,Status:statusOfPrimary}" -o table

# Verify file share
az storage share show --account-name bankxstorage776 --name dynamicdata --query "{Name:name,Quota:quota,ProvisionedIops:provisionedIops}" -o table
```

**Expected Output:**
- Storage Account: bankxstorage776 (Active)
- File Share: dynamicdata (ReadWrite access)

---

### Step 2: Upload Latest JSON Files to Azure Files

**Navigate to source directory:**
```bash
cd d:\Metakaal\Updated_BankX\claude_bank\dynamic_data
```

**Upload all JSON files:**
```bash
az storage file upload-batch \
  --account-name bankxstorage776 \
  --destination dynamicdata \
  --source . \
  --pattern "*.json"
```

**Verify upload:**
```bash
az storage file list \
  --account-name bankxstorage776 \
  --share-name dynamicdata \
  --query "[].{Name:name,Size:properties.contentLength,LastModified:properties.lastModified}" \
  -o table
```

**Expected Files:**
- accounts.json (3,264 bytes)
- contacts.json (11,483 bytes)
- customers.json (2,117 bytes)
- limits.json (1,964 bytes)
- transactions.json (52,347 bytes)

---

### Step 3: Fix payment-mcp (Add Volume Mount)

**Export current configuration:**
```bash
az containerapp show \
  --name payment-mcp \
  --resource-group rg-banking-new \
  --query "properties.template" \
  -o json > payment-mcp-template.json
```

**Create YAML configuration:**
```yaml
# File: payment-mcp-complete.yaml
properties:
  template:
    containers:
    - name: payment-mcp
      image: multimodaldemoacroy6neblxi3zkq.azurecr.io/payment-mcp-server:v3
      resources:
        cpu: 0.5
        memory: 1Gi
        ephemeralStorage: 2Gi
      env:
      - name: STORAGE_ENABLED
        value: "true"
      probes:
      - type: Liveness
        tcpSocket:
          port: 23040
        failureThreshold: 3
        periodSeconds: 10
        successThreshold: 1
        timeoutSeconds: 5
      - type: Readiness
        tcpSocket:
          port: 23040
        failureThreshold: 48
        periodSeconds: 5
        successThreshold: 1
        timeoutSeconds: 5
      - type: Startup
        tcpSocket:
          port: 23040
        failureThreshold: 240
        initialDelaySeconds: 1
        periodSeconds: 1
        successThreshold: 1
        timeoutSeconds: 3
      volumeMounts:
      - volumeName: bankx-shared-data
        mountPath: /app/dynamic_data
    scale:
      cooldownPeriod: 300
      maxReplicas: 10
      minReplicas: 0
      pollingInterval: 30
    volumes:
    - name: bankx-shared-data
      storageType: AzureFile
      storageName: bankx-shared-data
```

**Apply configuration:**
```bash
az containerapp update \
  --name payment-mcp \
  --resource-group rg-banking-new \
  --yaml payment-mcp-complete.yaml
```

**Verify update:**
```bash
az containerapp show \
  --name payment-mcp \
  --resource-group rg-banking-new \
  --query "properties.template.{containers:containers[0].volumeMounts,volumes:volumes}" \
  -o json
```

---

### Step 4: Fix account-mcp (Change Mount Path)

**Export configuration:**
```bash
az containerapp show \
  --name account-mcp \
  --resource-group rg-banking-new \
  --query "properties.template" \
  -o json > account-mcp-template.json
```

**Create YAML with corrected mount path:**
```yaml
# File: account-mcp-updated.yaml
properties:
  template:
    containers:
    - name: account-mcp
      image: multimodaldemoacroy6neblxi3zkq.azurecr.io/account-mcp-server:v3
      resources:
        cpu: 0.5
        memory: 1Gi
        ephemeralStorage: 2Gi
      env:
      - name: AZURE_STORAGE_ACCOUNT_NAME
        value: bankxstorage776
      - name: AZURE_STORAGE_CONTAINER_NAME
        value: banking-data
      volumeMounts:
      - volumeName: bankx-shared-data
        mountPath: /app/dynamic_data  # Changed from /app/data
      - volumeName: bankx-shared-data
        mountPath: /app/memory
    volumes:
    - name: bankx-shared-data
      storageType: AzureFile
      storageName: bankx-shared-data
```

**Apply configuration:**
```bash
az containerapp update \
  --name account-mcp \
  --resource-group rg-banking-new \
  --yaml account-mcp-updated.yaml
```

---

### Step 5: Fix limits-mcp (Change Mount Path)

**Create YAML configuration:**
```yaml
# File: limits-mcp-updated.yaml
properties:
  template:
    containers:
    - name: limits-mcp
      image: multimodaldemoacroy6neblxi3zkq.azurecr.io/limit-mcp-server:v3
      volumeMounts:
      - volumeName: bankx-shared-data
        mountPath: /app/dynamic_data  # Changed from /app/data
      - volumeName: bankx-shared-data
        mountPath: /app/memory
    volumes:
    - name: bankx-shared-data
      storageType: AzureFile
      storageName: bankx-shared-data
```

**Apply configuration:**
```bash
az containerapp update \
  --name limits-mcp \
  --resource-group rg-banking-new \
  --yaml limits-mcp-updated.yaml
```

---

### Step 6: Fix contacts-mcp (Change Mount Path)

**Create and apply YAML:**
```bash
# Create contacts-mcp-updated.yaml with /app/dynamic_data mount path
az containerapp update \
  --name contacts-mcp \
  --resource-group rg-banking-new \
  --yaml contacts-mcp-updated.yaml
```

---

### Step 7: Fix escalation-mcp (Change Mount Path)

**Create and apply YAML:**
```bash
# Create escalation-mcp-updated.yaml with /app/dynamic_data mount path
az containerapp update \
  --name escalation-mcp \
  --resource-group rg-banking-new \
  --yaml escalation-mcp-updated.yaml
```

---

### Step 8: Fix transaction (Add Volume Mount)

**Export configuration:**
```bash
az containerapp show \
  --name transaction \
  --resource-group rg-multimodaldemo \
  --query "properties.template" \
  -o json > transaction-template.json
```

**Create YAML configuration:**
```yaml
# File: transaction-updated.yaml
properties:
  template:
    containers:
    - name: transaction
      image: multimodaldemoacroy6neblxi3zkq.azurecr.io/transaction-mcp-server:v3
      volumeMounts:
      - volumeName: bankx-shared-data
        mountPath: /app/dynamic_data
      - volumeName: bankx-shared-data
        mountPath: /app/memory
    volumes:
    - name: bankx-shared-data
      storageType: AzureFile
      storageName: bankx-shared-data
```

**Apply configuration:**
```bash
az containerapp update \
  --name transaction \
  --resource-group rg-multimodaldemo \
  --yaml transaction-updated.yaml
```

---

## ✅ Verification

### Step 1: Check All Container Status

```bash
az containerapp list \
  --query "[?contains(name,'mcp') || contains(name,'transaction')].{Name:name,ResourceGroup:resourceGroup,Status:properties.runningStatus,LatestRevision:properties.latestRevisionName}" \
  -o table
```

**Expected Output:**
```
Name            ResourceGroup      Status    LatestRevision
--------------  -----------------  --------  -----------------------
payment-mcp     rg-banking-new     Running   payment-mcp--0000004
account-mcp     rg-banking-new     Running   account-mcp--0000007
limits-mcp      rg-banking-new     Running   limits-mcp--0000005
contacts-mcp    rg-banking-new     Running   contacts-mcp--0000005
escalation-mcp  rg-banking-new     Running   escalation-mcp--0000005
transaction     rg-multimodaldemo  Running   transaction--0000004
```

---

### Step 2: Verify Volume Mounts

```bash
# Check payment-mcp
az containerapp show \
  --name payment-mcp \
  --resource-group rg-banking-new \
  --query "properties.template.{volumeMounts:containers[0].volumeMounts,volumes:volumes}" \
  -o json

# Check account-mcp
az containerapp show \
  --name account-mcp \
  --resource-group rg-banking-new \
  --query "properties.template.{volumeMounts:containers[0].volumeMounts,volumes:volumes}" \
  -o json
```

**Expected Configuration (All Containers):**
```json
{
  "volumeMounts": [
    {
      "mountPath": "/app/dynamic_data",
      "volumeName": "bankx-shared-data"
    },
    {
      "mountPath": "/app/memory",
      "volumeName": "bankx-shared-data"
    }
  ],
  "volumes": [
    {
      "name": "bankx-shared-data",
      "storageName": "bankx-shared-data",
      "storageType": "AzureFile"
    }
  ]
}
```

---

### Step 3: Verify Data in Azure Files

```bash
# Download current accounts.json
az storage file download \
  --account-name bankxstorage776 \
  --share-name dynamicdata \
  --path accounts.json \
  --dest accounts-current.json

# View content
Get-Content accounts-current.json | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

**Verify CUST-002 Balance:**
```json
{
  "account_id": "CHK-002",
  "customer_id": "CUST-002",
  "cust_name": "Nattaporn Suksawat",
  "bankx_email": "nattaporn@bankxthb.onmicrosoft.com",
  "ledger_balance": 74270.0,
  "available_balance": 74270.0
}
```

✅ **Current Balance: THB 74,270** (Correct!)

---

## 📊 Final Configuration

### Summary of Changes

| Container | Resource Group | Before | After | Status |
|-----------|---------------|--------|-------|--------|
| payment-mcp | rg-banking-new | ❌ No volumes | ✅ /app/dynamic_data | ✅ Running |
| account-mcp | rg-banking-new | ⚠️ /app/data | ✅ /app/dynamic_data | ✅ Running |
| limits-mcp | rg-banking-new | ⚠️ /app/data | ✅ /app/dynamic_data | ✅ Running |
| contacts-mcp | rg-banking-new | ⚠️ /app/data | ✅ /app/dynamic_data | ✅ Running |
| escalation-mcp | rg-banking-new | ⚠️ /app/data | ✅ /app/dynamic_data | ✅ Running |
| transaction | rg-multimodaldemo | ❌ No volumes | ✅ /app/dynamic_data | ✅ Running |

---

### Storage Architecture

```
Azure Files (bankxstorage776/dynamicdata)
    ↓
Environment Storage Mount (bankx-shared-data)
    ↓
Volume Mount Path: /app/dynamic_data
    ↓
StateManager reads/writes via path_utils.get_dynamic_data_dir()
    ↓
All MCP servers share the same persistent JSON files
```

---

### Key Configuration Elements

**1. Volume Definition (in all containers):**
```yaml
volumes:
- name: bankx-shared-data
  storageType: AzureFile
  storageName: bankx-shared-data
```

**2. Volume Mount (in all containers):**
```yaml
volumeMounts:
- volumeName: bankx-shared-data
  mountPath: /app/dynamic_data
```

**3. StateManager Path Resolution:**
```python
# /app/common/path_utils.py
def get_dynamic_data_dir():
    return get_base_dir() / "dynamic_data"  # Returns: /app/dynamic_data
```

---

## 🔧 Troubleshooting

### Issue: Containers Not Reading Shared Files

**Symptoms:**
- Balance still incorrect
- Containers appear to use isolated data

**Debug Steps:**
```bash
# 1. Check if container can access the mount
az containerapp exec \
  --name payment-mcp \
  --resource-group rg-banking-new \
  --command "/bin/sh"

# Inside container:
ls -la /app/dynamic_data/
cat /app/dynamic_data/accounts.json
```

**Solution:**
- Verify volume mount path is exactly `/app/dynamic_data`
- Ensure StateManager is using correct path from path_utils
- Check file permissions in Azure Files

---

### Issue: Stale Data Persists

**Symptoms:**
- Updated files don't reflect in container
- Old data still being read

**Debug Steps:**
```bash
# 1. Restart containers to force remount
az containerapp revision restart \
  --name payment-mcp \
  --resource-group rg-banking-new \
  --revision payment-mcp--0000004

# 2. Verify Azure Files has latest data
az storage file list \
  --account-name bankxstorage776 \
  --share-name dynamicdata \
  -o table
```

**Solution:**
- Re-upload JSON files to Azure Files
- Restart all MCP containers
- Clear any cached data

---

### Issue: Volume Mount Fails

**Symptoms:**
- Container logs show "mount failed"
- Volume appears in config but not working

**Debug Steps:**
```bash
# Check environment storage configuration
az containerapp env storage show \
  --name acae-a2a-test \
  --resource-group rg-a2a-test \
  --storage-name bankx-shared-data \
  -o json
```

**Solution:**
- Verify environment has storage configured
- Check storage account access keys
- Ensure file share exists and is accessible

---

## 📝 Lessons Learned

### Key Takeaways

1. **Always verify mount paths match code expectations**
   - StateManager expected `/app/dynamic_data`
   - Containers were mounted at `/app/data`
   - Path mismatch caused isolated file usage

2. **Test volume mounts immediately after deployment**
   - Don't assume Docker COPY and volume mounts work together
   - Verify containers are reading from mounted storage, not image files

3. **Use consistent volume mount patterns**
   - All MCP servers should use identical mount configuration
   - Reduces configuration drift and troubleshooting complexity

4. **Document storage architecture clearly**
   - Map Azure Files → Environment Storage → Volume Mounts → Code paths
   - Makes debugging much faster

5. **YAML configuration is safer than --set parameters**
   - Complex objects (volumes, volumeMounts) need YAML
   - JSON-to-YAML conversion requires proper formatting

---

## 🎯 Success Criteria

✅ All 6 MCP containers have volumes mounted at `/app/dynamic_data`  
✅ Azure Files share contains latest JSON files  
✅ StateManager reading from correct path  
✅ Balance showing correctly: CUST-002 = THB 74,270  
✅ All containers running with new revisions  
✅ Persistent storage survives container restarts  

---

## 📚 References

- **Azure Container Apps Volume Mounts:** https://learn.microsoft.com/en-us/azure/container-apps/storage-mounts
- **Azure Files Integration:** https://learn.microsoft.com/en-us/azure/storage/files/storage-files-introduction
- **Container App YAML Schema:** https://learn.microsoft.com/en-us/azure/container-apps/azure-resource-manager-api-spec

---

**Document Version:** 1.0  
**Last Updated:** February 23, 2026  
**Maintained By:** BankX Development Team
