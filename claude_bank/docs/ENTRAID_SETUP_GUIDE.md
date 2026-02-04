# BankX Entra ID Authentication Setup Guide

## Overview
This guide walks you through setting up Microsoft Entra ID authentication for the BankX Multi-Agent Banking System.

## Prerequisites

Before running the setup script, ensure you have:

1. **Azure CLI installed** (version 2.50.0 or later)
   ```powershell
   az --version
   ```
   If not installed: https://aka.ms/installazurecliwindows

2. **Logged into Azure CLI**
   ```powershell
   az login
   ```

3. **Global Administrator rights** (required for tenant creation)
   - You need this to create a new Entra ID tenant
   - Check your role: https://portal.azure.com → Microsoft Entra ID → Roles and administrators

4. **Contributor role** on `rg-multimodaldemo` resource group
   - Required to create Key Vault

## Quick Start

### Step 1: Run the Setup Script

```powershell
cd d:\Metakaal\BankX\claude_bank
.\scripts\setup-bankx-entraid.ps1
```

### Step 2: Follow the Prompts

The script will:
1. ✅ Check prerequisites
2. ✅ Create Azure Key Vault (kv-bankx-XXXX)
3. ⚠️  **PAUSE for manual tenant creation** - Follow on-screen instructions
4. ✅ Create App Registration with App Roles
5. ✅ Create 4 test users
6. ✅ Store passwords in Key Vault
7. ✅ Generate `.env.bankx-auth` configuration file

### Step 3: Manual Tenant Creation (When Prompted)

When the script pauses, you'll need to:

1. Open: https://portal.azure.com
2. Search for **"Microsoft Entra ID"**
3. Click **"Manage tenants"** → **"Create"**
4. Select **"Azure Active Directory"** (NOT B2C)
5. Fill in:
   - **Organization name**: `BankX`
   - **Initial domain**: `bankx` (becomes bankx.onmicrosoft.com)
   - **Country/Region**: United States
6. Click **"Review + Create"** → **"Create"**
7. Wait 2-3 minutes for tenant creation
8. Copy the **Tenant ID** (it looks like: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
9. Return to the PowerShell script and paste the Tenant ID when prompted

### Step 4: Merge Configuration

After successful setup, merge the generated configuration into your main `.env` file:

```powershell
# The script creates: .env.bankx-auth
# Copy its contents and append to your main .env file

Get-Content .env.bankx-auth | Add-Content .env
```

## What Gets Created

### 1. Azure Key Vault
- **Name**: `kv-bankx-XXXX` (random suffix)
- **Location**: East US
- **Resource Group**: rg-multimodaldemo
- **Purpose**: Stores test user passwords securely

### 2. BankX Entra ID Tenant
- **Domain**: bankx.onmicrosoft.com
- **Purpose**: User authentication directory

### 3. App Registration
- **Name**: BankX-Multi-Agent-App
- **Type**: Single-tenant (BankX tenant only)
- **Redirect URI**: http://localhost:8081
- **App Roles**:
  - `Customer` - Banking customers
  - `BankAgent` - Support agents
  - `BankTeller` - Branch tellers

### 4. Test Users (4)

| UPN | Display Name | Customer ID | Role |
|-----|--------------|-------------|------|
| somchai@bankx.onmicrosoft.com | Somchai Rattanakorn | CUST-001 | Customer |
| nattaporn@bankx.onmicrosoft.com | Nattaporn Suksawat | CUST-002 | Customer |
| pimchanok@bankx.onmicrosoft.com | Pimchanok Thongchai | CUST-003 | Customer |
| anan@bankx.onmicrosoft.com | Anan Chaiyaporn | CUST-004 | Customer |

## Retrieving Test User Passwords

Passwords are stored in Key Vault. To retrieve them:

```powershell
# Get Key Vault name
$kvName = az keyvault list --resource-group rg-multimodaldemo --query "[?starts_with(name, 'kv-bankx')].name" -o tsv

# Retrieve specific user password
az keyvault secret show --vault-name $kvName --name user-somchai-password --query value -o tsv

# Retrieve all user passwords
@("somchai", "nattaporn", "pimchanok", "anan") | ForEach-Object {
    $password = az keyvault secret show --vault-name $kvName --name "user-$_-password" --query value -o tsv
    Write-Host "$_@bankx.onmicrosoft.com: $password"
}
```

## Configuration Values

After setup, you'll have these new environment variables:

```properties
# Authentication Tenant (BankX)
AZURE_AUTH_TENANT_ID=<your-bankx-tenant-id>
AZURE_AUTH_TENANT_NAME=bankx.onmicrosoft.com
AZURE_APP_CLIENT_ID=<your-app-client-id>

# Key Vault
AZURE_KEYVAULT_NAME=kv-bankx-XXXX
AZURE_KEYVAULT_URL=https://kv-bankx-XXXX.vault.azure.net/

# Frontend
FRONTEND_REDIRECT_URI=http://localhost:8081
```

## Troubleshooting

### Error: "az: command not found"
**Solution**: Install Azure CLI: https://aka.ms/installazurecliwindows

### Error: "Insufficient privileges to complete the operation"
**Solution**: You need Global Administrator rights to create a tenant. Ask your Azure AD admin.

### Error: "Resource 'kv-bankx-XXXX' already exists"
**Solution**: The script will automatically use the existing Key Vault.

### Error: "User already exists"
**Solution**: Delete existing users in BankX tenant or modify the script to use different usernames.

### Error: "App Registration failed"
**Solution**: Ensure you switched to the BankX tenant context. The script does this automatically via `az login --tenant`.

## Verification Steps

After setup, verify everything works:

### 1. Verify Key Vault
```powershell
az keyvault list --resource-group rg-multimodaldemo --output table
```

### 2. Verify BankX Tenant
```powershell
az login --tenant <BANKX_TENANT_ID> --allow-no-subscriptions
az ad user list --output table
```

### 3. Verify App Registration
```powershell
az ad app list --display-name "BankX-Multi-Agent-App" --output table
```

### 4. Verify App Roles
```powershell
$appId = az ad app list --display-name "BankX-Multi-Agent-App" --query "[0].appId" -o tsv
az ad app show --id $appId --query "appRoles[].{DisplayName:displayName, Value:value}" --output table
```

## Next Steps

After successful setup:

1. **Update .env file** with new configuration
2. **Implement backend token validation** (Phase 1)
3. **Update frontend authConfig.ts** (Phase 2)
4. **Test authentication flow** (Phase 3)

## Support

If you encounter issues:
1. Check Azure CLI is logged in: `az account show`
2. Verify tenant context: `az account tenant list`
3. Check script output for detailed error messages
4. Review Azure Portal → Entra ID for created resources

## Clean Up (If Needed)

To remove everything created by the script:

```powershell
# Delete Key Vault
az keyvault delete --name kv-bankx-XXXX --resource-group rg-multimodaldemo

# Delete App Registration (in BankX tenant)
az login --tenant <BANKX_TENANT_ID> --allow-no-subscriptions
az ad app delete --id <APP_OBJECT_ID>

# Delete Users (in BankX tenant)
@("somchai", "nattaporn", "pimchanok", "anan") | ForEach-Object {
    az ad user delete --id "$_@bankx.onmicrosoft.com"
}

# Note: Tenant deletion must be done via Azure Portal
# https://portal.azure.com → Microsoft Entra ID → Properties → Delete tenant
```
