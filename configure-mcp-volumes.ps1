# PowerShell script to configure volume mounts for all MCP containers
$containers = @(
    @{ name = "limits-mcp"; image = "multimodaldemoacroy6neblxi3zkq.azurecr.io/limits-mcp-server:latest" },
    @{ name = "contacts-mcp"; image = "multimodaldemoacroy6neblxi3zkq.azurecr.io/contacts-mcp-server:latest" },
    @{ name = "escalation-mcp"; image = "multimodaldemoacroy6neblxi3zkq.azurecr.io/escalation-mcp-server:latest" }
)

$resourceGroup = "rg-banking-new"
$storageVolumeName = "bankx-shared-data"

foreach ($container in $containers) {
    Write-Host "Configuring $($container.name)..."
    
    # Get current container configuration  
    $currentConfig = az containerapp show --name $container.name --resource-group $resourceGroup | ConvertFrom-Json
    
    # Add volume configuration
    $volume = @{
        name = $storageVolumeName
        storageName = $storageVolumeName  
        storageType = "AzureFile"
    }
    
    # Add volume mounts
    $volumeMounts = @(
        @{ mountPath = "/app/data"; volumeName = $storageVolumeName },
        @{ mountPath = "/app/memory"; volumeName = $storageVolumeName }
    )
    
    # Update configuration
    $currentConfig.properties.template.volumes = @($volume)
    $currentConfig.properties.template.containers[0].volumeMounts = $volumeMounts
    
    # Remove system-managed fields
    $currentConfig.PSObject.Properties.Remove('id')
    $currentConfig.properties.PSObject.Properties.Remove('latestRevisionName')  
    $currentConfig.properties.PSObject.Properties.Remove('latestRevisionFqdn')
    $currentConfig.properties.PSObject.Properties.Remove('latestReadyRevisionName')
    
    # Save configuration file
    $configFile = "$($container.name)-updated.json" 
    $currentConfig | ConvertTo-Json -Depth 20 | Out-File -FilePath $configFile -Encoding UTF8
    
    Write-Host "Updating $($container.name) with volume configuration..."
    az containerapp update --name $container.name --resource-group $resourceGroup --yaml $configFile
}

Write-Host "Volume configuration completed for all MCP containers!"