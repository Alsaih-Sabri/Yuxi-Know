# PowerShell script for Windows
Write-Host "🔐 Generating secure secrets..." -ForegroundColor Cyan

$SECRETS_DIR = "docker\secrets"
New-Item -ItemType Directory -Force -Path $SECRETS_DIR | Out-Null

function Generate-Secret {
    param([int]$Length = 32)
    $bytes = New-Object byte[] $Length
    [Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes)
}

Write-Host "Generating Neo4j password..."
Generate-Secret | Out-File -FilePath "$SECRETS_DIR\neo4j_password" -NoNewline -Encoding ASCII

Write-Host "Generating MinIO credentials..."
Generate-Secret | Out-File -FilePath "$SECRETS_DIR\minio_access_key" -NoNewline -Encoding ASCII
Generate-Secret | Out-File -FilePath "$SECRETS_DIR\minio_secret_key" -NoNewline -Encoding ASCII

Write-Host "Generating admin password..."
Generate-Secret | Out-File -FilePath "$SECRETS_DIR\admin_password" -NoNewline -Encoding ASCII

Write-Host "Generating JWT secret..."
$bytes = New-Object byte[] 32
[Security.Cryptography.RNGCryptoServiceProvider]::Create().GetBytes($bytes)
$hex = ($bytes | ForEach-Object { $_.ToString("x2") }) -join ''
$hex | Out-File -FilePath "$SECRETS_DIR\jwt_secret" -NoNewline -Encoding ASCII

Write-Host "✅ Secrets generated in $SECRETS_DIR" -ForegroundColor Green
Write-Host ""
Write-Host "⚠️  IMPORTANT: Store these secrets securely!" -ForegroundColor Yellow
Write-Host "📝 Add API keys manually:"
Write-Host "   echo 'your-key' | Out-File -FilePath '$SECRETS_DIR\openai_api_key' -NoNewline"
Write-Host "   echo 'your-key' | Out-File -FilePath '$SECRETS_DIR\siliconflow_api_key' -NoNewline"
Write-Host "   echo 'your-key' | Out-File -FilePath '$SECRETS_DIR\tavily_api_key' -NoNewline"
Write-Host ""
Write-Host "🔒 Generated passwords:" -ForegroundColor Green
Write-Host "   Neo4j: $(Get-Content $SECRETS_DIR\neo4j_password)"
Write-Host "   Admin: $(Get-Content $SECRETS_DIR\admin_password)"
Write-Host "   MinIO Access: $(Get-Content $SECRETS_DIR\minio_access_key)"
Write-Host "   MinIO Secret: $(Get-Content $SECRETS_DIR\minio_secret_key)"
Write-Host ""
Write-Host "⚠️  SAVE THESE PASSWORDS - They won't be shown again!" -ForegroundColor Yellow
