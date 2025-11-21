# ops/publish_to_repo.ps1
param(
  [string]$Message
)

# Always work from repo root
Set-Location -Path (Join-Path $PSScriptRoot "..")

# Default message if none provided
if (-not $Message -or $Message.Trim() -eq "") {
  $stamp = Get-Date -Format "yyyy-MM-dd_HHmm"
  $Message = Read-Host "Commit message [default: chore: dataset refresh $stamp]"
  if (-not $Message -or $Message.Trim() -eq "") {
    $Message = "chore: dataset refresh $stamp"
  }
}

# Stage intentional files only
git add ops\*.bat ops\*.ps1 scripts\**\*.py exports\index_*.json exports\embeddings.jsonl .gitignore
if (Test-Path README.md) { git add README.md }


# Commit & push
git commit -m "$Message"
if ($LASTEXITCODE -eq 0) {
  git push
  Write-Host "[OK] Published to GitHub with message: $Message"
} else {
  Write-Host "[INFO] Nothing to commit (working tree clean)."
}
