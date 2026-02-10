# Infisical Self-Hosted Secrets Import Guide

This guide explains how to push your local `.env` secrets to your self-hosted Infisical instance using the provided PowerShell script.

## Prerequisites

1.  **Infisical CLI** installed.
2.  **PowerShell** (standard on Windows).
3.  A local `.env` file with your secrets.

## Step 1: Login to Self-Hosted Instance

Before running the script, you must authenticate with your specific domain.

```powershell
# Login pointing to your self-hosted URL
infisical login --domain https://infisical.webget.co.uk/
```

Follow the browser prompt to complete the login.

## Step 2: Run the Import Script

We have created a script `import_secrets.ps1` that automates the upload process. It handles complex values (like JSON keys) safely.

### standard usage (Default: reads `.env`, uploads to `dev`)

```powershell
./import_secrets.ps1
```

### verify the script execution

If you see execution policy errors, run it like this:

```powershell
pwsh -ExecutionPolicy Bypass -File import_secrets.ps1
```

### Custom Usage

You can specify a different file or environment if needed:

```powershell
./import_secrets.ps1 -EnvFile ".env.prod" -Environment "prod"
```

## Step 3: Verify the Secrets

Once the script finishes, you can check that the secrets were uploaded correctly:

```powershell
# List secrets in the dev environment
infisical export --env=dev
```

---

## How the Script Works

1.  **Locates CLI**: Finds where `infisical.exe` is installed on your system.
2.  **Reads .env**: Scans your `.env` file line-by-line.
3.  **Parses Config**: Ignores comments (`#`) and splits values at the first `=`.
4.  **Handles Complexity**:
    *   **Simple values** are uploaded directly.
    *   **Complex values** (containing spaces, quotes, or JSON) are written to a temporary file first, then uploaded using Infisical's file-input syntax (`KEY=@path/to/file`). This prevents shell errors with special characters.
5.  **Clean Up**: Deletes any temporary files created during the process.

## Deploying with Infisical & Docker Compose

We have updated `docker-compose.prod.yml` and `docker-compose.dokploy.yml` to support hybrid secret management.

1.  **Local Development**: If a `.env` file is present, services will load secrets from it.
2.  **Production / CI/CD**: If no `.env` file is present (because secrets are not in git), Docker will not crash. Instead, you should inject secrets directly using Infisical.

### How to Deploy (Production)

Instead of relying on a `.env` file on disk, use the `infisical run` command. This fetches your secrets from the vault and injects them into the Docker process.

```bash
# Example: Deploying the PROD environment
infisical run --env=prod -- docker compose -f docker-compose.prod.yml up -d
```

### Why this is better
*   **Security**: No secrets stored in files on the server.
*   **Version Control**: Your secrets are versioned in Infisical, not lost in a `.env` file on a random server.
*   **Reliability**: If you rotate a key in Infisical, the next deployment automatically picks it up.
