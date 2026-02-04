# BankX Azure Infrastructure Provisioning

This directory contains scripts to provision all required Azure resources for the BankX Multi-Agent Banking System.

## Prerequisites

1. **Azure CLI** - Install and login:
   ```bash
   az login
   az account set --subscription <your-subscription-id>
   ```

2. **Python 3.9+** with required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. **Azure Permissions** - You need Contributor role on the subscription or resource group

## Quick Start

### Option 1: Using Configuration File (Recommended)

1. Copy and edit the configuration file:
   ```bash
   cp config.example.json config.json
   # Edit config.json with your values
   ```

2. Run the provisioning script:
   ```bash
   python azure_provision.py --config config.json
   ```

### Option 2: Using Command Line Arguments

```bash
python azure_provision.py \
  --subscription-id "your-subscription-id" \
  --resource-group "bankx-dev-rg" \
  --location "eastus" \
  --environment "dev"
```

## What Gets Provisioned

The script provisions the following Azure services:

### Core AI Services (UC1, UC2, UC3)
- ✅ **Azure OpenAI** - LLM backbone for all agents
- ✅ **Azure AI Foundry** - Agent framework and management
- ✅ **Azure AI Search** - Vector search for RAG (UC2, UC3)

### Data Storage
- ✅ **Azure Cosmos DB** - NoSQL database for:
  - Decision Ledger (audit trails)
  - Support tickets
  - Conversation history
  - Cache for RAG results
- ✅ **Azure Storage** - Blob storage for documents and invoices
- ⚠️ **Azure SQL Database** - Relational database (optional, currently using CSV)

### Document Processing
- ✅ **Azure Document Intelligence** - OCR and invoice data extraction

### Communication
- ✅ **Azure Communication Services** - Email notifications for support tickets

### Infrastructure
- ⚠️ **Azure API Management** - Gateway for MCP tools (manual setup required)
- ✅ **Azure Application Insights** - Telemetry and monitoring
- ✅ **Azure Key Vault** - Secrets management
- ⚠️ **Azure App Service/Container Apps** - Hosting (manual setup required)

Legend:
- ✅ Fully automated by script
- ⚠️ Partially automated or requires manual configuration

## Output

The script generates a `.env.generated` file with all connection strings and endpoints:

```bash
# Review the generated file
cat .env.generated

# Copy to your application
cp .env.generated ../app/copilot/.env.dev
```

**⚠️ IMPORTANT**: Never commit `.env.generated` or files with secrets to version control!

## Configuration Options

### Resource Naming

Resources are named using the pattern: `{project_name}-{environment}-{service_type}`

Example:
- Project: `bankx`
- Environment: `dev`
- OpenAI Service: `bankx-dev-openai`

### SKU Selection

Default SKUs are optimized for development. For production:

```json
{
  "openai_sku": "S0",
  "search_sku": "standard",
  "app_service_sku": "P1v2",
  "environment": "prod"
}
```

### Multi-Region Setup

For high availability, deploy to multiple regions:

```bash
# Primary region
python azure_provision.py --config config.json --location eastus

# Secondary region (disaster recovery)
python azure_provision.py --config config.json --location westus --resource-group bankx-prod-rg-west
```

## Dry Run Mode

Test what would be created without actually provisioning:

```bash
python azure_provision.py --config config.json --dry-run
```

## Idempotency

The script is idempotent - running it multiple times:
- ✅ Checks if resources already exist
- ✅ Only creates missing resources
- ✅ Retrieves connection strings for existing resources
- ✅ Safe to run repeatedly

## Cost Estimation

Approximate monthly costs for development environment:

| Service | SKU | Est. Cost/Month |
|---------|-----|-----------------|
| Azure OpenAI | S0 | $10-100 (usage-based) |
| Azure AI Search | Standard | $250 |
| Cosmos DB | Serverless | $10-50 (usage-based) |
| Storage | Standard LRS | $5-20 |
| Document Intelligence | S0 | $10-50 (usage-based) |
| Communication Services | - | $1-10 (usage-based) |
| App Insights | - | $5-20 |
| **Total** | | **~$300-500/month** |

Production costs will be higher based on scale and redundancy requirements.

## Troubleshooting

### Authentication Issues

```bash
# Clear and re-authenticate
az logout
az login
az account set --subscription <subscription-id>
```

### Resource Name Conflicts

If a resource name is already taken globally (e.g., Storage Account, Key Vault):

1. Edit `config.json` with unique names
2. Or let the script generate names by omitting them

### Permission Errors

Ensure you have the required roles:
```bash
az role assignment list --assignee $(az account show --query user.name -o tsv)
```

Required roles:
- `Contributor` on the resource group
- Or specific roles: `Cognitive Services Contributor`, `Storage Account Contributor`, etc.

### Quota Limits

If you hit quota limits:
```bash
# Check current quotas
az vm list-usage --location eastus -o table

# Request quota increase via Azure Portal
```

## Manual Steps Required

After provisioning, some manual configuration is needed:

### 1. Azure OpenAI Deployments

Create model deployments:
```bash
az cognitiveservices account deployment create \
  --name bankx-dev-openai \
  --resource-group bankx-dev-rg \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-05-13" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name "Standard"
```

### 2. Azure AI Search Indexes

Create search indexes for UC2 and UC3:
- Product Information & FAQ index
- Money Coach document index

See `../docs/search_index_setup.md` for details.

### 3. Cosmos DB Containers

Create containers:
```bash
# Decision Ledger container
az cosmosdb sql container create \
  --account-name bankx-dev-cosmos \
  --database-name bankx_db \
  --name decision_ledger \
  --partition-key-path "/sessionId"

# Support Tickets container
az cosmosdb sql container create \
  --account-name bankx-dev-cosmos \
  --database-name bankx_db \
  --name support_tickets \
  --partition-key-path "/ticketId"
```

### 4. Communication Services Email Domain

Configure email domain in Azure Portal for email notifications.

### 5. API Management Setup

Import and configure MCP tool APIs - see `../docs/apim_setup.md`.

## Next Steps

After provisioning:

1. ✅ Review `.env.generated` and copy to application
2. ✅ Complete manual configuration steps above
3. ✅ Index documents in Azure AI Search (UC2, UC3)
4. ✅ Test connectivity from application
5. ✅ Set up monitoring alerts in Application Insights
6. ✅ Configure backup policies for Cosmos DB and Storage

## Additional Resources

- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [Azure AI Search Documentation](https://learn.microsoft.com/azure/search/)
- [Azure Cosmos DB Documentation](https://learn.microsoft.com/azure/cosmos-db/)
- [BankX Architecture Docs](../docs/multi-agents/introduction.md)

## Support

For issues or questions:
- Check troubleshooting section above
- Review Azure service health: https://status.azure.com/
- Open an issue in the repository
