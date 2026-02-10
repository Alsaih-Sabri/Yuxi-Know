
<#
.SYNOPSIS
    Imports secrets from a local .env file to Infisical.
.DESCRIPTION
    This script reads a .env file line by line, parses the key-value pairs,
    and uses the Infisical CLI to set them in the specified environment.
    It handles complex values (like JSON or multiline strings) by using temporary files
    to avoid shell escaping issues.
.PARAMETER EnvFile
    The path to the .env file. Defaults to ".env" in the current directory.
.PARAMETER Environment
    The Infisical environment to upload to (e.g., "dev", "prod"). Defaults to "dev".
#>

param(
    [string]$EnvFile = ".env",
    [string]$Environment = "dev"
)

# 1. Check for Infisical CLI
$infisical = Get-Command infisical -ErrorAction SilentlyContinue
if (-not $infisical) {
    # Fallback check for common npm location if not in PATH
    $npmPath = "$env:APPDATA\npm\node_modules\@infisical\cli\bin\infisical.exe"
    if (Test-Path $npmPath) {
        $infisical = $npmPath
    } else {
        Write-Error "Infisical CLI not found. Please install it or ensure it is in your PATH."
        exit 1
    }
}
Write-Host "Using Infisical at: $infisical" -ForegroundColor Cyan

# 2. Check for .env file
if (-not (Test-Path $EnvFile)) {
    Write-Error "Environment file not found at $EnvFile"
    exit 1
}

Write-Host "Reading secrets from $EnvFile..." -ForegroundColor Cyan

# 3. Process the file
$lines = Get-Content $EnvFile
foreach ($line in $lines) {
    # Skip comments and empty lines
    if ($line -match "^\s*#" -or $line -match "^\s*$") { continue }
    
    # Split by first '=' only
    $parts = $line.Split('=', 2)
    if ($parts.Count -ne 2) { continue }
    
    $key = $parts[0].Trim()
    $val = $parts[1].Trim()
    
    # Remove surrounding quotes (single or double) if present
    if (($val.StartsWith("'") -and $val.EndsWith("'")) -or 
        ($val.StartsWith('"') -and $val.EndsWith('"'))) {
        $val = $val.Substring(1, $val.Length - 2)
    }
    
    # 4. Handle Upload
    # Check if value is "complex" (contains quotes, spaces, newlines, or is long)
    # Complex values are safer to upload via file input to avoid shell parsing errors
    $isComplex = $val -match "[\`"'\s\n]" -or $val.Length -gt 50
    
    if ($isComplex) {
        # Create a temp file for the value
        $tempFile = [System.IO.Path]::GetTempFileName()
        $val | Out-File -FilePath $tempFile -NoNewline -Encoding utf8
        
        Write-Host "  Uploading $key (via temp file due to complexity)..." -NoNewline
        
        # Construct command: infisical secrets set KEY=@/path/to/file
        $arg = "$key=@$tempFile"
        $proc = Start-Process -FilePath $infisical -ArgumentList "secrets", "set", "--env=$Environment", $arg -NoNewWindow -PassThru -Wait
        
        if ($proc.ExitCode -eq 0) {
            Write-Host " OK" -ForegroundColor Green
        } else {
            Write-Host " FAILED" -ForegroundColor Red
        }
        
        # Clean up temp file
        Remove-Item $tempFile -ErrorAction SilentlyContinue
    } else {
        # Simple values can be passed directly
        Write-Host "  Uploading $key..." -NoNewline
        
        $arg = "$key=$val"
        $proc = Start-Process -FilePath $infisical -ArgumentList "secrets", "set", "--env=$Environment", $arg -NoNewWindow -PassThru -Wait
        
        if ($proc.ExitCode -eq 0) {
            Write-Host " OK" -ForegroundColor Green
        } else {
            Write-Host " FAILED" -ForegroundColor Red
        }
    }
}

Write-Host "`nImport completed." -ForegroundColor Cyan
