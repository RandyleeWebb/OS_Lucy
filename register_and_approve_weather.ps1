$manifestPath = "D:\lucy ecosystem\OS_Lucy's\plugins\weather\manifest.json"
$manifest = Get-Content -Raw $manifestPath

# Register plugin
$register = Invoke-RestMethod -Uri http://localhost:8005/plugins `
    -Method POST `
    -Headers @{ 'x-secret-key'='lucy-secret' } `
    -ContentType 'application/json' `
    -Body $manifest

Write-Host "REGISTER RESPONSE:" $register

# Approve plugin
$approve = Invoke-RestMethod -Uri http://localhost:8005/plugins/weather-plugin/approve `
    -Method POST `
    -Headers @{ 'x-secret-key'='lucy-secret' } `
    -ContentType 'application/json' `
    -Body '{}'

Write-Host "APPROVE RESPONSE:" $approve
