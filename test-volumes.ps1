# Simple approach - Test if volume mount works by checking directories
Write-Host "Testing current volume mount status..."

# Check account-mcp logs to see if volumes are accessible
Write-Host "Checking account-mcp container..."
az containerapp exec --name account-mcp --resource-group rg-banking-new --command "ls -la /app/" --revision-suffix

Write-Host "`nDone! Let's test if the file share access is working."