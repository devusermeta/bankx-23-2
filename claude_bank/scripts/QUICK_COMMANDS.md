# Quick Command Reference for BankX Entra ID Setup

## Run the Complete Setup
```powershell
cd d:\Metakaal\BankX\claude_bank
.\scripts\setup-bankx-entraid.ps1
```

## Retrieve Test User Passwords
```powershell
# Get Key Vault name
$kvName = az keyvault list --resource-group rg-multimodaldemo --query "[?starts_with(name, 'kv-bankx')].name" -o tsv

# Get all passwords
@("somchai", "nattaporn", "pimchanok", "anan") | ForEach-Object {
    $pwd = az keyvault secret show --vault-name $kvName --name "user-$_-password" --query value -o tsv
    Write-Host "$_@bankx.onmicrosoft.com : $pwd" -ForegroundColor Cyan
}
```

## Verify Setup
```powershell
# Check Key Vault
az keyvault list --resource-group rg-multimodaldemo --output table

# Check App Registration (after setup)
az login --tenant <BANKX_TENANT_ID> --allow-no-subscriptions
az ad app list --display-name "BankX-Multi-Agent-App" --output table

# Check Users
az ad user list --output table
```

## Switch Between Tenants
```powershell
# Switch to Metakaal tenant (for resources)
az login --tenant c1e8c736-fd22-4d7b-a7a2-12c6f36ac388

# Switch to BankX tenant (for user management)
az login --tenant <BANKX_TENANT_ID> --allow-no-subscriptions
```

## Merge .env Files
```powershell
# After setup completes
Get-Content .env.bankx-auth | Add-Content .env
```
