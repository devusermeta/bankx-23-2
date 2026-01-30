# Account MCP Server - Docker Build & Deploy Scripts

## Prerequisites
- Azure CLI installed and logged in
- Docker installed
- ACR name: Replace `<your-acr-name>` with your actual ACR name
- Container App name: Replace `<your-container-app-name>` with your actual Container App name

## Step 1: Build Docker Image

```powershell
# Navigate to MCP server directory
cd banking-platform/account-agent-a2a/mcp-server

# Build the Docker image
docker build -t account-mcp-server:latest .

# Test locally (optional)
docker run -p 8070:8070 account-mcp-server:latest
```

## Step 2: Tag and Push to ACR

```powershell
# Set your ACR name
$ACR_NAME = "your-acr-name"

# Login to ACR
az acr login --name $ACR_NAME

# Tag the image
docker tag account-mcp-server:latest ${ACR_NAME}.azurecr.io/account-mcp-server:latest
docker tag account-mcp-server:latest ${ACR_NAME}.azurecr.io/account-mcp-server:v1.0.0

# Push to ACR
docker push ${ACR_NAME}.azurecr.io/account-mcp-server:latest
docker push ${ACR_NAME}.azurecr.io/account-mcp-server:v1.0.0
```

## Step 3: Deploy to Azure Container App

### Option A: Via Portal
1. Go to Azure Portal → Your Container App
2. Update Container:
   - Image: `<your-acr-name>.azurecr.io/account-mcp-server:latest`
   - Port: 8070
3. Add Environment Variables (if needed):
   - `LOG_LEVEL=INFO`
4. Save and Deploy

### Option B: Via Azure CLI

```powershell
# Set variables
$RESOURCE_GROUP = "your-resource-group"
$CONTAINER_APP_NAME = "account-mcp-server"
$ACR_NAME = "your-acr-name"

# Update the container app with new image
az containerapp update `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --image ${ACR_NAME}.azurecr.io/account-mcp-server:latest
```

## Step 4: Get Public URL

```powershell
# Get the container app URL
az containerapp show `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --query properties.configuration.ingress.fqdn `
  --output tsv
```

Your MCP server will be accessible at:
- `https://<fqdn>/mcp` - MCP JSON-RPC endpoint
- `https://<fqdn>/health` - Health check

## Step 5: Test Deployed MCP Server

```powershell
# Set the public URL
$MCP_URL = "https://your-container-app.azurecontainerapps.io"

# Test health endpoint
curl "${MCP_URL}/health"

# Test MCP tools/list
$body = @{
    jsonrpc = "2.0"
    id = 1
    method = "tools/list"
    params = @{}
} | ConvertTo-Json

Invoke-RestMethod -Uri "${MCP_URL}/mcp" -Method Post -Body $body -ContentType "application/json"
```

## Step 6: Use in Azure AI Foundry

When creating the agent in Azure AI Foundry:
- **MCP Server URL**: `https://<your-fqdn>/mcp`
- **Server Label**: `account-mcp`
- **Tools**: Select all 5 tools
- **Approval**: Never (auto-approve)

## Troubleshooting

### Check Container Logs
```powershell
az containerapp logs show `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --tail 50
```

### Check Container Status
```powershell
az containerapp show `
  --name $CONTAINER_APP_NAME `
  --resource-group $RESOURCE_GROUP `
  --query properties.runningStatus
```

## Notes

- The container app needs access to the dynamic_data JSON files
- Consider using Azure Files or Azure Blob Storage for persistent data
- Port 8070 is exposed and should be configured in Container App ingress
- Health check endpoint: `/health`
