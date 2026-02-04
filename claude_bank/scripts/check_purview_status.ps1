# Check Purview Account Status
$token = az account get-access-token --query accessToken -o tsv
$subscriptionId = "e0783b50-4ca5-4059-83c1-524f39faa624"
$response = Invoke-RestMethod -Uri "https://management.azure.com/subscriptions/$subscriptionId/resourceGroups/rg-multimodaldemo/providers/Microsoft.Purview/accounts/bankx-purview?api-version=2021-07-01" -Method Get -Headers @{Authorization="Bearer $token"}

$state = $response.properties.provisioningState
$color = if($state -eq 'Succeeded'){'Green'}elseif($state -eq 'Failed'){'Red'}else{'Yellow'}

Write-Host "`nPurview Account Status:" -ForegroundColor Cyan
Write-Host "  Name: $($response.name)" -ForegroundColor Gray
Write-Host "  State: $state" -ForegroundColor $color
Write-Host "  Location: $($response.location)" -ForegroundColor Gray
Write-Host "`nEndpoints:" -ForegroundColor Cyan
Write-Host "  Catalog: $($response.properties.endpoints.catalog)" -ForegroundColor Gray
Write-Host "  Scan: $($response.properties.endpoints.scan)" -ForegroundColor Gray

if ($state -eq 'Succeeded') {
    Write-Host "`n✅ Purview account is READY!" -ForegroundColor Green
    Write-Host "Next: Open Purview Governance Portal and assign roles" -ForegroundColor Yellow
} else {
    Write-Host "`n⏳ Still provisioning... Check again in 2-3 minutes" -ForegroundColor Yellow
}
