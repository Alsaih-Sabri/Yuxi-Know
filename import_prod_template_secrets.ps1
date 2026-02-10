
# Define Infisical path explicitly
$infisical = "C:\Users\Sabri\AppData\Roaming\npm\node_modules\@infisical\cli\bin\infisical.exe"

# Get .env content
$envFile = "$PSScriptRoot\.env.prod.template"
if (-not (Test-Path $envFile)) {
    Write-Error ".env file not found at $envFile"
    exit 1
}

$lines = Get-Content $envFile
foreach ($line in $lines) {
    if ($line -match "^\s*#" -or $line -match "^\s*$") { continue }
    
    # Split by first =
    $parts = $line.Split('=', 2)
    if ($parts.Count -ne 2) { continue }
    
    $key = $parts[0].Trim()
    $val = $parts[1].Trim()
    
    # Remove surrounding quotes
    if ($val.StartsWith("'") -and $val.EndsWith("'")) {
        $val = $val.Substring(1, $val.Length - 2)
    } elseif ($val.StartsWith('"') -and $val.EndsWith('"')) {
        $val = $val.Substring(1, $val.Length - 2)
    }
    
    # Check complexity
    $isComplex = $val -match "[\`"'\s\n]" -or $val.Length -gt 100
    
    if ($isComplex) {
        $tempFile = "$PSScriptRoot\temp_$key.txt"
        $val | Out-File -FilePath $tempFile -NoNewline -Encoding utf8
        
        Write-Host "Setting complex secret: $key (via file)"
        $arg = "$key=@$tempFile"
        & $infisical secrets set --env=prod $arg
        
        Remove-Item $tempFile -ErrorAction SilentlyContinue
    } else {
        Write-Host "Setting secret: $key"
        $arg = "$key=$val"
        & $infisical secrets set --env=prod $arg
    }
}
Write-Host "Done importing secrets."
